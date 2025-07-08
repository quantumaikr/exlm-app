# EXLM Platform RunPod 네이티브 배포 가이드

Docker를 사용할 수 없는 RunPod 환경에서 EXLM 플랫폼을 직접 설치하는 방법을 안내합니다.

## 🚀 자동 배포 (권장)

### 방법 1: 소스코드가 이미 있는 경우 (가장 간단) ⭐

이미 `git pull` 또는 다른 방법으로 소스코드를 가져온 경우:

```bash
# EXLM 프로젝트 루트 디렉토리에서 실행
cd /path/to/exlm-app
chmod +x scripts/setup-runpod-local.sh
./scripts/setup-runpod-local.sh

# 또는 스크립트 직접 다운로드
curl -sSL https://raw.githubusercontent.com/quantumaikr/exlm-app/main/scripts/setup-runpod-local.sh -o setup.sh
chmod +x setup.sh
./setup.sh
```

**장점:**

- ✅ GitHub Token 불필요
- ⚡ 저장소 클론 과정 생략으로 빠른 설치
- 🛠️ 자동 서비스 관리 스크립트 생성

### 방법 2: 저장소부터 새로 시작하는 경우

#### 2-1. GitHub Personal Access Token 준비 (선택사항)

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token" 클릭
3. 권한: `repo`, `read:org` 선택
4. 토큰 복사

#### 2-2. 자동 배포 스크립트 실행

```bash
# 스크립트 다운로드
curl -sSL https://raw.githubusercontent.com/quantumaikr/exlm-app/main/scripts/deploy-runpod-native.sh -o deploy-runpod-native.sh
chmod +x deploy-runpod-native.sh

# 토큰과 함께 배포 (권장)
./deploy-runpod-native.sh YOUR_GITHUB_TOKEN

# 또는 토큰 없이 배포 (Public 저장소인 경우)
./deploy-runpod-native.sh
# 프롬프트에서 'y' 입력하여 계속 진행
```

## 📋 수동 배포 과정

### 1. 시스템 준비

```bash
# 시스템 업데이트
apt-get update -y
apt-get install -y git curl wget build-essential software-properties-common

# Python 3.11 설치
add-apt-repository ppa:deadsnakes/ppa -y
apt-get update
apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Node.js 18 설치
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt-get install -y nodejs

# PostgreSQL 설치
apt-get install -y postgresql postgresql-contrib
service postgresql start

# Redis 설치
apt-get install -y redis-server
service redis-server start
```

### 2. 저장소 클론

```bash
# Personal Access Token 사용
git clone https://YOUR_TOKEN@github.com/quantumaikr/exlm-app.git
cd exlm-app
```

### 3. 데이터베이스 설정

```bash
# PostgreSQL 사용자 및 데이터베이스 생성
sudo -u postgres psql -c "CREATE USER exlm_user WITH PASSWORD 'exlm_password';"
sudo -u postgres psql -c "CREATE DATABASE exlm_db OWNER exlm_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE exlm_db TO exlm_user;"
```

### 4. 백엔드 설정

```bash
cd backend

# Python 가상환경 생성
python3.11 -m venv venv
source venv/bin/activate

# 의존성 설치 (GPU 환경)
pip install -r requirements-gpu.txt
# 또는 CPU 환경
# pip install -r requirements.txt

# 환경 변수 설정
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://exlm_user:exlm_password@localhost:5432/exlm_db
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
BUILD_ENV=gpu
DEBUG=True
EOF

# 데이터베이스 마이그레이션
alembic upgrade head
```

### 5. 프론트엔드 설정

```bash
cd ../frontend

# 의존성 설치
npm install

# 빌드
npm run build
```

### 6. 서비스 시작

```bash
cd ..

# 로그 디렉토리 생성
mkdir -p logs

# 백엔드 시작 (백그라운드)
cd backend
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > ../logs/backend.log 2>&1 &

# 프론트엔드 시작 (백그라운드)
cd ../frontend
nohup npm run start > ../logs/frontend.log 2>&1 &

# Celery 워커 시작 (백그라운드)
cd ../backend
source venv/bin/activate
nohup celery -A app.core.celery_app worker --loglevel=info > ../logs/celery.log 2>&1 &

# Flower 시작 (백그라운드)
nohup celery -A app.core.celery_app flower --port=5555 > ../logs/flower.log 2>&1 &
```

