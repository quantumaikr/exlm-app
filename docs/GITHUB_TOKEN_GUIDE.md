# GitHub Personal Access Token 가이드

## 🤔 GitHub Token이 필요한 이유

### **1. GitHub의 보안 정책 변화**

- **2021년 8월부터**: GitHub이 비밀번호 기반 인증 중단
- **Token 필수**: HTTPS를 통한 Git 작업에 Personal Access Token 필요
- **보안 강화**: 더 세밀한 권한 제어 및 보안 향상

### **2. 저장소 접근 권한**

```bash
# ❌ 토큰 없이 시도 (실패)
git clone https://github.com/quantumaikr/exlm-app.git
# fatal: Authentication failed

# ✅ 토큰 사용 (성공)
git clone https://YOUR_TOKEN@github.com/quantumaikr/exlm-app.git
```

### **3. 저장소 유형별 차이**

| 저장소 유형 | 읽기 (Clone) | 쓰기 (Push) | Token 필요 여부            |
| ----------- | ------------ | ----------- | -------------------------- |
| **Public**  | ✅ 가능      | ❌ 불가능   | 읽기: 선택사항, 쓰기: 필수 |
| **Private** | ❌ 불가능    | ❌ 불가능   | 필수                       |

## 🔑 GitHub Personal Access Token 생성 방법

### **1. GitHub 웹사이트 접속**

1. [GitHub.com](https://github.com) 로그인
2. 우측 상단 프로필 클릭 → **Settings**

### **2. Personal Access Token 생성**

1. 왼쪽 메뉴에서 **Developer settings** 클릭
2. **Personal access tokens** → **Tokens (classic)** 클릭
3. **Generate new token** → **Generate new token (classic)** 클릭

### **3. 토큰 설정**

```
Note: EXLM Platform Access
Expiration: 90 days (또는 원하는 기간)

Select scopes:
☑️ repo (전체 저장소 접근)
☑️ read:org (조직 정보 읽기)
```

### **4. 토큰 복사**

- **중요**: 토큰은 한 번만 표시됩니다!
- 안전한 곳에 저장하세요
- 예시: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

## 🚀 사용 방법

### **방법 1: 토큰과 함께 사용**

```bash
# 토큰을 사용한 배포
./deploy-runpod-native.sh ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### **방법 2: 토큰 없이 사용 (Public 저장소)**

```bash
# 토큰 없이 배포 (저장소가 Public인 경우)
./deploy-runpod-native.sh
# 프롬프트에서 'y' 입력하여 계속 진행
```

### **방법 3: 환경 변수 사용**

```bash
# 환경 변수로 토큰 설정
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
./deploy-runpod-native.sh $GITHUB_TOKEN
```

## 🔧 문제 해결

### **문제 1: "Authentication failed" 오류**

```bash
# 원인: 토큰이 없거나 권한 부족
# 해결: 올바른 토큰 사용
git clone https://YOUR_TOKEN@github.com/quantumaikr/exlm-app.git
```

### **문제 2: "Permission denied" 오류**

```bash
# 원인: 토큰 권한 부족
# 해결: repo 권한이 있는 토큰 생성
```

### **문제 3: 토큰 만료**

```bash
# 원인: 토큰이 만료됨
# 해결: 새 토큰 생성 또는 기존 토큰 갱신
```

## 💡 토큰 없이 사용하는 방법

### **Public 저장소인 경우**

```bash
# 1. 직접 클론
git clone https://github.com/quantumaikr/exlm-app.git

# 2. 스크립트 실행
cd exlm-app
chmod +x scripts/deploy-runpod-native.sh
./scripts/deploy-runpod-native.sh
```

### **스크립트 직접 다운로드**

```bash
# 스크립트만 다운로드
curl -sSL https://raw.githubusercontent.com/quantumaikr/exlm-app/main/scripts/deploy-runpod-native.sh -o deploy.sh
chmod +x deploy.sh
./deploy.sh
```

## 🔒 보안 모범 사례

### **1. 토큰 보안**

- 토큰을 공개 저장소에 커밋하지 마세요
- 환경 변수나 보안 저장소 사용
- 정기적으로 토큰 갱신

### **2. 최소 권한 원칙**

```
필요한 권한만 선택:
☑️ repo (저장소 접근 필요시)
☑️ read:org (조직 저장소 접근 필요시)
❌ admin:org (불필요한 권한 제외)
```

### **3. 토큰 관리**

- 사용하지 않는 토큰은 삭제
- 토큰 사용 로그 정기 확인
- 의심스러운 활동 시 즉시 토큰 재생성

## 📋 요약

| 상황                   | 토큰 필요 여부 | 사용 방법        |
| ---------------------- | -------------- | ---------------- |
| **Public 저장소 읽기** | 선택사항       | 토큰 없이 가능   |
| **Private 저장소**     | 필수           | 토큰 필요        |
| **Push/Pull Request**  | 필수           | 토큰 필요        |
| **조직 저장소**        | 대부분 필수    | 토큰 + 조직 권한 |

## 🆘 도움이 필요한 경우

1. **GitHub 공식 문서**: [Personal Access Token 가이드](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
2. **EXLM 프로젝트 Issues**: [GitHub Issues](https://github.com/quantumaikr/exlm-app/issues)
3. **토큰 없이 배포**: `./deploy-runpod-native.sh` 실행 후 'y' 입력
