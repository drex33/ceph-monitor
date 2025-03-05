import time
import json
import requests
from datetime import datetime, timedelta

def print_with_timestamp(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 바이트를 기가바이트로 변환하는 함수
def bytes_to_gigabytes(bytes_value):
    return bytes_value / (1024 ** 3)

# Ceph Health 상태를 조회하는 함수
def get_pg_status(active_mgr_ip, token_headers):
    health_url = f"https://{active_mgr_ip}:8443/api/health/minimal"

    # Ceph Health Check API Call
    health_response = requests.get(health_url, headers=token_headers, verify=False)
    print(f"DEBUG - pg status code - {health_response.status_code}")

    if health_response.status_code == 200:
        health_data = health_response.json()

        # PG 정보 추출
        pg_details = health_data.get('pg_info', {}).get('statuses', {})
        print_with_timestamp(f"DEBUG - {pg_details}")
        if pg_details:
            return ', '.join([f"{value} PGs - {key}" for key, value in pg_details.items()])
        else:
            return "No PG info available"
    else:
        return None

# Ceph Capacity 정보를 조회하는 함수
def get_cluster_capacity(active_mgr_ip, token_headers):
    capacity_url = f"https://{active_mgr_ip}:8443/api/health/get_cluster_capacity"

    # Ceph Capacity API Call
    capacity_response = requests.get(capacity_url, headers=token_headers, verify=False)
    print(f"DEBUG - capacity response code - {capacity_response.status_code}")

    if capacity_response.status_code == 200:
        capacity_data = capacity_response.json()

        # 클러스터 용량 정보 추출
        total_avail_gb = bytes_to_gigabytes(capacity_data.get('total_avail_bytes', 0))
        total_gb = bytes_to_gigabytes(capacity_data.get('total_bytes', 0))
        total_used_raw_gb = bytes_to_gigabytes(capacity_data.get('total_used_raw_bytes', 0))

        return total_avail_gb, total_gb, total_used_raw_gb
    else:
        return None, None, None

# OSD 상태를 조회하는 함수
def get_osd_status(active_mgr_ip, token_headers):
    osd_status_url = f"https://{active_mgr_ip}:8443/api/health/minimal"

    # Ceph Health Check API Call
    osd_status_response = requests.get(osd_status_url, headers=token_headers, verify=False)
    print(f"DEBUG - osd status code - {osd_status_response.status_code}")

    if osd_status_response.status_code == 200:
        osd_data = osd_status_response.json()
        osd_map = osd_data.get("osd_map", {}).get("osds", [])

        # OSD 상태 카운트
        osd_in_count = sum(1 for osd in osd_map if osd.get("in") == 1)
        osd_up_count = sum(1 for osd in osd_map if osd.get("up") == 1)

        return osd_in_count, osd_up_count
    else:
        return None, None

# Main 함수
def main(active_mgr_ip, token_headers):
    # PG 상태 정보 조회
    pg_info_str = get_pg_status(active_mgr_ip, token_headers)
    if not pg_info_str:
        return

    # Ceph 클러스터 용량 정보 조회
    total_avail_gb, total_gb, total_used_raw_gb = get_cluster_capacity(active_mgr_ip, token_headers)
    if total_avail_gb is None or total_gb is None or total_used_raw_gb is None:
        return

    # OSD 상태 정보 조회
    osd_in_count, osd_up_count = get_osd_status(active_mgr_ip, token_headers)
    if osd_in_count is None or osd_up_count is None:
        return

    return {
        "pg_info_str": pg_info_str,
        "total_avail_gb": total_avail_gb,
        "total_gb": total_gb,
        "total_used_raw_gb": total_used_raw_gb,
        "osd_in_count": osd_in_count,
        "osd_up_count": osd_up_count
    }

if __name__ == "__main__":
    main()