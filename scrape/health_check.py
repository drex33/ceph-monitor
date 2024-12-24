# scrape/health_check.py

import requests

def main(active_mgr_ip, token_headers):
    health_url = f"https://{active_mgr_ip}:8443/api/health/minimal"

    # Ceph Health Check API 호출
    health_response = requests.get(health_url, headers=token_headers, verify=False)

    if health_response.status_code == 200:
        health_data = health_response.json()

        # Health 상태에서 check 리스트 추출
        health_status = health_data.get('health', {}).get('status', {})
        health_details = health_data.get('health', {}).get('checks', [])

        # health_detail check 리스트에서 위험도, 상태 추출하여 메시지로 변환
        ceph_severity = health_status

        ceph_detail = ""
        for health_detail in health_details:
            ceph_detail += f"{health_detail.get('summary', {}).get('message', 'No message')}\n\n"

        # Ceph 클러스터 상태 반환
        return ceph_severity, ceph_detail.strip()
    
    else:
        return None, None
