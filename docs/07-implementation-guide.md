# Tableau 저작 AI — 구현 가이드 (Implementation Guide)

> SOR 문서. 인덱스 [`tableau-ai-sor.md`](./tableau-ai-sor.md).
> 진입점은 루트 [`CLAUDE.md`](../CLAUDE.md).

## 문서 관리

| 항목 | 값 |
|---|---|
| 상태 | 🔄 living doc (구현 진행하며 갱신) |
| 버전 | v1.1 (2026-07-29) |
| 소유자 | ax3didim@gmail.com |
| 전제 | [설계](./03-design.md) v1.3 확정 · [스파이크](./05-xsd-spike.md) 완료 |
| v1.1 변경 | G8~G10 신설(필드 참조 표기 · 규칙 입력 계약 · 조용히 통과 금지) · G7 교체(stub 사실 갱신) · §2 검증 파이프라인 갱신 · §4 구현 순서 갱신 |

---

## 1. 구현 전 반드시 아는 것 (G1~G10)

모르면 **틀리게 구현하는** 항목만 추렸다. 근거는 [`05-xsd-spike.md`](./05-xsd-spike.md) 실측.

### G1. 버전 키는 `source-build`다 — `<workbook version>`이 아니다

```xml
<workbook version='18.1' original-version='18.1'
          source-build='2026.1.1 (20261.26.0410.0924)'>
```

Tableau **2026.1**이 저장한 파일도 `version='18.1'`이다. 이 값은 저작 버전이 아니라
*"이 버전 이상이면 열 수 있다"* 는 **최소 호환 버전**이며 사용 기능에서 역산된다.

```python
release = config.release_from_source_build(model.source_build)   # "2026.1"
config.xsd_path(release)
```

`model.twb_version`은 버리지 않는다 — 로더 문법 판정(G4)의 입력이다. (근거: 05 F4)

### G2. 공식 XSD를 그대로 쓰면 정상 파일이 전부 실패한다

실사용 워크북 9개 전부 실패했다. 전처리 3단계를 넣어야 9/9 통과한다.

| 단계 | 내용 | 시점 |
|---|---|---|
| 스텁 주입 | `user`·`xml` import에 `schemaLocation` 없음 → 컴파일 자체 불가 | vendoring |
| 과엄격 패치 | `explain-data`가 필수 선언 (실제 Tableau는 미사용 시 생략) | vendoring |
| **fcp 정규화** | `_.fcp.<기능>.<true\|false>...<이름>` 접두사 제거 | **검증 직전** |

```python
FCP = re.compile(r'^_\.fcp\.[^.]+\.(?:true|false)\.\.\.')
# 요소 태그와 속성 키 양쪽에 적용. 반드시 트리 사본에서 — 원본 불변
```

fcp는 Tableau 하위호환 장치다. 오류의 98%가 이것이었다(파일당 48~55건). (근거: 05 F1~F3)

### G3. ERROR는 확신할 때만 — 거짓양성이 더 치명적이다

> **파일이 열리지 않는다고 확신할 때만 ERROR. 우리 지식의 공백은 WARNING.**
> ([`02-specification.md`](./02-specification.md) S1-6)

게이트가 mandatory라 거짓 ERROR 1건이 멀쩡한 파일을 막는다 → 사용자가 게이트를 끈다 →
프로젝트 목적 소멸. **AC7 = 정상 골든셋 ERROR 0건**은 AC2(검출율)와 동급 기준이다.

- 화이트리스트에 없는 함수 = "그 함수가 없다"가 아니라 "**우리 목록이 불완전하다**" → WARNING
- calc 파싱 실패 → WARNING + 해당 calc 하위 검사 스킵(스킵 사실을 보고)
- 대응표에 없는 요소를 추측해서 ERROR 내지 않는다

### G4. XSD 통과 ≠ 열린다 — 매니페스트가 문법을 게이팅한다

> **유효 문법 = `version` 선언 × `<document-format-change-manifest>` 항목 집합**

기능을 쓰면서 대응 매니페스트 항목을 선언하지 않으면
`no declaration found for element '<요소>'`로 **로드 거부**된다.

실측 쌍: `<manual-sort>` ↔ `SortTagCleanup`,
`<edit-group-action>` ↔ `GroupAction` + `GroupActionAddRemove`.

