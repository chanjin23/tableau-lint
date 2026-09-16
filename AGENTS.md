# AGENTS.md

**twb-lint** — Tableau `.twb/.twbx` 오프라인 검증 게이트.
공식 XSD(구문) 위에 시맨틱 검증기를 얹어, Tableau를 실행하지 않고
**"열었을 때 빨간 느낌표가 없는가"**를 판정한다.

대상: Tableau **2026.1 단독 · 로컬 오프라인**.
현 단계: **규칙 13종 가동** — io · L-A(XSD) · L-B 규칙 ①②③⑥⑦⑧⑨⑩⑪⑬⑭⑮.
정상본 **61개** ERROR 0 · 주입 6종 중 5종 차단(R1a는 의도적 WARNING).

**2026-07-31 문제정의 재설정 (01 v2.0)** — 위험은 *편집*이 아니라 **생성**에 있다.
판정 대상 4항목: **T1** 파일이 열린다(✅) · **T2** 계산·매개변수(🟡) ·
**T3** 집합·동작(✅) · **T4** 선반 배치(🟡 T4-a만 — 조합 규칙은 정답지 없음).
남은 코드 작업 = 규칙 **⑫ `calc.types`**.

실패는 **층으로 나온다** — 로드 거부 → 설정 버려짐 → 데이터 안 나옴 → 필드 오류 상태
(05 F5-b~F5-e). **앞 층을 고치기 전에는 뒤 층이 보이지 않는다.**
**층 1은 막고(ERROR), 층 2~4는 말한다(WARNING).**
층을 벗겨 **규칙으로 바꾸는** 절차가 [`/defect-loop`](./.Codex/commands/defect-loop.md),
그 규칙으로 **워크북을 저작하는** 절차가 [`/author-loop`](./.Codex/commands/author-loop.md)다.
진행 상황은 [`docs/impl-progress.md`](./docs/impl-progress.md)가 갖는다.

## 작업 전 반드시 읽는다

| | 문서 |
|---|---|
| **프로젝트 정보** | [`docs/tableau-ai-sor.md`](./docs/tableau-ai-sor.md) — SOR 인덱스. 여기서 시작 |
| **무엇을 판정하는가** | [`docs/01-problem-definition.md`](./docs/01-problem-definition.md) **v2.0** — T1~T4 · 실패 4층 |
| **구현 시 필수** | [`docs/07-implementation-guide.md`](./docs/07-implementation-guide.md) — G1~G10 함정 · 검증 파이프라인 · 관례 |
| **지금 할 일** | [`TODO.md`](./TODO.md) — `/defect-loop` D2 · 규칙 ⑫. 라벨링 배치(L)는 블로커에서 강등됐다 |

`docs/`가 권위 문서다. 이 파일과 어긋나면 **`docs/` 우선.**

## 검증 파이프라인 (코드 수정 시 필수)

```bash
.venv/Scripts/python -m pytest -q        # 316 passed, 14 skipped (골든셋 미설정 시)
.venv/Scripts/python -m ruff check .     # All checks passed
.venv/Scripts/python -m mypy             # Success: no issues in 55 source files
```

하나라도 깨지면 커밋하지 않는다. 규칙을 구현했으면 **실파일 회귀**까지 —
골든셋 경로를 환경변수로 걸면 `330 passed`가 된다 (AC8 xfail은 io 1단계 완료로 해제됐다).
절차는 [`07-implementation-guide.md`](./docs/07-implementation-guide.md) §2.

```bash
export TWB_LINT_GOLDEN_NORMAL='<정상본 glob>;<glob>;...'   # ';' 구분, 미설정 시 skip
```

> `uv`는 이 머신에서 실행이 차단된다(Smart App Control). 위 `.venv` 경로를 쓴다.
> **`mypy`도 2026-07-30부터 같은 정책에 막힌다** (`mypy/ipc.py`가 base64 확장 로드 실패).
> 타입 검사는 이 머신에서 돌리지 못한다 — 재설치로 풀리는지 확인 전까지 pytest·ruff만 게이트다.

## 자주 트리는 것 (상세는 07)

- 버전 키는 `source-build`다. `<workbook version>`은 최소 호환 버전(`18.1`)이라 못 쓴다
- 공식 XSD를 그대로 쓰면 정상 파일이 전부 실패한다 — 전처리 3단계(스텁·패치·**fcp 정규화**) 필수
- **fcp 정규화는 정보를 지운다.** 규칙 ⑥-a는 `ctx.raw_tree`(정규화 전), L-A는
  `ctx.normalized_tree()`(정규화 후)를 본다 — 입력이 다르다 (05 F7)
- **저작할 때도 접두사를 지우면 안 된다.** 모서리 반경은
  `<_.fcp.DashboardRoundedCorners.true...format>`이지 맨 `<format>`이 아니다 —
  맨 이름으로 쓰면 `not in enumeration`으로 거부된다. 규칙 ⑮가 잡는다 (05 F5-j)
- **필드 참조 표기가 2종이다.** calc 안 `[Calculation_1234]` vs 속성 `[ds].[usr:name:qk]`.
  정규화 없이 대조하면 규칙 ②가 전량 dangling을 뱉는다 (03 D3.6, 07 G8)
- **ERROR는 확신할 때만.** 거짓양성 1건이 게이트를 무력화한다 (AC7 = 정상본 ERROR 0건).
  L-A조차 전부 ERROR가 아니다 — 거짓양성과 진짜 오류가 **같은 오류코드**를 쓴다 (03 D3)
- **`passed=true`는 "괜찮다"가 아니다.** 층 2~4(설정 버려짐·데이터 없음·빨간 느낌표)는
  파일이 열리므로 WARNING이고 `passed`를 막지 않는다. **findings를 읽는다** (02 AC9)
- XSD 통과 ≠ 열린다 — 매니페스트가 문법을 게이팅한다. 주입본 R1b·R2·R3가 이를 실증한다
- **규칙은 `ctx`를 받는다.** 트리를 규칙 안에서 재파싱하지 않는다 (파싱은 파일당 1회).
  파서는 `io.safety.make_parser()`로만 만든다 — 기본 파서는 엔티티를 해석한다(XXE)
- **검사 못 했으면 말한다** — `ctx.note_skip()`. 빈 리스트를 조용히 반환하면
  "전부 검사했고 문제없음"으로 기록된다
- 새 규칙 = `validation/semantic/` 파일 1개 + `@register`. 코어 무수정 (현재 13규칙).
  계약 테스트가 새 규칙도 자동으로 잡는다
- findings 정렬은 **엔진이 보장**한다(`stage→rule_id→line→location`). 규칙은 반환 순서를 신경 쓰지 않는다
- 테스트 입력은 `tests/fixtures`의 `make_twb()`/`make_ctx()`로. 1MB 실파일로 디버깅하지 않는다
- `@pytest.mark.stub` 테스트는 stub 사실을 고정한 것 — 구현하면 깨지는 게 정상이고,
  그때 고칠 것은 **코드가 아니라 테스트**다
- **골든셋은 저장소에 없다.** 용량이 아니라 사내 재무 데이터 기밀이다