## 🔗 접속 정보

배포 완료 후 다음 URL로 접속:

- **Frontend**: `http://YOUR_RUNPOD_IP:3000`
- **Backend API**: `http://YOUR_RUNPOD_IP:8000`
- **API 문서**: `http://YOUR_RUNPOD_IP:8000/docs`
- **Flower**: `http://YOUR_RUNPOD_IP:5555`

## 🛠️ 관리 명령어

### 자동 생성된 스크립트 사용 (권장) ⭐

로컬 설치 스크립트를 사용한 경우, 편리한 관리 스크립트들이 자동 생성됩니다:

```bash
# 모든 서비스 한 번에 시작
./start-all.sh

# 개별 서비스 시작
./start-backend.sh    # 백엔드만
./start-frontend.sh   # 프론트엔드만
./start-celery.sh     # Celery 워커만
./start-flower.sh     # Flower만

# 모든 서비스 중지
./stop-all.sh
```

### 수동 서비스 관리

#### 서비스 상태 확인

```bash
# 실행 중인 프로세스 확인
ps aux | grep -E "(uvicorn|npm|celery)" | grep -v grep

# 포트 사용 상태 확인
netstat -tulpn | grep -E ':(3000|8000|5555)'
```

#### 로그 확인

```bash
# 백엔드 로그
tail -f logs/backend.log

# 프론트엔드 로그
tail -f logs/frontend.log

# Celery 로그
tail -f logs/celery.log

# Flower 로그
tail -f logs/flower.log
```

#### 서비스 재시작

```bash
# 모든 서비스 중지
pkill -f "uvicorn|npm|celery"

# 개별 서비스 재시작
# 백엔드
cd backend && source venv/bin/activate && nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > ../logs/backend.log 2>&1 &

# 프론트엔드
cd frontend && nohup npm run start > ../logs/frontend.log 2>&1 &

# Celery
cd backend && source venv/bin/activate && nohup celery -A app.core.celery_app worker --loglevel=info > ../logs/celery.log 2>&1 &
```

## 🔧 문제 해결

### 포트 충돌 문제

```bash
# 포트 사용 중인 프로세스 확인
lsof -i :8000
lsof -i :3000

# 프로세스 종료
kill -9 PID_NUMBER
```

### 데이터베이스 연결 문제

```bash
# PostgreSQL 상태 확인
service postgresql status

# 데이터베이스 연결 테스트
psql -U exlm_user -d exlm_db -h localhost
```

### Redis 연결 문제

```bash
# Redis 상태 확인
service redis-server status

# Redis 연결 테스트
redis-cli ping
```

### GPU 관련 문제

```bash
# GPU 상태 확인
nvidia-smi

# CUDA 버전 확인
nvcc --version

# PyTorch GPU 지원 확인
cd backend && source venv/bin/activate
python -c "import torch; print(torch.cuda.is_available())"
```

## 📊 성능 모니터링

### 시스템 리소스 모니터링

```bash
# CPU 및 메모리 사용률
htop

# GPU 사용률 (GPU 환경)
nvidia-smi -l 1

# 디스크 사용량
df -h
```

### 애플리케이션 모니터링

- **Flower**: Celery 작업 큐 모니터링 (`http://YOUR_RUNPOD_IP:5555`)
- **API 문서**: FastAPI 자동 문서 (`http://YOUR_RUNPOD_IP:8000/docs`)

## 🔒 보안 설정

### 기본 보안 설정

```bash
# 방화벽 설정 (필요한 포트만 열기)
ufw allow 22    # SSH
ufw allow 3000  # Frontend
ufw allow 8000  # Backend API
ufw allow 5555  # Flower (선택사항)
ufw enable
```

### 환경 변수 보안

1. `.env` 파일의 모든 기본 비밀번호 변경
2. 실제 API 키로 교체
3. 프로덕션 환경에서는 `DEBUG=False` 설정

## 📚 추가 정보

- **포트 설정**: RunPod에서 3000, 8000, 5555 포트를 Public으로 설정
- **GPU 지원**: NVIDIA GPU가 있는 경우 자동으로 GPU 버전 설치
- **확장성**: 필요에 따라 여러 워커 프로세스 실행 가능
- **모니터링**: Flower를 통한 실시간 작업 모니터링
