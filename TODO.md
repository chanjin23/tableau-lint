# TODO — 빨간 느낌표 0을 목표로

> 권위 문서는 `docs/`다. 여기는 **작업 목록**일 뿐 결정의 근거가 아니다.
> 결정이 나면 **먼저 `docs/`를 고치고** 여기에 체크한다.
> 구현 진행 상황은 [`docs/impl-progress.md`](./docs/impl-progress.md)가 갖는다.

**2026-07-31 문제정의 재설정.** 기존 목표(= 기존 파일이 열리는가)는 달성했고,
목표가 한 칸 넓어졌다 — **새로 만든 파일을 Tableau에서 열었을 때 빨간 느낌표가
하나도 없는가**. 판정 대상이 "파일"에서 "화면에 보이는 모든 필드·시트"로 옮겨간다.

---

## 목표 4항목 (= 새 AC)

| | 요구 | 상태 |
|---|---|---|
| **T1** | 파일이 무조건 열린다 | ✅ **저작 4종 4/4 열림** (2026-07-31 실측) |
| **T2** | 워크시트의 계산필드·매개변수가 오류를 내지 않는다 | 🟡 부분 — 집계 수준(R23)이 빠졌다 |
| **T3** | 집합·동작을 걸 때 오류가 나지 않는다 | 🟡 동작은 참조+모양 ✅ — **집합 모양(R20)이 남았다** |
| **T4** | 페이지·필터·마크·열·행에 올릴 때 오류가 나지 않는다 | 🟡 T4-a만 |

현 규칙 12종의 담당:

| 규칙 id | 담당 | 심각도 |
|---|---|---|
| `input.readable` | 층 0 — 입력 | ERROR |
| `xsd.schema` (L-A) | T1 | ERROR/WARNING 혼합 |
| `named.refs` | T1 — zone·worksheet·viewpoint·window 4자 일치 | ERROR |
| `manifest.gates` | T1 — 매니페스트 게이트 | ⑥-b ERROR / ⑥-a WARNING |
| `ref.notation` | T1·T2·T4 — 표기 정합 (⑦-a·b·c·d·**e** 정렬) | ERROR/WARNING |
| `calc.functions` | T2 — 함수 화이트리스트 | WARNING |
| `calc.field_refs` | T2 — dangling 참조 | WARNING |
| `calc.aggregation` | T2 — 집계 정합 (⑧-a 모자람 · ⑧-b **이중 집계**) | WARNING |
| `set.definition` | T3 — 집합 정의 | WARNING |
| `action.refs` | T3 — 동작 배선 참조 | WARNING |
| `action.shape` | T3 — 동작 배선 **어휘** (명령·param·`<link>` 짝) | WARNING |
| `shelf.refs` | T4-a — 선반 배치 참조 | WARNING |
| `datasource.shape` | 층 밖 — `<object-graph>` 누락(앱 종료) | **ERROR** |

**T1은 지키는데 층 2~4는 1/8이었다** (05 F5-g 실측). 저작 3종을 열어 찾은
결함 7건 중 린터가 잡은 건 0건이고, 앞 반복에서 규칙화한 ⑦-d 1건만 잡혔다.
**D1(규칙 ⑬)이 ④⑤⑥을 잡아 4/8이 됐다** (05 F5-h).

---

## 지금 할 일

### 1. 문제정의 교체 — 코드보다 먼저

- [x] **P1.** `docs/01-problem-definition.md` **v2.0** — §1~§7 신규(문제 한 문장 · 생성이 위험 ·
      실패 4층 · T1~T4 · 성공 기준 · 비-목표 · 열린 질문), 기존 v1.2 본문은 **부록 A**로 이동
- [x] **P2.** `docs/02-specification.md` **v1.3** — S4.0 T1~T4↔AC 매핑표 · **AC9 빨간 느낌표 0**
      신설(층 2~4는 *막는* 게 아니라 *말한다*) · S1-7 층 원칙 · C3 L-B 목록을 규칙 id ①~⑫로 교체 ·
      **AC2·AC5 목표 수치는 "두지 않는다"로 확정** (S6 미결에서 제거)
