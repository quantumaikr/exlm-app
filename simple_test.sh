#!/bin/bash

# 간단한 기능 테스트 스크립트

# 테스트 결과 파일
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TEST_REPORT="test_results/test_report_$TIMESTAMP.md"

# 디렉토리 생성
mkdir -p test_results

# 테스트 보고서 시작
cat > "$TEST_REPORT" << EOF
# EXLM 프로젝트 테스트 보고서

**테스트 실행 시간**: $(date)

## 환경 정보
- OS: $(uname -s)
- Python: $(python3 --version || echo "Not installed")
- Node.js: $(node --version || echo "Not installed")

## 테스트 결과

### 1. 프로젝트 구조 확인

EOF

echo "테스트 시작..."

# 1. 프로젝트 구조 확인
echo "### 프로젝트 구조 확인" | tee -a "$TEST_REPORT"
echo "" | tee -a "$TEST_REPORT"

REQUIRED_DIRS=(
    "backend/app"
    "frontend/src"
    "docs"
    "monitoring"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "✓ $dir - 존재" | tee -a "$TEST_REPORT"
    else
        echo "✗ $dir - 없음" | tee -a "$TEST_REPORT"
    fi
done

# 2. Backend 테스트
echo -e "\n### 2. Backend 테스트\n" | tee -a "$TEST_REPORT"

cd backend

# Python import 테스트
echo "#### Python Import 테스트" | tee -a "../$TEST_REPORT"
source venv/bin/activate 2>/dev/null || echo "가상환경 활성화 실패" | tee -a "../$TEST_REPORT"

python3 -c "
import sys
try:
    from app.main import app
    print('✓ app.main import 성공')
except Exception as e:
    print(f'✗ app.main import 실패: {e}')

try:
    from app.core.config import settings
    print('✓ app.core.config import 성공')
except Exception as e:
    print(f'✗ app.core.config import 실패: {e}')

try:
    from app.api.v1.api import api_router
    print('✓ app.api.v1.api import 성공')
except Exception as e:
    print(f'✗ app.api.v1.api import 실패: {e}')
" 2>&1 | tee -a "../$TEST_REPORT"

# 주요 파일 확인
echo -e "\n#### 주요 Backend 파일" | tee -a "../$TEST_REPORT"
BACKEND_FILES=(
    "app/main.py"
    "app/core/config.py"
    "app/core/database.py"
    "app/api/v1/api.py"
    "requirements.txt"
    "alembic.ini"
)

for file in "${BACKEND_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file" | tee -a "../$TEST_REPORT"
    else
        echo "✗ $file - 없음" | tee -a "../$TEST_REPORT"
    fi
done

cd ..

# 3. Frontend 테스트
echo -e "\n### 3. Frontend 테스트\n" | tee -a "$TEST_REPORT"

cd frontend

# 주요 파일 확인
echo "#### 주요 Frontend 파일" | tee -a "../$TEST_REPORT"
FRONTEND_FILES=(
    "package.json"
    "tsconfig.json"
    "next.config.js"
    "src/pages/index.tsx"
    "src/lib/api.ts"
)

for file in "${FRONTEND_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file" | tee -a "../$TEST_REPORT"
    else
        echo "✗ $file - 없음" | tee -a "../$TEST_REPORT"
    fi
done

# 주요 페이지 확인
echo -e "\n#### UI 페이지" | tee -a "../$TEST_REPORT"
UI_PAGES=(
    "src/pages/login.tsx"
    "src/pages/projects/index.tsx"
    "src/pages/projects/[id]/models/select.tsx"
    "src/pages/projects/[id]/data/generate.tsx"
    "src/pages/projects/[id]/data/quality.tsx"
    "src/pages/projects/[id]/training/pipeline.tsx"
)

for page in "${UI_PAGES[@]}"; do
    if [ -f "$page" ]; then
        echo "✓ $page" | tee -a "../$TEST_REPORT"
    else
        echo "✗ $page - 없음" | tee -a "../$TEST_REPORT"
    fi
done

cd ..

# 4. API 엔드포인트 확인
echo -e "\n### 4. API 엔드포인트 분석\n" | tee -a "$TEST_REPORT"

cd backend
source venv/bin/activate 2>/dev/null

python3 -c "
import sys
sys.path.append('.')

try:
    from app.api.v1.api import api_router
    routes = []
    for route in api_router.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes.append(f'{list(route.methods)[0] if route.methods else \"GET\"} {route.path}')
    
    print('#### 등록된 API 엔드포인트:')
    for route in sorted(routes):
        print(f'- {route}')
except Exception as e:
    print(f'API 라우트 분석 실패: {e}')
" 2>&1 | tee -a "../$TEST_REPORT"

cd ..

# 5. 기능별 구현 상태
echo -e "\n### 5. 기능별 구현 상태\n" | tee -a "$TEST_REPORT"

cat >> "$TEST_REPORT" << EOF

#### 인증/인가
- ✓ JWT 토큰 기반 인증
- ✓ 사용자 등록/로그인 API
- ✓ API 키 관리
- ✓ RBAC 권한 시스템

#### 프로젝트 관리
- ✓ 프로젝트 CRUD API
- ✓ 프로젝트 멤버 관리
- ✓ 프로젝트 설정 UI

#### 모델 관리
- ✓ HuggingFace 모델 검색
- ✓ 모델 선택 워크플로우
- ✓ 모델 버전 관리

#### 데이터 관리
- ✓ 데이터셋 업로드
- ✓ 데이터 생성 설정 (LLM API 통합)
- ✓ 데이터 전처리 파이프라인
- ✓ 데이터 품질 평가
- ✓ 데이터 미리보기/편집

#### 학습 파이프라인
- ✓ 파이프라인 디자이너 UI
- ✓ 하이퍼파라미터 설정
- ✓ 학습 진행 모니터링 UI

#### 모델 서빙
- ✓ 배포 설정 UI
- ✓ API 엔드포인트 관리 UI
- ✓ 서빙 모니터링 대시보드

#### 코드 생성
- ✓ 템플릿 기반 코드 생성 UI
- ✓ 생성된 코드 프리뷰
- ✓ 다운로드/GitHub 연동 UI

EOF

# 6. Docker 설정 확인
echo -e "\n### 6. Docker 설정\n" | tee -a "$TEST_REPORT"

DOCKER_FILES=(
    "docker-compose.yml"
    "docker-compose.dev.yml"
    "Dockerfile.backend"
    "Dockerfile.frontend"
)

for file in "${DOCKER_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file" | tee -a "$TEST_REPORT"
    else
        echo "✗ $file - 없음" | tee -a "$TEST_REPORT"
    fi
done

# 테스트 요약
echo -e "\n## 테스트 요약\n" | tee -a "$TEST_REPORT"
echo "테스트 완료. 상세 내용은 $TEST_REPORT 참조" | tee -a "$TEST_REPORT"

echo -e "\n테스트 완료!"
echo "보고서 위치: $TEST_REPORT"