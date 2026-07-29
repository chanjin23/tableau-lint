"""핵심 데이터 모델 — 모든 검증 단계가 공유하는 통합 타입.

`Finding` 하나로 L-A(구문)·L-B(시맨틱)·향후 E2E 결과를 균일하게 표현한다.
`WorkbookModel`은 규칙 ①②③⑥이 공유하는 구조 모델이다 (docs/03-design.md D3.5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class Severity(StrEnum):
    """결과 심각도. ERROR 하나라도 있으면 게이트 실패.

    배정 원칙 (docs/02-specification.md S1-6):
    **파일이 열리지 않는다고 확신할 때만 ERROR. 우리 지식의 공백은 WARNING.**
    게이트가 mandatory이므로 거짓 ERROR 1건이 멀쩡한 파일을 막는다.
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class Finding:
    """단일 검증 결과.

    Attributes:
        severity: 심각도.
        rule_id: 규칙 식별자 (예: "calc.functions").
        location: 위치 (xpath, 필드명 등 사람이 짚을 수 있는 표시).
        message: 무엇이 잘못됐는지.
        fix: 제안 수정 (없으면 None).
        line: `.twb` 안 1-기반 줄번호. 모르면 None.
    """

    severity: Severity
    rule_id: str
    location: str
    message: str
    fix: str | None = None

    line: int | None = None
    """줄번호를 **문자열이 아니라 정수로** 갖는다. lxml `error_log`가 `error.line`을 주므로
    L-A는 항상 채울 수 있다. 문자열이면 정렬에서 `line 10 < line 9`가 되어 결정론적이지만
    사람이 읽기엔 틀린 순서가 나온다 (docs/03-design.md D3 정렬 규칙)."""

    @property
    def sort_key(self) -> tuple[str, int, str]:
        """엔진이 findings를 정렬할 때 쓰는 키 (단계 안에서).

        `rule_id → line → location` 순. 줄번호를 모르는 finding(`None`)은 `-1`로 앞에 모인다 —
        L-B 규칙 대부분은 모델 대조라 줄번호가 없고, 줄번호가 있는 L-A 결과와 섞이면
        읽는 순서가 흔들리기 때문이다.
        """
        return (self.rule_id, self.line if self.line is not None else -1, self.location)


class CoverageStatus(StrEnum):
    """규칙이 실제로 무엇을 했는지. "조용히 통과" 금지의 실체 (02 S5).

    findings가 비었다는 사실만으로는 "검사했고 문제없음"과 "검사하지 못했음"을
    구분할 수 없다. 소비자가 AI이므로 이 차이를 명시적으로 넘긴다.
    """

    RAN = "ran"
    """대상 전체를 검사했다."""

    PARTIAL = "partial"
    """일부만 검사했다 (예: calc 3개 중 1개가 파싱 실패해 그 calc만 스킵)."""

    SKIPPED = "skipped"
    """아예 검사하지 못했다 (예: 미지원 릴리스라 L-A 미실행)."""


@dataclass(frozen=True, slots=True)
class CoverageNote:
    """규칙 하나의 검사 범위 보고.

    엔진이 실행한 모든 규칙에 대해 최소 1건을 보장한다 — 규칙이 아무 말도 하지 않으면
    `RAN`으로 기록된다. 규칙이 스스로 `ctx.note_skip()`을 부르면 그것이 우선한다.
    """

    rule_id: str
    status: CoverageStatus
    scope: str = "*"
    """무엇에 대한 보고인지. 파일 전체면 `"*"`, 부분이면 해당 대상(calc 이름 등)."""

    reason: str | None = None
    """왜 스킵/부분인지. `SKIPPED`·`PARTIAL`이면 필수적으로 채운다."""


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """한 파일에 대한 전체 검증 결과 = mandatory gate 판정."""

    findings: tuple[Finding, ...] = ()

    coverage: tuple[CoverageNote, ...] = ()
    """무엇을 검사했고 무엇을 못 했는지 (02 S5 "조용히 통과 금지").

    `findings`가 비어 있고 `passed`가 True여도 여기 `SKIPPED`가 있으면
    **검사되지 않은 영역이 있다**는 뜻이다. 호출자는 이 값을 보고 판단해야 한다."""

    @property
    def passed(self) -> bool:
        """ERROR 심각도 finding이 하나도 없으면 통과.

        주의: 통과 = "검사한 범위에서 문제없음"이지 "전부 검사했음"이 아니다.
        검사 범위는 `coverage`/`skipped`가 말한다.
        """
        return not any(f.severity is Severity.ERROR for f in self.findings)

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.ERROR)

    @property
    def skipped(self) -> tuple[CoverageNote, ...]:
        """검사하지 못했거나 일부만 검사한 항목."""
        return tuple(
            c for c in self.coverage if c.status is not CoverageStatus.RAN
        )

    @property
    def fully_covered(self) -> bool:
        """모든 규칙이 대상 전체를 검사했는가. False면 `passed`를 액면대로 믿으면 안 된다."""
        return not self.skipped


