# TODO — 남은 것은 사용자 라벨링 배치뿐

> 권위 문서는 `docs/`다. 여기는 **작업 목록**일 뿐 결정의 근거가 아니다 —
> 각 항목은 근거 문서를 가리킨다. 결정이 나면 **먼저 `docs/`를 고치고** 여기에 체크한다.
>
> 구현 진행 상황은 [`docs/impl-progress.md`](./docs/impl-progress.md)가 갖는다.

현 지점 (2026-07-29): **MVP 규칙 5종 전부 가동.** io · L-A(XSD) · L-B 규칙 ①②③⑥이
실로직이다. 정상본 10개 ERROR 0 · 주입 6종 중 5종을 게이트가 막는다.

**남은 것은 하나다** — 사람이 Tableau를 열어야 하는 라벨링 배치(D). 여기에 B4와
E의 수치 항목이 매달려 있다. **코드로 더 진행할 수 있는 것은 없다.**

---

## A. 설계 결정 — ✅ 전부 해소

- [x] **A1. 규칙에 파싱 트리를 어떻게 넘길 것인가**
  - 결정: `check(model)` → **`check(ctx)`**. `ValidationContext`가 모델 + `raw_tree`(정규화 전)
    + `normalized_tree()`(정규화 후, 캐시)를 함께 든다. 파싱은 `inspect.load_context()`에서 1회
  - 산출: `src/twb_lint/validation/context.py` · `docs/03-design.md` D3.5 · 계약 테스트
- [x] **A2. 입력 오류(파일 없음·손상 ZIP)의 처리 주체**
  - 결정: **엔진**. `Stage.INPUT` · `rule_id="input.readable"`로 나가되 규칙 파일은 없다.
    규칙에 맡기면 "컨텍스트를 못 만들어 실패한 상황을 컨텍스트 받는 규칙이 판정"하는 순환
  - 입력에서 멈추면 나머지 규칙 전부를 `SKIPPED`로 기록한다 (침묵 = 통과로 읽힘)
  - 산출: `engine.validate` · `docs/03-design.md` D3.0 · stub 테스트 교체 완료
- [x] **A3. L-A 위반의 심각도 정책**
  - 실측이 판을 바꿨다 — **거짓양성(`explain-data`)과 진짜 오류(R4)가 같은 오류코드**
    (`SCHEMAV_ELEMENT_CONTENT`)를 쓴다. 코드만으로는 못 가른다
  - 결정: 열거형·데이터타입 위반 → ERROR · `not expected` → ERROR ·
    `Missing child element` → WARNING · 미분류 → WARNING. **검증한 릴리스에서만** ERROR
  - 산출: `syntactic/xsd.py` `severity_for()` · `docs/03-design.md` D3
- [x] **A4. "검사 안 함"을 리포트가 표현할 방법**
  - 결정: `ValidationReport.coverage: tuple[CoverageNote, ...]` (`ran`/`partial`/`skipped`).
    `passed` = "검사한 범위에서 ERROR 없음", `fully_covered` = "전부 검사했음"
  - 산출: `models.py` · `context.note_skip()/note_partial()` · `docs/03-design.md` D3 출력
- [x] **A5. `Finding`에 라인 번호 추가**
  - 결정: `line: int | None`. 정렬 키 = `rule_id → line → location`. 줄번호 없는 finding은 앞
  - 산출: `models.py` `Finding.sort_key` · `engine.py` · 회귀 테스트 2건
- [x] **A6. calc을 어디서 걷을 것인가** — 표본 9개 전수 실측
  - 수식 표면 **2곳**: `<calculation@formula>` 4,757회 + **`<groupfilter@expression>`** 3회
  - `groupfilter@expression`이 `//` 주석 · XML 엔티티 · 개행을 **전부** 담고 있었다
  - 직접 참조 표면 7곳 (`column-instance@column`·`format@field`·`filter@column` 등)
  - ⚠️ **표기가 2종이다** — calc 안 `[Calculation_1234]` vs 속성 `[ds].[usr:…:qk]`.
    정규화 없이 대조하면 규칙 ②가 전량 dangling을 뱉는다. `[:Measure Names]` 1,294회
  - 산출: `docs/03-design.md` **D3.6** · `docs/07` G8
