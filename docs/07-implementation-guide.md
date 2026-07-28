# Tableau 저작 AI — 구현 가이드 (Implementation Guide)

> SOR 문서. 인덱스 [`tableau-ai-sor.md`](./tableau-ai-sor.md).
> 진입점은 루트 [`CLAUDE.md`](../CLAUDE.md).

## 문서 관리

| 항목 | 값 |
|---|---|
| 상태 | 🔄 living doc (구현 진행하며 갱신) |
| 버전 | v1.0 (2026-07-28) |
| 소유자 | ax3didim@gmail.com |
| 전제 | [설계](./03-design.md) 확정 · [스파이크](./05-xsd-spike.md) 완료 |

---

## 1. 구현 전 반드시 아는 것 (G1~G7)

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

### G7. 지금은 stub이라 항상 PASS다

```
twb-lint validate nonexistent.twb   →  PASS (exit 0)
```

규칙이 전부 `return []`이고 파일을 읽지 않아서다. **버그가 아니다.** 구현하면 사라진다.

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

기대 출력:

```
4 passed
All checks passed!
Success: no issues found in 25 source files
```

### 규칙을 구현·추가했을 때 추가로 할 것

정적 게이트만으로는 부족하다. 규칙은 **실파일 회귀**까지 봐야 한다.

1. **정상본 회귀 먼저 (AC7)** — 실사용 워크북 9개에 **ERROR 0건**인지 확인.
   여기서 깨지면 규칙이 틀린 것이다. 파일을 의심하기 전에 규칙을 의심한다
   ```
   C:\dev\JW\2.개발\MA_002_경영관리-재무-현금흐름\*.twbx          (7개)
   C:\dev\JW\2.개발\MA_004_경영관리-재무-손익계산서\*_JWLH_*.twbx  (1개)
   C:\dev\태블로판차분석_제약_260616_진행중_2.twbx                 (1개)
   ```
2. **고장본 검출 (AC2)** — [`06-rule-candidates.md`](./06-rule-candidates.md) §D의 주입
   레시피로 고장본을 만들고 검출되는지 확인. 라벨은 로컬 Tableau Desktop 2026.1 수동 로드로 확정
3. WARNING 건수를 기록한다 (경고 인플레이션 방지)

전체 검증 절차는 [`03-design.md`](./03-design.md) D7.

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
      def check(self, model: WorkbookModel) -> list[Finding]:
          return []
  ```
  레지스트리가 자동 수집한다. `engine.py`·`registry.py`를 건드릴 필요 없다
- **findings 정렬**: `stage → rule_id → location` 고정 (결정론, 골든셋 diff 노이즈 방지).
  **`engine.validate_model`이 보장한다 — 규칙은 반환 순서를 신경 쓰지 않아도 된다**
- **stub 테스트**: `@pytest.mark.stub`는 stub 상태의 사실을 고정한 테스트다.
  구현하면 깨지는 게 정상이며, 그때 고칠 것은 **코드가 아니라 테스트**다
- **임시 파일**: 스크래치패드에. 저장소에 실험 산출물을 남기지 않는다

## 4. 구현 순서 (현재 지점)

1. `io/twbx.unpack` + `io/twb` 파싱 → `inspect` 실채움 ← **다음**
   (모델이 채워져야 나머지 규칙이 전부 돈다)
2. `tools/vendor_schemas.py` — XSD vendoring + 스텁 2개 + `explain-data` 패치
3. `syntactic/xsd.py` — fcp 정규화 + 검증. **첫 목표는 정상 9개 ERROR 0건**
4. `calc/extractor.py` + 규칙 ①② / 규칙 ③ / 규칙 ⑥
5. 골든셋 주입 스크립트 → AC2·AC3 측정
