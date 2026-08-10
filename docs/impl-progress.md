# 구현 진행 대장

> **용도**: 구현 루프(`/impl-loop`) 반복 간 상태 전달. 반복은 이전 기억이 없으므로
> 여기가 유일한 연속성이다.
>
> 권위 문서는 `docs/`다 — 여기는 **진행 상황만**. 설계 결정이 생기면 먼저 해당 문서를
> 고치고 여기엔 링크만 남긴다. 구현 순서의 근거는
> [`07-implementation-guide.md`](./07-implementation-guide.md) §4.

**현재** (2026-07-30, 골든셋 걸고 실측): `219 passed` · `ruff All checks passed!`
(골든셋 미설정 시 `205 passed, 14 skipped`)

> ⚠️ **mypy는 이 머신에서 실행이 차단됐다** (2026-07-30, `uv`와 같은 Smart App Control
> 정책 — `mypy/ipc.py`의 base64 확장 로드 실패). 타입 검사가 게이트에서 빠져 있다.

## 🏁 07 §4의 1~4단계 전부 완료

| 주입 레시피 | 판정 | 막은 계층 |
|---|---|---|
| R4 · R7 | ERROR | L-A (XSD) |
| R2 · R3 | ERROR | 규칙 ③ |
| R1b | ERROR | 규칙 ⑥-b |
| R1a | WARNING (의도) | 규칙 ⑥-a — 인과 미검증 |

정상본 10개: **ERROR 0** · WARNING 24 (전부 규칙 ②, 실제 잔재 참조).

**남은 것은 5단계뿐이고 루프가 할 수 없다** — 사용자 라벨링 배치(TODO D1~D4)는
Tableau Desktop 실행이 필요하다. 그것이 막는 것: 규칙 ⑥-a WARNING→ERROR 승격 ·
규칙 ② ERROR 승격(표면별) · AC2/AC3/AC5 수치 확정.

**1단계 완료.** AC8(`.hyper` 라운드트립 바이트 동일성) xfail이 통과로 뒤집혀 마커를 제거했다.
여기가 다시 xfail로 돌아가면 무손실 보존이 깨진 것이다.

---

## 1. io 실로직 ✅ 완료

- [x] **1a. `io/twbx.unpack`** — zip slip(`safe_extract_path`) · zip bomb(`check_zip_entry`)
      정책 통과. `.hyper`는 바이트 그대로.
      오류 전달은 `ArchiveError`(`InputProblem` 운반) — 계약은 [`03-design.md`](./03-design.md) D9.1.
      `load_context`가 잡아 문제 목록으로 바꾼다(엔진 경계에서 02 S5 유지)
- [x] **1b. `io/twb.parse` / `read_version` / `serialize`** — 파서는 `safety.make_parser()`만.
      실패는 `MalformedXmlError`(= `safety.InputError`). `read_version` 독스트링이
      "XSD 버전 매칭용"이라 G1과 어긋나 있었다 — 바로잡았다(용도는 규칙 ⑥)
- [x] **1c. `inspect.load_context`** — `raw_tree` + 버전 3종 · `manifest_features`(원문 그대로) ·
      `datasources`(직계 `column`만) · `worksheets`/`dashboards`/`worksheet_windows` 채움.
      실측 10/10에서 `zone ⊆ worksheets ∧ zone ⊆ viewpoints` — 규칙 ③이 정상본에서
      침묵해야 한다는 뜻이고, 골든셋 회귀가 이 관계를 고정한다
- [x] **1d. `io/twbx.pack`** — AC8 xfail **해제됨**. `.hyper`는 무압축(ZIP_STORED)으로 넣어
      "재압축하지 않는다"를 경로로 보장한다. 엔트리 타임스탬프는 고정값 — 원본 mtime은
      unpack 시점에 이미 사라지므로 재현성을 택했다

## 2. L-A (구문 검증) ✅ 완료

