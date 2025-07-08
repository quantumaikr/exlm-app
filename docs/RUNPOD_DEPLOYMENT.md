# EXLM Platform RunPod 배포 가이드

RunPod에서 EXLM 플랫폼을 배포하는 방법을 안내합니다.

## 🚀 빠른 시작

### 1. GitHub Personal Access Token 생성

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token" 클릭
3. 권한 선택: `repo`, `read:org`
4. 토큰 복사 (한 번만 표시됨)

### 2. RunPod 인스턴스 설정

1. **GPU 인스턴스 선택**: RTX 3090, RTX 4090, A100 등
2. **포트 설정**: 다음 포트들을 Public으로 설정
   - `3000` (Frontend - 필수)
   - `8000` (Backend API - 필수)
   - `3001` (Grafana - 선택사항)
   - `9090` (Prometheus - 선택사항)
   - `5555` (Flower - 선택사항)

### 3. 자동 배포 스크립트 실행

```bash
# 배포 스크립트 다운로드 및 실행
curl -sSL https://raw.githubusercontent.com/quantumaikr/exlm-app/main/scripts/deploy-runpod.sh -o deploy-runpod.sh
chmod +x deploy-runpod.sh

# 배포 실행 (YOUR_GITHUB_TOKEN을 실제 토큰으로 교체)
./deploy-runpod.sh YOUR_GITHUB_TOKEN
```

## 📋 수동 배포 과정

### 1. 저장소 클론

```bash
# Personal Access Token 사용
git clone https://YOUR_TOKEN@github.com/quantumaikr/exlm-app.git
cd exlm-app
```

### 2. 환경 변수 설정

```bash
# .env 파일 생성
cat > .env << EOF
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123!
POSTGRES_DB=exlm_db
BUILD_ENV=gpu
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
GRAFANA_ADMIN_PASSWORD=admin123!
EOF
```

### 3. Docker 및 NVIDIA Container Toolkit 설치

```bash
# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Docker Compose 설치
curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# NVIDIA Container Toolkit 설치
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | tee /etc/apt/sources.list.d/nvidia-docker.list
apt-get update
apt-get install -y nvidia-docker2
systemctl restart docker
```

### 4. 서비스 시작

```bash
# GPU 환경으로 시작
docker-compose -f docker-compose.gpu.yml up -d

# 서비스 상태 확인
docker-compose -f docker-compose.gpu.yml ps
```

## 🔗 접속 정보

배포 완료 후 다음 URL로 접속할 수 있습니다:

- **Frontend**: `http://YOUR_RUNPOD_IP:3000`
- **Backend API**: `http://YOUR_RUNPOD_IP:8000`
- **API 문서**: `http://YOUR_RUNPOD_IP:8000/docs`
- **Grafana**: `http://YOUR_RUNPOD_IP:3001` (admin/admin123!)
- **Prometheus**: `http://YOUR_RUNPOD_IP:9090`
- **Flower**: `http://YOUR_RUNPOD_IP:5555`

## 🛠️ 관리 명령어

```bash
# 로그 확인
docker-compose -f docker-compose.gpu.yml logs -f

# 특정 서비스 로그 확인
docker-compose -f docker-compose.gpu.yml logs -f backend
docker-compose -f docker-compose.gpu.yml logs -f frontend

# 서비스 재시작
docker-compose -f docker-compose.gpu.yml restart

# 서비스 중지
docker-compose -f docker-compose.gpu.yml down

# 시스템 리소스 확인
docker stats
nvidia-smi
```

## 🔧 문제 해결

### GPU 인식 문제

```bash
# GPU 상태 확인
nvidia-smi

# Docker에서 GPU 사용 가능 여부 확인
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi
```

### 메모리 부족 문제

```bash
# 메모리 사용량 확인
free -h
docker stats

# 불필요한 컨테이너 정리
docker system prune -f
```

### 포트 접근 문제

```bash
# 포트 사용 상태 확인
netstat -tulpn | grep :3000
netstat -tulpn | grep :8000

# 방화벽 설정 확인
ufw status
```

## 📊 성능 모니터링

- **Grafana 대시보드**: 시스템 메트릭, API 성능, GPU 사용률
- **Prometheus**: 메트릭 수집 및 알림
- **Flower**: Celery 작업 큐 모니터링

## 🔒 보안 설정

1. **기본 비밀번호 변경**: `.env` 파일의 모든 비밀번호 변경
2. **방화벽 설정**: 필요한 포트만 열기
3. **SSL 인증서**: 프로덕션 환경에서는 HTTPS 설정 권장

## 📚 추가 문서

- [프로젝트 구조](PROJECT_STRUCTURE.md)
- [환경 설정](ENVIRONMENT_SETUP.md)
- [모니터링](monitoring.md)
- [API 문서](http://YOUR_RUNPOD_IP:8000/docs)
