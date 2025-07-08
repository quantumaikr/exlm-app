# exlm - Domain-Specific LLM Automation Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)

exlm은 도메인 특화 LLM을 자동으로 생성하고 배포할 수 있는 통합 플랫폼입니다. 오픈소스 LLM 파인튜닝부터 합성 데이터 생성, 최신 학습 기법 적용, 그리고 프로덕션 서빙까지 전체 파이프라인을 자동화합니다.

## 🚀 주요 기능

### 🤖 모델 관리

- **최신 오픈소스 LLM 지원**: Llama3, Mistral, Qwen2, Phi-3 등
- **자동 파인튜닝**: LoRA, QLoRA, DPO, ORPO 등 최신 기법 지원
- **모델 버전 관리**: 실험 추적 및 모델 버전 관리

### 📊 데이터 생성

- **합성 데이터 생성**: OpenAI, Claude, Gemini API를 활용한 고품질 데이터 생성
- **프롬프트 템플릿**: 도메인별 커스터마이징 가능한 템플릿
- **품질 관리**: 자동 중복 제거, 품질 점수 계산, 도메인 관련성 검증

### 🔧 파이프라인 자동화

- **드래그 앤 드롭 인터페이스**: 직관적인 파이프라인 설계
- **최신 기법 조합**: 다양한 학습 기법을 자유롭게 조합
- **코드 자동 생성**: 설계한 파이프라인을 실행 가능한 코드로 변환

### 🌐 모델 서빙

- **vLLM 통합**: 고성능 추론 서버
- **OpenAI API 호환**: 기존 애플리케이션과 쉽게 통합
- **자동 스케일링**: 트래픽에 따른 자동 확장

## ⚡ 빠른 시작

### RunPod 원클릭 배포 (권장) ⭐

GPU 환경에서 **1분 만에** 완전 자동 설치가 가능합니다.

```bash
# RunPod SSH 접속 후 한 번의 명령어로 완료
curl -sSL https://raw.githubusercontent.com/quantumaikr/exlm-app/main/scripts/runpod-full-setup.sh | bash
```

- ✅ **완전 자동화**: 시스템 설정부터 서비스 시작까지 모든 과정 자동
- ✅ **GPU 자동 감지**: CUDA 환경 자동 구성
- ✅ **즉시 사용 가능**: 설치 완료 후 바로 웹 UI 접속 가능

**포트 설정**: RunPod 콘솔에서 3000, 8000 포트를 Public으로 설정
**접속**: `https://[POD_ID]-3000.proxy.runpod.net`

📚 **상세 가이드**: [RunPod 빠른 설치 가이드](docs/RUNPOD_QUICK_SETUP.md)

## 📋 요구사항

- Python 3.9+
- Node.js 18+
- Docker & Docker Compose (선택사항)
- CUDA 11.8+ (GPU 학습 시)

## 🛠️ 설치 방법

### 방법 1: RunPod 배포 (권장) ⭐

GPU 환경에서 빠른 배포를 원한다면 RunPod을 사용하세요:

#### 소스코드가 이미 있는 경우 (가장 간단)

```bash
# EXLM 프로젝트 디렉토리에서 실행
cd /workspace/exlm-app
chmod +x scripts/setup-runpod-local.sh
./scripts/setup-runpod-local.sh

# 서비스 시작
./start-all.sh
```

#### 처음부터 설치하는 경우

```bash
# 자동 배포 스크립트 다운로드
curl -sSL https://raw.githubusercontent.com/quantumaikr/exlm-app/main/scripts/deploy-runpod-native.sh -o deploy.sh
chmod +x deploy.sh

# 토큰과 함께 배포 (권장)
./deploy.sh YOUR_GITHUB_TOKEN

# 또는 토큰 없이 배포 (Public 저장소인 경우)
./deploy.sh
```

**RunPod 포트 설정**: 3000, 8000, 5555 포트를 Public으로 설정하세요.

📚 **상세 가이드**: [RunPod 네이티브 배포 가이드](docs/RUNPOD_NATIVE_DEPLOYMENT.md)

### 방법 2: Docker 환경 (로컬/서버)

#### 1. 저장소 클론

```bash
git clone https://github.com/quantumaikr/exlm-app.git
cd exlm-app
```

#### 2. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 열어 필요한 API 키와 설정을 입력하세요
```

#### 3. Docker Compose로 실행

```bash
# 개발 환경 (CPU)
docker-compose up -d

# GPU 환경
docker-compose -f docker-compose.gpu.yml up -d
```

### 방법 3: 개발 환경 설정 (로컬)

#### Backend (Python/FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

#### Frontend (React/Next.js)

```bash
cd frontend
npm install
npm run dev
```

## 📖 사용 방법

1. **프로젝트 생성**: 웹 UI에서 새 프로젝트를 생성합니다.
2. **모델 선택**: 사용할 베이스 모델을 선택합니다.
3. **데이터 준비**: 기존 데이터를 업로드하거나 합성 데이터를 생성합니다.
4. **파이프라인 설계**: 원하는 학습 기법을 선택하고 조합합니다.
5. **학습 실행**: 설계한 파이프라인으로 모델을 학습시킵니다.
6. **배포**: 학습된 모델을 API로 서빙합니다.

## 🏗️ 아키텍처

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│     ML      │
│  (Next.js)  │     │  (FastAPI)  │     │  Pipeline   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                    │
       ▼                   ▼                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │     │  PostgreSQL │     │    vLLM     │
│     UI      │     │    Redis    │     │   Server    │
└─────────────┘     └─────────────┘     └─────────────┘
```

## 🤝 기여하기

