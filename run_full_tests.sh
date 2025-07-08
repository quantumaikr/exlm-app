#!/bin/bash

# EXLM 프로젝트 전체 기능 테스트 스크립트

set -e

# 변수 설정
TEST_RESULTS_DIR="test_results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TEST_REPORT="$TEST_RESULTS_DIR/test_report_$TIMESTAMP.md"
BACKEND_TEST_LOG="$TEST_RESULTS_DIR/backend_test_$TIMESTAMP.log"
FRONTEND_TEST_LOG="$TEST_RESULTS_DIR/frontend_test_$TIMESTAMP.log"
API_TEST_LOG="$TEST_RESULTS_DIR/api_test_$TIMESTAMP.log"

# 색상 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 테스트 결과 카운터
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 함수: 테스트 결과 기록
log_test() {
    test_name=$1
    status=$2
    message=$3
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [ "$status" = "PASS" ]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo -e "${GREEN}✓${NC} $test_name"
        echo "✓ $test_name: $message" >> "$TEST_REPORT"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo -e "${RED}✗${NC} $test_name"
        echo "✗ $test_name: $message" >> "$TEST_REPORT"
    fi
}

# 테스트 보고서 헤더 작성
cat > "$TEST_REPORT" << EOF
# EXLM 프로젝트 테스트 보고서

**테스트 실행 시간**: $(date)

## 요약
- 총 테스트: TOTAL_PLACEHOLDER
- 성공: PASSED_PLACEHOLDER
- 실패: FAILED_PLACEHOLDER

---

## 테스트 결과

EOF

echo "========================================="
echo "EXLM 프로젝트 전체 기능 테스트 시작"
echo "========================================="

# 1. 환경 설정 테스트
echo -e "\n${YELLOW}1. 환경 설정 테스트${NC}"

# Python 환경 확인
if python3 --version &> /dev/null; then
    log_test "Python 설치 확인" "PASS" "$(python3 --version)"
else
    log_test "Python 설치 확인" "FAIL" "Python이 설치되지 않음"
fi

# Node.js 환경 확인
if node --version &> /dev/null; then
    log_test "Node.js 설치 확인" "PASS" "$(node --version)"
else
    log_test "Node.js 설치 확인" "FAIL" "Node.js가 설치되지 않음"
fi

# 2. Backend 테스트
echo -e "\n${YELLOW}2. Backend 테스트${NC}"
cd backend

# 가상환경 활성화
source venv/bin/activate

# 의존성 확인
echo "### Backend 의존성 테스트" >> "$BACKEND_TEST_LOG"
if pip list >> "$BACKEND_TEST_LOG" 2>&1; then
    log_test "Backend 의존성 설치" "PASS" "모든 패키지 설치됨"
else
    log_test "Backend 의존성 설치" "FAIL" "패키지 설치 오류"
fi

# Import 테스트
echo -e "\n### Import 테스트" >> "$BACKEND_TEST_LOG"
python3 << EOF >> "$BACKEND_TEST_LOG" 2>&1 && log_test "Backend 모듈 Import" "PASS" "모든 모듈 정상 import" || log_test "Backend 모듈 Import" "FAIL" "Import 오류 발생"
try:
    from app.main import app
    from app.core.config import settings
    from app.api.v1.api import api_router
    print("모든 주요 모듈 import 성공")
except Exception as e:
    print(f"Import 오류: {e}")
    raise
EOF

# API 엔드포인트 테스트
echo -e "\n### API 엔드포인트 테스트" >> "$API_TEST_LOG"

# FastAPI 서버 시작 (백그라운드)
echo "FastAPI 서버 시작 중..." >> "$API_TEST_LOG"
uvicorn app.main:app --host 0.0.0.0 --port 8000 >> "$API_TEST_LOG" 2>&1 &
BACKEND_PID=$!
sleep 5

