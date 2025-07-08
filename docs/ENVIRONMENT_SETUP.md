# EXLM 환경 설정 가이드

## 개요

EXLM 플랫폼은 개발 환경(macOS/Linux)과 프로덕션 환경(GPU 서버) 모두에서 실행할 수 있도록 설계되었습니다.

## 환경별 특징

### 개발 환경 (CPU only)

- **대상**: macOS, Linux (GPU 없음)
- **용도**: 개발, 테스트, 기본 기능 확인
- **제한사항**:
  - 모델 학습 속도가 느림
  - vLLM 서빙 불가
  - 대용량 모델 처리 제한

### GPU 환경

- **대상**: NVIDIA GPU가 있는 Linux 서버
- **용도**: 실제 모델 학습, 고성능 서빙
- **장점**:
  - 빠른 모델 학습
  - vLLM 기반 고성능 서빙
  - 대용량 모델 처리 가능

## 개발 환경 설정 (macOS/Linux)

### 1. 사전 요구사항

```bash
# Docker 설치
# macOS: https://docs.docker.com/desktop/install/mac-install/
# Linux: https://docs.docker.com/engine/install/

# Node.js 18+ 설치
# macOS: brew install node
# Linux: https://nodejs.org/
```

### 2. 프로젝트 클론 및 설정

```bash
git clone <repository-url>
cd exlm

# 개발 환경 시작
make up-dev
```

### 3. 환경 확인

```bash
# 서비스 상태 확인
make status

# 로그 확인
make logs

# API 테스트
curl http://localhost:8000/api/v1/health
```

## GPU 환경 설정 (Linux)

### 1. 사전 요구사항

#### NVIDIA 드라이버 설치

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nvidia-driver-535  # 또는 최신 버전

# 확인
nvidia-smi
```

#### Docker 설치

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose
sudo usermod -aG docker $USER
newgrp docker
```

### 2. 자동 설정 스크립트 실행

```bash
# GPU 환경 설정 스크립트 실행
./scripts/setup-gpu.sh
```

### 3. 수동 설정 (스크립트 실패 시)

#### NVIDIA Container Toolkit 설치

```bash
# 저장소 추가
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# 패키지 설치
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

#### GPU 테스트

```bash
# GPU 컨테이너 테스트
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi
```

### 4. GPU 환경 시작

```bash
# GPU 환경 빌드 및 시작
make up-gpu

# 또는 직접 실행
docker-compose -f docker-compose.gpu.yml up -d
```

## 환경 변수 설정

### .env 파일 생성

```bash
# 프로젝트 루트에 .env 파일 생성
cat > .env << EOF
# 데이터베이스
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=exlm_db

# 빌드 환경 (dev 또는 gpu)
BUILD_ENV=dev

# API 키들 (필요시 설정)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key

# 추가 설정
LOG_LEVEL=INFO
UPLOAD_DIR=uploads
MODEL_CACHE_DIR=models
EOF
```

## 환경별 명령어

### 개발 환경

```bash
# 서비스 시작
make up-dev

# 빌드
make build-dev

# 테스트
make test-dev

# 로그 확인
make logs
```

### GPU 환경

```bash
# 서비스 시작
make up-gpu

# 빌드
make build-gpu

# 테스트
make test-gpu

# 로그 확인
make logs-gpu
```

### 공통 명령어

```bash
# 서비스 중지
make down

# 정리
make clean

# 상태 확인
make status
make status-gpu

# 쉘 접속
make shell-backend
make shell-frontend
```

## 문제 해결

### 일반적인 문제들

#### 1. PostgreSQL 연결 오류

```bash
# 볼륨 삭제 후 재시작
make clean
make up-dev  # 또는 make up-gpu
```

#### 2. GPU 컨테이너 시작 실패

```bash
# NVIDIA Container Toolkit 확인
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi

# Docker 재시작
sudo systemctl restart docker
```

#### 3. 메모리 부족 오류

```bash
# Docker 메모리 제한 증가
# Docker Desktop > Settings > Resources > Memory

# 또는 시스템 스왑 추가
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 4. 포트 충돌

```bash
# 사용 중인 포트 확인
sudo netstat -tulpn | grep :8000
sudo netstat -tulpn | grep :3000

# 다른 포트 사용
# docker-compose.yml에서 포트 변경
```

### 로그 확인

```bash
# 전체 로그
make logs

# 특정 서비스 로그
make backend-logs
make frontend-logs
make celery-logs
make flower-logs

# GPU 환경 로그
make logs-gpu
```

### 디버깅

```bash
# 컨테이너 쉘 접속
make shell-backend
make shell-frontend

# GPU 환경 쉘 접속
make shell-backend-gpu
make shell-frontend-gpu

# 서비스 재시작
make restart-backend
make restart-frontend
make restart-celery
```

## 성능 최적화

### GPU 환경 최적화

#### 1. GPU 메모리 설정

```bash
# .env 파일에 추가
GPU_MEMORY_UTILIZATION=0.9
CUDA_VISIBLE_DEVICES=0,1  # 특정 GPU만 사용
```

#### 2. 배치 크기 조정

```bash
# 학습 설정에서 배치 크기 조정
DEFAULT_BATCH_SIZE=8  # GPU 메모리에 따라 조정
```

#### 3. 모델 양자화

```bash
# vLLM 설정에서 양자화 활성화
QUANTIZATION=awq  # 또는 gptq
```

### 개발 환경 최적화

#### 1. 메모리 사용량 최소화

```bash
# 작은 모델 사용
DEFAULT_MODEL_NAME=microsoft/DialoGPT-small

# 배치 크기 줄이기
DEFAULT_BATCH_SIZE=1
```

#### 2. 캐시 활용

```bash
# 모델 캐시 디렉토리 설정
MODEL_CACHE_DIR=/path/to/cache
```

## 모니터링

### Prometheus 메트릭

- **URL**: http://localhost:9090
- **메트릭**: 시스템, 애플리케이션, 데이터베이스

### Grafana 대시보드

- **URL**: http://localhost:3001
- **계정**: admin/admin
- **대시보드**: 사전 구성된 대시보드 포함

### Flower (Celery 모니터링)

- **URL**: http://localhost:5555
- **기능**: 태스크 상태, 워커 모니터링

## 보안 고려사항

### 프로덕션 환경

#### 1. 환경 변수 보안

```bash
# 민감한 정보는 환경 변수로 관리
export SECRET_KEY="your-secret-key"
export DATABASE_URL="your-database-url"
```

#### 2. 네트워크 보안

```bash
# 방화벽 설정
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

#### 3. SSL/TLS 설정

```bash
# Nginx 리버스 프록시 설정
# Let's Encrypt SSL 인증서 적용
```

## 백업 및 복구

### 데이터베이스 백업

```bash
# 백업
docker-compose exec postgres pg_dump -U postgres exlm_db > backup.sql

# 복구
docker-compose exec -T postgres psql -U postgres exlm_db < backup.sql
```

### 모델 백업

```bash
# 모델 파일 백업
tar -czf models_backup.tar.gz models/

# 복구
tar -xzf models_backup.tar.gz
```

## 업데이트

### 코드 업데이트

```bash
# 코드 풀
git pull origin main

# 컨테이너 재빌드
make build-dev  # 또는 make build-gpu

# 서비스 재시작
make up-dev     # 또는 make up-gpu
```

### 의존성 업데이트

```bash
# requirements.txt 업데이트 후
docker-compose build --no-cache backend
docker-compose up -d
```
