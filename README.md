# twb-lint

**Tableau `.twb/.twbx` 파일을 위한 필수 오프라인 검증 게이트.**

> 철학: **모든 Tableau 산출물(AI 저작·편집 포함)은 twb-lint 게이트를 무조건 통과해야 한다.**
> XML이 well-formed여도 Tableau가 파일을 못 여는 "시맨틱 실패"를 앱 실행 없이 빠르게 잡아, 느린 E2E(앱 실행→스크린샷) 검증을 대체한다.

## 왜?

Tableau 파일이 열리려면 두 계층을 모두 통과해야 한다:

- **(A) 구문(syntactic)** — XML well-formed + 공식 XSD. 통과해도 안 열리는 경우가 대부분.
- **(B) 시맨틱(semantic)** — calc 함수·필드 참조·named 참조·메타↔hyper 일관성. 공식 XSD가 **명시적으로 검증하지 않는** 영역. "열리는데 안 열리는" 원인 전부 여기.

twb-lint = 공식 XSD(A) 위에 **(B) 시맨틱 검증기**를 얹은 것.

배경 문서: [`docs/`](./docs) (문제정의·스펙·설계).

## 상태

**MVP 규칙 5종 가동.** io · L-A(XSD) · L-B 규칙 ①②③⑥이 실로직이다.

| | 상태 |
|---|---|
| io (unpack·parse·모델 추출·pack) | ✅ `.hyper` 라운드트립 바이트 동일성(AC8) 통과 |
| L-A 구문 (vendored XSD) | ✅ 컴파일 캐시 + 심각도 등급. 정상본 10/10 통과 |
| L-B 규칙 ①②③⑥ | ✅ 전부 가동 |
| 테스트 | ✅ 3층 (스모크 / 규칙 계약·단위 / 골든셋) — **170 passed** |
| 라벨 확정 | ⏸ 사용자 배치 대기 (Tableau Desktop 필요 — `TODO.md` D) |

**게이트가 실제로 무엇을 막는가** (결함 주입 6종, 정상본 10개 기준):

| 주입 결함 | 판정 | 막은 계층 |
|---|---|---|
| `R4` 자식 순서 위반 · `R7` 잘못된 열거값 | ERROR | L-A (XSD) |
| `R2` viewpoint 누락 · `R3` dangling zone | ERROR | 규칙 ③ |
| `R1b` 매니페스트 항목 누락 | ERROR | 규칙 ⑥-b |
| `R1a` fcp 매니페스트 항목 누락 | WARNING **(의도)** | 규칙 ⑥-a — 인과 미검증 |

정상본 10개는 **ERROR 0건**(AC7). WARNING 24건은 전부 규칙 ②가 잡은 실제 잔재 참조다 —
삭제된 계산필드를 가리키는 서식 규칙이 남아 있어도 Tableau는 그 파일을 연다.

대상 환경: **Tableau 2026.1 · 로컬 전용** (`docs/02-specification.md` S7).

MVP 검증 규칙 (고가치 4) — **심각도는 실측이 정했다**:

| 규칙 | 심각도 | 근거 |
|---|---|---|
| `calc.functions` 미지원/환각 함수 | WARNING | 목록이 스크랩본이라 불완전할 수 있다 |
| `calc.field_refs` dangling 참조 | WARNING | **정상 파일에도 잔재 참조가 있다**(실측) |
| `named.refs` worksheet↔dashboard↔window | **ERROR** | 표본 10/10에서 세 집합이 일치. viewpoint 누락 = 내부 오류 2805CF18 |
| `manifest.gates` 기능↔매니페스트 | ERROR / WARNING | 대응표 쌍은 로드 거부 실측 → ERROR. fcp 계열은 인과 미검증 → WARNING |

`manifest.gates`와 `named.refs`가 **XSD가 원리적으로 못 잡는** 로드 거부 클래스다.

2차: `meta.hyper`(메타↔hyper 대조, `[hyper]` extra), `connection.attrs`.

