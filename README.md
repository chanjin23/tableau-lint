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

**구현 착수 준비 완료** — 골격 + stub. 설계 미결·데이터·테스트 인프라는 갖췄고,
실제 검증 로직은 구현 단계에서 채운다.

| | 상태 |
|---|---|
| 설계 결정 | ✅ 8건 해소 (규칙 입력 계약 · 심각도 정책 · calc 표면 · 입력 방어 …) |
| vendored XSD | ✅ 패치 3건 + 컴파일 검증. 정상본 **9/9 통과** |
| 함수 화이트리스트 | ✅ 218종 |
| 테스트 | ✅ 3층 (스모크 / 규칙 계약·단위 / 골든셋) — 64 passed |
| 고장본 골든셋 | ✅ 주입 스크립트로 생성 가능. 라벨 확정은 사용자 배치 대기 |
| 규칙 로직 | ⏳ stub |

대상 환경: **Tableau 2026.1 · 로컬 전용** (`docs/02-specification.md` S7).

MVP 검증 규칙 (고가치 4):
1. `calc.functions` — calc 내 미지원/환각 함수 (함수 화이트리스트) — **WARNING 기조**
2. `calc.field_refs` — calc 필드 참조 dangling 해소
3. `named.refs` — worksheet↔dashboard↔window 참조 무결성 (viewpoint 누락 = 내부 오류 2805CF18)
4. `manifest.gates` — 기능↔`document-format-change-manifest` 일관성. **XSD가 못 잡는 로드 거부 클래스**

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