- [x] **P3.** `CLAUDE.md`·`README.md`·`docs/tableau-ai-sor.md` 갱신 — 4층 표 · T1~T4 상태 ·
      규칙 8종 심각도 표 · 낡은 수치(5종·170 passed·정상본 10개) 정정 ·
      "층 1은 막고 층 2~4는 말한다" 명시

### 2. 신규 규칙 (코어 무수정 · 파일 1개 + `@register`)

- [x] **R⑩ `action.refs` — T3 동작(action) 검증** ✅ 2026-07-31
      표면 9종을 실파일 84개(그중 `<actions>` 보유 33개) 전수 실측으로 확정.
      `source@worksheet/@dashboard/@datasource` · `exclude-sheet@name` ·
      `param target`/`exclude`/`target-parameter`(대상 + `[Parameters]` 한정자)/
      `target-group`/`source-field`. **전부 WARNING** — `source-field` 반례 4건 중 1건이
      골든셋 파일이라 ERROR가 불가능하다. 근거는 `docs/06-rule-candidates.md` R17
- [x] **R⑪ `shelf.refs` — T4-a 선반 배치 참조 무결성** ✅ 2026-07-31
      행·열(요소 텍스트, 수식 가능) · 페이지 · 필터(`<slices>/<column>`·`groupfilter@level`) ·
      마크(color·size·tooltip·shape·detail·label·path) · 정렬 5종 · 축·참조선.
      **WARNING** — 반례 28건이 전부 골든셋 파일 하나의 진짜 dangling이다.
      근거는 `docs/06-rule-candidates.md` R18
      - 부수: **`fieldref` 다층 장식 결함**을 고쳤다 (`[pcto:sum:값:qk]`를 한 겹만
        벗기고 있었다). 반례 48 → 28. 규칙 ②의 거짓 dangling도 같이 준다
      - ⚠️ **T4-b(조합 규칙)는 여기 없다** — 정답지가 없다. L1 참조
- [ ] **R⑫ `calc.types` — T2 타입 정합**
      문자열↔숫자 혼합 · 집계와 비집계 인자 혼합(`SUM([A]) + [B]`) · `IF` 분기 반환형 불일치.
      **WARNING 기조로 시작한다** — 타입 추론이 불완전한 채 ERROR를 내면 AC7이 깨진다
      - ⚠️ 시제품 실측이 실파일에서 **혼합 0건**을 냈다. 잡을 게 없는 규칙을 만들기 전에
        `inject_defects.py`에 `SUM([A]) + [B]` 레시피를 먼저 넣어 검출 가치를 세운다
      - **R23(집계 수준)을 여기 넣을지 먼저 정한다** — 뷰 그레인 계산이 필요해 성격이 다르다

### 2-1. `/defect-loop` 대기열 — 실측 끝, 구현 전

저작 2차(A·B·C)가 낸 결함을 실측까지 마쳐 후보로 박아 뒀다.
**근거는 `docs/06-rule-candidates.md` R20~R24 · `docs/05-xsd-spike.md` F5-g.**
한 반복에 하나씩, `/defect-loop`으로 돈다.

| 순서 | 후보 | 규칙 | 실측 (정상 : 반례) | 층 |
|---|---|---|---|---|
| ~~D1~~ | ~~동작 명령·param 어휘 + `<link>` 짝~~ | ✅ **⑬ `action.shape`** (신규) | `tsl-filter 14:0` · `brush 17:0` · 종류별 param 어휘 교차 0 | 2 |
| **D2-a** | 집합 모양 — 시스템 표식(`auto-column`)과 `hidden`의 짝 | ⑨ `set.definition` 확장 | **80 : 2** (반례 2건은 거부된 MA_003 하나) · ⏸ **증상 귀속 대기** | 2 |
| **D2-b** | 집합을 인코딩/선반에 배치 | 재개 가능 | **2026-08-10 표본 확보** — 통제 관찰로 `io:` 배치 4건(레시피 23). 폐기 사유(배치 표본 0)가 해소됐다 | 2 |
| **D3** | 집계 수준 정합 (인코딩의 행수준 차원) | ⑫ `calc.types` 또는 신규 | 뷰 그레인 계산 방법 미정 | 4 |
| — | `<pages>`의 `<current-page>` | — | **표본 0 — 규칙화하지 않는다** (R24) | 3 |

