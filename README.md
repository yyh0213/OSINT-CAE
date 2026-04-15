# 🌐 OSINT System (Monorepo)

최신 OSINT 데이터를 수집·임베딩하는 **Intelligence 백엔드 엔진**과, 수집된 데이터를 바탕으로 AI 자동 보고서를 생성하여 시각화하는 **OSINT Dashboard**가 통합된 시스템입니다.

---

## ✨ 아키텍처 개요 (Microservices)

이 저장소는 두 가지 주요 서비스를 통합 관리합니다.
1. **`collector/`**: RSS 기반으로 게시물을 파싱하고, LLM을 이용해 기사를 정제/요약한 뒤 Qdrant(벡터DB)와 SQLite에 메타데이터 및 신뢰도를 적재합니다.
2. **`analyzer/`**: 수집된 데이터를 조회하여 데일리 리포트를 생성하고, 채팅 인터페이스와 매체 신뢰도 시각화 대시보드를 제공합니다.

---

## 🚀 빠른 시작 (Docker Compose — 권장)

최상위 디렉토리에 포함된 통합 `docker-compose.yml`을 통해 **백엔드 수집기**와 **대시보드 Web서버**를 한 번에 빌드하고 구동할 수 있습니다.

### 1단계: 환경 변수 설정
```bash
cp analyzer/.env.sample analyzer/.env
nano analyzer/.env          # 실제 API 키와 IP 주소 삽입
```

### 2단계: 폴더 권한 부여 및 마운트 준비 (Linux)
```bash
# 로컬 저장용 리포트 폴더 생성
mkdir -p analyzer/OSINT_REPORT
```

### 3단계: 통합 컨테이너 띄우기
루트 디렉토리(`osint-system` 폴더)에서 다음 명령어를 실행합니다.
```bash
docker compose up -d --build
```
> 브라우저에서 `http://localhost:8000`에 접속하여 대시보드를 사용할 수 있습니다!

---

## 📂 리포지토리 구조

```text
osint-system/
├── docker-compose.yml            # 전체 시스템 통합 실행 포맷
├── README.md                     # 공통 가이드 라인
├── CHANGELOG.md                  # 통합 변경/업데이트 이력 보관
│
├── collector/                    # (Core) 자율 수집 분석 엔진 
│   ├── collector.py              # 데이터 수집 코어 프로세스
│   ├── evaluator.py              # 데이터 및 매체 신뢰성 검증기
│   ├── main.py                   # (Core/API) 통합 스케줄러 & 신뢰도 조회용 FastAPI 백엔드
│   └── config/                   # RSS YAML 타겟 정보 및 SQLite DB 보유
│
└── analyzer/                     # (Frontend) 브리퍼 & 뷰어 대시보드
    ├── analyzer.py               # AI 보고서 작성 코어 (OpenRouter 연동)
    ├── .env.sample
    └── report_viewer/
        ├── server.py             # FastAPI 대시보드 백엔드
        └── static/               # HTML/JS/CSS 프론트엔드 자원
```

---

## 📝 관리 패러다임 (Monorepo)

이제 두 서브 시스템은 내부 Docker Bridge 망을 통해 서로 HTTP 통신으로 연결되어 데이터베이스 파일 직접 마운트 구조에서 벗어났습니다. 
개발 및 코드 커밋은 항상 `osint-system` 루트 레벨에서 진행하여 양쪽 프로젝트 패키지 동기화와 히스토리를 깔끔하게 관리하십시오.
