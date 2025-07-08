# 모니터링 가이드

## 개요

exlm 플랫폼은 Prometheus와 Grafana를 사용하여 시스템 모니터링을 제공합니다.

## 구성 요소

### 1. Prometheus
- **URL**: http://localhost:9090
- **역할**: 메트릭 수집 및 저장
- **수집 주기**: 15초

### 2. Grafana
- **URL**: http://localhost:3001
- **기본 계정**: admin / admin
- **역할**: 메트릭 시각화 및 대시보드

### 3. Exporters
- **Node Exporter**: 시스템 메트릭 (CPU, 메모리, 디스크)
- **Postgres Exporter**: PostgreSQL 데이터베이스 메트릭
- **Redis Exporter**: Redis 캐시 메트릭

## 주요 메트릭

### HTTP 메트릭
- `http_requests_total`: 총 HTTP 요청 수
- `http_request_duration_seconds`: HTTP 요청 지연 시간
- `http_requests_inprogress`: 진행 중인 HTTP 요청 수

### 시스템 메트릭
- `cpu_usage_percent`: CPU 사용률
- `memory_usage_percent`: 메모리 사용률
- `disk_usage_percent`: 디스크 사용률

### 애플리케이션 메트릭
- `active_users`: 활성 사용자 수
- `active_websocket_connections`: 활성 WebSocket 연결 수
- `model_training_total`: 모델 학습 작업 수
- `dataset_processing_total`: 데이터셋 처리 작업 수

### 에러 메트릭
- `error_count`: 에러 발생 수 (타입별)

### 캐시 메트릭
- `cache_hits`: 캐시 히트 수
- `cache_misses`: 캐시 미스 수

### Celery 메트릭
- `celery_tasks_pending`: 대기 중인 Celery 작업 수
- `celery_tasks_active`: 실행 중인 Celery 작업 수

## Health Check 엔드포인트

### 1. 기본 Health Check
```bash
GET /api/v1/health
```
응답:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-07T10:00:00.000Z",
  "version": "0.1.0",
  "environment": "development",
  "service": "exlm-backend"
}
```

### 2. Readiness Check
```bash
GET /api/v1/health/ready
```
모든 의존성(DB, Redis, 디스크, 메모리)의 상태를 확인합니다.

### 3. Liveness Check
```bash
GET /api/v1/health/live
```
애플리케이션이 실행 중인지 확인합니다.

### 4. System Metrics
```bash
GET /api/v1/health/metrics
```
현재 시스템 메트릭을 JSON 형식으로 반환합니다.

## Grafana 대시보드

기본 대시보드는 다음 패널을 포함합니다:

1. **시스템 상태**
   - CPU 사용률 게이지
   - 메모리 사용률 게이지
   - 활성 사용자 수
   - WebSocket 연결 수

2. **HTTP 트래픽**
   - 요청 속도 (RPS)
   - 응답 시간 백분위수 (p50, p95, p99)

3. **작업 모니터링**
   - 모델 학습 작업 상태
   - 데이터셋 처리 작업 상태

4. **에러 모니터링**
   - 에러 발생률
   - 에러 타입별 분포

## 알람 설정

Prometheus AlertManager를 통해 다음과 같은 알람을 설정할 수 있습니다:

1. **높은 CPU 사용률**: CPU > 80% for 5분
2. **높은 메모리 사용률**: Memory > 90% for 5분
3. **디스크 공간 부족**: Disk > 90%
4. **높은 에러율**: Error rate > 5% for 5분
5. **서비스 다운**: Health check 실패

## 모니터링 시작하기

1. Docker Compose로 모든 서비스 시작:
```bash
docker-compose up -d
```

2. Grafana 접속:
```
http://localhost:3001
ID: admin
PW: admin
```

3. Prometheus 확인:
```
http://localhost:9090
```

4. 메트릭 엔드포인트 확인:
```
http://localhost:8000/metrics
```

## 트러블슈팅

### Grafana에 데이터가 표시되지 않는 경우
1. Prometheus가 실행 중인지 확인
2. Prometheus targets 페이지에서 모든 타겟이 UP 상태인지 확인
3. Grafana 데이터소스 설정 확인

### 메트릭이 수집되지 않는 경우
1. 백엔드 애플리케이션이 실행 중인지 확인
2. `/metrics` 엔드포인트가 접근 가능한지 확인
3. Prometheus 설정 파일 확인

### 높은 메모리 사용률
1. 불필요한 로그 레벨 조정
2. 캐시 크기 제한 설정
3. 오래된 메트릭 데이터 정리