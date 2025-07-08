#!/bin/bash

# EXLM 의존성 충돌 해결 스크립트
# RunPod에서 의존성 설치 오류 발생 시 사용

set -e

echo "🔧 EXLM 의존성 충돌 해결 중..."
echo "================================"

# 컬러 출력 함수
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 현재 디렉토리 확인
if [ ! -f "app/main.py" ]; then
    print_error "backend 디렉토리에서 실행해주세요"
    exit 1
fi

# 가상환경 활성화
if [ -d "venv" ]; then
    print_status "가상환경 활성화 중..."
    source venv/bin/activate
else
    print_error "가상환경이 없습니다. 먼저 가상환경을 생성해주세요"
    exit 1
fi

# GPU 확인
if command -v nvidia-smi &> /dev/null; then
    print_success "GPU 감지됨"
    GPU_AVAILABLE=true
else
    print_warning "GPU 미감지 - CPU 모드로 설치"
    GPU_AVAILABLE=false
fi

# 기존 충돌 패키지 제거
print_status "기존 충돌 패키지 제거 중..."
pip uninstall -y transformers peft trl vllm accelerate datasets tokenizers bitsandbytes pydantic fastapi openai anthropic 2>/dev/null || true

# pip 업그레이드
print_status "pip 업그레이드 중..."
pip install --upgrade pip -q

if [ "$GPU_AVAILABLE" = true ]; then
    print_status "GPU 환경 의존성 재설치 중..."
    
    # PyTorch CUDA 버전 설치
    print_status "PyTorch CUDA 버전 설치 중..."
    pip install torch==2.1.1 torchvision==0.16.1 torchaudio==2.1.1 --index-url https://download.pytorch.org/whl/cu118 -q
    
    # 핵심 라이브러리 단계별 설치
    print_status "Pydantic 설치 중 (vLLM 호환 버전)..."
    pip install "pydantic==1.10.13" -q
    
    print_status "Pydantic-settings 설치 중..."
    pip install "pydantic-settings==0.2.5" -q
    
    print_status "FastAPI 설치 중..."
    pip install "fastapi==0.100.1" -q
    
    print_status "Transformers 라이브러리 설치 중..."
    pip install "transformers>=4.36.0,<4.38.0" -q
    
    print_status "Accelerate 설치 중..."
    pip install "accelerate>=0.24.1,<0.26.0" -q
    
    print_status "Tokenizers 설치 중..."
    pip install "tokenizers>=0.15.0,<0.16.0" -q
    
    print_status "Datasets 설치 중..."
    pip install "datasets>=2.15.0,<2.17.0" -q
    
    print_status "PEFT 설치 중..."
    pip install "peft>=0.6.2,<0.8.0" -q
    
    print_status "TRL 설치 중..."
    pip install "trl>=0.7.4,<0.9.0" -q
    
    print_status "Bitsandbytes 설치 중..."
    pip install "bitsandbytes>=0.41.2,<0.42.0" -q
    
    print_status "vLLM 설치 중..."
    pip install "vllm>=0.2.5,<0.3.0" -q
    
    print_status "나머지 의존성 설치 중..."
    pip install -r requirements-gpu.txt -q
    
else
    print_status "CPU 환경 의존성 재설치 중..."
    
    # 핵심 라이브러리 단계별 설치
    print_status "Pydantic 설치 중 (vLLM 호환 버전)..."
    pip install "pydantic==1.10.13" -q
    
    print_status "Pydantic-settings 설치 중..."
    pip install "pydantic-settings==0.2.5" -q
    
    print_status "FastAPI 설치 중..."
    pip install "fastapi==0.100.1" -q
    
    print_status "Transformers 라이브러리 설치 중..."
    pip install "transformers>=4.36.0,<4.38.0" -q
    
    print_status "PyTorch CPU 버전 설치 중..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu -q
    
    print_status "나머지 의존성 설치 중..."
    pip install -r requirements.txt -q
fi

# 설치 확인
print_status "설치 확인 중..."
python -c "import transformers; print(f'Transformers: {transformers.__version__}')" 2>/dev/null || print_error "Transformers 설치 실패"

if [ "$GPU_AVAILABLE" = true ]; then
    python -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')" 2>/dev/null || print_error "PyTorch 설치 실패"
    python -c "import vllm; print(f'vLLM: {vllm.__version__}')" 2>/dev/null || print_error "vLLM 설치 실패"
else
    python -c "import torch; print(f'PyTorch: {torch.__version__}')" 2>/dev/null || print_error "PyTorch 설치 실패"
fi

print_success "의존성 충돌 해결 완료!"
print_status "이제 애플리케이션을 시작할 수 있습니다."

echo ""
echo "다음 명령어로 애플리케이션을 시작하세요:"
echo "uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" 