공식 XSD는 `manual-sort`를 무조건 허용한다 → **L-A를 통과하고 Tableau에서 안 열린다.**
AC3(무거짓통과) 위반의 실증 사례이자 규칙 ⑥의 존재 이유. (근거: 05 F5, [`06`](./06-rule-candidates.md) R1)

**fcp 계열은 표가 필요 없다** (05 F7). 매니페스트 항목 이름에도 fcp 접두사가 붙어서,
`_.fcp.<F>....`를 쓰면 `_.fcp.<F>.true...<F>` 항목이 있어야 한다는 규칙이 구조에서 나온다.

```
_.fcp.DashboardRoundedCorners.true...format                    ← 사용 요소
_.fcp.DashboardRoundedCorners.true...DashboardRoundedCorners   ← 필요한 매니페스트 항목
```

⚠️ **G2의 fcp 정규화가 이 정보를 지운다** (`…...format` → `format`). 규칙 ⑥-a는
**정규화 전 원본 트리**에서 돌려야 한다 — L-A(정규화 후 사본)와 입력이 다르다.

### G5. 필드 참조는 네임스페이스가 있다

참조는 `[datasource].[Field]`다. 플랫 `set[str]`으로 대조하면 동명 필드에서
오통과(FN) 또는 거짓 dangling(FP)이 난다.

- `model.field_names(ds)` / `model.qualified_field_names()`를 쓴다
- **caption이 아니라 내부 `name`으로 대조한다** (계산필드는 `[Calculation_1234567890]`)
- **특수 네임스페이스 예외 필수**: `[:Measure Names]`·`[:Measure Values]`·
  `[Parameters].[…]`·집합/그룹/bin/계층. 과거 lint가 `[:Measure Names]`에서 오탐했다
  ([`06`](./06-rule-candidates.md) R9 비고)

상세 모델 정의: [`03-design.md`](./03-design.md) D3.5.

### G6. XML은 문자열로 편집하지 않는다

모든 `.twb` 변경은 **파싱된 lxml 트리 조작 → 재직렬화**다. 문자열 치환 불허 (02 S1-1).
`.twbx` unpack/pack 시 `.hyper` 바이너리는 **무손실 보존**(재압축·재인코딩 금지).

### G7. 지금은 stub이지만 **조용히 통과하지는 않는다** (v1.1 갱신)

```
twb-lint validate nonexistent.twb   →  FAIL (exit 1, input.readable ERROR)
twb-lint validate real.twbx         →  PASS, 단 coverage에 skipped 5건
```

v1.0에서는 없는 파일도 PASS였다. 지금은 입력 점검이 들어가 ERROR가 나고, 규칙들은
"미구현이라 검사하지 못했다"를 `coverage`로 보고한다. **`passed=True`를 액면대로 읽지 마라** —
`report.fully_covered`가 False면 검사되지 않은 영역이 있다는 뜻이다.

### G8. 필드 참조 표기가 **두 가지**다 — 규칙 ②의 최대 함정 (v1.1 신설)

```
calc 수식 안       [Calculation_2403322100842499]                 내부 이름 그대로
워크시트 속성      [federated.1wko…].[usr:Calculation_1737…:qk]   역할 접두 + 집계 접미
```

같은 필드인데 표기가 다르다. **정규화 없이 대조하면 규칙 ②가 전량 dangling을 뱉는다.**

실측 분포(표본 9개): 역할 접두 `none:`·`usr:`·`sum:`·`min:`·`mn:`·`yr:`·`cnt:`·`io:`·`attr:`,
종류 접미 `:nk`·`:qk`·`:ok`. 데이터소스는 `federated.*` 10,045회 · `Parameters` 2,135회.

특수 네임스페이스 예외는 선택이 아니다 — `[:Measure Names]`가 **1,294회** 나온다.
과거 lint가 정확히 여기서 오탐했다(함정 S9).

수집 표면 전체 목록은 [`03-design.md`](./03-design.md) D3.6. 요약:
- 수식이 있는 곳 = `<calculation@formula>` (4,757회) + **`<groupfilter@expression>`** (3회)
- `groupfilter@expression`은 적지만 `//` 주석 · XML 엔티티 · 개행을 **전부** 담고 있다.
  Lark 문법이 이걸 못 먹으면 파싱 실패 WARNING이 그 자리에서 난다

