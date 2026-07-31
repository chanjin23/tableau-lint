# twb-lint

**Tableau `.twb/.twbx` 파일을 위한 필수 오프라인 검증 게이트.**

> 목표: **Tableau에서 열었을 때 빨간 느낌표가 하나도 없다.** 그것을 Tableau를 실행하지 않고 판정한다.
> 느린 E2E(앱 실행→스크린샷) 검증을 대체한다.

## 왜?

"열린다"는 기준선이 낮다. 실사용 파일 하나가 **4층**을 냈다 — 앞 층을 고치기 전에는
뒤 층이 **보이지 않는다**(Tableau가 첫 실패에서 멈춘다):

| 층 | 증상 | 사용자가 보는 것 | 규칙 |
|---|---|---|---|
| 1 | 로드 거부 (`D2E8DA72`) | 파일이 안 열린다 | `xsd.schema` · `named.refs` · `manifest.gates` |
| 2 | 설정이 버려짐 | 열리는데 **필터가 사라졌다** — 조용히 틀린 숫자 | `ref.notation` ⑦-a·⑦-b |
| 3 | 계산 오류 상태 | 열리는데 **데이터가 하나도 안 나온다** | `ref.notation` ⑦-c |
| 4 | 필드·집합 오류 상태 | 열리는데 **빨간 느낌표** | `calc.aggregation` · `set.definition` |

**층 1만 막는 게이트는 쓸모가 절반이다.** 2~4층은 파일이 "열리므로" 통과로 기록되지만,
사용자에게는 실패다.

기저에 2계층 구조가 있다:

- **(A) 구문(syntactic)** — XML well-formed + 공식 XSD. 통과해도 안 열리는 경우가 대부분.
- **(B) 시맨틱(semantic)** — calc 함수·필드 참조·named 참조·표기 규약·매니페스트 게이트.
  공식 XSD가 **명시적으로 검증하지 않는** 영역. 위 4층이 전부 여기.

twb-lint = 공식 XSD(A) 위에 **(B) 시맨틱 검증기**를 얹은 것.

배경 문서: [`docs/`](./docs) — 시작점은 [`01-problem-definition.md`](./docs/01-problem-definition.md).

## 상태

**규칙 11종 가동.** io · L-A(XSD) · L-B 규칙 ①②③⑥⑦⑧⑨⑩⑪⑬이 실로직이다.

| | 상태 |
|---|---|
| io (unpack·parse·모델 추출·pack) | ✅ `.hyper` 라운드트립 바이트 동일성(AC8) 통과 |
| L-A 구문 (vendored XSD) | ✅ 컴파일 캐시 + 심각도 등급. 정상본 61/61 통과 |
| L-B 규칙 ①②③⑥⑦⑧⑨⑩⑪ | ✅ 전부 가동 |
| 테스트 | ✅ 3층 (스모크 / 규칙 계약·단위 / 골든셋) — **271 passed, 14 skipped** (골든셋 걸면 285) |
| 라벨 확정 | ⏸ 사용자 배치 대기 (Tableau Desktop 필요 — `TODO.md` L1~L3) |

**판정 대상 4항목** (`docs/01-problem-definition.md` §4):

| | 요구 | 상태 |
|---|---|---|
| **T1** | 파일이 무조건 열린다 | ✅ 가동 |
| **T2** | 계산필드·매개변수가 오류를 내지 않는다 | 🟡 타입 정합 미구현 |
| **T3** | 집합·동작을 걸어도 오류가 나지 않는다 | ✅ 집합 + 동작 |
| **T4** | 페이지·필터·마크·열·행에 올려도 오류가 나지 않는다 | 🟡 참조 무결성(T4-a)만 — 조합 규칙은 정답지 없음 |

**게이트가 실제로 무엇을 막는가** (결함 주입 6종):

