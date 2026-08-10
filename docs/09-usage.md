# 사용 상세 — MCP 서버 · CLI · 도구 · 확장

> README에서 이관한 상세 레퍼런스. 첫 소개는 [`../README.md`](../README.md).

## 인터페이스 3종

노출 범위가 다르다:

| 인터페이스 | 대상 | 노출 |
|---|---|---|
| MCP 서버 (`twb-lint-mcp`) | LLM 호스트 | 도구 3개 |
| CLI (`twb-lint`) | 사람·CI | `validate` 하나 |
| 파이썬 import | 코드 | 전부 (`twbx.pack()` 포함) |

```bash
uv run twb-lint-mcp                              # MCP stdio 서버
uv run twb-lint validate path/to/workbook.twbx   # CLI
```

## MCP 서버

### 어떤 MCP인가

**서버**다 (클라이언트가 아니다). 호스트에게 도구를 제공하는 쪽이다.

| | |
|---|---|
| 이름 | `twb-lint` |
| 트랜스포트 | **stdio** |
| SDK | 공식 `mcp[cli]` FastMCP |
| 진입점 | `twb-lint-mcp` = `twb_lint.mcp.server:main` |
| 도구 | `twb_validate` · `twb_inspect` · `twb_unpack` · `twb_recipe` |
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

### 도구 4개

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
- WARNING은 `passed`를 막지 않는다. 심각도 원칙의 결과다 — **findings를 읽어야 한다**
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

#### `twb_recipe(query='') -> {found, ...}`

XML을 쓰기(생성·편집) **전에** 조회하는 저작 레시피. 다른 PC·세션에서 MCP만
연결해도 레시피가 넘어가게 하는 통로다 — 도구 설명 자체가 "쓰기 전에 반드시 조회"를
지시하므로 호스트 LLM이 편집 전에 자연스럽게 부른다.

| 호출 | 반환 |
|---|---|
| `twb_recipe()` | `{found:true, index:<매핑표 본문>, recipes:[파일명…]}` |
| `twb_recipe('계산 필드 추가')` | `{found:true, name:'01-calc-field-create.md', content:<본문>}` |
| 맞는 게 없음 | `{found:false, message, index}` — **지어내지 말고** 미관찰로 보고 |

- 매칭은 결정론 — 질의어 토큰의 제목·본문 등장 점수, 동점은 파일명 순
- 내용의 SOR은 `docs/recipes/`다. 서버는 읽기만 한다 — 문서를 고치면 그대로 반영
- wheel 설치처럼 `docs/`가 없는 배치에서는 `found:false` + 안내 메시지
  (저장소 체크아웃 + `--directory` 등록이 전제)

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
4. twb_recipe('작업')    레시피 확보 → 그대로 XML 편집 (편집 도구는 없다)
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
| 편집 연산이 없다 | 의존 참조 자동 갱신·dangling 유발 시 거부는 C4 편집기 몫. 지금은 XML을 직접 만진다 — 쓸 때는 [`recipes/`](./recipes) 레시피를 따른다 |
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
함정·관례는 [`07-implementation-guide.md`](./07-implementation-guide.md).

## 아키텍처

- `twb_lint/` — 순수 코어 라이브러리 (**MCP를 모름**). CLI·Skill·자체앱이 그대로 import.
- `twb_lint/mcp/` — 얇은 MCP 어댑터.
- `ValidationReport.passed = ERROR 없음` = mandatory gate 판정.
- `ValidationReport.coverage` = **무엇을 검사하지 못했는가.** `passed=True`가
  "전부 검사했다"를 뜻하지 않는다 — 조용한 통과를 금지하기 위한 별도 채널이다.
  단, **MCP `twb_validate`는 이 필드를 반환하지 않는다** — 어댑터가 버린다
  (`TODO.md` F3).