프로젝트에 기여하고 싶으신가요? [CONTRIBUTING.md](CONTRIBUTING.md)를 참고해주세요.

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참고하세요.

## 📚 문서

- [🚀 RunPod 빠른 설치 가이드](docs/RUNPOD_QUICK_SETUP.md) - **추천**
- [⚡ 빠른 시작 가이드](docs/QUICK_START.md) - 배포 방법 비교
- [RunPod 네이티브 배포 가이드](docs/RUNPOD_NATIVE_DEPLOYMENT.md)
- [Docker 배포 가이드](docs/RUNPOD_DEPLOYMENT.md)
- [GitHub Token 가이드](docs/GITHUB_TOKEN_GUIDE.md)
- [환경 설정 가이드](docs/ENVIRONMENT_SETUP.md)
- [프로젝트 구조](docs/PROJECT_STRUCTURE.md)
- [모니터링 설정](docs/monitoring.md)

## 💬 지원

- GitHub Issues: [버그 리포트 및 기능 제안](https://github.com/yourusername/exlm/issues)
- Discord: [커뮤니티 채널](https://discord.gg/exlm)
- Email: support@exlm.io

## 🛠️ 환경 요구사항

### 개발 환경 (macOS/Linux)

- Docker & Docker Compose
- Node.js 18+
- Python 3.9+

### 프로덕션 환경 (GPU 서버)

- NVIDIA GPU (CUDA 11.8+)
- Docker & Docker Compose
- NVIDIA Container Toolkit

## 📦 설치 및 실행

### 1. 개발 환경 (CPU only)

```bash
# 저장소 클론
git clone <repository-url>
cd exlm

# 개발 환경 시작
make up-dev

# 또는 직접 실행
docker-compose up -d
```

### 2. GPU 환경

```bash
# GPU 환경 시작
make up-gpu

# 또는 직접 실행
docker-compose -f docker-compose.gpu.yml up -d
```

### 3. 환경별 빌드

```bash
# 개발 환경 빌드 (CPU only)
make build-dev

# GPU 환경 빌드
make build-gpu
```

## 🌐 서비스 접속

- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **Flower (Celery 모니터링)**: http://localhost:5555
- **Grafana**: http://localhost:3001 (admin/admin)

## 🔧 환경 설정

### 환경 변수

`.env` 파일을 생성하여 환경 변수를 설정할 수 있습니다:

```env
# 데이터베이스
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=exlm_db

# 빌드 환경 (dev 또는 gpu)
BUILD_ENV=dev

# API 키들
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key
```

### GPU 환경 설정

GPU 환경을 사용하려면:

1. **NVIDIA Container Toolkit 설치**:

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

2. **GPU 환경 시작**:

```bash
make up-gpu
```

## 🧪 테스트

```bash
# 개발 환경 테스트
make test-dev

# GPU 환경 테스트
make test-gpu
```

## 📊 모니터링

### Prometheus 메트릭

- **Prometheus**: http://localhost:9090
- **Node Exporter**: 시스템 메트릭
- **PostgreSQL Exporter**: 데이터베이스 메트릭
- **Redis Exporter**: 캐시 메트릭

### Grafana 대시보드

- **Grafana**: http://localhost:3001
- 기본 계정: admin/admin
- 사전 구성된 대시보드 포함

## 🔍 로그 확인

```bash
# 전체 로그
make logs

# GPU 환경 로그
make logs-gpu

# 특정 서비스 로그
make backend-logs
make frontend-logs
make celery-logs
make flower-logs
```

## 🛠️ 개발 도구

### 컨테이너 쉘 접속

```bash
# 개발 환경
make shell-backend
make shell-frontend

# GPU 환경
make shell-backend-gpu
make shell-frontend-gpu
```

### 서비스 재시작

```bash
make restart-backend
make restart-frontend
make restart-celery
```

## 📁 프로젝트 구조

```
exlm/
├── backend/                 # FastAPI 백엔드
│   ├── app/
│   │   ├── api/            # API 엔드포인트
│   │   │   ├── core/           # 핵심 설정
│   │   │   ├── models/         # SQLAlchemy 모델
│   │   │   ├── schemas/        # Pydantic 스키마
│   │   │   ├── services/       # 비즈니스 로직
│   │   │   └── tasks/          # Celery 태스크
│   │   ├── requirements.txt    # 개발 환경 의존성
│   │   └── requirements-gpu.txt # GPU 환경 의존성
│   ├── frontend/               # Next.js 프론트엔드
│   ├── monitoring/             # 모니터링 설정
│   ├── docker-compose.yml      # 개발 환경 설정
│   ├── docker-compose.gpu.yml  # GPU 환경 설정
│   └── Makefile               # 자동화 스크립트
```

## 🔄 환경별 차이점

| 기능         | 개발 환경 (CPU) | GPU 환경       |
| ------------ | --------------- | -------------- |
| PyTorch      | CPU 버전        | CUDA 11.8 버전 |
| vLLM         | 미설치          | 설치됨         |
| bitsandbytes | 미설치          | 설치됨         |
| 모델 학습    | 제한적          | 전체 기능      |
| 모델 서빙    | 제한적          | 전체 기능      |

## 🚨 문제 해결

### 일반적인 문제들

1. **PostgreSQL 연결 오류**

   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

2. **GPU 컨테이너 시작 실패**

   ```bash
   # NVIDIA Container Toolkit 확인
   docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi
   ```

3. **메모리 부족 오류**
   ```bash
   # Docker 메모리 제한 증가
   # Docker Desktop > Settings > Resources > Memory
   ```

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
