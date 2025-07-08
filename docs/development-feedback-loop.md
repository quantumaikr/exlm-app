# 🔄 개발 피드백 루프 가이드

이 문서는 exlm 프로젝트의 개발 과정에서 발생하는 일반적인 오류들을 자동으로 감지하고 수정하는 개발 피드백 루프 시스템에 대해 설명합니다.

## 🎯 목적

개발 피드백 루프는 다음과 같은 목표를 가집니다:

1. **자동 오류 감지**: 일반적인 개발 오류를 사전에 감지
2. **자동 수정**: 가능한 경우 자동으로 문제 해결
3. **개발 속도 향상**: 반복적인 설정 작업 자동화
4. **일관성 유지**: 코드 스타일과 설정의 일관성 보장

## 🛠 구현된 기능

### 1. 프론트엔드 오류 수정

#### Tailwind CSS 설정 자동 수정
```bash
# 문제: border-border 클래스가 정의되지 않음
# 해결: tailwind.config.ts에 CSS 변수 색상 정의 자동 추가
```

**수정 전:**
```typescript
// tailwind.config.ts
colors: {
  primary: { ... }
}
```

**수정 후:**
```typescript
// tailwind.config.ts
colors: {
  border: "hsl(var(--border))",
  input: "hsl(var(--input))",
  ring: "hsl(var(--ring))",
  background: "hsl(var(--background))",
  foreground: "hsl(var(--foreground))",
  primary: { ... }
}
```

#### 누락된 의존성 자동 설치
- `@mui/icons-material`
- `@mui/x-data-grid`
- `@radix-ui/react-slot`
- `tailwindcss-animate`

#### 기본 UI 컴포넌트 자동 생성
- `/src/components/ui/button.tsx`
- `/src/components/ui/dialog.tsx`
- `/src/components/ui/select.tsx`
- `/src/lib/utils.ts`
- `/src/types/index.ts`

### 2. 백엔드 오류 수정

#### Python 가상환경 자동 설정
```bash
# 가상환경이 없는 경우 자동 생성
python3 -m venv venv

# 의존성 자동 설치
pip install -r requirements.txt
```

#### 데이터베이스 초기화
```bash
# Alembic 초기화 (필요한 경우)
alembic init alembic
```

### 3. 개발 환경 확인

#### 환경 상태 체크
- Node.js 버전 확인
- Python 버전 확인
- Docker 상태 확인
- Redis 설치 상태 확인

#### 포트 충돌 감지
- 프론트엔드 포트 (3000) 사용 여부 확인
- 백엔드 포트 (8000) 사용 여부 확인

## 🚀 사용 방법

### 1. 자동화된 개발 시작

#### 프론트엔드
```bash
cd frontend
npm run dev          # 자동 체크 + 개발 서버 시작
npm run dev:check     # 체크만 실행
npm run dev:force     # 체크 없이 개발 서버 시작
npm run fix          # 종합 수정 실행
```

#### 통합 스크립트
```bash
# 프로젝트 루트에서
./scripts/dev-feedback-loop.sh
```

### 2. 개별 도구 사용

#### 프론트엔드 개발 피드백 루프
```bash
cd frontend
node scripts/dev-feedback-loop.js
```

#### ESLint 자동 수정
```bash
npm run lint:fix
```

#### Prettier 포맷팅
```bash
npm run format
```

#### TypeScript 타입 체크
```bash
npm run type-check
```

## 🔧 자동 수정 항목

### ✅ 자동으로 수정되는 문제들

1. **Tailwind CSS 설정 누락**
   - CSS 변수 색상 정의 추가
   - darkMode 설정 추가

2. **누락된 패키지 설치**
   - UI 라이브러리 의존성
   - 개발 도구 의존성

3. **기본 파일/디렉토리 생성**
   - UI 컴포넌트 디렉토리
   - 유틸리티 함수 파일
   - 타입 정의 파일

4. **코드 스타일 통일**
   - ESLint 자동 수정
   - Prettier 포맷팅

### ⚠️ 수동 수정이 필요한 문제들

1. **TypeScript 타입 오류**
   - 복잡한 타입 정의
   - 외부 라이브러리 타입 충돌

2. **로직 오류**
   - 비즈니스 로직 버그
   - API 연동 오류

3. **환경별 설정**
   - 프로덕션 환경 설정
   - 개발자별 로컬 설정

## 📋 체크리스트

개발 시작 전 다음 사항들을 확인하세요:

### 환경 요구사항
- [ ] Node.js 18+ 설치
- [ ] Python 3.9+ 설치
- [ ] Docker 설치 및 실행 (선택사항)
- [ ] Redis 설치 (선택사항)

### 프로젝트 설정
- [ ] 프론트엔드 의존성 설치: `npm install`
- [ ] 백엔드 가상환경 설정: `python -m venv venv`
- [ ] 환경변수 파일 설정: `.env`

### 개발 서버 실행
- [ ] 프론트엔드: `npm run dev`
- [ ] 백엔드: `uvicorn main:app --reload`

## 🐛 트러블슈팅

### 일반적인 문제 해결

#### 1. Tailwind CSS 클래스 오류
```bash
# 문제: 클래스가 정의되지 않음
# 해결: 개발 피드백 루프 실행
npm run dev:check
```

#### 2. 패키지 설치 오류
```bash
# 캐시 클리어 후 재설치
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

#### 3. TypeScript 컴파일 오류
```bash
# 타입 체크만 실행
npm run type-check

# 점진적 수정을 위해 strict 모드 일시 비활성화
# tsconfig.json에서 "strict": false
```

#### 4. 포트 충돌
```bash
# 사용 중인 포트 확인
lsof -i :3000
lsof -i :8000

# 프로세스 종료
kill -9 <PID>
```

## 🔄 지속적 개선

개발 피드백 루프는 지속적으로 개선됩니다:

1. **새로운 오류 패턴 감지** 시 자동 수정 로직 추가
2. **개발자 피드백** 기반 기능 개선
3. **성능 최적화** 및 안정성 향상

## 📝 기여 방법

새로운 자동 수정 기능을 추가하려면:

1. `frontend/scripts/dev-feedback-loop.js` 수정
2. `scripts/dev-feedback-loop.sh` 업데이트
3. 테스트 후 PR 생성

---

이 시스템을 통해 개발자는 설정과 환경 문제에 시간을 낭비하지 않고 핵심 개발 작업에 집중할 수 있습니다.