- [x] **2a.** XSD 로드 + **컴파일 캐시** (`load_schema`, `lru_cache` 경로 키. TODO E1 해소).
      ⚠️ 캐시된 `XMLSchema`는 호출 간 공유 — 멀티스레드 서버면 락이 필요하다(코드에 명시)
- [x] **2b.** `schema.validate(ctx.normalized_tree())` → `severity_for()` 등급 →
      `Finding(line=e.line, location=e.path)`. 상한 200건 + 초과 시 `note_partial`
- [x] **2c.** 정상본 10/10 **ERROR 0 · WARNING 0** · 주입본 R4·R7이 게이트를 막는다(실측)

## 3. calc ✅ 완료

- [x] **3a. `calc/extractor.py`** — **Lark 문법 대신 어휘 스캐너**로 뒤집었다 (03 D3.7).
      실측: 수식 5,270건 · 함수 26종 · 화이트리스트 미매칭 **0건** · 파싱 실패 구조상 불가.
      `lark` 의존과 `grammar.lark`를 제거했다. 골든 회귀가 이 관계를 고정한다
- [x] **3b-1. 표기 정규화** (G8) — `twb_lint/fieldref.py`. 계약은 03 D3.6.1.
      `]]`가 `]`의 이스케이프임을 실측으로 발견해 추출기·정규화기·인스펙터 **세 곳**의
      대괄호 패턴을 맞췄다
- [x] **3b-2. 필드 유니버스 보강** — `<column>` + `<metadata-record>` + `<group>` +
      `<column-instance>` 네 곳 (03 D3.6.2, `FieldDef.origin`으로 출처 표시).
      인스턴스 번호(`:qk:3`)도 처리. **미해소 687 → 94.**
- [x] **3b-3. 규칙 ② 심각도 재판정** (03 D3.6.3) — 남은 94건을 추적하니 **전부 정상 파일의
      실제 잔재 참조**였다(삭제된 계산필드를 가리키는 `format@field` 규칙 등, 파일은 정상 열림).
      **규칙 ②를 ERROR로 두면 정상 골든셋 10/10이 막힌다** → WARNING으로 하향.
      ERROR 승격은 라벨링 배치(D1~D4) 이후, dangling 0인 표면 4종부터
- [x] **3c. 규칙 ①** 함수 화이트리스트 대조. **WARNING 고정** · 함수 이름별 1건
      (첫 자리 + 수식 개수). 수식 표면 2곳을 `extractor.formulas_in()`으로 공유해
      규칙 ②와 커버리지가 어긋나지 않게 했다. 골든셋 10개 WARNING **0건**
- [x] **3d. 규칙 ②** 필드 참조. 표면 = 수식 2곳 + `fieldref.REFERENCE_SURFACES` 9곳.
      특수 네임스페이스 3종 제외 · 이름별 1건(참조 개수 포함) · **WARNING 고정**.
      골든셋 10개 실측: ERROR 0 · **WARNING 24건**(파일당 1~6, 전부 실제 잔재 참조)

## 4. 나머지 규칙 ✅ 완료

- [x] **4a. 규칙 ③** 3자 대조. **유일하게 ERROR를 내는 규칙** — 표본 10개 전부에서
      `zone ⊆ worksheets ∧ zone ⊆ viewpoints ∧ worksheets == worksheet_windows`라는 실측이
      근거다. 배치되지 않은 시트는 보고하지 않는다(정상이다).
      **주입본 R2·R3가 이제 게이트에서 막힌다 — AC3 무거짓통과의 해소 실증**
- [x] **4b. 규칙 ⑥** — ⑥-a fcp(`ctx.raw_tree`, **WARNING** — 인과 미검증) ·
      ⑥-b 대응표 5쌍(**ERROR** — 로드 거부 메시지 실측).
      매핑을 모르는 항목 14종은 `note_partial`로 "검사하지 못했다"를 보고한다.
      **주입본 R1b가 게이트에서 막힌다**
