# CLAUDE.md

**twb-lint** — Tableau `.twb/.twbx` 오프라인 검증 게이트.
공식 XSD(구문) 위에 시맨틱 검증기를 얹어, Tableau를 실행하지 않고 "이 파일이 열리는가"를 판정한다.

대상: Tableau **2026.1 단독 · 로컬 오프라인**.
현 단계: **io + L-A 완료** — unpack/pack · 파싱 · 모델 추출 · XSD 구문 검증이 실로직이다
(AC8 통과 · 정상본 ERROR 0). **L-B는 규칙 ①② 가동 · ③⑥ stub.** 다음은 규칙 ③·⑥.
진행 상황은 [`docs/impl-progress.md`](./docs/impl-progress.md)가 갖는다.

## 작업 전 반드시 읽는다

| | 문서 |
|---|---|
| **프로젝트 정보** | [`docs/tableau-ai-sor.md`](./docs/tableau-ai-sor.md) — SOR 인덱스. 여기서 시작 |
| **구현 시 필수** | [`docs/07-implementation-guide.md`](./docs/07-implementation-guide.md) — G1~G10 함정 · 검증 파이프라인 · 관례 |
| **지금 할 일** | [`TODO.md`](./TODO.md) — 남은 것은 사용자 라벨링 배치(D)뿐 |

`docs/`가 권위 문서다. 이 파일과 어긋나면 **`docs/` 우선.**

## 검증 파이프라인 (코드 수정 시 필수)

```bash
.venv/Scripts/python -m pytest -q        # 142 passed, 11 skipped (골든셋 미설정 시)
.venv/Scripts/python -m ruff check .     # All checks passed
.venv/Scripts/python -m mypy             # Success: no issues in 52 source files
```

하나라도 깨지면 커밋하지 않는다. 규칙을 구현했으면 **실파일 회귀**까지 —
골든셋 경로를 환경변수로 걸면 `153 passed`가 된다 (AC8 xfail은 io 1단계 완료로 해제됐다).
절차는 [`07-implementation-guide.md`](./docs/07-implementation-guide.md) §2.

```bash
export TWB_LINT_GOLDEN_NORMAL='<정상본 glob>;<glob>;...'   # ';' 구분, 미설정 시 skip
```

> `uv`는 이 머신에서 실행이 차단된다(Smart App Control). 위 `.venv` 경로를 쓴다.

## 자주 트리는 것 (상세는 07)

- 버전 키는 `source-build`다. `<workbook version>`은 최소 호환 버전(`18.1`)이라 못 쓴다
- 공식 XSD를 그대로 쓰면 정상 파일이 전부 실패한다 — 전처리 3단계(스텁·패치·**fcp 정규화**) 필수
- **fcp 정규화는 정보를 지운다.** 규칙 ⑥-a는 `ctx.raw_tree`(정규화 전), L-A는
  `ctx.normalized_tree()`(정규화 후)를 본다 — 입력이 다르다 (05 F7)
- **필드 참조 표기가 2종이다.** calc 안 `[Calculation_1234]` vs 속성 `[ds].[usr:name:qk]`.
  정규화 없이 대조하면 규칙 ②가 전량 dangling을 뱉는다 (03 D3.6, 07 G8)
- **ERROR는 확신할 때만.** 거짓양성 1건이 게이트를 무력화한다 (AC7 = 정상본 ERROR 0건).
  L-A조차 전부 ERROR가 아니다 — 거짓양성과 진짜 오류가 **같은 오류코드**를 쓴다 (03 D3)
- XSD 통과 ≠ 열린다 — 매니페스트가 문법을 게이팅한다. 주입본 R1b·R2·R3가 이를 실증한다
- **규칙은 `ctx`를 받는다.** 트리를 규칙 안에서 재파싱하지 않는다 (파싱은 파일당 1회).
  파서는 `io.safety.make_parser()`로만 만든다 — 기본 파서는 엔티티를 해석한다(XXE)
- **검사 못 했으면 말한다** — `ctx.note_skip()`. 빈 리스트를 조용히 반환하면
  "전부 검사했고 문제없음"으로 기록된다
- 새 규칙 = `validation/semantic/` 파일 1개 + `@register`. 코어 무수정 (현재 5규칙).
  계약 테스트가 새 규칙도 자동으로 잡는다
- findings 정렬은 **엔진이 보장**한다(`stage→rule_id→line→location`). 규칙은 반환 순서를 신경 쓰지 않는다
- 테스트 입력은 `tests/fixtures`의 `make_twb()`/`make_ctx()`로. 1MB 실파일로 디버깅하지 않는다
- `@pytest.mark.stub` 테스트는 stub 사실을 고정한 것 — 구현하면 깨지는 게 정상이고,
  그때 고칠 것은 **코드가 아니라 테스트**다
- **골든셋은 저장소에 없다.** 용량이 아니라 사내 재무 데이터 기밀이다
