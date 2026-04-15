# Changelog: OSINT System (Monorepo)

이 통합 저장소의 변경 사항을 기록합니다.
(기존 `intelligence` 엔진과 `osint-dashboard` 대시보드가 단일 시스템으로 통합되었습니다.)

---

## [3.1.0] - 2026-04-15 (Event-Driven Architecture & Scheduler)

### 🚀 단일 프로세스(FastAPI) 아키텍처 개편 및 스케줄링 고도화
기존 파일 폴링(Polling) 방식의 비효율을 제거하고, FastAPI 기반의 메모리-이벤트 구동 방식으로 시스템을 완전히 재설계했습니다.

### Added
- **UI 크롤러 스케줄 통제 (`osint-dashboard`)**: 대시보드의 설정 메뉴 내에서 크롤링 예약 윈도우(KST 기준, 다중 시간 설정) 및 "즉시 크롤링 시도" 버튼 추가.
- **KST 타임존 강제 동기화 (`docker-compose.yml`)**: 스케줄러 오작동 버그를 방지하기 위해 각 컨테이너의 시스템 시간대를 한국 표준시(`TZ=Asia/Seoul`)로 고정.

### Changed
- **모노레포 디렉토리 직관적 개명**: `intelligence` 폴더를 `collector`로, `osint-dashboard` 폴더를 `analyzer`로 변경하여 역할을 명확히 제시.
- **`collector/main.py` 통합 백엔드 구성**: 기존 분리된 쉘 스크립트 실행(`start.sh`) 구조를 폐기하고, `FastAPI` 기반 단일 프로세스로 `collector.py`와 API 서버를 병합. 내부에 `APScheduler`를 장착하여 메모리 공유.
- **이벤트-메모리 트리거 최적화**: 즉시 실행 명령 등의 REST API 요청 인입 시 백그라운드 태스크로 `run_crawl_cycle()`이 즉시 트리거되도록 딜레이 타임랙을 제거.

---

## [3.0.0] - 2026-04-15 (Monorepo Integration)

### 🚀 아키텍처 대통합
독립적인 두 개의 리포지토리(`intelligence`, `osint-dashboard`)를 하나의 모노레포(`osint-system`)로 통합하였습니다.

### Added & Changed
- **모노레포화**: 최상위 폴더 레벨로 두 프로젝트를 이동 및 병합. 통합 `.git` 관리 체계 구축 기반 마련.
- **Microservices 오케스트레이션**: 루트 디렉토리에 통합 `docker-compose.yml` 추가
  - `intelligence` 서비스와 `osint-dashboard` 서비스를 단일 네트워크(`osint-net`)로 매핑
  - `osint-dashboard`가 컨테이너 내부 통신(`http://intelligence:5050`)을 통해 매체 신뢰도 API 연동 수행
- **API 연동 최적화**: 
  - `intelligence` 수집기 컨테이너 내부에 `reliability_viewer.py`를 함께 백그라운드로 띄우도록 `start.sh` 스크립트 적용
  - `osint-dashboard`의 SQLite 직접 접근 방식을 HTTP REST API(`httpx`) 내부 프록시 호출로 전환하여 결합도 낮춤. 안전한 마이크로서비스 설계 완성.

### Fixed
- **환경 변수 유실 버그 수정**: 모노레포 통합 과정에서 `intelligence` 서비스가 `DB_IP` 환경 변수를 전달받지 못해 Qdrant 접속을 localhost로 시도하다가 충돌(Crash) 및 종료되던 문제를 해결 (`docker-compose.yml`에 환경 변수 바인딩 추가)

---

## [2.1.0] - 2026-04-15 (Intelligence Legacy)

### 🕵️ 감찰관 모듈(evaluator.py) 신규 구현

수집기가 Qdrant에 기사를 적재한 직후, 비동기 훅을 통해 자동으로 매체 신뢰도를 평가하는 **감찰관 모듈**을 구현하고 시스템에 통합했습니다.

### Added

- **`evaluator.py` — `SourceEvaluator` 클래스 전면 구현**
  - SQLite `source_reliability` 테이블 자동 생성 (source_id, status, strikes 등 9개 컬럼)
  - **4단계 평가 파이프라인:** (upsert -> Qdrant 유사도 검증 -> LLM 분석 -> 점수/상태 갱신)
  - **상태 판정 규칙:** BLACKLISTED, TRUSTED, PROBATION 등 지원.
  - 모든 내부 예외 격리 메커니즘 제공 및 LLM 폴백/Mock 지원.

### Changed

- **`collector.py` — 훅 시스템 통합**
  - 메인 수집 루프에 `article_inserted` 훅 연동
  - LLM 호출용 `httpx.AsyncClient`의 수명을 전체 라이프사이클과 동일하게 관리.

---

## [2.0.0] - 2026-04-13 (Intelligence Legacy)

### 🚀 자율형 OSINT Collector 2.0

### Added

- RSS 기반 자율 수집 엔진 (`collector.py`)
- `trafilatura` 1차 + `llama3` 2차 하이브리드 본문 추출
- Overlap 기반 지능형 텍스트 청킹 (2500자, 300자 겹침)
- `bge-m3` 임베딩 + Qdrant 벡터 저장
- 지원 플랫폼 연동 및 상태 추척(Docker, YAML 설정, CSV 데이터화 등)