- [x] **D1** ✅ 2026-07-31 — ⑩ 확장이 아니라 **신규 규칙 ⑬**으로 냈다. ⑩은 *참조*,
      ⑬은 *어휘*라 묻는 것이 다르고, 같은 id에 두면 "refs"가 아닌 것이 `action.refs`로
      보고된다. 부수로 **F5-g의 동작 수치를 정정**했다 — 그 표는 내 저작본을 정상본으로
      셌고, `source-field`는 "없는 이름"이 아니라 **자리가 틀린 이름**이었다 (05 F5-h)

- [ ] **D2** ⏸ 2026-07-31 — **측정이 후보 하나를 죽였다.** D2-b의 `filter 38 : 인코딩 0`은
      사용자 집합과 동작 집합을 한 칸에 셌다. 38건은 전부 동작 집합(2개 파일)이고
      **사용자 집합 46개는 뷰에 한 번도 배치되지 않았다** — 배치 표본 0이라 폐기한다.
      D2-a는 불변식 80:2가 섰지만 **증상 귀속이 안 된다** — 저작 B에서 속성과 배치를
      한꺼번에 고쳤다. 분리 실험본 2개를 사용자에게 넘겼다 (05 F5-i)

D3은 뷰 그레인을 정적으로 구할 수 있는지부터 정해야 하므로 마지막이다.

### 3. 자잘한 것

- [ ] **F3. MCP `twb_validate`가 `coverage`를 버린다** — 코어 `ValidationReport`는 갖고 있는데
      어댑터가 응답에서 뺀다. 호출자가 **무엇을 검사하지 못했는지 알 수 없다** (03 D2).
      "조용한 통과 금지"(02 S5)가 MCP 경계에서 새는 자리다
- [ ] **F4. MCP에 `pack` 미노출** — 재포장은 파이썬 `twbx.pack(root, out)`뿐.
      생성이 주 용도가 된 이상(01 v2.0 §2) 노출을 재검토한다

### 4. 라벨이 필요한 것 — ⏸ Tableau Desktop 필요

**블로커에서 강등한다.** 없어도 T1~T3는 간다. 정확도 개선용으로만 남긴다.

- [ ] **L1. T4 조합 규칙 정답지** — 어떤 필드×선반 조합이 빨간 느낌표를 내는지는
      XSD에도 매니페스트에도 없다. Tableau에서 조합을 열어 봐야 규칙 근거가 선다.
      **T4의 절반(조합)이 여기 매달려 있다.** 참조 무결성 절반은 라벨 없이 간다
- [ ] **L2. 심각도 승격** — `manifest.gates` ⑥-a WARNING→ERROR ·
      `calc.field_refs` 표면별 ERROR 승격(dangling 0인 표면 4종).
      **그때까지 현재 심각도로 동결한다**
- [ ] **L3. 수치 확정** — AC2(커버리지)·AC5(속도) baseline 1회 계측
- [x] **L4. `simple-id` 게이트 분리 실험** ✅ 2026-08-10 — SIT만 빼면 거부,
      WPSI만 빼면 열린다. 게이트는 `SheetIdentifierTracking` 단독이고 최초안은
      과요구였다. WPSI는 `known_items_unmapped`로 복귀
