
# ceph-monitor
=======
## Ceph Monitor
24/10/30 개발,테스트 완료 도커 이미지 빌드완료


24/11/06 세부정보 조회 API - 전부 다 CEPH API 로 로직 수정 / 일일 알람 로직 추가 / 전사 인프라 배포완료 


24/11/11 일일알람 로직 추가 (매일 오전 09시에 일일알람 전송)


24/12/11 Ceph active mgr 자동추적 모듈 추가, 중복된 코드 병합 및 class 로 메인함수 리팩토링 / 커넥션에러, 인증토큰에러 알람 추가 / 하드코딩된 변수 (mgr ip, 인증정보) conf 파일로 개별 분리


24/12/24 ver3 브랜치 생성 및 테스트중 - 리팩터링된 코드에서 중복된 코드 삭제 / MGR 검출은 ensure_mgr 모듈에서 검증, 검색하도록 변경 / scrape.auth 메인함수로 통합 / 각 알람 전송모듈 예외처리


24/12/27 만료 토큰 갱신함수 추가 / 기존 모듈 통폐합 및 리팩터링 / 전사 인프라 업데이트 완료

스토리지 모니터링위하여 기존 존재하는 모니터링 툴 (Prometheus, Grafana ..etc) 사용하였으나 mattermost integration 의 부재, 원하는 정보 활용불가하여, Ceph API 이용하여 직접 개발
<br>

## Flow Chart
![image](https://github.com/user-attachments/assets/417f5600-a038-43ae-9204-46bfc3a66a1c)

1. 인증 모듈에서 토큰요청 / 토큰 수신
2. 토큰 헤더 탑재하여 헬스체크 API 호출
3. HEALTH_OK 일 시 추가 작동없이 SLEEP
4. HEALTH_WARN or ERR 일 시 추가 정보 조회
5. 웹훅 모듈에 추가정보 전달 / Alert 전송
<br>

## 기능
- 헬스체크 인터벌의 경우 1분

- 전달된 Alert 의 경우 한시간의 대기시간을 갖는다. 이후에도 조치 안됬을 시, 재 알람

- 조치 시 Resolved 알람 전송됨

- 로그의 경우 docker logs 로 확인
