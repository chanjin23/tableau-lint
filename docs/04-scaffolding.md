# Tableau 저작 AI — 스캐폴딩 (Scaffolding)

> SOR 문서. 설계 [`03-design.md`](./03-design.md), 인덱스 [`tableau-ai-sor.md`](./tableau-ai-sor.md). 코드 사용법은 루트 [`README.md`](../README.md).

## 문서 관리

| 항목 | 값 |
|---|---|
| 상태 | ✅ 완료 (골격 + stub, 전 검사 green) |
| 버전 | v1.2 (2026-07-29) |
| 다음 | 구현 — I/O 실로직 → XSD → L-B MVP 4규칙 |
| v1.1 변경 | 스파이크 후 벌어진 drift 해소 — 규칙 ⑥ 골격 반영 · findings 정렬 구현 · stub 테스트 표시 |
| v1.2 변경 | **남은 미결 3건 해소** + A그룹 8건 결정 · vendored XSD·함수목록 확보 · 테스트 3층 · 주입 스크립트 |

---

## 확정 결정

| 항목 | 값 |
|---|---|
| 이름 | `twb-lint` (모듈 `twb_lint`) |
| 구조 | 단일 패키지 + src-layout |
| MCP SDK | 공식 `mcp[cli]` (설치 확인: mcp 1.28.1) |
| 빌드툴 | `uv` (0.10.4) |
| Python | 3.11+ (실행환경 3.14) |
| 품질 | ruff · mypy(strict) · pytest — 전부 green |
| 철학 | **mandatory gate** — `ValidationReport.passed = ERROR 없음` |

## 확장성 3대 메커니즘 (실증됨)

1. **코어↔MCP 분리** — `twb_lint/`는 MCP 미의존. `twb_lint/mcp/server.py`만 어댑터. 코어 순수 import로 `engine.validate` 동작 확인.
2. **규칙 플러그인 레지스트리** — `registry._discover()`가 `syntactic/`·`semantic/` 하위 모듈을 pkgutil로 자동 import. **새 규칙 = 파일 1개 + `@register`, 코어 무수정.** (현재 5규칙이 나열 없이 자동수집됨 — 규칙 ⑥을 파일 1개로 추가하며 실증됐다)
3. **통합 `Finding`/`ValidationReport`** — 전 단계 공용. stage 추가로 L-C(E2E) 확장 가능.

**대가**: pkgutil 순회 순서 = 파일시스템 순서다. 그대로 두면 출력 순서가 환경에 따라 흔들려
결정론(02 S1-5)이 깨진다. → `engine.validate_model`이 `stage → rule_id → location`으로
**정렬해서 반환한다.** 개별 규칙은 반환 순서를 신경 쓰지 않는다.

## 생성물

- `pyproject.toml` · `README.md` · `.gitignore`
- `src/twb_lint/` — `models.py`·`config.py`·`inspect.py`·`cli.py` + `io/`·`calc/`·`validation/`(engine·rule·registry·syntactic·semantic)·`data/`·`mcp/`
- `src/twb_lint/data/manifest_gates.json` — 기능↔매니페스트 대응표 (규칙 ⑥. 실측 2쌍, 확장 경로 = 03 D8)
- `tests/` — `unit/test_smoke.py`(5 pass) + `golden/`(placeholder)
- `tools/` — `scrape_functions.py`·`vendor_schemas.py`(stub)

전체 트리·인터페이스 계약은 플랜 Part IV / 루트 README 참조.

## 검증 (실행 결과)

```
uv sync --extra dev          # OK
uv run pytest -q             # 5 passed
uv run ruff check .          # All checks passed
uv run mypy                  # Success: no issues (26 files)
# MCP 부팅 → tools: twb_inspect, twb_unpack, twb_validate
# registry → calc.field_refs, calc.functions, manifest.gates, named.refs, xsd.schema
```

> 이 머신에서는 `uv`가 차단된다 → 아래 "개발 환경" 절의 `.venv/Scripts/python -m …`로 읽는다.

## stub 테스트 표시 (v1.1)

`@pytest.mark.stub`가 붙은 테스트는 **stub 상태의 사실을 단언한다.** 실로직이 들어오면
반드시 깨지며, 그때 고칠 것은 코드가 아니라 테스트다.

현재 1건 — `없는 파일도 PASS`(규칙이 전부 `return []`, I/O 미구현이라 파일 미접근).
구현 시 파일 없음은 예외가 아니라 **ERROR finding**이 돼야 한다(02 S5).
표시가 없으면 "구현했더니 테스트가 깨졌다 = 내가 틀렸나?"로 헤매게 된다.

```bash
.venv/Scripts/python -m pytest -q -m "not stub"   # 부채 제외하고 돌리기
```

## 개발 환경 — 머신별 제약 (2026-07-28 추가)

**Smart App Control이 켜진 Windows에서는 `uv`를 실행할 수 없다.**

```
VerifiedAndReputablePolicyState = 1   (켜짐 — 끄면 Windows 재설치 전까지 재활성화 불가)
uv.exe = NotSigned
→ Program 'uv.exe' failed to run: An Application Control policy has blocked this file
```

winget본·PyPI본 모두 동일하게 차단된다(배포 경로가 아니라 바이너리 서명 문제).

