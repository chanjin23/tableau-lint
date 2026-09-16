---
name: "source-command-impl-loop"
description: "twb-lint 구현 루프 1회분 — 다음 작업 단위 1개를 골라 구현·검증·커밋한다"
---

# source-command-impl-loop

Use this skill when the user asks to run the migrated source command `impl-loop`.

## Command Template

twb-lint 구현 루프 1회분이다. 이전 반복의 기억은 없다고 가정한다 — 상태는 전부 저장소에서 읽는다.

## 0. 상태 파악 (매 반복 필수, 생략 금지)

1. `docs/impl-progress.md`를 읽는다. 없으면 `docs/07-implementation-guide.md` §4의 구현 순서로
   대장을 새로 만들고 이번 반복은 거기서 끝낸다.
2. `docs/07-implementation-guide.md` §1(G1~G10)·§4를 읽는다. G1~G10은 **매번** 읽는다 —
   여기 적힌 함정이 곧 실패 원인이다.
3. `git log --oneline -5`로 마지막 커밋을 본다.
4. 골든셋 환경변수를 걸고 게이트를 돌려 baseline을 확인한다. **환경변수와 명령을 같은 호출
   안에 둔다** — Bash 도구는 셸 상태를 유지하지 않아, 따로 `export`하면 다음 호출에서
   골든셋이 조용히 skip된다(`67 passed`로 보이고 실파일 회귀를 안 돈 상태다):

```bash
export TWB_LINT_GOLDEN_NORMAL='C:/dev/JW/2.개발/MA_002_경영관리-재무-현금흐름/*.twbx;C:/dev/JW/2.개발/MA_004_경영관리-재무-손익계산서/*_JWLH_*.twbx;C:/dev/태블로판차분석_제약_260616_진행중_2.twbx' \
  && .venv/Scripts/python -m pytest -q \
  && .venv/Scripts/python -m ruff check . \
  && .venv/Scripts/python -m mypy
```

`74 passed`(또는 그 이상)가 안 보이면 골든셋이 안 걸린 것이다. 다시 건다.

baseline이 이미 red면 **새 작업을 시작하지 않는다.** 그 red를 고치는 것이 이번 반복의 작업이다.

## 1. 이번 반복의 작업 단위 1개를 고른다

순서는 `07` §4를 따른다. 진행 대장에서 `[ ]`인 첫 항목을 집는다:

1. `io/twbx.unpack` + `io/twb.parse` → `inspect.load_context` 실채움 ← 병목
2. `syntactic/xsd.py` 스키마 로드(캐시) + `severity_for()` 배선
3. `calc/extractor.py` + 규칙 ①②
4. 규칙 ③ / 규칙 ⑥

한 항목이 크면 쪼갠다. **한 반복에 파일 3개 이상을 건드리게 되면 너무 크다** —
쪼개서 앞부분만 하고, 쪼갠 결과를 대장에 반영한다.

## 2. 구현한다

지킬 것 (어기면 게이트가 잡거나, 더 나쁘게는 조용히 틀린다):

- 파서는 `io.safety.make_parser()`로만 만든다. `etree.parse(path)` 단독 호출 금지 (XXE)
- ZIP 해제는 `safety.safe_extract_path()` + `safety.check_zip_entry()`를 통과시킨다
- 규칙 안에서 재파싱 금지. 파싱은 `inspect.load_context()`에서 파일당 1회
- 규칙 ⑥-a는 `ctx.raw_tree`(정규화 전), L-A는 `ctx.normalized_tree()`(정규화 후).
  입력을 바꾸지 않는다
- 검사 못 했으면 `ctx.note_skip()`. 빈 리스트를 조용히 반환하지 않는다
- **ERROR는 파일이 안 열린다고 확신할 때만.** 애매하면 WARNING.
  거짓 ERROR 1건이 게이트를 무력화한다 (AC7 = 정상본 ERROR 0건)
- 버전 키는 `source-build`다. `<workbook version>`은 최소 호환 버전이라 못 쓴다
- `.hyper`는 바이트 무손실. 재압축·재인코딩 금지 (AC8)
- `@pytest.mark.stub` 테스트가 깨지면 **고칠 것은 코드가 아니라 테스트다**.
  stub 사실을 고정한 테스트이므로 구현 후 실제 동작을 단언하도록 교체한다
- 새 규칙은 `validation/semantic/` 파일 1개 + `@register`. `engine.py`·`registry.py` 무수정
- 테스트 입력은 `tests/fixtures`의 `make_twb()`/`make_ctx()`로. 1MB 실파일로 디버깅하지 않는다

## 3. 검증한다 — 통과 못 하면 커밋하지 않는다

0번의 게이트 3종을 골든셋 환경변수를 건 상태로 다시 돌린다.

구현한 것이 규칙이면 추가로:

- **정상본 회귀 (AC7)**: `pytest tests/golden`에서 **ERROR 0건**.
  여기서 깨지면 파일이 아니라 규칙을 의심한다
- WARNING 건수를 대장에 적는다 (경고 인플레이션 감시)
- 1단계를 끝냈으면 AC8 테스트(`test_c4_hyper_survives_a_roundtrip`)가 xfail → 통과로
  뒤집혔는지 확인하고 xfail 마커를 뗀다

## 4. 커밋하고 대장을 갱신한다

- 커밋 접두: `feat:`/`fix:`/`test:`/`docs:`. 본문에 **왜**를 적는다
- `docs/impl-progress.md`의 해당 항목을 `[x]`로 바꾸고 반복 로그에 한 줄 남긴다
  (게이트 수치 포함)
- 설계 결정이 새로 생겼으면 **먼저 `docs/`를 고치고** 대장에 적는다. `docs/`가 권위 문서다

## 5. 멈춤 조건

아래 중 하나면 루프를 끝내고 최종 보고를 낸다:

- `07` §4의 1~4단계가 전부 `[x]`이고, 골든셋 포함 게이트가 green이며, AC8이 통과한다
- **같은 실패로 3회 연속 막혔다** — 무한 재시도 대신 멈추고, 무엇을 시도했고 무엇이
  어떻게 실패했는지 정확한 오류 문구와 함께 보고한다
- 사람이 Tableau를 열어야만 진행되는 지점에 닿았고, 우회할 다른 단위도 없다

## 절대 하지 않는 것

- **D1~D4·B4를 시도하지 않는다.** Tableau Desktop 실행이 필요한 사용자 배치다.
  그 자리에 닿으면 우회해서 다른 단위를 집는다
- **골든셋 원본 9개를 수정하지 않는다.** 주입은 `tools/inject_defects.py`가 복사본에만 한다
- 저장소에 실험 산출물을 남기지 않는다. 임시 파일은 스크래치패드로
- 게이트가 red인데 커밋하지 않는다. 테스트를 통과시키려고 단언을 약화시키지 않는다
- `docs/`와 코드가 어긋난 채로 반복을 끝내지 않는다
