# CLAUDE.md

**twb-lint** — Tableau `.twb/.twbx` 오프라인 검증 게이트.
공식 XSD(구문) 위에 시맨틱 검증기를 얹어, Tableau를 실행하지 않고 "이 파일이 열리는가"를 판정한다.

대상: Tableau **2026.1 단독 · 로컬 오프라인**. 현 단계: **스캐폴딩 + 스파이크 완료** (규칙 로직은 stub).

## 작업 전 반드시 읽는다

| | 문서 |
|---|---|
| **프로젝트 정보** | [`docs/tableau-ai-sor.md`](./docs/tableau-ai-sor.md) — SOR 인덱스. 여기서 시작 |
| **구현 시 필수** | [`docs/07-implementation-guide.md`](./docs/07-implementation-guide.md) — G1~G7 함정 · 검증 파이프라인 · 관례 |
| **지금 할 일** | [`TODO.md`](./TODO.md) — 구현 착수 전 체크리스트 (설계 미결·데이터·라벨링 배치) |

`docs/`가 권위 문서다. 이 파일과 어긋나면 **`docs/` 우선.**

## 검증 파이프라인 (코드 수정 시 필수)

```bash
.venv/Scripts/python -m pytest -q        # 4 passed
.venv/Scripts/python -m ruff check .     # All checks passed
.venv/Scripts/python -m mypy             # Success: no issues in 25 source files
```

하나라도 깨지면 커밋하지 않는다. 규칙을 구현했으면 **실파일 회귀**(정상 9개 ERROR 0건)까지 —
절차는 [`07-implementation-guide.md`](./docs/07-implementation-guide.md) §2.

> `uv`는 이 머신에서 실행이 차단된다(Smart App Control). 위 `.venv` 경로를 쓴다.

## 자주 트리는 것 (상세는 07)

- 버전 키는 `source-build`다. `<workbook version>`은 최소 호환 버전(`18.1`)이라 못 쓴다
- 공식 XSD를 그대로 쓰면 정상 파일이 전부 실패한다 — 전처리 3단계(스텁·패치·**fcp 정규화**) 필수
- **ERROR는 확신할 때만.** 거짓양성 1건이 게이트를 무력화한다 (AC7 = 정상본 ERROR 0건)
- XSD 통과 ≠ 열린다 — 매니페스트가 문법을 게이팅한다
- 새 규칙 = `validation/semantic/` 파일 1개 + `@register`. 코어 무수정