### G9. 규칙은 `ctx`를 받는다 — 트리를 다시 파싱하지 마라 (v1.1 신설)

```python
def check(self, ctx: ValidationContext) -> list[Finding]:
    ctx.model              # 구조 모델
    ctx.raw_tree           # 정규화 전 원본   ← 규칙 ⑥-a는 반드시 이것
    ctx.normalized_tree()  # fcp 정규화 사본  ← L-A는 이것 (캐시됨)
```

- **`etree.parse()`를 규칙 안에서 부르지 않는다.** 파싱은 `inspect.load_context()`에서
  파일당 1회다. 규칙마다 재파싱하면 1MB × 규칙 수가 되어 AC5와 충돌한다
- 파서가 필요하면 **`io.safety.make_parser()`만** 쓴다 (G10)
- 규칙은 트리를 변경하지 않는다 — 뒤에 도는 규칙의 입력이 달라진다 (계약 테스트가 잡는다)

### G10. 입력은 적대적이라고 가정한다 (v1.1 신설)

AI가 만든 파일을 먹는 도구다. `etree.parse(path)`를 파서 없이 부르면 **기본 파서(엔티티
해석 활성)** 가 쓰여 XXE·엔티티 폭탄이 그대로 열린다.

```python
from twb_lint.io import safety
etree.parse(path, safety.make_parser())     # 항상 이렇게
```

ZIP 해제는 `safety.safe_extract_path()`(zip slip) + `safety.check_zip_entry()`(zip bomb)를
통과시킨다. 상한값과 근거는 [`03-design.md`](./03-design.md) D9.

---

## 2. 검증 파이프라인

**코드를 고쳤으면 반드시 아래 3개를 통과시킨다. 하나라도 깨지면 커밋하지 않는다.**

```bash
.venv/Scripts/python -m pytest -q        # 테스트
.venv/Scripts/python -m ruff check .     # 린트 (line-length 100)
.venv/Scripts/python -m mypy             # 타입 (strict)
```

venv를 활성화했으면 접두사 없이:

```bash
source .venv/Scripts/activate   # bash    /    .\.venv\Scripts\Activate.ps1   # PowerShell
pytest -q && ruff check . && mypy
```

VS Code: **Ctrl+Shift+B** = 게이트 전체. F5 = 디버그 실행(CLI·MCP·pytest).

기대 출력 (2026-07-29 기준):

```
158 passed, 12 skipped
All checks passed!
Success: no issues found in 54 source files
```

`skipped` 8건은 골든셋 테스트다 — 경로 환경변수가 없으면 건너뛴다(아래).

**mypy는 `src`·`tests`·`tools`를 전부 본다.** 테스트에 타입 오류가 있으면 그 테스트가
의도한 것을 검사하지 못하고 있을 수 있다 — 실제로 범위를 넓혔더니 죽은 `type: ignore`
2건이 드러났다.

### 게이트가 실제로 무엇을 잡는지 (2026-07-29 확인)

green이라는 사실과 게이트가 **실패를 잡는다**는 사실은 다르다. 방어선을 하나씩 고의로
깨뜨려 확인했다 — 12건 중 11건 검출:

| 깨뜨린 것 | 잡은 게이트 |
|---|---|
| 규칙이 `note_skip` 없이 조용히 통과 | pytest (계약 2) |
| 규칙이 원본 트리를 변경 | pytest (계약 3) |
| **규칙 ⑥-a가 정규화 후 트리를 봄** | pytest (계약 4, 호출 감시) |
| findings 정렬 제거 / line을 문자열 정렬 | pytest |
| fcp 정규화가 속성 키를 놓침 | pytest |
| fcp가 매니페스트 항목을 "사용"으로 셈 | pytest |
| 파서 엔티티 방어 해제 | pytest (실제 XXE·폭탄 페이로드) |
| 입력 점검 무력화 | pytest + mypy |
| **`Missing child` 분기를 ERROR로** | pytest (A3 정책 테스트) |
| 미지원 릴리스를 조용히 통과 | pytest |
| XSD 패치/스텁 제거 · 함수 목록 훼손 · gates에 미매핑 항목 | pytest (골든셋 포함 4/4) |