- [ ] **L5. `object-graph` 게이트 분리 실험** — V3는 `ObjectModelTableType`·
      `ObjectModelEncapsulateLegacy`·`SchemaViewerObjectModel` 3항목을 **한꺼번에**
      지웠다. 어느 것이 `object-graph`를 게이팅하는지 모른 채 셋 다 요구하고 있다 —
      L4에서 드러난 과요구와 같은 위험이다. 정본에서 하나씩만 뺀 변형 3개를 연다
- [ ] **L7. 총계·부동 존 관찰 (MA_011 260812에서 절반만 닫혔다)** — 총계가 `<rows>`의
      `total`·`onTop` 속성이라는 것은 확보했다(레시피 11). 남은 것: **총계 계산 방식**
      (자동/합계/평균 — "자동"은 기본값이라 아무 XML도 안 남는다. 비율 측정값의 총계가
      재계산되는지 합산되는지가 여기 달렸다) · 행 총합계(`<cols>` 추정) · 소계 ·
      **부동(floating) 존**(레시피 16에 패턴 없음. 클릭 하이라이트를 막는 투명 오버레이용).
      한 저장 = 한 조작으로 받는다
- [ ] **L6. 실패 층 분류에 빈칸이 있다** — 규칙 ⑭가 잡는 것("열리는데 데이터 원본
      탭에서 앱이 종료")은 `01 v2.0 §4`의 4층 어디에도 없다. 층 1(로드 거부)이
      아닌데 증상은 층 4(빨간 느낌표)보다 무겁다. 층을 늘릴지, 층 1의 변종으로 볼지
      정해야 심각도 정책(`02 AC9`)이 일관된다. **지금은 규칙 ⑭만 예외로 ERROR다**

주입 고장본은 이미 생성기가 있다. 배치를 돌릴 때 이 명령 하나면 된다:

```bash
.venv/Scripts/python tools/inject_defects.py --source <원본.twbx> --out <디렉토리> --experiment-b
```

산출 디렉토리 `labels.json`의 `observed`·`error_text`를 채운다.
보고 형식: ① 열림 ② 안 열림 + **에러 문구 원문** ③ 열리는데 이상함 + 무엇이.

---

## 해소된 것 (다시 논의하지 않는다)

설계 결정 8건 · 데이터 확보 · 테스트 인프라는 전부 끝났고 근거는 `docs/`에 있다.
요약이 필요하면 [`docs/03-design.md`](./docs/03-design.md) D3~D9,
[`docs/impl-progress.md`](./docs/impl-progress.md) 완료 로그를 본다.

- 규칙 입력 계약 = `check(ctx)` · 입력 오류는 엔진 담당 · L-A 심각도 정책 · `coverage`
- vendored XSD(Apache-2.0) · 함수 218종 · `io/safety.py` 방어 · `.hyper` 바이트 무손실(AC8)
- 골든셋 외부화(`TWB_LINT_GOLDEN_NORMAL`) · 계약 테스트가 신규 규칙을 자동으로 잡는다

---

## 검증 파이프라인

```bash
.venv/Scripts/python -m pytest -q     # 306 passed, 14 skipped (골든셋 미설정 시)
.venv/Scripts/python -m ruff check .  # All checks passed
```

> `mypy`는 이 머신에서 실행이 막혔다(Smart App Control). pytest·ruff만 게이트다.

## 다음 한 걸음

**D2-b가 열렸다.** 2026-08-10 통제 관찰로 사용자 집합을 뷰에 올린 표본 4건을 확보했다
(레시피 23 — `io:` 한정자 · `derivation='InOut'`). 폐기 사유였던 "배치 표본 0"이 해소됐다.
관찰본은 `C:\dev\새 폴더\관찰_06`~`09`.

그 다음 후보: **L5**(`object-graph` 게이트 3항목 분리 — 지금 과요구 상태) ·
**D3**(뷰 그레인을 정적으로 구할 수 있는가부터) · **규칙 ⑫**
(`inject_defects.py`에 `SUM([A]) + [B]` 레시피를 먼저 넣어 검출 가치를 세운다).
