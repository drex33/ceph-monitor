import requests
import json
from datetime import datetime, timedelta

def print_with_timestamp(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def send_alert(webhook_url, bot_token, channel_id, ceph_severity, ceph_detail, more_info=None):
    # 메인함수에서 인증실패시 - 헬스체크 안함
    if more_info == "CONNECTION_ERR":
        payload = {
            "channel_id": f"{channel_id}",  # Mattermost Channel Token
            "props": {
                "attachments": [
                    {
                        "color": "#ff2d00",
                        "title": "# :pepe_tears: Gurum Ceph API Connection Fail",
                        "footer": "Powered by Jssong - LAB / Cloud Platform",
                        "fields": [
                            {
                                "short": "true",
                                "title": "Alert",
                                "value": "Connection Fail"
                            },
                            {
                                "short": "true",
                                "title": "Detail",
                                "value": "Check mgr and Network"
                            }
                        ]
                    }
                ]
            }
        }
    elif more_info == "CEPH_RESOLVED":
        payload = {
            "channel_id": f"{channel_id}",  # Mattermost Channel Token
            "props": {
                "attachments": [
                    {
                        "color": "#39a745",
                        "title": "# :pepe_good: Gurum Ceph Resolved",
                        "footer": "Powered by Jssong - LAB / Cloud Platform",
                        "fields": [
                            {
                                "short": "true",
                                "title": "Alert",
                                "value": "Ceph Cluster Resolved"
                            },
                            {
                                "short": "true",
                                "title": "Detail",
                                "value": "Ceph cluster recovered"
                            }
                        ]
                    }
                ]
            }
        }
    elif ceph_detail == "DAILY_STATUS":
        # more_info 딕셔너리에서 개별 값을 추출
        pg_info_str = more_info.get("pg_info_str", "No PG info")
        osd_up_count = more_info.get("osd_up_count", 0)
        osd_in_count = more_info.get("osd_in_count", 0)
        total_avail_gb = more_info.get("total_avail_gb", 0)
        total_gb = more_info.get("total_gb", 0)
        total_used_raw_gb = more_info.get("total_used_raw_gb", 0)
        used_percent = (total_used_raw_gb / total_gb) * 100

        payload = {
            "channel_id": f"{channel_id}",  # Mattermost Channel Token
            "props": {
                "attachments": [
                    {
                        "color": "#4585ed",
                        "title": "# :pepe_good: Gurum Ceph Daily Status",
                        "footer": "Powered by Jssong - LAB / Cloud Platform",
                        "fields": [
                            {
                                "short": "true",
                                "title": "Alert",
                                "value": "Ceph Cluster Daily Alert"
                            },
                            {
                                "short": "true",
                                "title": "Status",
                                "value": f"{ceph_severity}"
                            },
                            {
                                "short": "true",
                                "title": "PG Status",
                                "value": f"{pg_info_str}"
                            },
                            {
                                "short": "true",
                                "title": "Ceph OSD Status",
                                "value": f"{osd_up_count} UP / {osd_in_count} IN"
                            },
                            {
                                "short": "true",
                                "title": "Ceph Cluster Capacity",
                                "value": f"{int(total_avail_gb)} / {int(total_gb)} GB   ` {int(total_used_raw_gb)} GB USED - ({used_percent:.2f}%)`"
                            }
                        ]
                    }
                ]
            }
        }       
    else:
        # more_info 딕셔너리에서 개별 값을 추출
        pg_info_str = more_info.get("pg_info_str", "No PG info")
        osd_up_count = more_info.get("osd_up_count", 0)
        osd_in_count = more_info.get("osd_in_count", 0)
        total_avail_gb = more_info.get("total_avail_gb", 0)
        total_gb = more_info.get("total_gb", 0)
        total_used_raw_gb = more_info.get("total_used_raw_gb", 0)
        used_percent = (total_used_raw_gb / total_gb) * 100

        # Ceph 클러스터 상태 알림 생성
        payload = {
            "channel_id": f"{channel_id}",  # Mattermost Channel Token
            "props": {
                "attachments": [
                    {
                        "color": "#ff2d00",
                        "title": "# :pepe_tears: Gurum Ceph Cluster Alert",
                        "footer": "Powered by Jssong - LAB / Cloud Platform",
                        "fields": [
                            {
                                "short": "true",
                                "title": "Ceph Cluster Status",
                                "value": f"{ceph_severity}"
                            },
                            {
                                "short": "true",
                                "title": "Ceph Cluster Detail",
                                "value": f"{ceph_detail}"
                            },
                            {
                                "short": "true",
                                "title": "PG Status",
                                "value": f"{pg_info_str}"
                            },
                            {
                                "short": "true",
                                "title": "Ceph OSD Status",
                                "value": f"{osd_up_count} UP / {osd_in_count} IN"
                            },
                            {
                                "short": "true",
                                "title": "Ceph Cluster Capacity",
                                "value": f"{int(total_avail_gb)} / {int(total_gb)} GB   ` {int(total_used_raw_gb)} GB USED - ({used_percent:.2f}%)`"
                            }
                        ]
                    }
                ]
            }
        }

    # 웹훅 전송
    response = requests.post(
        url=webhook_url,
        verify=False,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bot_token}"  # Mattermost Bot Account Token
        },
        json=payload
    )
    
    if response.status_code == 201:
        print_with_timestamp("Alert sent successfully!")
    else:
        print_with_timestamp(f"Failed to send alert: {response.status_code}, {response.text}")
