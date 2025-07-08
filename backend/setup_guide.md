# Backend 개발 환경 설정 가이드

## Python 가상환경 설정

### 1. 가상환경 생성
```bash
cd backend
python -m venv venv
```

### 2. 가상환경 활성화
- **Linux/macOS**:
  ```bash
  source venv/bin/activate
  ```
- **Windows**:
  ```bash
  venv\Scripts\activate
  ```

### 3. 패키지 설치
```bash
# 프로덕션 패키지
pip install -r requirements.txt

# 개발 도구 (선택사항)
pip install -r requirements-dev.txt
```

### 4. 환경 변수 설정
```bash
# .env 파일 생성
cp .env.example .env

# .env 파일을 편집하여 필요한 설정 추가
```

### 5. 개발 서버 실행
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 데이터베이스 설정

### PostgreSQL 설치 및 설정
```bash
# 데이터베이스 생성
createdb exlm_db

# 마이그레이션 실행
alembic upgrade head
```

### Redis 설치 및 실행
```bash
# macOS
brew install redis
brew services start redis

# Linux
sudo apt-get install redis-server
sudo systemctl start redis
```

## 개발 도구

### 코드 포맷팅
```bash
# Black으로 코드 포맷팅
black .

# isort로 import 정렬
isort .
```

### 린팅
```bash
# Flake8으로 코드 스타일 체크
flake8

# mypy로 타입 체크
mypy .
```

### 테스트
```bash
# 전체 테스트 실행
pytest

# 커버리지 포함
pytest --cov=app

# 특정 테스트만 실행
pytest tests/test_api.py::test_function_name
```

## Pre-commit 설정
```bash
# pre-commit 설치
pre-commit install

# 수동으로 모든 파일에 대해 실행
pre-commit run --all-files
```