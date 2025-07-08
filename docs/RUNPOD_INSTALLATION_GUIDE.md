# RunPod EXLM 설치 완전 가이드

RunPod에서 EXLM 플랫폼을 설치하고 실행하는 완전한 단계별 가이드입니다.

## 📋 목차

1. [RunPod Pod 생성](#1-runpod-pod-생성)
2. [SSH 접속](#2-ssh-접속)
3. [자동 설치](#3-자동-설치)
4. [포트 설정](#4-포트-설정)
5. [접속 확인](#5-접속-확인)
6. [문제 해결](#6-문제-해결)
7. [관리 명령어](#7-관리-명령어)

## 1. RunPod Pod 생성

### 1.1 RunPod 계정 생성

1. [RunPod.io](https://runpod.io) 접속
2. GitHub 또는 Google 계정으로 로그인
3. 결제 정보 등록 (크레딧 또는 카드)

### 1.2 Pod 생성

1. **"Deploy"** 클릭
2. **Template 선택**: `RunPod PyTorch` 또는 `Ubuntu 22.04`
3. **GPU 선택**:
   - **최소**: RTX 4090 (24GB) - 7B 모델 학습 가능
   - **권장**: RTX 4090 (24GB) - 13B 모델 학습 가능
   - **고성능**: A100 (40GB) - 70B 모델 학습 가능
4. **Pod 설정**:
   - **Container Disk**: 50GB 이상
   - **Volume Disk**: 100GB 이상 (데이터 저장용)
   - **Docker Image**: `runpod/pytorch:2.1.1-py3.10-cuda11.8.0-devel-ubuntu22.04`
5. **"Deploy"** 클릭

### 1.3 Pod 시작 대기

- Pod 상태가 **"Running"**이 될 때까지 대기 (약 2-3분)
- **"Connect"** 버튼이 활성화되면 준비 완료

## 2. SSH 접속

### 2.1 SSH 키 설정 (선택사항)

```bash
# 로컬에서 SSH 키 생성
ssh-keygen -t ed25519 -C "your_email@example.com"

# 공개키를 RunPod에 등록
# RunPod 웹 콘솔 → Settings → SSH Keys → Add Key
```

### 2.2 SSH 접속

```bash
# RunPod 웹 콘솔에서 제공하는 SSH 명령어 사용
ssh root@[POD_IP] -p [SSH_PORT]

# 또는 SSH 키를 등록한 경우
ssh root@[POD_IP] -p [SSH_PORT] -i ~/.ssh/id_ed25519
```

### 2.3 접속 확인

```bash
# 시스템 정보 확인
uname -a
nvidia-smi  # GPU 확인
df -h       # 디스크 용량 확인
```

## 3. 자동 설치

### 3.1 원클릭 설치 (권장)

```bash
# 한 번의 명령어로 완전 자동 설치
curl -sSL https://raw.githubusercontent.com/quantumaikr/exlm-app/main/scripts/runpod-full-setup.sh | bash
```

**설치 과정 (약 10-15분)**:

- ✅ 시스템 업데이트
- ✅ Python 3.11, Node.js 18 설치
- ✅ PostgreSQL, Redis 설치 및 설정
- ✅ EXLM 프로젝트 클론
- ✅ 백엔드/프론트엔드 의존성 설치
- ✅ 데이터베이스 마이그레이션
- ✅ 서비스 자동 시작

### 3.2 설치 진행 상황 모니터링

```bash
# 실시간 로그 확인
tail -f /workspace/exlm-app/logs/backend.log
tail -f /workspace/exlm-app/logs/frontend.log

# 설치 상태 확인
cd /workspace/exlm-app
./status.sh
```

### 3.3 설치 완료 확인

```bash
# 서비스 상태 확인
ps aux | grep -E "(uvicorn|npm|celery)"

# 포트 사용 확인
netstat -tulpn | grep -E ':(3000|8000|5555)'

# API 응답 테스트
curl -s http://localhost:8000/api/v1/health
```

## 4. 포트 설정

### 4.1 RunPod 포트 설정

1. **RunPod 웹 콘솔** 접속
2. Pod 관리 페이지에서 **"Edit"** 클릭
3. **Ports** 섹션에서 다음 포트들을 **Public**으로 설정:

| 포트 | 서비스      | 설명            | 필수 여부 |
| ---- | ----------- | --------------- | --------- |
| 3000 | Frontend    | 웹 UI           | ✅ 필수   |
| 8000 | Backend API | API 서버        | ✅ 필수   |
| 5555 | Flower      | Celery 모니터링 | ⚪ 선택   |

4. **"Save"** 클릭

### 4.2 접속 URL 확인

포트 설정 완료 후 다음 URL로 접속:

```bash
# Frontend (웹 UI)
https://[POD_ID]-3000.proxy.runpod.net

# Backend API
https://[POD_ID]-8000.proxy.runpod.net

# API 문서
https://[POD_ID]-8000.proxy.runpod.net/docs

# Flower (선택사항)
https://[POD_ID]-5555.proxy.runpod.net
```

**POD_ID 확인 방법**: RunPod 웹 콘솔에서 Pod 이름 또는 Connect 정보에서 확인

## 5. 접속 확인

### 5.1 웹 UI 접속

1. 브라우저에서 `https://[POD_ID]-3000.proxy.runpod.net` 접속
2. **회원가입** 또는 **로그인**
3. 대시보드 확인

### 5.2 API 테스트

```bash
# API 상태 확인
curl -s https://[POD_ID]-8000.proxy.runpod.net/api/v1/health

# API 문서 접속
# 브라우저에서 https://[POD_ID]-8000.proxy.runpod.net/docs
```

### 5.3 GPU 확인

```bash
# GPU 상태 확인
nvidia-smi

# PyTorch GPU 인식 확인
cd /workspace/exlm-app/backend
source venv/bin/activate
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

## 6. 문제 해결

### 6.1 일반적인 문제들

#### 서비스가 시작되지 않음

```bash
# 상태 확인
cd /workspace/exlm-app
./status.sh

# 로그 확인
tail -f logs/backend.log
tail -f logs/frontend.log

# 서비스 재시작
./restart.sh
```

#### 포트 접근 안됨

```bash
# 포트 사용 상태 확인
netstat -tulpn | grep -E ':(3000|8000|5555)'

# RunPod 포트 설정 재확인
# → RunPod 웹 콘솔에서 포트가 Public으로 설정되었는지 확인
```

#### 의존성 충돌 오류

```bash
# 의존성 충돌 해결 스크립트 실행
cd /workspace/exlm-app/backend
chmod +x ../scripts/fix-dependencies.sh
../scripts/fix-dependencies.sh

# 수동 해결
source venv/bin/activate
pip uninstall -y transformers peft trl vllm accelerate pydantic fastapi openai anthropic
pip install "pydantic>=1.10.13,<2.0.0"
pip install "fastapi>=0.95.0,<0.105.0"
pip install "transformers>=4.36.0,<4.38.0"
pip install "vllm>=0.2.5,<0.3.0"
pip install -r requirements-gpu.txt
```

#### 데이터베이스 연결 문제

```bash
# PostgreSQL 상태 확인
systemctl status postgresql

# 데이터베이스 연결 테스트
sudo -u postgres psql -c "\l" | grep exlm_db

# Redis 연결 테스트
redis-cli ping
```

#### GPU 인식 문제

```bash
# NVIDIA 드라이버 확인
nvidia-smi

# CUDA 버전 확인
nvcc --version

# PyTorch CUDA 확인
cd /workspace/exlm-app/backend
source venv/bin/activate
python -c "import torch; print(torch.version.cuda)"
```

### 6.2 로그 분석

#### 에러 로그 찾기

```bash
# 모든 로그에서 에러 검색
grep -i error logs/*.log

# 특정 서비스 에러 검색
grep -i "error\|exception\|failed" logs/backend.log
```

#### 실시간 에러 모니터링

```bash
# 실시간으로 에러 로그만 확인
tail -f logs/*.log | grep -i --line-buffered "error\|exception\|failed"
```

### 6.3 성능 모니터링

#### 시스템 리소스

```bash
# CPU 및 메모리 사용률
htop

# 디스크 사용량
df -h

# GPU 사용량
watch -n 1 nvidia-smi
```

#### 애플리케이션 성능

```bash
# API 응답 테스트
curl -s http://localhost:8000/api/v1/health

# 프론트엔드 접속 테스트
curl -s http://localhost:3000 | head -10
```

## 7. 관리 명령어

### 7.1 서비스 관리

```bash
cd /workspace/exlm-app

# 모든 서비스 시작
./start-all.sh

# 모든 서비스 중지
./stop-all.sh

# 서비스 재시작
./restart.sh

# 서비스 상태 확인
./status.sh
```

### 7.2 개별 서비스 관리

```bash
# 백엔드만 시작
./start-backend.sh

# 프론트엔드만 시작
./start-frontend.sh

# Celery 워커만 시작
./start-celery.sh

# Flower만 시작
./start-flower.sh
```

### 7.3 로그 확인

```bash
# 실시간 백엔드 로그
tail -f logs/backend.log

# 실시간 프론트엔드 로그
tail -f logs/frontend.log

# 모든 로그 동시 확인
tail -f logs/*.log
```

### 7.4 설정 파일 관리

#### 백엔드 환경 변수

```bash
# 파일 위치
/workspace/exlm-app/backend/.env

# API 키 설정 (실제 키로 교체)
OPENAI_API_KEY=your_actual_openai_key
ANTHROPIC_API_KEY=your_actual_anthropic_key
GOOGLE_API_KEY=your_actual_google_key
HF_TOKEN=your_actual_huggingface_token
```

#### 프론트엔드 환경 변수

```bash
# 파일 위치
/workspace/exlm-app/frontend/.env.local

# 내용 (자동 설정됨)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### 7.5 업데이트 방법

```bash
cd /workspace/exlm-app

# 서비스 중지
./stop-all.sh

# 최신 코드 가져오기
git pull origin main

# 백엔드 의존성 업데이트 (필요시)
cd backend
source venv/bin/activate
pip install -r requirements-gpu.txt -q

# 프론트엔드 의존성 업데이트 (필요시)
cd ../frontend
npm install
npm run build

# 서비스 재시작
cd ..
./start-all.sh
```

## 🎉 성공 확인

설치가 성공적으로 완료되었다면:

1. ✅ 스크립트 실행 완료 메시지 확인
2. ✅ `./status.sh` 실행 시 모든 서비스 실행 중
3. ✅ `curl http://localhost:8000/api/v1/health` 응답 확인
4. ✅ RunPod 포트 설정 완료
5. ✅ 웹 브라우저에서 Frontend URL 접속 가능
6. ✅ GPU 인식 및 사용 가능

## 💡 팁

### 효율적인 사용법

1. **Screen/Tmux 사용**: SSH 연결이 끊어져도 서비스 유지
2. **로그 모니터링**: 개발 중에는 실시간 로그 확인
3. **API 키 설정**: 실제 사용 전에 반드시 API 키 설정
4. **정기적 백업**: 중요한 데이터는 정기적으로 백업

### 개발 모드

```bash
# 개발 중에는 개별 서비스 실행 권장
./start-backend.sh    # 터미널 1
./start-frontend.sh   # 터미널 2
./start-celery.sh     # 터미널 3
```

### 비용 최적화

1. **Spot 인스턴스 사용**: 70% 할인
2. **자동 종료 설정**: 사용하지 않을 때 자동 종료
3. **적절한 GPU 선택**: 작업에 맞는 GPU 선택

이제 RunPod에서 EXLM 플랫폼을 완전히 설치하고 사용할 수 있습니다! 🚀
