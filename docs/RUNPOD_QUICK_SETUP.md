# RunPod EXLM 빠른 설치 가이드

RunPod 깡통 Ubuntu에서 **한 번의 명령어**로 EXLM 플랫폼을 완전 자동 설치하는 가이드입니다.

## 🚀 1분 설치 (원라이너)

### SSH 접속 후 바로 실행

```bash
curl -sSL https://raw.githubusercontent.com/quantumaikr/exlm-app/main/scripts/runpod-full-setup.sh | bash
```

**끝!** 이 명령어 하나로 모든 설치가 완료됩니다.

## 📋 설치 과정 (자동)

스크립트가 자동으로 다음 작업들을 수행합니다:

### 1. 시스템 환경 확인

- ✅ Ubuntu 버전 확인
- ✅ GPU 감지 (NVIDIA)
- ✅ 시스템 리소스 확인

### 2. 필수 소프트웨어 설치

- ✅ Python 3.11
- ✅ Node.js 18
- ✅ PostgreSQL
- ✅ Redis
- ✅ 기본 도구들

### 3. EXLM 프로젝트 설정

- ✅ 저장소 클론
- ✅ 백엔드 환경 구성
- ✅ GPU/CPU 자동 감지하여 적절한 의존성 설치
- ✅ 프론트엔드 빌드
- ✅ 데이터베이스 마이그레이션

### 4. 서비스 시작

- ✅ 백엔드 API 서버
- ✅ 프론트엔드 웹 서버
- ✅ Celery 워커
- ✅ Flower 모니터링

## 🌐 RunPod 포트 설정

설치 완료 후 **RunPod 웹 콘솔**에서 포트를 Public으로 설정하세요:

### 필수 포트

- **3000** - Frontend (웹 UI)
- **8000** - Backend API

### 선택 포트

- **5555** - Flower (Celery 모니터링)

### 포트 설정 방법

1. RunPod 웹 콘솔 접속
2. Pod 관리 페이지
3. "Edit" 또는 "Configure" 클릭
4. Ports 섹션에서 위 포트들을 "Public"으로 설정
5. 변경사항 저장

## 🔗 접속 URL

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

## 🛠️ 관리 명령어

설치 완료 후 `/workspace/exlm-app` 디렉토리에서 사용할 수 있는 명령어들:

### 서비스 관리

```bash
# 모든 서비스 시작
./start-all.sh

# 모든 서비스 중지
./stop-all.sh

# 서비스 재시작
./restart.sh

# 서비스 상태 확인
./status.sh
```

### 개별 서비스 관리

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

### 로그 확인

```bash
# 실시간 백엔드 로그
tail -f logs/backend.log

# 실시간 프론트엔드 로그
tail -f logs/frontend.log

# 모든 로그 동시 확인
tail -f logs/*.log
```

## 🔧 설정 파일 위치

### 백엔드 환경 변수

```bash
# 파일 위치
/workspace/exlm-app/backend/.env

# API 키 설정 (실제 키로 교체)
OPENAI_API_KEY=your_actual_openai_key
ANTHROPIC_API_KEY=your_actual_anthropic_key
GOOGLE_API_KEY=your_actual_google_key
HF_TOKEN=your_actual_huggingface_token
```

### 프론트엔드 환경 변수

```bash
# 파일 위치
/workspace/exlm-app/frontend/.env.local

# 내용 (자동 설정됨)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## 🎮 GPU 환경 확인

### GPU 상태 확인

```bash
# GPU 정보 확인
nvidia-smi

# PyTorch GPU 인식 확인
cd /workspace/exlm-app/backend
source venv/bin/activate
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### GPU 메모리 모니터링

```bash
# 실시간 GPU 사용량 모니터링
watch -n 1 nvidia-smi
```

## 🔍 문제 해결

### 일반적인 문제들

#### 1. 서비스가 시작되지 않음

```bash
# 상태 확인
./status.sh

# 로그 확인
tail -f logs/backend.log
tail -f logs/frontend.log

# 서비스 재시작
./restart.sh
```

#### 2. 포트 접근 안됨

```bash
# 포트 사용 상태 확인
netstat -tulpn | grep -E ':(3000|8000|5555)'

# RunPod 포트 설정 재확인
# → RunPod 웹 콘솔에서 포트가 Public으로 설정되었는지 확인
```

#### 3. 데이터베이스 연결 문제

```bash
# PostgreSQL 상태 확인
systemctl status postgresql

# 데이터베이스 연결 테스트
sudo -u postgres psql -c "\l" | grep exlm_db
```

#### 4. Redis 연결 문제

```bash
# Redis 상태 확인
systemctl status redis-server

# Redis 연결 테스트
redis-cli ping
```

#### 5. apt_pkg 모듈 오류

```bash
# add-apt-repository 오류 발생 시
chmod +x scripts/fix-apt-pkg.sh
./scripts/fix-apt-pkg.sh

# 수동으로 해결하는 경우
sudo rm -f /usr/lib/python3/dist-packages/apt_pkg.cpython-*.so
sudo ln -sf /usr/lib/python3/dist-packages/apt_pkg.cpython-310-x86_64-linux-gnu.so /usr/lib/python3/dist-packages/apt_pkg.cpython-311-x86_64-linux-gnu.so
```

#### 6. 의존성 충돌 문제

```bash
# 의존성 충돌 오류 발생 시 (transformers, vllm 등)
cd /workspace/exlm-app/backend
chmod +x ../scripts/fix-dependencies.sh
../scripts/fix-dependencies.sh

# 수동으로 해결하는 경우
source venv/bin/activate
pip uninstall -y transformers peft trl vllm accelerate pydantic fastapi openai anthropic pydantic-settings
pip install "pydantic==1.10.13"
pip install "pydantic-settings==0.2.5"
pip install "fastapi==0.100.1"
pip install "transformers>=4.36.0,<4.38.0"
pip install "vllm>=0.2.5,<0.3.0"
pip install -r requirements-gpu.txt
```

#### 6. GPU 인식 문제

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

### 로그 분석

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

## 📊 성능 모니터링

### 시스템 리소스

```bash
# CPU 및 메모리 사용률
htop

# 디스크 사용량
df -h

# 네트워크 연결
netstat -tulpn
```

### 애플리케이션 성능

```bash
# API 응답 테스트
curl -s http://localhost:8000/api/v1/health

# 프론트엔드 접속 테스트
curl -s http://localhost:3000 | head -10
```

## 🔄 업데이트 방법

### 코드 업데이트

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

# 프론트엔드 다시 빌드
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

이제 RunPod에서 **한 번의 명령어**로 EXLM 플랫폼을 완전히 설치하고 실행할 수 있습니다! 🚀