| 주입 결함 | 판정 | 막은 계층 |
|---|---|---|
| `R4` 자식 순서 위반 · `R7` 잘못된 열거값 | ERROR | L-A (XSD) |
| `R2` viewpoint 누락 · `R3` dangling zone | ERROR | 규칙 ③ |
| `R1b` 매니페스트 항목 누락 | ERROR | 규칙 ⑥-b |
| `R1a` fcp 매니페스트 항목 누락 | WARNING **(의도)** | 규칙 ⑥-a — 인과 미검증 |

정상본 61개는 **ERROR 0건**(AC7). WARNING은 전부 실제 잔재 참조다 —
삭제된 계산필드를 가리키는 서식 규칙이 남아 있어도 Tableau는 그 파일을 연다.

대상 환경: **Tableau 2026.1 · 로컬 전용** (`docs/02-specification.md` S7).

가동 규칙 11종 — **심각도는 실측이 정했다**:

| 규칙 | 담당 층 | 심각도 | 근거 |
|---|---|---|---|
| `xsd.schema` | 1 | ERROR/WARNING | 오류코드별. 거짓양성과 진짜 오류가 같은 코드를 쓴다 |
| `named.refs` worksheet↔dashboard↔window | 1 | **ERROR** | 표본 전량에서 세 집합이 일치. viewpoint 누락 = 내부 오류 2805CF18 |
| `manifest.gates` 기능↔매니페스트 | 1 | ERROR / WARNING | ⑥-b는 로드 거부 실측 → ERROR. ⑥-a(fcp)는 인과 미검증 → WARNING |
| `ref.notation` 표기 규약 | 2·3 | WARNING | 714:0 · 235:0 · **3,377:0** (매개변수 한정자) |
| `calc.functions` 미지원/환각 함수 | 3 | WARNING | 목록이 스크랩본이라 불완전할 수 있다 |
| `calc.field_refs` dangling 참조 | 3 | WARNING | **정상 파일에도 잔재 참조가 있다**(실측) |
| `calc.aggregation` 사용자 지정 집계 | 4 | WARNING | 20:0. LOD는 집계로 치지 않는다 |
| `set.definition` 집합 기반 필드 | 4 | WARNING | 82:0. 모양을 열거하지 않고 **기반 필드 유무만** 본다 |
| `action.refs` 동작 배선 | 2·4 | WARNING | 표면 9종 실측. `source-field` 반례 1건이 골든셋 파일이라 ERROR 불가 |
| `action.shape` 동작 어휘 | 2 | WARNING | `<action>`은 세 모양뿐(14:0 · 17:0 · 1). 명령·param 목록이 좁아 ERROR 불가 |
| `shelf.refs` 선반 배치 | 2·4 | WARNING | 표면 20여 종 실측. 반례 28건이 골든셋 파일 1개의 진짜 dangling |

`manifest.gates`와 `named.refs`가 **XSD가 원리적으로 못 잡는** 로드 거부 클래스다.

신규 예정: `calc.types`(⑫ 타입 정합).
2차: `meta.hyper`(메타↔hyper 대조, `[hyper]` extra) · `connection.attrs`.

### L-A는 공짜가 아니다 (실측)

공식 XSD를 그대로 쓰면 **정상 파일이 전부 실패한다.** 전처리 3단계가 필요하다:

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

**층 1은 막고, 층 2~4는 말한다.** 2~4층은 파일이 열리므로 WARNING이다 — 그래서
`passed=true`를 "괜찮다"로 읽으면 안 된다. **findings를 읽어야 한다** (02 AC9).

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

인터페이스 3종. 노출 범위가 다르다:

| 인터페이스 | 대상 | 노출 |
|---|---|---|
| MCP 서버 (`twb-lint-mcp`) | LLM 호스트 | 도구 3개 |
| CLI (`twb-lint`) | 사람·CI | `validate` 하나 |
| 파이썬 import | 코드 | 전부 (`twbx.pack()` 포함) |

## MCP 서버

### 어떤 MCP인가

**서버**다 (클라이언트가 아니다). 호스트에게 도구를 제공하는 쪽이다.