- [x] **A7. 신뢰 못 할 입력 방어 정책**
  - 결정: `io/safety.py`에 파서 팩토리 + 상한. XXE·엔티티 폭탄·zip slip·zip bomb
  - **파서는 `safety.make_parser()`로만** 만든다 (기본 파서는 엔티티를 해석한다)
  - 상한은 실측 대비 수십 배 — 정상 파일을 막는 방어는 그 자체로 AC7 위반
  - 산출: `io/safety.py` · `docs/03-design.md` **D9** · 실제 페이로드 테스트
- [x] **A8. 규칙 ⑥의 version 상호작용 (기록만)**
  - 산출: `docs/01-problem-definition.md` **§9.2**. MVP(read-only)엔 무해, C4 편집기에서 터진다

## B. 데이터·전제 확보

- [x] **B1. 공식 XSD 원본 확보** — 정식 경로 승격 완료
  - `tools/vendor_schemas.py` 구현: 상류(GitHub) 또는 로컬 클론 → 패치 3건 → 컴파일 검증
  - **패치를 목록으로 코드에 둔다.** 매치 횟수까지 단언하고, 하나라도 실패하면 vendoring 실패
  - 라이선스: **Apache-2.0** (Salesforce). 재배포 가능 — `data/schemas/NOTICE`에 표기
  - 검증: 정상본 **9/9 통과** (우리 코드 경로 `fcp` + `safety.make_parser`로 재확인)
- [x] **B2. 함수 화이트리스트 1회 스크랩**
  - `tools/scrape_functions.py` → `functions_2026.1.json` **218종**, 10페이지
  - 앵커만으로는 불완전(`WINDOW_SUM`·`RANK_DENSE` 누락) → 앵커 ∪ 본문 시그니처 − 블랙리스트
  - 누락은 **노이즈일 뿐 게이트를 무력화하지 않는다**(규칙 ①은 WARNING 기조, S1-6)
- [x] **B3. fcp ↔ 매니페스트 대응 스파이크** — 완료 (2026-07-29)
  - 결과: 매니페스트 항목 이름에도 fcp 접두사가 붙는다 → 10/10 완전 일치.
    규칙 ⑥-a는 **표 없이** 구조에서 도출된다. 항목 이름 22종 확보(매핑 미지 16종)
  - 근거: `docs/05-xsd-spike.md` F7 · 구현: `src/twb_lint/fcp.py`
- [ ] **B4. E2E baseline 1회 실측** ⏸ **사용자 배치 대기** (= D4)
  - AC5(속도) 목표 배수를 정하려면 "Tableau 실행→렌더" 시간이 필요하다. **Tableau 실행이 필수**
  - D 배치와 함께 진행한다 (어차피 Tableau를 여는 김에 1회 계측)
  - 산출 예정: 측정치 1건을 `docs/03-design.md` D5에 기록
- [x] **B5. AC3 회귀 코퍼스 발굴 판단** — 결론: **불가, 대안으로 대체**
  - `old/generate-report`가 이 머신에 없다(경로 부재 확인). 함정 문서 원본을 열 수 없다
  - 그러나 그 자산은 이미 `docs/06-rule-candidates.md`에 **규칙 후보로 번역돼 있다** —
    R1~R13이 그 산물이다. 원본 없이도 주입 레시피는 성립한다
  - 남은 한계: "모르는 실패는 정의상 못 잰다"는 문제는 그대로다. 표본 확대로만 줄어든다

## C. 테스트 인프라 — ✅ 전부 완료

- [x] **C1. 골든셋 경로 외부화**
  - `TWB_LINT_GOLDEN_NORMAL` / `TWB_LINT_GOLDEN_BROKEN` 환경변수(`;` 구분 glob).
    미설정 시 skip → 이 PC 밖에서도 나머지 테스트가 전부 돈다
  - **커밋 회피 사유를 정정했다: 용량이 아니라 사내 재무 데이터 기밀이다**
  - 산출: `tests/conftest.py` · `docs/03-design.md` D5 · `docs/07` §2
