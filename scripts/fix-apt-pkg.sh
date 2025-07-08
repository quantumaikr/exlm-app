#!/bin/bash

# apt_pkg 모듈 문제 해결 스크립트
# RunPod에서 add-apt-repository 오류 발생 시 사용

set -e

echo "🔧 apt_pkg 모듈 문제 해결 중..."
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

# 현재 Python 버전 확인
print_status "현재 Python 버전 확인 중..."
python3 --version

# apt_pkg 모듈 문제 해결
print_status "apt_pkg 모듈 문제 해결 중..."

# 기존 심볼릭 링크 제거
print_status "기존 apt_pkg 심볼릭 링크 제거 중..."
rm -f /usr/lib/python3/dist-packages/apt_pkg.cpython-*.so 2>/dev/null || true

# 현재 Python 버전에 맞는 apt_pkg 파일 찾기
print_status "현재 Python 버전에 맞는 apt_pkg 파일 찾는 중..."
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')")
print_status "Python 버전: $PYTHON_VERSION"

# apt_pkg 파일 찾기
APT_PKG_FILE=$(find /usr/lib/python3/dist-packages/ -name "apt_pkg.cpython-*.so" | head -1)

if [ -n "$APT_PKG_FILE" ]; then
    print_status "발견된 apt_pkg 파일: $APT_PKG_FILE"
    
    # 새로운 심볼릭 링크 생성
    TARGET_FILE="/usr/lib/python3/dist-packages/apt_pkg.cpython-${PYTHON_VERSION}*-x86_64-linux-gnu.so"
    print_status "심볼릭 링크 생성 중: $APT_PKG_FILE -> $TARGET_FILE"
    
    ln -sf "$APT_PKG_FILE" "$TARGET_FILE" 2>/dev/null || true
    
    # 확인
    if [ -L "$TARGET_FILE" ]; then
        print_success "apt_pkg 심볼릭 링크 생성 완료"
    else
        print_warning "apt_pkg 심볼릭 링크 생성 실패"
    fi
else
    print_warning "apt_pkg 파일을 찾을 수 없습니다"
fi

# 대안 방법: apt 업데이트
print_status "apt 업데이트 시도 중..."
apt update -qq || print_warning "apt update 실패"

# add-apt-repository 테스트
print_status "add-apt-repository 테스트 중..."
if add-apt-repository --help > /dev/null 2>&1; then
    print_success "add-apt-repository 정상 작동"
else
    print_error "add-apt-repository 여전히 문제가 있습니다"
    echo ""
    echo "대안 방법:"
    echo "1. 기본 Python 사용 (Python 3.11 대신)"
    echo "2. 수동으로 PPA 추가"
    echo "3. 다른 Python 설치 방법 사용"
fi

print_success "apt_pkg 문제 해결 완료!" 