| | |
|---|---|
| 이름 | `twb-lint` |
| 트랜스포트 | **stdio** |
| SDK | 공식 `mcp[cli]` FastMCP |
| 진입점 | `twb-lint-mcp` = `twb_lint.mcp.server:main` |
| 도구 | `twb_validate` · `twb_inspect` · `twb_unpack` |
| 리소스·프롬프트 | 없음 |
| 네트워크 | 없음. 전부 로컬 파일 I/O |

`src/twb_lint/mcp/server.py`는 **얇은 어댑터**다 — 코어 함수를 부르고 결과를 dict로 바꾸는 것뿐,
검증 로직이 없다. MCP를 걷어내도 CLI·파이썬 경로가 그대로 돈다 (호스트 독립).

서버는 자기 버전을 `__version__`으로 보고한다. 비워 두면 저수준 서버가 **MCP SDK 버전**으로
채워서 호스트가 "twb-lint 1.28.1"을 보게 된다 — 게이트가 판정을 내리는 도구라 버전 오인은
값이 크다 (실측으로 드러났다, `server.py:22-25`).

### 등록

Claude Code:

```bash
claude mcp add twb-lint -- uv run --directory /path/to/tableau-lint twb-lint-mcp
```

`uv`가 차단된 머신(Smart App Control):

