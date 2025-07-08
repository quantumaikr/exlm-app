# Contributing to exlm

exlm 프로젝트에 기여해주셔서 감사합니다! 이 문서는 프로젝트에 기여하는 방법을 안내합니다.

## 📋 목차

- [행동 강령](#행동-강령)
- [기여 방법](#기여-방법)
- [개발 환경 설정](#개발-환경-설정)
- [코드 스타일](#코드-스타일)
- [커밋 메시지 규칙](#커밋-메시지-규칙)
- [Pull Request 프로세스](#pull-request-프로세스)
- [이슈 리포팅](#이슈-리포팅)

## 행동 강령

이 프로젝트는 모든 참여자가 존중받고 환영받는 환경을 만들기 위해 노력합니다. 모든 기여자는 다음을 준수해야 합니다:

- 서로를 존중하고 친절하게 대하기
- 건설적인 비판과 피드백 제공하기
- 커뮤니티의 이익을 우선시하기

## 기여 방법

### 1. 이슈 확인
- 기존 이슈를 확인하여 중복을 피하세요
- 작업하고 싶은 이슈에 댓글을 남겨 할당받으세요

### 2. Fork & Clone
```bash
# 저장소 Fork 후
git clone https://github.com/yourusername/exlm.git
cd exlm
git remote add upstream https://github.com/originalowner/exlm.git
```

### 3. 브랜치 생성
```bash
git checkout -b feature/your-feature-name
# 또는
git checkout -b fix/your-fix-name
```

## 개발 환경 설정

### Backend (Python)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 개발 도구
```

### Frontend (Node.js)
```bash
cd frontend
npm install
```

### 환경 변수
```bash
cp .env.example .env
# 필요한 API 키와 설정을 .env 파일에 입력
```

## 코드 스타일

### Python (Backend)
- [PEP 8](https://www.python.org/dev/peps/pep-0008/) 준수
- Black으로 코드 포맷팅
- isort로 import 정렬
- mypy로 타입 체크

```bash
# 코드 포맷팅
black backend/
isort backend/

# 린팅
flake8 backend/
mypy backend/

# 테스트
pytest backend/tests/
```

### JavaScript/TypeScript (Frontend)
- ESLint 규칙 준수
- Prettier로 코드 포맷팅

```bash
# 린팅
npm run lint

# 포맷팅
npm run format

# 테스트
npm test
```

## 커밋 메시지 규칙

[Conventional Commits](https://www.conventionalcommits.org/) 규칙을 따릅니다:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type
- `feat`: 새로운 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 스타일 변경 (포맷팅, 세미콜론 등)
- `refactor`: 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 빌드, 도구 설정 등

### 예시
```
feat(api): add model versioning endpoint

- Implement GET /api/models/{id}/versions
- Add version comparison functionality
- Update OpenAPI schema

Closes #123
```

## Pull Request 프로세스

1. **코드 완성도 확인**
   - 모든 테스트 통과
   - 코드 스타일 준수
   - 문서 업데이트 (필요시)

2. **PR 생성**
   - 명확한 제목과 설명 작성
   - 관련 이슈 연결
   - 변경사항 요약

3. **리뷰 대응**
   - 리뷰어의 피드백에 신속히 응답
   - 요청된 변경사항 적용

### PR 템플릿
```markdown
## 개요
이 PR이 해결하는 문제나 추가하는 기능을 설명하세요.

## 변경사항
- 주요 변경사항을 나열하세요
- 
- 

## 테스트
어떻게 테스트했는지 설명하세요.

## 체크리스트
- [ ] 코드가 프로젝트 스타일 가이드를 따름
- [ ] 셀프 리뷰 완료
- [ ] 문서 업데이트 (필요한 경우)
- [ ] 테스트 추가/업데이트
- [ ] 모든 테스트 통과

Fixes #(issue)
```

## 이슈 리포팅

### 버그 리포트
버그를 발견하면 다음 정보를 포함하여 이슈를 생성하세요:

1. **환경 정보**
   - OS 및 버전
   - Python/Node.js 버전
   - 브라우저 (Frontend 이슈의 경우)

2. **재현 단계**
   - 상세한 단계별 설명
   - 예상 동작
   - 실제 동작

3. **로그/스크린샷**
   - 에러 메시지
   - 관련 로그
   - 스크린샷 (UI 이슈의 경우)

### 기능 제안
새로운 기능을 제안할 때:

1. **명확한 설명**
   - 기능의 목적
   - 사용 사례

2. **구현 제안**
   - 가능한 구현 방법
   - API 변경사항 (있는 경우)

## 도움 받기

- GitHub Discussions에서 질문하기
- Discord 채널 참여
- 메인테이너에게 멘션 (@maintainer)

## 라이선스

기여하신 코드는 프로젝트와 동일한 MIT 라이선스로 배포됩니다.