- [x] **C2. 규칙별 단위 테스트 계층**
  - `tests/fixtures/builder.py` — 최소 `.twb` 조각 빌더(`make_twb`/`make_ctx`).
    실측 표기(`[ds].[usr:name:qk]`)를 그대로 낼 수 있다
  - `tests/unit/test_rules_contract.py` — 규칙 계약 4종을 **등록된 전 규칙에 자동 적용**.
    새 규칙을 추가하면 자동으로 검사에 태워진다
  - `test_fcp.py`·`test_safety.py`·`test_vendored_data.py` 추가
- [x] **C3. 정상 표본 편향 기록**
  - 9개 중 7개가 MA_002 변형 → **실제 다양성 3종**. "9개 ERROR 0건"은 인상보다 약한 근거
  - 산출: `docs/03-design.md` D5 · `docs/01` §9.2 · `docs/07` §2
- [x] **C4. `.hyper` 무손실의 측정 기준**
  - **AC8 신설** — `unpack → pack` 라운드트립 **바이트 동일성**. 등가성이 아니라 동일성
  - 산출: `docs/02-specification.md` S4 AC8 · `docs/03` D5 · 테스트
  - **2026-07-29 통과.** `io/twbx.pack` 구현으로 xfail이 뒤집혔고 마커를 제거했다.
    여기가 다시 xfail로 돌아가면 무손실 보존이 깨진 것이다
  - 부수 확인: 주입 스크립트가 만든 고장본 6개에서 `.hyper` **6/6 바이트 동일**

## D. 사용자 라벨링 배치 — ⏸ **유일하게 남은 블로커**

로컬 Tableau Desktop 2026.1이 **유일한 정답지**다 — 공식 검증 REST API는 Cloud 전용이라 못 쓴다(S7).
**한 배치로 몰아서 한 번에** 진행한다 (두 번 부르지 않기).

**고장본은 이미 만들어져 있다** — `tools/inject_defects.py`가 결정론적으로 생성한다.
사용자가 할 일은 **열어 보고 결과를 적는 것뿐**이다.

```bash
# 기본 레시피 6종
.venv/Scripts/python tools/inject_defects.py --source <원본.twbx> --out <디렉토리>

# 실험 B까지 (매니페스트 항목 16종을 하나씩 삭제)
.venv/Scripts/python tools/inject_defects.py --source <원본.twbx> --out <디렉토리> --experiment-b
```

산출 디렉토리의 `labels.json`에 `observed`·`error_text` 칸이 비어 있다. 그것을 채우면 된다.

- [ ] **D1. 실험 A — 규칙 ⑥-a 인과 확정** (파일 1개)
  - 레시피 `R1a-drop-fcp-manifest-item`. 거부되면 ⑥-a를 ERROR로 승격, 열리면 fcp는 상관일 뿐
- [ ] **D2. 실험 B — 일반 항목 요소 매핑 캐기** (파일 ~16개)
  - 거부 메시지 `no declaration found for element '<요소>'`가 답을 준다
  - 성공 시 `data/manifest_gates.json`의 `known_items_unmapped` → `gates`로 승격
- [ ] **D3. 기존 주입 레시피 라벨 확정** (R1b·R2·R3·R4·R7)
  - **R4·R7은 이미 L-A가 잡는 것이 확인됐다** — 라벨은 "실제로 안 열리는가"를 확정하는 용도
  - **R1b·R2·R3는 L-A를 그대로 통과한다** = AC3 무거짓통과의 실증. L-B 규칙의 존재 근거
- [ ] **D4. E2E baseline 계측** (B4와 동일 — 파일 1개를 열어 시간만 재면 된다)

**보고 형식** (이것만 있으면 된다): ① 열림 ② 안 열림 + **에러 문구/코드 원문**
(`2805CF18`, `D2E8DA72`, `no declaration found…`) ③ 열리는데 이상함 + 무엇이