- [x] **4c. 게이트 3쌍 추가** (2026-07-30, 05 F5-b) — 실사용 파일 로드 거부를
      twb-lint가 놓친 것을 계기로 `computed-sort` · `edit-parameter-action` ·
      `clear-option`을 확보했다. 실파일 61개 전수 상관으로 쌍조건 확인 · ERROR 0 유지
- [x] **4d. 규칙 ⑦ `ref.notation`** (2026-07-30, 05 F5-c·F5-d · 06 R14) — 매니페스트를
      고친 뒤 드러난 **2·3번째 층**. ⑦-a 필터 member 따옴표 · ⑦-b `[Multiple Values]`
      한정자 · ⑦-c 수식 안 매개변수 `[Parameters].` 한정자.
      셋 다 **WARNING**(열리지만 설정이 버려지거나 데이터가 안 나온다).
      ⑦-c는 **규칙 ②가 원리적으로 못 잡는 자리**다 (07 G5 트레이드오프의 대가)

- [x] **4e. 규칙 ⑧ `calc.aggregation` · ⑨ `set.definition`** (2026-07-30, 05 F5-e · 06 R15·R16)
      — 4번째 층. `usr:` 인스턴스의 집계 정합 · 집합의 기반 필드. 둘 다 **WARNING**.
      ⑧은 **판정 불가와 위반을 가른다**(못 펼친 참조 = `note_partial`),
      ⑨는 **모양이 아니라 성질**을 본다(기반 필드 유무). 정상본 60개 0건
- [x] **4f. 루프 엔지니어링** — `/defect-loop` 커맨드 신설. 오늘 4층을 벗긴 절차를
      재현 가능한 형태로 고정했다. 주입 레시피 6종 추가(R15~R20) +
      `test_every_recipe_is_caught_by_the_rule_it_declares` — **레시피 목록 자체가 입력**이라
      레시피를 넣으면 검사가 자동으로 따라온다(손으로 갱신하는 집합의 구멍을 막는다)
## 보류 (사람이 Tableau를 열어야 한다 — 루프가 건드리지 않는다)

- TODO **D1~D4** 라벨링 배치 · **B4** E2E baseline 계측
- 이것들이 막는 것: 규칙 ⑥-a WARNING→ERROR 승격 · AC2/AC3/AC5 수치 확정 ·
  매니페스트 미매핑 16종 승격

---

## 반복 로그