@dataclass(frozen=True, slots=True)
class FieldDef:
    """데이터소스의 필드 하나 (일반 컬럼 또는 계산필드).

    `name`과 `caption`을 반드시 구분한다 — **calc 수식이 참조하는 것은 내부 `name`**이며,
    계산필드는 `[Calculation_1234567890]` 형태일 수 있다. caption만 모으면 규칙 ②가
    정상 참조를 전량 dangling으로 오판한다 (docs/03-design.md D3.5).
    """

    name: str
    """내부 이름. calc 수식·참조가 가리키는 값."""

    caption: str | None = None
    """UI 표시명. 참조 해소에 쓰지 않는다 (사람이 읽는 메시지용)."""

    datatype: str | None = None
    """`datatype` 속성 (string/real/integer/date ...)."""

    formula: str | None = None
    """계산필드면 수식, 일반 컬럼이면 None."""

    origin: str = "column"
    """이 이름이 어디서 왔는가. 규칙 ②의 참조 해소 범위를 결정한다 (03 D3.6.2).

    | 값 | 출처 | 왜 필요한가 |
    |---|---|---|
    | `column` | `<datasource>/<column>` | 커스터마이즈된 필드만 여기 적힌다 |
    | `metadata` | `<metadata-record class='column'>/<local-name>` | **손대지 않은 DB 컬럼** |
    | `group` | `<datasource>/<group>` | 그룹/집합 |
    | `instance` | `<datasource>/<column-instance>` | 집계 인스턴스 (`[min:x:qk]`) |

    `column` 하나만 모으면 실사용 참조의 약 4%가 dangling으로 잡힌다 (실측 687/16,754)."""

    @property
    def is_calc(self) -> bool:
        return self.formula is not None


@dataclass(slots=True)
class DataSource:
    """데이터소스 하나 = 필드 참조의 네임스페이스.

    필드 참조는 `[datasource].[Field]`로 소속이 있다. 데이터소스 2개에 동명 필드가
    있으면 플랫 집합으로는 구분할 수 없어 오통과(FN) 또는 거짓 dangling(FP)이 난다.
    """

    name: str
    """`[ds]` 참조에 쓰이는 내부 이름."""

    caption: str | None = None

    fields: dict[str, FieldDef] = field(default_factory=dict)
    """내부 name → FieldDef."""


@dataclass(slots=True)
class Dashboard:
    """대시보드 하나 + 로드 가능성에 필요한 참조들.

    규칙 ③(R2·R3)이 소비한다. `viewpoints`는 엄밀히는 대시보드가 아니라 대응
    `<window class='dashboard'>`의 소유지만, 대조가 항상 대시보드 단위라 함께 담는다.
    """

    name: str

    sheet_zones: tuple[str, ...] = ()
    """존이 참조하는 worksheet 이름들 (`<zone name=...>`)."""

    viewpoints: frozenset[str] = frozenset()
    """대시보드 window `<viewpoints>`의 viewpoint 이름 집합.
    배치된 시트에 대응 viewpoint가 없으면 로드 시 내부 오류 2805CF18."""


@dataclass(slots=True)
class WorkbookModel:
    """검증 규칙에 넘기는 워크북 구조 모델 (C2 인스펙터 산출물).

    스캐폴딩 단계에서는 인스펙터가 최소 필드만 채운다. 구현 단계에서
    datasources/dashboards/매니페스트를 실제로 추출한다.
    """

    source: Path
    """원본 .twb 또는 .twbx 경로."""

    twb_path: Path | None = None
    """unpack된 .twb 경로 (.twbx면 임시추출, .twb면 source와 동일)."""

    source_build: str | None = None
    """`<workbook source-build>` 값 (예: "2026.1.1 (20261.26.0410.0924)").
    **XSD·함수목록 선택 키** — `config.release_from_source_build()`로 릴리스를 얻는다."""

    twb_version: str | None = None
    """`<workbook version>` 값 (예: "18.1"). 최소 호환 버전이며 **XSD 선택에 쓰지 않는다**.
    로더 문법 판정(규칙 ⑥)의 입력이다. 근거: docs/05-xsd-spike.md F4."""

    original_version: str | None = None
    """`<workbook original-version>` 값."""

    manifest_features: frozenset[str] = frozenset()
    """`<document-format-change-manifest>`의 항목 이름 집합. **원문 그대로** — 접두사를
    벗기면 `_.fcp.X.true...X`와 `_.fcp.X.false...X`가 구분되지 않는다 (05 F7).

    유효 문법 = `version` × 이 집합. 기능을 쓰면서 대응 항목을 선언하지 않으면
    `no declaration found for element`로 로드 거부된다 (규칙 ⑥, 05-xsd-spike.md F5)."""

    datasources: dict[str, DataSource] = field(default_factory=dict)
    """내부 name → DataSource (규칙 ② 참조 해소용)."""

    worksheets: set[str] = field(default_factory=set)
    """`<worksheets>`에 정의된 워크시트 이름."""

    dashboards: dict[str, Dashboard] = field(default_factory=dict)
    """이름 → Dashboard (규칙 ③)."""

    worksheet_windows: set[str] = field(default_factory=set)
    """`<window class='worksheet'>`가 존재하는 시트 이름 (규칙 ③)."""

    def field_names(self, datasource: str) -> set[str]:
        """특정 데이터소스의 필드 내부 이름 집합. 없는 데이터소스면 빈 집합."""
        ds = self.datasources.get(datasource)
        return set(ds.fields) if ds else set()

    def qualified_field_names(self) -> set[str]:
        """`[ds].[field]` 형태의 정규화된 전체 참조 집합."""
        return {
            f"[{ds.name}].[{fname}]"
            for ds in self.datasources.values()
            for fname in ds.fields
        }
