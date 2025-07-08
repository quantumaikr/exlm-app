# RunPod EXLM 빠른 시작 가이드

RunPod에서 EXLM을 **5분 만에** 시작하는 간단한 가이드입니다.

## 🚀 5분 빠른 시작

### 1. RunPod Pod 생성 (2분)

1. [RunPod.io](https://runpod.io) 접속
2. **"Deploy"** 클릭
3. **Template**: `RunPod PyTorch`
4. **GPU**: RTX 4090 (24GB) 선택
5. **"Deploy"** 클릭

### 2. SSH 접속 (1분)

```bash
# RunPod 웹 콘솔에서 제공하는 SSH 명령어 복사하여 실행
ssh root@[POD_IP] -p [SSH_PORT]
```

### 3. 원클릭 설치 (2분)

```bash
# 한 번의 명령어로 완전 자동 설치
curl -sSL https://raw.githubusercontent.com/quantumaikr/exlm-app/main/scripts/runpod-full-setup.sh | bash
```

### 4. 포트 설정 (1분)

1. RunPod 웹 콘솔 → Pod → **"Edit"**
2. **Ports** 섹션에서:
   - **3000** → **Public** (Frontend)
   - **8000** → **Public** (Backend)
3. **"Save"** 클릭

### 5. 접속 확인

```bash
# Frontend 접속
https://[POD_ID]-3000.proxy.runpod.net

# API 문서 접속
https://[POD_ID]-8000.proxy.runpod.net/docs
```

## 📋 필수 정보

### GPU 추천

| GPU      | 메모리 | 모델 크기 | 비용/시간 |
| -------- | ------ | --------- | --------- |
| RTX 4090 | 24GB   | 7B-13B    | $0.60     |
| A100     | 40GB   | 13B-70B   | $2.00     |
| H100     | 80GB   | 70B+      | $4.00     |

### 필수 포트

- **3000**: Frontend (웹 UI)
- **8000**: Backend API

### 접속 URL 형식

```
https://[POD_ID]-[PORT].proxy.runpod.net
```

## 🛠️ 관리 명령어

```bash
cd /workspace/exlm-app

# 서비스 관리
./start-all.sh    # 모든 서비스 시작
./stop-all.sh     # 모든 서비스 중지
./restart.sh      # 서비스 재시작
./status.sh       # 상태 확인

# 로그 확인
tail -f logs/backend.log    # 백엔드 로그
tail -f logs/frontend.log   # 프론트엔드 로그
```

## 🔧 문제 해결

### 의존성 충돌 오류

```bash
cd /workspace/exlm-app/backend
chmod +x ../scripts/fix-dependencies.sh
../scripts/fix-dependencies.sh
```

### 서비스 시작 안됨

```bash
cd /workspace/exlm-app
./restart.sh
./status.sh
```

### 포트 접근 안됨

- RunPod 웹 콘솔에서 포트가 **Public**으로 설정되었는지 확인

## 💡 팁

1. **Spot 인스턴스**: 70% 할인으로 사용
2. **자동 종료**: 사용 후 자동 종료 설정
3. **API 키 설정**: `backend/.env` 파일에서 실제 키 입력

## 📚 상세 가이드

더 자세한 정보는 [RunPod 설치 완전 가이드](RUNPOD_INSTALLATION_GUIDE.md)를 참고하세요.

---

**5분 만에 EXLM 플랫폼 시작 완료!** 🚀