미검출 1건은 `safe_extract_path`의 절대경로 조기 반환인데, `resolve()` + `relative_to()`가
같은 경우를 전부 막는 **중복 방어**라 동작 차이가 없다(코드에 명시해 뒀다).

굵게 표시한 둘은 **처음엔 아무도 못 잡았다.** 규칙 ⑥-a의 트리 선택은 구현이 들어와야
차이가 나고, A3 심각도 정책은 단위 테스트가 없었다. 둘 다 구현 단계에서 조용히 틀릴
자리였다 — 지금 막았다.

### 골든셋 경로 (실파일 회귀)

**골든셋은 저장소에 없다. 용량이 아니라 사내 재무 데이터라서다.** 경로를 환경변수로 준다:

```bash
# bash
export TWB_LINT_GOLDEN_NORMAL='C:/dev/JW/2.개발/MA_002_경영관리-재무-현금흐름/*.twbx;C:/dev/JW/2.개발/MA_004_경영관리-재무-손익계산서/*_JWLH_*.twbx;C:/dev/태블로판차분석_제약_260616_진행중_2.twbx'
```

```powershell
# PowerShell
$env:TWB_LINT_GOLDEN_NORMAL = 'C:\dev\JW\2.개발\MA_002_경영관리-재무-현금흐름\*.twbx;C:\dev\JW\2.개발\MA_004_경영관리-재무-손익계산서\*_JWLH_*.twbx;C:\dev\태블로판차분석_제약_260616_진행중_2.twbx'
```

설정하면 `pytest -q`가 170 passed가 된다. AC8(`.hyper` 라운드트립)은 io 1단계가
끝나 xfail에서 풀렸다 — 여기가 다시 xfail로 돌아가면 무손실 보존이 깨진 것이다.

### 규칙을 구현·추가했을 때 추가로 할 것

정적 게이트만으로는 부족하다. 규칙은 **실파일 회귀**까지 봐야 한다.

1. **정상본 회귀 먼저 (AC7)** — 위 환경변수를 걸고 `pytest tests/golden`.
   **ERROR 0건**이어야 한다. 여기서 깨지면 규칙이 틀린 것이다 —
   파일을 의심하기 전에 규칙을 의심한다
2. **고장본 검출 (AC2)** — 주입본을 만들고 검출되는지 확인
   ```bash
   .venv/Scripts/python tools/inject_defects.py --source <원본.twbx> --out <디렉토리>
   ```
   레시피 6종 + `labels.json`(라벨 대장)이 나온다. 라벨 확정은 로컬 Tableau Desktop 2026.1
   수동 로드
3. WARNING 건수를 기록한다 (경고 인플레이션 방지)

**표본 편향을 기억한다** — 9개 중 7개가 MA_002 변형이라 실제 다양성은 3종이다.
"9개 ERROR 0건"은 숫자가 주는 인상보다 약한 근거다.

전체 검증 절차는 [`03-design.md`](./03-design.md) D7.

### 데이터 재생성 (vendored XSD · 함수 목록)

```bash
.venv/Scripts/python tools/vendor_schemas.py            # XSD (패치 적용 + 컴파일 검증)
.venv/Scripts/python tools/vendor_schemas.py --check    # 상류와 어긋났는지만 확인
.venv/Scripts/python tools/scrape_functions.py --diff   # 함수 목록 변화만 보기
```

패치가 하나라도 적용되지 않으면 **vendoring이 실패한다.** 조용히 넘기면 "패치된 줄 알았던"
XSD로 검증하게 되고 정상본이 전부 ERROR가 난다. 상류 갱신 후에는 반드시 1번 회귀를 다시 돈다.

### 환경 — uv를 쓰지 마라 (이 머신)

**Smart App Control이 `uv.exe` 실행을 차단한다.** 설치는 되지만 실행이 안 된다
(서명 없는 바이너리, winget본·PyPI본 동일). SAC는 한 번 끄면 Windows 재설치 전까지
못 켜므로 **끄지 않는다.**

