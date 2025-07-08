📄 PRD: 도메인 특화 LLM 자동화 플랫폼
1. 🎯 목표
오픈소스 LLM 또는 유료 API를 이용하여 특정 도메인 데이터셋을 생성하고, 최신 알고리즘을 조합해 파인튜닝한 뒤, vLLM을 통해 서빙까지 가능한 자동화 플랫폼을 구축한다.

최신 기법(DPO, ORPO, QLoRA, RAG 등)을 사용자가 선택해 조합하면, 이를 코드로 자동 생성하여 새로운 학습 파이프라인을 설계·구현할 수 있도록 한다.

2. 📝 주요 기능
🔷 A. 모델 선택 및 학습
최신 오픈소스 LLM 목록을 UI에서 쉽게 탐색하고 선택 (Llama3, Mistral, Qwen2, Phi-3 등)

선택된 모델과 도메인 데이터로 파인튜닝 진행

소량 데이터에 적합한 LoRA/QLoRA 등의 경량화 학습 지원

최신 기법(LoRA, QLoRA, DPO, ORPO, RAG 등)을 옵션으로 선택 가능

최적화되지 않은 조합은 경고/권장사항 제공

🔷 B. 도메인 데이터 생성
OpenAI / Claude / Gemini API로 합성 데이터 생성

프롬프트 템플릿 관리 및 도메인별 생성 설정

데이터 품질 평가 및 필터링 (deduplication, quality scoring)

생성된 데이터는 바로 학습에 사용 가능

🔷 C. 학습 파이프라인 자동화
데이터 업로드 → 전처리 → 학습 → 평가 → 모델 저장까지 자동 실행

최신 기법을 혼합한 파이프라인 구성 가능

학습 상태, 로그, 메트릭 모니터링 제공

🔷 D. vLLM 서빙
학습이 완료된 모델을 vLLM으로 OpenAI API 호환 형태로 서빙

선택적으로 TGI, FastAPI 등으로 서빙 가능

배포 자동화 및 관리 대시보드

🔷 E. 신규 모델 설계 & 코드 생성
사용자가 최신 기법을 선택형으로 조합해 신규 파이프라인 설계

모델: Base 모델, LoRA/QLoRA, DPO, RAG, 양자화, 서빙 등

설계한 파이프라인을 코드로 자동 생성

학습 스크립트 (train.py)

데이터 파이프라인 (data_pipeline.py)

서빙 코드 (serve.py)

README 및 requirements

생성된 코드는 다운로드 혹은 GitHub에 Push 가능

3. 🖥️ 주요 사용자 흐름
markdown
복사
편집
1️⃣ 로그인 → 프로젝트 생성
    ↓
2️⃣ 모델 선택 & 데이터 생성 or 업로드
    ↓
3️⃣ 최신 기법 조합 선택
    ↓
4️⃣ 학습 파이프라인 설계 & 실행
    ↓
5️⃣ 평가 및 저장
    ↓
6️⃣ vLLM으로 서빙 or 신규 파이프라인 코드 생성
4. 🔧 기술 스택 (예시)
영역	기술/툴
UI	React / Next.js
Backend API	FastAPI
파이프라인 관리	Prefect / Celery
모델 학습	HF Transformers, PEFT, trl
데이터 생성	OpenAI, Claude, Gemini API
코드 생성	Python + Jinja2
서빙	vLLM
모니터링	W&B / MLflow
배포	Docker / Kubernetes

5. 📊 주요 요구사항
카테고리	요구사항
✅ 모델 선택	최신 LLM을 UI에서 선택 가능
✅ 데이터 생성	유료 API로 합성 데이터 생성, 품질관리
✅ 학습 자동화	최신 기법을 조합해 자동 학습
✅ 소량 데이터 대응	QLoRA 등 최신 기법으로 소량 데이터 학습
✅ 최신 알고리즘	DPO, ORPO, QLoRA, RAG 등 지원
✅ 서빙	vLLM으로 OpenAI 호환 API 제공
✅ 신규 설계	최신 기법 조합 → 파이프라인 코드 생성