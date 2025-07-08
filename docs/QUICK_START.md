# EXLM Platform 빠른 시작 가이드

이 가이드는 EXLM 플랫폼을 가장 빠르게 시작할 수 있는 방법들을 소개합니다.

## 🚀 상황별 빠른 시작

### 1️⃣ RunPod + 소스코드 있음 (1분 배포) ⭐

**가장 빠른 방법**: 이미 소스코드가 있고 RunPod을 사용하는 경우

```bash
# 한 줄 명령어로 배포
cd /workspace/exlm-app && ./scripts/setup-runpod-local.sh && ./start-all.sh
```

**접속**: `http://YOUR_RUNPOD_IP:3000`

### 2️⃣ RunPod + 처음 시작 (3분 배포)

```bash
# 자동 배포 스크립트 다운로드 및 실행
curl -sSL https://raw.githubusercontent.com/quantumaikr/exlm-app/main/scripts/deploy-runpod-native.sh -o deploy.sh && chmod +x deploy.sh && ./deploy.sh
```

### 3️⃣ Docker 환경 (5분 배포)

```bash
git clone https://github.com/quantumaikr/exlm-app.git
cd exlm-app
docker-compose up -d
```

### 4️⃣ 로컬 개발 환경 (10분 설정)

```bash
# 백엔드
cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# 프론트엔드 (새 터미널)
cd frontend && npm install && npm run dev
```

## 📋 방법별 비교

| 방법                  | 시간 | 장점                             | 단점              | 추천 상황             |
| --------------------- | ---- | -------------------------------- | ----------------- | --------------------- |
| **RunPod + 소스코드** | 1분  | ⚡ 매우 빠름, 🔧 자동 관리       | 🌐 RunPod 필요    | GPU 테스트, 빠른 데모 |
| **RunPod + 처음**     | 3분  | 🚀 빠른 설치, 📦 완전 자동화     | 🌐 RunPod 필요    | 프로덕션 테스트       |
| **Docker**            | 5분  | 🐳 일관된 환경, 📊 모니터링 포함 | 💾 Docker 필요    | 로컬 개발, 서버 배포  |
| **로컬 개발**         | 10분 | 🔧 최대 제어, 🐛 디버깅 용이     | ⚙️ 수동 설정 많음 | 개발, 커스터마이징    |

## 🎯 목적별 추천

### 🏃‍♂️ 빠른 데모/테스트

→ **RunPod + 소스코드 있음**

### 🏭 프로덕션 환경 테스트

→ **RunPod + 처음 시작**

### 🏠 로컬 개발

→ **Docker 환경**

### 🔧 커스터마이징/개발

→ **로컬 개발 환경**

## 📍 접속 정보

배포 완료 후 다음 URL로 접속:

- **Frontend**: `http://localhost:3000` (또는 `http://YOUR_RUNPOD_IP:3000`)
- **Backend API**: `http://localhost:8000` (또는 `http://YOUR_RUNPOD_IP:8000`)
- **API 문서**: `http://localhost:8000/docs`
- **Flower (Celery)**: `http://localhost:5555`
- **Grafana**: `http://localhost:3001` (Docker 환경)

## 🛠️ 서비스 관리

### RunPod 네이티브 환경

```bash
# 서비스 시작
./start-all.sh

# 서비스 중지
./stop-all.sh

# 로그 확인
tail -f logs/backend.log
```

### Docker 환경

```bash
# 서비스 시작
docker-compose up -d

# 서비스 중지
docker-compose down

# 로그 확인
docker-compose logs -f
```

## 🔧 필수 포트 설정

### RunPod 사용 시

다음 포트들을 **Public**으로 설정:

- `3000` - Frontend (필수)
- `8000` - Backend API (필수)
- `5555` - Flower (선택사항)

### 로컬 환경

기본적으로 localhost에서 접근 가능

## ⚡ 성능 최적화 팁

### GPU 환경

- **GPU 메모리**: 최소 8GB 권장 (모델 학습용)
- **시스템 메모리**: 최소 16GB 권장
- **스토리지**: SSD 권장, 최소 50GB

### CPU 환경

- **메모리**: 최소 8GB
- **CPU**: 4코어 이상 권장

## 🆘 빠른 문제 해결

### 포트 접근 안됨

```bash
# 포트 사용 상태 확인
netstat -tulpn | grep -E ':(3000|8000)'

# 방화벽 확인 (Ubuntu)
ufw status
```

### 서비스 시작 안됨

```bash
# 프로세스 확인
ps aux | grep -E "(uvicorn|npm|celery)"

# 로그 확인
tail -f logs/backend.log
tail -f logs/frontend.log
```

### 메모리 부족

```bash
# 메모리 사용량 확인
free -h

# 불필요한 프로세스 종료
./stop-all.sh
```

## 📚 다음 단계

1. **기본 사용법**: [사용 방법 가이드](../README.md#사용-방법)
2. **상세 설정**: [환경 설정 가이드](ENVIRONMENT_SETUP.md)
3. **배포 옵션**: [RunPod 배포 가이드](RUNPOD_NATIVE_DEPLOYMENT.md)
4. **문제 해결**: [GitHub Token 가이드](GITHUB_TOKEN_GUIDE.md)

## 🎉 성공!

축하합니다! EXLM 플랫폼이 성공적으로 실행되었습니다.

이제 다음을 시도해보세요:

1. 🌐 웹 UI 접속 (`http://localhost:3000`)
2. 📊 API 문서 확인 (`http://localhost:8000/docs`)
3. 🔧 첫 번째 프로젝트 생성
4. 🤖 모델 학습 파이프라인 설계
