# 프로젝트 디렉토리 구조

```
exlm/
├── backend/                    # FastAPI 백엔드 애플리케이션
│   ├── api/                   # API 엔드포인트
│   ├── core/                  # 핵심 설정 및 유틸리티
│   ├── models/                # 데이터베이스 모델
│   ├── schemas/               # Pydantic 스키마
│   ├── services/              # 비즈니스 로직
│   ├── utils/                 # 유틸리티 함수
│   └── tests/                 # 백엔드 테스트
│
├── frontend/                   # React/Next.js 프론트엔드
│   ├── src/
│   │   ├── components/        # React 컴포넌트
│   │   ├── pages/            # 페이지 컴포넌트
│   │   ├── hooks/            # 커스텀 훅
│   │   ├── utils/            # 유틸리티 함수
│   │   ├── services/         # API 클라이언트
│   │   └── styles/           # 스타일 파일
│   ├── public/               # 정적 파일
│   └── tests/                # 프론트엔드 테스트
│
├── ml/                        # ML 파이프라인 및 모델 관련
│   ├── data_generation/       # 데이터 생성 모듈
│   ├── training/              # 학습 파이프라인
│   ├── evaluation/            # 평가 시스템
│   ├── serving/               # 모델 서빙
│   ├── pipelines/             # 파이프라인 정의
│   └── tests/                 # ML 테스트
│
├── services/                   # 공통 서비스
│   ├── database/              # 데이터베이스 설정
│   ├── cache/                 # Redis 캐시 설정
│   ├── monitoring/            # 모니터링 설정
│   └── deployment/            # 배포 설정
│
├── docs/                       # 문서
│   ├── PRD.md                 # 제품 요구사항 문서
│   ├── WBS.md                 # 작업 분해 구조
│   └── PROJECT_STRUCTURE.md   # 프로젝트 구조 문서
│
├── scripts/                    # 유틸리티 스크립트
├── tests/                      # 통합 테스트
├── .github/                    # GitHub 설정
│   └── workflows/             # GitHub Actions
│
├── .gitignore                 # Git 무시 파일
├── README.md                  # 프로젝트 소개
├── CONTRIBUTING.md            # 기여 가이드
├── CLAUDE.md                  # Claude Code 가이드
├── docker-compose.yml         # Docker Compose 설정
├── Dockerfile.backend         # 백엔드 Dockerfile
└── Dockerfile.frontend        # 프론트엔드 Dockerfile
```

## 디렉토리 설명

### backend/
FastAPI 기반 백엔드 애플리케이션
- `api/`: RESTful API 엔드포인트
- `core/`: 설정, 보안, 데이터베이스 연결 등
- `models/`: SQLAlchemy ORM 모델
- `schemas/`: 요청/응답 검증을 위한 Pydantic 스키마
- `services/`: 비즈니스 로직 구현
- `utils/`: 공통 유틸리티 함수

### frontend/
React/Next.js 기반 프론트엔드 애플리케이션
- `components/`: 재사용 가능한 UI 컴포넌트
- `pages/`: 라우팅을 위한 페이지 컴포넌트
- `hooks/`: 커스텀 React 훅
- `services/`: API 통신 로직

### ml/
머신러닝 관련 모듈
- `data_generation/`: LLM API를 통한 데이터 생성
- `training/`: 모델 학습 파이프라인
- `evaluation/`: 모델 평가 및 벤치마킹
- `serving/`: vLLM 기반 모델 서빙
- `pipelines/`: 전체 ML 워크플로우 정의

### services/
인프라 및 공통 서비스
- `database/`: PostgreSQL 설정 및 마이그레이션
- `cache/`: Redis 캐시 설정
- `monitoring/`: Prometheus, Grafana 설정
- `deployment/`: Kubernetes 매니페스트, Helm 차트