```bash
claude mcp add twb-lint -- /path/to/tableau-lint/.venv/Scripts/python -m twb_lint.mcp.server
```

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "twb-lint": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/tableau-lint", "twb-lint-mcp"]
    }
  }
}
```

경로는 **절대경로**로 준다. 도구에 넘기는 파일 경로가 상대경로면 서버 프로세스의 작업
디렉토리 기준으로 해석된다 — 호스트가 어디서 띄웠는지에 따라 달라진다.

### 도구 3개

#### `twb_validate(path) -> {passed, findings[]}`

게이트 판정. `.twb`/`.twbx` 둘 다 받는다.

```json
{
  "passed": false,
  "findings": [
    {
      "severity": "error",
      "rule_id": "named.refs",
      "location": "dashboards/요약",
      "message": "시트 '지역별'에 대응하는 viewpoint가 대시보드 window에 없다 — 로드 시 내부 오류 2805CF18",
      "fix": "..."
    }
  ]
}
```

- `passed = ERROR 없음`. **`false`면 산출물을 내보내지 않는다** (mandatory gate)
- WARNING은 `passed`를 막지 않는다. 심각도 원칙(위)의 결과다 — **findings를 읽어야 한다**
- 예외를 던지지 않는다. 파일이 없어도 `passed=false` + `rule_id="input.readable"` finding이다
  (판정 경로는 하나다, 02 S5)
- findings 정렬은 엔진이 보장한다 (`stage→rule_id→line→location`)

#### `twb_inspect(path) -> 구조 모델`

판정 없이 **사실만** 추출. 편집 전 정찰용.

```json
{
  "source_build": "2026.1.1 (20261.26.0410.0924)",
  "release": "2026.1",
  "twb_version": "18.1",
  "manifest_features": ["SheetIdentifierTracking"],
  "datasources": {
    "federated.0abc": {
      "caption": "Sales Extract",
      "fields": ["Calculation_1", "Profit", "Sales"],
      "calcs": ["Calculation_1"]
    }
  },
  "worksheets": ["매출 추이"],
  "dashboards": {"요약": {"sheet_zones": ["매출 추이"], "viewpoints": ["매출 추이"]}}
}
```

읽는 법:

- `release`가 어떤 XSD·함수 목록으로 검증될지를 결정한다. `null`이면 구문 검증이 스킵된다
- `twb_version`은 **최소 호환 버전**이다. 2026.1이 만든 파일도 `18.1`이라 버전 판별에 못 쓴다
- `fields`는 `<column>`만이 아니다 — `<group>`·`<column-instance>`·`<metadata-record>`까지 모은다.
  손대지 않은 DB 컬럼은 `<column>`에 없으므로, 좁게 모으면 실사용 참조의 약 4%가
  dangling으로 잡힌다 (실측 687/16,754, 전부 거짓양성)
- 이름은 내부 ID다 (`Calculation_1`). 사용자에게 보이는 이름은 `caption`
- `sheet_zones`는 `type-v2`가 **없는** zone만 — 레이아웃 컨테이너·텍스트·이미지 존을 뺀다
- 파일을 열지 못하면 **예외를 던진다** (`safety.InputError`). 빈 모델을 반환하면
  "데이터소스도 시트도 없는 워크북"과 구분되지 않는다 (07 G7)

#### `twb_unpack(path, dest) -> {twb_path, root}`

`.twbx`(=ZIP)를 `dest`에 푼다. `.twb` 편집이 필요할 때.

```json
{"twb_path": "work/sales.twb", "root": "work/"}
```

- `.twb` 입력이면 no-op — 경로만 그대로 감싸 반환한다
- `.twb`는 **최상위 우선**으로 고른다. 하위 디렉토리 것을 집으면 엉뚱한 워크북을 검증한다
- `.hyper`는 바이트 그대로 나온다 (재압축·재인코딩 금지, 07 G6)
- 해제 정책 (`io/safety.py`): 엔트리 10,000개 · 해제 총량 2GiB · 압축비 200배 · 소스 512MiB ·
  `.twb` 64MiB. zip slip은 거부. 상한은 ZIP 헤더 선언값이 **아니라 실제로 읽은 바이트**로도 건다
  (헤더는 아카이브 제작자가 쓰는 값이라 거짓말할 수 있다)
- 정책 위반·깨진 ZIP·`.twb` 없음·권한 없음은 **예외** (`ArchiveError` ⊂ `safety.InputError`)

### 전형적 흐름

**게이트만** — CI·산출물 검사:

```
twb_validate(파일)  →  passed 확인 + findings 읽기
```

**정찰** — 필드·시트 이름이 필요할 때:

```
twb_inspect(파일)  →  caption↔내부 ID 대조, fields로 참조 가능 여부 확인
```

**편집 왕복** — `.twb` XML을 고쳐야 할 때:

```
1. twb_validate(.twbx)   기준선 — 원래 있던 WARNING을 기록한다
2. twb_unpack            .twb 꺼내기
3. twb_inspect           내부 ID·필드 목록·release 확보
4. (XML 편집)            ← 도구 없음. 아래 "한계" 참조
5. twb_validate(.twb)    채점. 1단계와 대조. 문제 있으면 4로
6. twbx.pack()           ← MCP 미노출. 파이썬에서 직접
7. twb_validate(.twbx)   최종
8. Tableau Desktop       ← 대체 불가
```

1단계 기준선이 중요하다. 정상 파일에도 잔재 참조 WARNING이 있으므로(실측 24건),
기준선 없이 편집하면 남의 흠집을 자기 것으로 오해한다.

편집 루프는 5단계를 `.twb`로 돌린다 — 고칠 때마다 다시 묶으면 느리다.

### 한계 (편집 루프 관점)

| | |
|---|---|
| `pack`이 MCP에 없다 | 재포장은 파이썬에서 `twbx.pack(root, out)`. MVP가 read-only라 노출하지 않았다 (02 §89) |
| 편집 연산이 없다 | 의존 참조 자동 갱신·dangling 유발 시 거부는 C4 편집기 몫. 지금은 XML을 직접 만진다 |
| `coverage`를 반환하지 않는다 | 코어 `ValidationReport`는 갖고 있는데 MCP 응답에서 버린다 → 호출자가 검사 범위를 알 수 없다 (03 D2, `TODO.md` F3) |
| 선반 **조합**을 검사하지 않는다 | 배치 참조 실존은 규칙 ⑪이 본다. 어떤 필드를 어떤 선반에 놓으면 오류인지(T4-b)는 정답지가 없다 (01 §7) |
| `passed=true` ≠ 열린다 | 규칙 ⑥의 품질은 `manifest_gates.json`의 쌍 개수다. 표가 2쌍이던 시점에 실파일 1건이 통과하고 Tableau가 `D2E8DA72`로 거부했다 (05 F9) |

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
  단, **MCP `twb_validate`는 이 필드를 반환하지 않는다** — 어댑터가 버린다
  (`TODO.md` F3).