| # | 단위 | 게이트 | WARNING수 | 비고 |
|---|---|---|---|---|
| 0 | 대장 생성 | 74 passed, 1 xfailed | — | baseline 실측 확인 |
| 1 | 1a `twbx.unpack` | 84 passed, 1 xfailed | 0 | 골든셋 10개 실해제 확인(각 <0.01s, 4엔트리). AC8은 `pack` 미구현이라 xfail 유지 |
| 2 | 1b `twb.parse`/`read_version`/`serialize` | 92 passed, 1 xfailed | 0 | io 예외를 `safety.InputError`로 통일(03 D9.1). XXE가 `parse()` 경로를 실제로 통과하는지 파일로 검사 |
| 3 | 1c `load_context` 모델 실채움 | 102 passed, 1 xfailed | 0 | 골든셋 10개 추출 실측: ds 2~5 · 필드 73~240 · calc 56~111 · ws=win=zone=vp 전부 일치. **픽스처 결함 2건**(`<datasources>` 래퍼 누락 · 시트 존에 `type-v2`)을 실측 기준으로 교정 |
| 4 | 1d `twbx.pack` | **108 passed** (xfail 0) | 0 | **AC8 뒤집힘 — io 1단계 완료.** CLAUDE.md·07의 게이트 수치도 갱신 |
| 5 | 2a~2c L-A 배선 | 114 passed | **0** | 정상본 10/10 ERROR 0·WARNING 0. R4·R7이 게이트를 막는다. 54ms/file(스키마 컴파일 포함). stub 테스트 `test_ac2_...`를 검출 단언 + AC3 실측으로 분리 |
| 6 | 3a calc 추출기 | 125 passed | 0 | **설계 뒤집기**: Lark 문법 → 어휘 스캐너 (03 v1.5 D3.7). 근거는 실측 5,270 수식/미매칭 0. `lark` 의존 제거 |
| 7 | 3b-1 표기 정규화 | 134 passed | 0 | `fieldref.py` 신설(03 v1.6 D3.6.1). 참조 16,754건 실측 → 미해소 687건은 **모델 필드 유니버스의 공백**임을 확인, 3b-2로 분리 |
| 8 | 3b-2·3b-3 필드 유니버스 + 규칙 ② 심각도 | 138 passed | 0 | 미해소 687→94. **남은 94건이 정상 파일의 실제 잔재 참조**임을 확인 → 규칙 ②를 ERROR→WARNING 하향 (03 v1.7 D3.6.3) |
| 9 | 3c 규칙 ① | 144 passed | **0** | 골든셋 10개에서 finding 0건(ERROR·WARNING 모두). stub 목록에서 `calc.functions` 제거 |
| 10 | 3d 규칙 ② | 153 passed | **24** | 골든셋 ERROR 0 · WARNING 24(파일당 1~6). 전부 실제 잔재 참조이며 D3.6.3 예측과 일치. 3단계 완료 |
| 11 | 4a 규칙 ③ | 161 passed | 24 | 골든셋 ERROR 0 유지. **R2·R3가 게이트에서 막힌다** — L-A가 원리적으로 못 잡는 것을 L-B가 잡는 첫 실증. 남은 미검출은 R1a·R1b(규칙 ⑥) |
| 12 | 4b 규칙 ⑥ | **170 passed** | 24 | R1b 차단. **주입 6종 중 5종을 게이트가 막는다**(R1a는 의도적 WARNING). 07 §4 1~4단계 완료 |
| 13 | 4c 게이트 3쌍 추가 | **183 passed** | 24 | 실사용 파일(MA_003 매출표) 로드 거부를 놓친 것을 수정. 실파일 61개 회귀: 거부된 1개만 ERROR 3건(줄 750·773·1965 = Tableau 지목 줄), 나머지 60개 ERROR 0. 게이트 finding에 줄번호 추가. ⚠️ mypy는 이 머신에서 실행 차단됨(Smart App Control) |
| 14 | 4d 규칙 ⑦ `ref.notation` (⑦-a·b·c) | **187 passed** (골든셋 미설정) · 골든셋 `200 passed` | 24 + 0 | 05 F5-c·F5-d. 고친 사본이 열리자 층이 둘 더 나왔다 — 경고 2종(member 따옴표·자리표시자 한정자)과 "데이터가 안 나옴"(매개변수 한정자). 정상본 60개 ref.notation 0건. ⑦-c는 규칙 ②가 원리적으로 못 잡는 자리(07 G5). 규칙 6종째, 코어 무수정 |
| 15 | 4e·4f 규칙 ⑧⑨ + 루프 엔지니어링 | **205 passed, 14 skipped** · 골든셋 `219 passed` | 24 + 0 | 05 F5-e. 4번째 층(집계 정합·집합 정의)을 규칙화. 실파일 61개: 정상본 60개 0건, 깨진 파일만 4건. `/defect-loop` 신설 + 주입 레시피 6종(R15~R20) — 레시피 9개 전부 선언한 규칙이 잡는 것을 회귀가 확인한다 |
| 16 | 규칙 ⑦-d `groupfilter@level` 한정자 (`/author-loop` → `/defect-loop`) | **268 passed** (골든셋 미설정 시 `254 passed, 14 skipped`) | 24 + 0 | 05 **F5-f** · 06 **R19**. **발견 경로가 처음으로 바뀌었다** — 남의 실파일이 아니라 `/author-loop`이 빈 손에서 만든 워크북이 층을 냈다. 린터 0 findings인데 Tableau는 경고 (AC3 위반). 실측 85개 중 31개 사용, **비한정 3,484 : 한정 0**. ⑦-b와 방향이 반대인 자리다. 정상본 85개 ⑦-d finding 0건, 깨진 판만 1건. 주입 레시피 R21 추가(13종) |
| 17 | 저작 2차 A·B·C — 실측만, 구현 없음 | 268 passed (변동 없음) | 24 + 0 | 05 **F5-g** · 06 **R20~R24**. `/author-loop`으로 워크북 3개를 만들어 열었다 — **3/3 열림**(층 1은 린터가 XSD 6건으로 지켰다). 그런데 화면은 틀렸고, 사용자가 찾은 결함 7건을 되돌려 넣어 재측정하니 **검출 1/8**. 잡은 하나는 직전 반복의 ⑦-d다. 대조 수치는 전부 반례 0 — 집합 `ui-builder 46 : auto-column 2` · 집합 위치 `filter 38 : 인코딩 0` · `tsl-filter 14`·`brush 16 : filter 0` · param `source-field 0` · `<link>` `14 : 0`. **구현은 하지 않았다** — `/defect-loop` 대기열 D1~D3으로 넘긴다 (`TODO.md` §2-1) |
| 18 | D1 — 규칙 ⑬ `action.shape` (`/defect-loop`) | **285 passed** (골든셋 미설정 시 `271 passed, 14 skipped`) | 24 + 0 | 05 **F5-h** · 06 **R21+R22**. F5-g의 결함 ④⑤⑥을 한 규칙으로 묶었다 — 같은 요소·같은 층·같은 증상(열리는데 동작이 안 먹는다). **⑩ 확장이 아니라 신규 규칙**이다: ⑩은 *참조*(가리키는 대상이 실재하는가), ⑬은 *어휘*(Tableau가 아는 모양인가). 저작본은 대상이 전부 실재해서 ⑩이 침묵했다. XSD도 원리적으로 못 잡는다 — `ActionList-CommandName-ST`가 열거가 아니라 `[^:]+:[^:]+` 패턴이다. 실측 재측정: `<action>`은 **세 모양뿐**(`tsl-filter`+link 14:0 · `brush` 17:0 · 명령없이 URL link 1)이고 param 어휘는 **종류별로 갈리며 교차 0건**. ⚠️ **F5-g 수치를 정정했다** — 그 표는 내 저작본을 정상본으로 셌고, `source-field`는 "없는 이름"이 아니라 `edit-parameter-action`에 **70건 관측되는 정상 이름**이었다(자리가 틀렸을 뿐). 전역 화이트리스트로는 못 잡는 결함이라 종류별로 갈랐고, 거짓양성 함정 테스트가 그 한 쌍을 고정한다. 실파일 63개 `action.shape` 0건(AC7 유지), 깨진 파일 1개만 검출. 주입 레시피 R22·R23 추가(15종). `<nav-action>`은 표본 0이라 `note_partial` |
| 19 | D2 — 집합 모양·자리 실측 (`/defect-loop`, **구현 없음**) | 285 passed (변동 없음) | 24 + 0 | 05 **F5-i** · 06 **R20-a 보류 / R20-b 폐기**. **측정이 후보 하나를 죽였다.** F5-g의 `집합 참조 filter 38 : 인코딩 0`은 사용자 집합과 동작 집합을 한 칸에 세고 있었다 — 38건은 전부 `auto-column`+`hidden` 동작 집합이고 **2개 파일**에서만 나온다. 사용자 집합 46개(22파일)는 **뷰에 한 번도 배치되지 않았다**(계산식 참조뿐). 배치 표본 0 → 멈춤 조건. 게다가 집합을 색상에 올리는 것은 Tableau 정규 기능이라 규칙화하면 정상 파일을 때린다. R20-a는 성질이 섰다 — *시스템 표식(`auto-column`)을 달았으면 `hidden='true'`다* **80:2**, 반례 2건은 거부된 MA_003 하나. `<group>` 128개 중 두 표식이 다 없는 것 0개. **그러나 증상 귀속 실패** — MA_003은 기반 필드도 없어 ⑨가 이미 잡고, 저작 B는 속성·배치를 **한꺼번에 고쳤다**(한 반복에 두 층을 고친 값을 여기서 치렀다), 매출요약은 집합 미확인. 분리 실험본 2개(`매출요약_V1_속성만`·`매출요약_V2_자리만`, 둘 다 ERROR 0)를 사용자에게 넘겼다. **확인 전에는 규칙화하지 않는다** |
| 20 | 임시 계산 거짓양성 수정 (사용자 실사용 제보) | **275 passed, 14 skipped** | 24 + 0 | 03 **D3.6.4**. 선반에서 더블클릭해 만든 **임시 계산**(`@user:unnamed`)은 `<datasources>`에 올라가지 않고, 쓰는 워크시트의 `<datasource-dependencies>` 안에만 정의가 있다. D3.6.2의 필드 유니버스 네 곳이 전부 `<datasources>` 아래라 못 봤고, 규칙 ②·⑪이 **정상 워크북**을 향해 finding 16건을 뱉었다 (MA_008 재고관리, 임시 계산 6종). AC7 위반이다. 유니버스에 다섯째 출처 `adhoc`을 더해 **16 → 0**. `<datasource-dependencies>`를 통째로 담지 않고 `@user:unnamed`가 붙은 `<column>`만 담는다 — 나머지는 정의의 **사본**이라 통째로 담으면 삭제된 필드의 사본이 진짜 dangling을 가린다. 픽스처 루트에 `xmlns:user` 선언 추가(실파일과 동일) |
| 21 | 게이트 `simple-id` 추가 (저작 실패 → `/defect-loop`) | **285 passed, 14 skipped** | 24 + 0 | **린터가 `passed=true`로 통과시킨 파일을 Tableau가 거부했다** (D2E8DA72, 2026-08-10). 레시피 관찰용 베이스 워크북을 손으로 저작하면서 `<document-format-change-manifest>` 블록을 통째로 빠뜨렸고, 두 워크시트의 `<simple-id>`가 거부 사유로 지목됐다: `element 'simple-id' is not allowed for content model '(((layout-options?)|(repository-location?)),table)'`. 규칙 ⑥-b의 **방향은 이미 맞았고 대응표에 항목이 없었을 뿐**이라 코어·규칙 코드 무수정, `manifest_gates.json` 한 항목 추가로 끝났다. `known_items_unmapped`가 예고한 확보 경로("로드 거부 메시지가 대응 요소를 직접 알려준다")가 **그대로 작동한 첫 사례** — 14종 중 2종이 gates로 이동(12종 잔여). 실파일 113개 상관: `simple-id` 보유 113개 전부 `WindowsPersistSimpleIdentifiers`·`SheetIdentifierTracking` 둘 다 선언(반례 0), 역방향 반례도 0. 부모는 `worksheet` 3737 · `window` 3854 · `dashboard` 117. 코퍼스로는 두 항목이 항상 함께 나타나 분리되지 않아 **같은 날 분리 실험을 돌렸다** — SIT만 뺀 변형은 거부, WPSI만 뺀 변형은 **열렸다**. 게이트는 `SheetIdentifierTracking` 단독이고 최초안(둘 다 요구)은 **과요구**였다. WPSI는 `window/simple-id`를 게이팅한다는 추정만 남아 `known_items_unmapped`로 되돌렸다(저작본에 `window/simple-id`가 없어 실험이 그 자리를 못 건드렸다). **상관만으로 ERROR를 냈으면 정상 파일을 때릴 뻔했다** — 실험 2회가 그걸 막았다. 회귀: 실파일 114개 ERROR 0(AC7 유지), 결함 표본만 ERROR 1 |