주입 규칙: **결함 1개씩** · **복사본에만**(원본 9개 불가침) · 배치로. — 스크립트가 전부 지킨다.

## E. 후속 (구현 중/후로 미뤄도 됨)

- [x] XSD 컴파일 캐시 — `xsd.load_schema()` 경로 키 `lru_cache`. 함수 목록·매니페스트 표도 같은 방식.
  ⚠️ 캐시된 `XMLSchema`는 호출 간 공유된다 — 서버를 멀티스레드로 돌리면 락이 필요하다(코드에 명시)
- [ ] AC2/AC5 목표 수치 확정 — D 배치 후 (02 S6)
- [ ] D8 `tablangres.rcc` 역수확 — **조건부**. 실험 B가 실패하거나 커버리지가 낮을 때만
- [ ] 표본 확대 — AC7의 신뢰도는 표본 다양성(현재 3종)에 직접 묶여 있다

---

## 완료 로그

| 날짜 | 항목 | 결과 |
|---|---|---|
| 2026-07-28 | XSD 스파이크 | L-A 성립, 단 전처리 3단계 전제 (05 F1~F6) |
| 2026-07-29 | 문서·코드 drift 해소 | 규칙 ⑥ 골격 · findings 정렬 · stub 테스트 표시 (04 v1.1) |
| 2026-07-29 | B3 fcp↔매니페스트 스파이크 | 규칙 ⑥-a는 표 불필요 · 항목 22종 확보 (05 F7) |
| 2026-07-29 | **A1~A8 설계 결정 8건** | 규칙 입력 계약 · 입력 단계 · 심각도 정책 · coverage · 줄번호 · calc 표면 · 입력 방어 (03 v1.3) |
| 2026-07-29 | **B1·B2 데이터 확보** | vendored XSD(9/9 통과) · 함수 218종 |
| 2026-07-29 | **C1~C4 테스트 인프라** | 3층 구조 · 골든셋 외부화 · AC8 신설 |
| 2026-07-29 | **D 준비** | 주입 스크립트 + 라벨 대장. `.hyper` 무손실 6/6 · AC3 실증 확보 |
| 2026-07-29 | **구현 1~4단계** | io(AC8 통과) · L-A · calc · 규칙 ①②③⑥. 정상본 ERROR 0 · 주입 5/6 차단 |
| 2026-07-29 | 설계 뒤집기 3건 | calc을 어휘 스캐너로(D3.7) · `]]` 이스케이프(D3.6.1) · **규칙 ② ERROR→WARNING**(D3.6.3) |

## 다음 한 걸음

**D 배치다. 코드로 갈 수 있는 데까지 갔다.**

```bash
.venv/Scripts/python tools/inject_defects.py --source <원본.twbx> --out <디렉토리> --experiment-b
```

산출 디렉토리의 `labels.json`에서 `observed`·`error_text`를 채운다. 우선순위:

| | 파일 수 | 이것이 푸는 것 |
|---|---|---|
| **D1** `R1a-drop-fcp-manifest-item` | **1개** | 규칙 ⑥-a 심각도. **지금 게이트를 통과하는 유일한 결함** |
| **D3** R1b·R2·R3·R4·R7 | 5개 | 게이트가 막는 것들이 실제로 안 열리는지 → AC3 실증 완성 |
| **D2** 실험 B | ~16개 | 매니페스트 요소 매핑. 규칙 ⑥-b 커버리지 2쌍 → 최대 18쌍 |
| **D4** 정상본 | 1개 | AC5 baseline (= B4) |

**D1이 가장 값싸고 값지다** — 파일 1개로 규칙 하나의 심각도가 정해진다.

라벨이 들어오면 코드 쪽에서 할 일: `manifest_gates.json` 승격 · 규칙 ⑥-a 심각도 조정 ·
규칙 ② 표면별 ERROR 승격 검토(dangling 0인 표면 4종) · AC2/AC3/AC5 수치를 02·03에 고정.