### L-A는 공짜가 아니다 (실측)

공식 XSD를 그대로 쓰면 **정상 파일 9/9가 실패한다.** 전처리 3단계가 필요하다:

| 단계 | 내용 | 시점 |
|---|---|---|
| 스텁 주입 | `user`·`xml` 네임스페이스 import에 `schemaLocation` 없음 → 컴파일 불가 | vendoring |
| 과엄격 패치 | `explain-data`가 필수로 선언됨 (실제 Tableau는 미사용 시 생략) | vendoring |
| fcp 정규화 | `_.fcp.<기능>.true...<이름>` 접두사를 트리 사본에서 제거 | 검증 직전 |

전체 실측: [`docs/05-xsd-spike.md`](./docs/05-xsd-spike.md).
XSD 선택 키는 `<workbook version>`이 **아니라** `source-build`다 (2026.1이 만든 파일도 `version='18.1'`).

### 심각도 원칙

> **파일이 열리지 않는다고 확신할 때만 ERROR. 우리 지식의 공백은 WARNING.**

게이트가 mandatory이므로 거짓 ERROR 1건이 멀쩡한 파일을 막는다 → 사용자가 게이트를 끈다.
`AC7 거짓양성 0`(정상 골든셋 ERROR 0건)을 AC2(검출율)와 동급 기준으로 둔다.

## 설치

```bash
uv sync                 # 런타임 + dev
uv sync --extra hyper   # rule ④용 hyperapi 포함 (2차)
```

> `uv`가 차단된 머신(Smart App Control)에서는 `python -m venv .venv` +
> `.venv/Scripts/python -m pip install -e ".[dev]"`. 상세는 `docs/04-scaffolding.md`.

## 사용

```bash
# MCP stdio 서버 (Claude Code/Desktop/자체앱)
uv run twb-lint-mcp

# CLI
uv run twb-lint validate path/to/workbook.twbx
```

MCP 도구: `twb_unpack` · `twb_inspect` · `twb_validate`.

## 도구 (`tools/`)

```bash
python tools/vendor_schemas.py             # 공식 XSD vendoring (패치 + 컴파일 검증)
python tools/vendor_schemas.py --check     # 상류와 어긋났는지 확인
python tools/scrape_functions.py           # 함수 화이트리스트 재생성
python tools/inject_defects.py --list      # 결함 주입 레시피 목록
python tools/inject_defects.py --source <원본.twbx> --out <디렉토리>
```

`inject_defects`는 고장본과 함께 **라벨 대장**(`labels.json`)을 낸다 —
Tableau Desktop에서 열어 본 결과를 채우면 그대로 AC2·AC3 측정 입력이 된다.

## 확장 (규칙 추가)

새 시맨틱 규칙 = **파일 1개 추가, 코어 무수정**:

```python
# src/twb_lint/validation/semantic/my_rule.py
from twb_lint.models import Finding, Severity
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage


@register
class MyRule(RuleBase):
    id = "my.rule"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        ctx.model              # 구조 모델
        ctx.raw_tree           # 정규화 전 원본 트리 (fcp 기능명이 살아 있다)
        ctx.normalized_tree()  # fcp 정규화 사본 (캐시됨)
        return []              # findings 반환. 정렬은 엔진이 한다
```

레지스트리가 `semantic/`·`syntactic/` 하위 모듈을 자동 수집하고,
계약 테스트가 새 규칙을 자동으로 검사에 태운다.

## 아키텍처

- `twb_lint/` — 순수 코어 라이브러리 (**MCP를 모름**). CLI·Skill·자체앱이 그대로 import.
- `twb_lint/mcp/` — 얇은 MCP 어댑터.
- `ValidationReport.passed = ERROR 없음` = mandatory gate 판정.
- `ValidationReport.coverage` = **무엇을 검사하지 못했는가.** `passed=True`가
  "전부 검사했다"를 뜻하지 않는다 — 조용한 통과를 금지하기 위한 별도 채널이다.