# API 테스트 실행
if curl -s http://localhost:8000/api/v1/health > /dev/null; then
    log_test "API 서버 시작" "PASS" "서버가 정상적으로 시작됨"
    
    # Health check
    HEALTH_RESPONSE=$(curl -s http://localhost:8000/api/v1/health)
    echo "Health check response: $HEALTH_RESPONSE" >> "$API_TEST_LOG"
    log_test "Health Check API" "PASS" "응답: $HEALTH_RESPONSE"
    
    # OpenAPI 문서
    if curl -s http://localhost:8000/docs > /dev/null; then
        log_test "OpenAPI 문서" "PASS" "Swagger UI 접근 가능"
    else
        log_test "OpenAPI 문서" "FAIL" "Swagger UI 접근 불가"
    fi
else
    log_test "API 서버 시작" "FAIL" "서버 시작 실패"
fi

# 서버 종료
kill $BACKEND_PID 2>/dev/null || true

cd ..

# 3. Frontend 테스트
echo -e "\n${YELLOW}3. Frontend 테스트${NC}"
cd frontend

# 의존성 확인
echo "### Frontend 의존성 테스트" >> "$FRONTEND_TEST_LOG"
if npm list --depth=0 >> "$FRONTEND_TEST_LOG" 2>&1; then
    log_test "Frontend 의존성 설치" "PASS" "모든 패키지 설치됨"
else
    log_test "Frontend 의존성 설치" "FAIL" "패키지 설치 오류"
fi

# TypeScript 컴파일 테스트
echo -e "\n### TypeScript 컴파일 테스트" >> "$FRONTEND_TEST_LOG"
if npx tsc --noEmit >> "$FRONTEND_TEST_LOG" 2>&1; then
    log_test "TypeScript 컴파일" "PASS" "타입 체크 통과"
else
    log_test "TypeScript 컴파일" "FAIL" "타입 오류 발견"
fi

# 빌드 테스트
echo -e "\n### Frontend 빌드 테스트" >> "$FRONTEND_TEST_LOG"
if npm run build >> "$FRONTEND_TEST_LOG" 2>&1; then
    log_test "Frontend 빌드" "PASS" "빌드 성공"
else
    log_test "Frontend 빌드" "FAIL" "빌드 실패"
fi

cd ..

# 4. 기능별 테스트
echo -e "\n${YELLOW}4. 기능별 상세 테스트${NC}"

# Backend 기능 테스트 스크립트 작성
cat > "$TEST_RESULTS_DIR/backend_feature_test.py" << 'EOF'
import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

async def test_features():
    results = []
    
    # 데이터베이스 연결 테스트
    try:
        from app.core.database import engine
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        results.append(("데이터베이스 연결", "PASS", "PostgreSQL 연결 성공"))
    except Exception as e:
        results.append(("데이터베이스 연결", "FAIL", str(e)))
    
    # Redis 연결 테스트
    try:
        from app.core.redis import get_redis
        redis = await get_redis()
        await redis.ping()
        results.append(("Redis 연결", "PASS", "Redis 연결 성공"))
    except Exception as e:
        results.append(("Redis 연결", "FAIL", str(e)))
    
    # 주요 서비스 테스트
    try:
        from app.services.huggingface import huggingface_service
        results.append(("HuggingFace 서비스", "PASS", "서비스 로드 성공"))
    except Exception as e:
        results.append(("HuggingFace 서비스", "FAIL", str(e)))
    
    try:
        from app.services.data_preprocessing import data_preprocessing_service
        results.append(("데이터 전처리 서비스", "PASS", "서비스 로드 성공"))
    except Exception as e:
        results.append(("데이터 전처리 서비스", "FAIL", str(e)))
    
    try:
        from app.services.data_quality import data_quality_service
        results.append(("데이터 품질 서비스", "PASS", "서비스 로드 성공"))
    except Exception as e:
        results.append(("데이터 품질 서비스", "FAIL", str(e)))
    
    return results

# 테스트 실행
if __name__ == "__main__":
    results = asyncio.run(test_features())
    for test_name, status, message in results:
        print(f"{test_name}|{status}|{message}")
EOF

# Backend 기능 테스트 실행
cd backend
source venv/bin/activate
python "$TEST_RESULTS_DIR/backend_feature_test.py" 2>&1 | while IFS='|' read -r test_name status message; do
    if [ -n "$test_name" ]; then
        log_test "$test_name" "$status" "$message"
    fi
done
cd ..

# 5. UI 컴포넌트 테스트
echo -e "\n${YELLOW}5. UI 컴포넌트 테스트${NC}"

# 주요 페이지 확인
UI_PAGES=(
    "src/pages/index.tsx|홈페이지"
    "src/pages/login.tsx|로그인 페이지"
    "src/pages/projects/index.tsx|프로젝트 목록"
    "src/pages/projects/[id]/index.tsx|프로젝트 상세"
    "src/pages/projects/[id]/models/select.tsx|모델 선택"
    "src/pages/projects/[id]/data/generate.tsx|데이터 생성"
    "src/pages/projects/[id]/data/quality.tsx|데이터 품질"
    "src/pages/projects/[id]/training/pipeline.tsx|학습 파이프라인"
)

cd frontend
for page_info in "${UI_PAGES[@]}"; do
    IFS='|' read -r page_path page_name <<< "$page_info"
    if [ -f "$page_path" ]; then
        log_test "UI: $page_name" "PASS" "파일 존재"
    else
        log_test "UI: $page_name" "FAIL" "파일 없음"
    fi
done
cd ..

# 6. 통합 테스트
echo -e "\n${YELLOW}6. 통합 테스트${NC}"

# Docker Compose 테스트
if docker-compose -f docker-compose.yml config > /dev/null 2>&1; then
    log_test "Docker Compose 설정" "PASS" "유효한 설정 파일"
else
    log_test "Docker Compose 설정" "FAIL" "설정 파일 오류"
fi

# 테스트 요약 업데이트
sed -i '' "s/TOTAL_PLACEHOLDER/$TOTAL_TESTS/g" "$TEST_REPORT"
sed -i '' "s/PASSED_PLACEHOLDER/$PASSED_TESTS/g" "$TEST_REPORT"
sed -i '' "s/FAILED_PLACEHOLDER/$FAILED_TESTS/g" "$TEST_REPORT"

# 최종 보고서 작성
cat >> "$TEST_REPORT" << EOF

---

## 상세 로그 파일
- Backend 테스트: $BACKEND_TEST_LOG
- Frontend 테스트: $FRONTEND_TEST_LOG
- API 테스트: $API_TEST_LOG

## 테스트 환경
- OS: $(uname -s)
- Python: $(python3 --version)
- Node.js: $(node --version)
- 테스트 실행자: $(whoami)
- 테스트 디렉토리: $(pwd)

EOF

# 결과 출력
echo -e "\n========================================="
echo -e "${YELLOW}테스트 완료${NC}"
echo -e "총 테스트: $TOTAL_TESTS"
echo -e "${GREEN}성공: $PASSED_TESTS${NC}"
echo -e "${RED}실패: $FAILED_TESTS${NC}"
echo -e "상세 보고서: $TEST_REPORT"
echo "========================================="

# 테스트 실패 시 exit code 1 반환
if [ $FAILED_TESTS -gt 0 ]; then
    exit 1
fi