**우회**: 새 실행파일을 띄우지 않고 서명된 `python.exe`만 쓴다.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q       # 4 passed
.venv/Scripts/python -m ruff check .    # All checks passed
.venv/Scripts/python -m mypy            # Success: no issues in 25 source files
```

`pytest.exe` 같은 콘솔 런처 대신 `python -m`으로 부르는 것이 요점이다.

한계: `uv.lock`의 정확한 핀을 pip이 못 읽어 `pyproject.toml` 범위로 설치된다.
dev 툴 용도라 실질 영향은 작지만, **재현성이 필요한 검증은 uv가 되는 머신에서 한다.**

> PC를 옮기면 개발 환경이 조용히 깨진다. 훅(`jq` 부재)·uv(정책 차단) 둘 다 같은 원인이었다.
> 환경 전제를 코드가 아니라 **문서에 남긴다.**

## 왜 v1.1이 필요했나 — 문서·코드 drift (2026-07-28)

```
7/25  이 문서 v1.0 + 코드 골격 생성     (L-B 규칙 3개)
7/28  05-xsd-spike                     (규칙 ⑥ 발견, 정렬 필요 발견)
7/28  01·02·03 → v1.1                  (문서만 따라감)
      04 + 코드                        (v1.0에 멈춤)  ← drift
```

**스파이크가 스캐폴딩보다 늦게 나왔다.** 07이 그 격차를 글로 메웠을 뿐 코드엔 반영이
없었다. 해소한 것:

| 항목 | 문서가 약속 | 코드 상태 | 조치 |
|---|---|---|---|
| 규칙 ⑥ `manifest.gates` | MVP 4규칙 (D0) | 파일 없음, 대응표 없음 | 규칙 파일 + `data/manifest_gates.json` 추가 |
| findings 정렬 | `stage→rule_id→location` (D3) | 등록 순서 그대로 | `engine.validate_model`에서 정렬 + 회귀 테스트 |
| stub 테스트 | — | 틀릴 동작을 green으로 고정 | `@pytest.mark.stub` 표시 |

**남은 미결(코드 아님, 설계 결정)** — 구현 착수 전에 정한다:

- **규칙이 파싱된 트리를 못 받는다.** `check(model)`뿐이라 XSD 규칙·규칙 ⑥이 1MB XML을
  각자 재파싱해야 한다 (AC5 속도와 충돌). → `WorkbookModel`에 트리 보유 or `ValidationContext`
- **입력 오류(파일 없음·손상 ZIP)의 소유자 미정.** 02 S5는 ERROR finding을 요구하는데
  모델 생성 **전** 단계라 규칙이 맡을 수 없다
- **L-A 위반의 심각도 정책 미정.** `explain-data`가 이미 "XSD가 실제보다 엄격"의 실증 —
  전부 ERROR로 내면 AC7이 위험

## v1.2 — 미결 3건 해소 + 구현 착수 준비 완료 (2026-07-29)

위 3건을 포함해 [`TODO.md`](../TODO.md) A그룹 8건을 전부 정했다. **구현이 아니라 결정과
그 결정을 못 박는 코드**만 넣었다 — 규칙 로직은 여전히 stub이다.

| 미결 | 결정 | 산출 |
|---|---|---|
| 규칙에 트리 전달 | `check(ctx)` — 컨텍스트가 모델 + 원본 트리 + 정규화 사본을 든다 | `validation/context.py` · 03 D3.5 |
| 입력 오류 소유자 | **엔진**. `Stage.INPUT`으로 나가되 규칙 파일은 없다 | `engine.validate` · 03 D3.0 |
| L-A 심각도 | 오류 유형 + **메시지**까지 본다 (거짓양성과 진짜 오류가 같은 코드다) | `syntactic/xsd.py` · 03 D3 |
| "검사 안 함" 표현 | `ValidationReport.coverage` 신설 | `models.py` · 03 D3 |
| 줄번호 | `Finding.line: int \| None` + 정렬 키 반영 | `models.py`·`engine.py` |
| calc 표면 | 실측 확정 — 수식 2곳 · 직접 참조 7곳 · **표기 2종** | 03 D3.6 |
| 입력 방어 | lxml 파서 옵션·ZIP 상한을 io 구현 **전에** 고정 | `io/safety.py` · 03 D9 |
| 규칙 ⑥ × version | 열린 질문으로 기록 | 01 §9.2 |

데이터·인프라도 함께 갖췄다:

- **vendored XSD** (Apache-2.0, 패치 3건 + 컴파일 검증) — 정상본 **9/9 통과 재확인**
- **함수 화이트리스트 218종** (`tools/scrape_functions.py`)
- **테스트 3층** — 스모크 / 규칙 계약·단위(최소 XML 빌더) / 골든셋(env 게이트)
- **결함 주입 스크립트** — 고장본 6종 + 라벨 대장. `.hyper` 무손실 6/6 확인

검사 결과: `64 passed, 1 xfailed`(골든셋 포함) · `ruff` 통과 · `mypy` 29 files 통과.
xfail 1건은 AC8(`.hyper` 라운드트립)이며 `io` 구현과 함께 풀린다.

## 다음 (구현 단계)

1. `io/twbx.py`·`io/twb.py`·`inspect.load_context` 실로직 (unpack/parse/모델추출).
2. `validation/syntactic/xsd.py` — 스키마 로드 + 심각도 적용 (vendoring은 이미 완료).
3. L-B MVP 4규칙(①②③⑥) 실로직 + `calc/extractor.py` Lark 파싱.
4. 사용자 라벨링 배치 → AC2/AC3 측정.

상세 순서와 함정은 [`07-implementation-guide.md`](./07-implementation-guide.md) §4 · G1~G10.
