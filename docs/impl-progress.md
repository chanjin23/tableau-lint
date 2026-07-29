# 구현 진행 대장

> **용도**: 구현 루프(`/impl-loop`) 반복 간 상태 전달. 반복은 이전 기억이 없으므로
> 여기가 유일한 연속성이다.
>
> 권위 문서는 `docs/`다 — 여기는 **진행 상황만**. 설계 결정이 생기면 먼저 해당 문서를
> 고치고 여기엔 링크만 남긴다. 구현 순서의 근거는
> [`07-implementation-guide.md`](./07-implementation-guide.md) §4.

**현재** (2026-07-29, 골든셋 걸고 실측): `161 passed` ·
`ruff All checks passed!` · `mypy Success: no issues found in 53 source files`
(골든셋 미설정 시 `149 passed, 12 skipped`)

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

## 4. 나머지 규칙 ← 다음

- [x] **4a. 규칙 ③** 3자 대조. **유일하게 ERROR를 내는 규칙** — 표본 10개 전부에서
      `zone ⊆ worksheets ∧ zone ⊆ viewpoints ∧ worksheets == worksheet_windows`라는 실측이
      근거다. 배치되지 않은 시트는 보고하지 않는다(정상이다).
      **주입본 R2·R3가 이제 게이트에서 막힌다 — AC3 무거짓통과의 해소 실증**
- [ ] **4b. 규칙 ⑥** — ⑥-a fcp(`ctx.raw_tree` 필수, `fcp.py`가 이미 다 준다) ·
      ⑥-b `manifest_gates.json` gates 2종

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