[`04-scaffolding.md`](./04-scaffolding.md)의 `uv run X`는 이 머신에서 이렇게 읽는다:

| 문서 | 이 머신 |
|---|---|
| `uv sync --extra dev` | `.venv/Scripts/python -m pip install -e ".[dev]"` |
| `uv run pytest -q` | `.venv/Scripts/python -m pytest -q` |
| `uv run twb-lint-mcp` | `.venv/Scripts/twb-lint-mcp` |

한계: pip이 `uv.lock` 핀을 못 읽어 `pyproject.toml` 범위로 설치된다.
**재현성이 필요한 검증은 uv가 되는 머신에서 한다.**

---

## 3. 관례

- **언어**: 문서·주석·커밋 메시지 한국어. 코드 식별자·기술 용어는 원문
- **커밋**: `feat:`/`fix:`/`docs:`/`chore:` 접두. 본문에 **왜**를 적는다
- **주석**: 무엇이 아니라 **왜**. 실측 근거가 있으면 문서를 가리킨다
  (`# docs/05-xsd-spike.md F4`)
- **타입**: mypy strict. `from __future__ import annotations` 상단에
- **새 규칙 추가** — 파일 1개 + `@register`. 코어 무수정:
  ```python
  # src/twb_lint/validation/semantic/my_rule.py
  @register
  class MyRule(RuleBase):
      id = "my.rule"
      stage = Stage.SEMANTIC
      def check(self, ctx: ValidationContext) -> list[Finding]:
          return []
  ```
  레지스트리가 자동 수집한다. `engine.py`·`registry.py`를 건드릴 필요 없다.
  `tests/unit/test_rules_contract.py`가 새 규칙도 자동으로 계약 검사에 태운다
- **findings 정렬**: `stage → rule_id → line → location` 고정 (결정론, 골든셋 diff 노이즈 방지).
  **`engine.validate_model`이 보장한다 — 규칙은 반환 순서를 신경 쓰지 않아도 된다**
- **검사 못 했으면 말한다**: `ctx.note_skip()`/`note_partial()`. 빈 리스트를 조용히
  반환하면 "전부 검사했고 문제없음"으로 기록된다 (02 S5)
- **테스트 입력**: 최소 XML은 `tests/fixtures`의 `make_twb()`/`make_ctx()`로 만든다.
  1MB 실파일로 규칙을 디버깅하지 않는다
- **stub 테스트**: `@pytest.mark.stub`는 stub 상태의 사실을 고정한 테스트다.
  구현하면 깨지는 게 정상이며, 그때 고칠 것은 **코드가 아니라 테스트**다
- **임시 파일**: 스크래치패드에. 저장소에 실험 산출물을 남기지 않는다

## 4. 구현 순서 (현재 지점 — v1.1 갱신)

착수 전 준비는 끝났다. **설계 미결 8건 해소 · vendored XSD · 함수 목록 218종 ·
테스트 3층 · 주입 스크립트**가 모두 자리에 있다.

1. ~~`io/twbx.unpack`·`io/twb.parse` → `inspect.load_context` 실채움~~ ✅
   - 모델과 `raw_tree`가 채워져야 나머지 규칙이 전부 돈다. 여기가 병목이다
   - 파서는 `safety.make_parser()`, ZIP은 `safe_extract_path`/`check_zip_entry`를 통과시킨다
   - **완료** (2026-07-29). AC8 테스트가 xfail → 통과로 뒤집혔고 마커를 제거했다
2. ~~`syntactic/xsd.py` — 스키마 로드(캐시) + `severity_for()` 적용~~ ✅
   - 정상본 10/10 ERROR 0 · WARNING 0, 주입본 R4·R7이 게이트를 막는다 (2026-07-29 실측)
3. ~~`calc/extractor.py` + 규칙 ①②~~ ✅ (정상본 ERROR 0 · WARNING 24)
4. ~~규칙 ③(R2·R3 3자 대조) / 규칙 ⑥~~ ✅ (주입 6종 중 5종 차단)
5. 사용자 라벨링 배치 → AC2·AC3 수치 고정 ← **다음. 루프가 할 수 없다(Tableau Desktop 필요)**

각 단계 후 `pytest`(골든셋 포함)·`ruff`·`mypy` 3종을 돌린다.
