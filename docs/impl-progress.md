# 구현 진행 대장

> **용도**: 구현 루프(`/impl-loop`) 반복 간 상태 전달. 반복은 이전 기억이 없으므로
> 여기가 유일한 연속성이다.
>
> 권위 문서는 `docs/`다 — 여기는 **진행 상황만**. 설계 결정이 생기면 먼저 해당 문서를
> 고치고 여기엔 링크만 남긴다. 구현 순서의 근거는
> [`07-implementation-guide.md`](./07-implementation-guide.md) §4.

**현재** (2026-07-29, 골든셋 걸고 실측): `114 passed` ·
`ruff All checks passed!` · `mypy Success: no issues found in 47 source files`
(골든셋 미설정 시 `104 passed, 10 skipped`)

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

## 3. calc ← 다음

- [ ] **3a. `calc/extractor.py`** — 수집 표면 2곳: `<calculation@formula>` ·
      `<groupfilter@expression>`. 후자가 `//` 주석 · XML 엔티티 · 개행을 전부 담는다
- [ ] **3b. 표기 정규화** (G8) — calc 안 `[Calculation_1234]` ↔ 속성 `[ds].[usr:name:qk]`.
      **여기가 규칙 ②의 최대 함정이다**
- [ ] **3c. 규칙 ①** 함수 화이트리스트 218종 대조 (WARNING 기조 — 목록 불완전이 전제)
- [ ] **3d. 규칙 ②** 필드 참조 — 특수 네임스페이스 예외 필수
      (`[:Measure Names]` 1,294회 · `[Parameters].[…]` · 집합/그룹/bin/계층)

## 4. 나머지 규칙

- [ ] **4a. 규칙 ③** 참조 무결성 3자 대조 (worksheet · dashboard · window)
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
