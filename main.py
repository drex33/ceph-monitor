import time
import schedule
import scrape.health_check
import scrape.details
import webhook.alert_webhook
import requests
import urllib3
import configparser
import jwt
from datetime import datetime, timedelta

# TLS 인증 무시 (Ceph 인증서)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CephMonitor:
    def __init__(self, mgr_ips, username, password, webhook_url, bot_token, channel_id):
        self.mgr_ips = mgr_ips
        self.username = username
        self.password = password
        self.active_mgr = None
        self.last_alert_times = {
            "CONNECTION_ERR": None,
            "CLUSTER_ALERT": None,
            "DAILY_STATUS": None
        }
        self.last_severity = None
        self.token_headers = None
        self.webhook_url = webhook_url
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.retries = 0
        self.max_retries = 3
        self.last_retry_time = None
        self.retry_wait_time = timedelta(minutes=60)

    def print_with_timestamp(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    # MGR IP 자동 추적함수
    def ensure_active_mgr(self):
        current_time = datetime.now()

        # 대기 시간이 지나지 않았다면 재시도 중단
        if self.last_retry_time and current_time - self.last_retry_time < self.retry_wait_time:
            self.print_with_timestamp("Retry interval not met. Skipping MGR discovery.")
            return

        # 대기 시간이 지난 경우 retries 초기화
        if self.last_retry_time and current_time - self.last_retry_time >= self.retry_wait_time:
            self.retries = 0  # 재시도 횟수 초기화
            self.print_with_timestamp("Retry wait time passed. Resetting retries.")

        # 활성 MGR 찾기 로직
        while not self.active_mgr and self.retries < self.max_retries:
            self.print_with_timestamp(f"Attempting to find active MGR (Attempt {self.retries + 1}/{self.max_retries})...")
            self.active_mgr = self.find_active_mgr()
            self.retries += 1

            if self.active_mgr:
                self.print_with_timestamp(f"Active MGR found: {self.active_mgr['mgr_ip']}")
                self.retries = 0  # 성공 시 재시도 횟수 초기화
                self.last_retry_time = None
                return

        # 실패한 경우
        if not self.active_mgr:
            self.print_with_timestamp("Failed to find an active MGR after max retries.")
            self.last_retry_time = current_time  # 마지막 실패 시간 기록
            self.send_alert("", "", "CONNECTION_ERR")


    # Active MGR IP 찾는 함수
    def find_active_mgr(self):
        headers = {
            "Accept": "application/vnd.ceph.api.v1.0+json",
            "Content-Type": "application/json"
        }
        for ip in self.mgr_ips:
            try:
                auth_url = f"https://{ip}:8443/api/auth"
                auth_payload = {
                    "username": self.username,
                    "password": self.password
                }
                response = requests.post(auth_url, json=auth_payload, headers=headers, verify=False)
                if response.status_code == 201:
                    token = response.json().get('token')
                    self.active_mgr = {
                        "mgr_ip": ip,
                        "token": token
                    }
                    return self.active_mgr
            except requests.exceptions.RequestException as e:
                self.print_with_timestamp(f"Failed to connect to {ip}: {e}")
        return None

    # 인증 토큰 발행 함수
    def get_token_headers(self):
        if not self.active_mgr:
            self.ensure_active_mgr()
            if not self.active_mgr:
                return

        if self.active_mgr:
            self.get_token_headers_expired()

    def get_token_headers_expired(self):
        decode = jwt.decode(self.active_mgr['token'], options={"verify_signature" : False})
        exp_time = datetime.fromtimestamp(decode.get("exp")) - timedelta(hours=1)
        current_time = datetime.now()
        self.print_with_timestamp(f"DEBUG LOG (Current Time Value) - {current_time}")
        self.print_with_timestamp(f"DEBUG LOG (Expired Time Value) - {exp_time}")
        if current_time > exp_time:
            self.print_with_timestamp("Renewal Expired Token..")
            headers = {
                "Accept": "application/vnd.ceph.api.v1.0+json",
                "Content-Type": "application/json"
            }
            auth_url = f"https://{self.active_mgr['mgr_ip']}:8443/api/auth"
            auth_payload = {
                "username": self.username,
                "password": self.password
            }
            response = requests.post(auth_url, json=auth_payload, headers=headers, verify=False)

            try:
                if response.status_code == 201:
                    api_auth_token = response.json().get('token')

                    self.token_headers = {
                        "Authorization": f"Bearer {api_auth_token}",
                        "Accept": "application/vnd.ceph.api.v1.0+json"
                    }

            except requests.exceptions.RequestException as e:
                    self.print_with_timestamp(f"Token Authentication Failed - {e}") 
        else:
            self.token_headers = {
                "Authorization": f"Bearer {self.active_mgr['token']}",
                "Accept": "application/vnd.ceph.api.v1.0+json"
            }

    def send_alert(self, ceph_severity, ceph_detail, more_info=None):
        if ceph_detail == "CONNECTION_ERR":
            alert_type = "CONNECTION_ERR"
        elif ceph_detail == "DAILY_STATUS":
            alert_type = "DAILY_STATUS"
        else:
            alert_type = "CLUSTER_ALERT"

        last_alert_time = self.last_alert_times.get(alert_type)
        current_time = datetime.now()

        if last_alert_time and current_time - last_alert_time < timedelta(hours=1) and alert_type != "DAILY_STATUS":
            self.print_with_timestamp(f"Alert for {alert_type} sent recently. Skipping alert.")
            return

        webhook.alert_webhook.send_alert(
            self.webhook_url,
            self.bot_token,
            self.channel_id,
            ceph_severity,
            ceph_detail,
            more_info
        )

        self.last_alert_times[alert_type] = current_time
        
        if alert_type != "DAILY_STATUS":
            self.print_with_timestamp(f"Alert sent for {alert_type} and updated last alert time.")

    def send_daily_status_alert(self):
        # 주말 일일알람 제외 로직 추가 
        today = datetime.now()
        if today.weekday() in [5, 6]:  # 5: 토요일, 6: 일요일
            self.print_with_timestamp("Today is a weekend. Skipping daily status alert.")
            return

        if not self.active_mgr:
            self.ensure_active_mgr()
            if not self.active_mgr:
                self.print_with_timestamp("Failed to send daily status. No active MGR")

#        if self.active_mgr:
#            self.get_token_headers()   # 토큰 호출 중복 가능성 위해 테스트 24.12.26
        
        try:
            if self.active_mgr:
                more_info = scrape.details.main(self.active_mgr['mgr_ip'], self.token_headers)
#           ceph_severity = scrape.health_check.main(self.active_mgr['mgr_ip'], self.token_headers)
                self.print_with_timestamp("Sending daily status alert...")
                self.send_alert(self.last_severity, "DAILY_STATUS", more_info)

        except requests.exceptions.RequestException as e:
            # 연결 실패 시 활성 MGR 상태 초기화 및 재탐색
            self.print_with_timestamp(f"Connection error: {e}. Resetting active MGR and retrying.")
            self.active_mgr = None
            self.ensure_active_mgr()
            
        except Exception as e:
            self.print_with_timestamp(f"Unexpected error in monitor: {e}")

    def monitor(self):
        if not self.active_mgr:
            self.ensure_active_mgr()
            if not self.active_mgr:
                self.print_with_timestamp("Active MGR Not Found Skipping Alert")
                return
            
        if self.active_mgr:
            self.get_token_headers()
#            self.print_with_timestamp(f"DEBUG - {self.token_headers}") // 토큰 에러 시 디버깅용

        try:
            ceph_severity, ceph_detail = scrape.health_check.main(self.active_mgr['mgr_ip'], self.token_headers)

            if ceph_severity != self.last_severity:
                self.print_with_timestamp("Cluster status changed. Resetting alert times.")
                self.last_alert_times["CLUSTER_ALERT"] = None

                if ceph_severity == "HEALTH_OK" and self.last_severity in ["HEALTH_WARN", "HEALTH_ERR"]:
                    self.send_alert("", "", more_info='CEPH_RESOLVED')
                    self.print_with_timestamp("Ceph Cluster resolved - Send Resolved Alert")

                self.last_severity = ceph_severity

            if ceph_severity in ["HEALTH_WARN", "HEALTH_ERR"]:
                self.print_with_timestamp("Ceph Cluster Something Wrong. Collecting more info.")
                more_info = scrape.details.main(self.active_mgr['mgr_ip'], self.token_headers)
                self.send_alert(ceph_severity, ceph_detail, more_info)
                
            elif ceph_severity == "HEALTH_OK":
                self.print_with_timestamp("Ceph HEALTH OK - Skip Alert")

        except requests.exceptions.RequestException as e:
            # 연결 실패 시 활성 MGR 상태 초기화 및 재탐색
            self.print_with_timestamp(f"Connection error: {e}. Resetting active MGR and retrying.")
            self.active_mgr = None
            self.ensure_active_mgr()
        except Exception as e:
            self.print_with_timestamp(f"Unexpected error in monitor: {e}")
    
def main():
    config = configparser.ConfigParser()
    config.read('ceph_monitor.conf')

    mgr_ips = config.get('ceph', 'mgr_ips').split(',')
    username = config.get('auth', 'username')
    password = config.get('auth', 'password')
    webhook_url = config.get('webhook', 'webhook_url')
    bot_token = config.get('webhook', 'bot_token')
    channel_id = config.get('webhook', 'channel_id')

    monitor = CephMonitor(mgr_ips, username, password, webhook_url, bot_token, channel_id)
    schedule.every(30).seconds.do(monitor.monitor)
    schedule.every().day.at("09:00").do(monitor.send_daily_status_alert)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
