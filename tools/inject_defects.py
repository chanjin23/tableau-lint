"""정상 워크북에 결함을 **하나씩** 주입해 고장본 골든셋을 만든다.

고장 파일이 남아 있지 않으므로(과거 산출물 미보존) 정상본에서 만들어 낸다.
레시피는 `docs/06-rule-candidates.md` §D의 실측 목록이며, 각 항목은
**"실제 Tableau에서 안 열림"이 과거에 관측된** 조건이다.

원칙 (docs/TODO D):
- **결함 1개씩** — 한 파일에 두 개를 넣으면 어느 쪽이 거부를 유발했는지 알 수 없다
- **복사본에만** — 원본 9개는 불가침이다. 이 스크립트는 입력을 절대 쓰지 않는다
- **결정론** — 같은 입력에 같은 산출. 골든셋을 언제든 재생성할 수 있다
- `.hyper`는 손대지 않는다 — `.twb` 엔트리만 교체하고 나머지는 바이트 그대로 복사한다

산출물과 함께 **라벨 대장**(`labels.json`)을 낸다. 사용자가 Tableau Desktop에서 한 배치로
열어 보고 결과를 채우면 그대로 AC2·AC3 측정 입력이 된다.

사용:
```bash
# 레시피 전부, 파일 1개에 대해
.venv/Scripts/python tools/inject_defects.py --source <원본.twbx> --out <디렉토리>

# 실험 B — 매니페스트 항목 16종을 하나씩 지운 파일들
.venv/Scripts/python tools/inject_defects.py --source <원본.twbx> --out <디렉토리> --experiment-b

# 목록만 보기
.venv/Scripts/python tools/inject_defects.py --list
```
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from twb_lint import fcp, fieldref  # noqa: E402
from twb_lint.io import safety  # noqa: E402

Mutator = Callable[[Any], str | None]
"""트리를 제자리에서 변형하고, 무엇을 했는지 한 줄로 반환한다.
변형할 대상이 없으면 None을 반환한다 (그 표본에 해당 기능이 없다는 뜻)."""


@dataclass(frozen=True, slots=True)
class Recipe:
    """결함 주입 레시피 1건."""

    id: str
    rule: str
    """이 결함을 잡아야 하는 twb-lint 규칙 id (검출 측정용)."""

    expected: str
    """과거 실측에서 관측된 Tableau의 반응."""

    source: str
    mutate: Mutator


# --- 레시피 구현 ---------------------------------------------------------------------


def _manifest(root: Any) -> Any:
    for el in root.iter():
        if isinstance(el.tag, str) and fcp.strip_prefix(el.tag) == fcp.MANIFEST_TAG:
            return el
    return None


def _drop_manifest_item(root: Any, predicate: Callable[[str], bool]) -> str | None:
    manifest = _manifest(root)
    if manifest is None:
        return None
    for child in list(manifest):
        if isinstance(child.tag, str) and predicate(child.tag):
            manifest.remove(child)
            return f"매니페스트 항목 '{child.tag}' 삭제"
    return None


def _r1a_drop_fcp_item(root: Any) -> str | None:
    """R1-a — fcp 매니페스트 항목만 삭제 (사용 요소는 유지). 실험 A와 같다."""
    used = sorted(fcp.features_in_tree(root))
    if not used:
        return None
    target = fcp.expected_manifest_item(used[0])
    return _drop_manifest_item(root, lambda tag: tag == target)


def _r1b_drop_sort_tag_cleanup(root: Any) -> str | None:
    """R1-b — `SortTagCleanup` 삭제. `<manual-sort>`는 그대로 둔다."""
    uses_manual_sort = any(
        isinstance(el.tag, str) and fcp.strip_prefix(el.tag) == "manual-sort" for el in root.iter()
    )
    if not uses_manual_sort:
        return None
    return _drop_manifest_item(root, lambda tag: fcp.strip_prefix(tag) == "SortTagCleanup")


def _r2_drop_viewpoint(root: Any) -> str | None:
    """R2 — 대시보드 window의 viewpoint 1개 삭제 → 내부 오류 2805CF18."""
    for window in root.iter():
        if not isinstance(window.tag, str) or fcp.strip_prefix(window.tag) != "window":
            continue
        if window.get("class") != "dashboard":
            continue
        for vps in window:
            if not isinstance(vps.tag, str) or fcp.strip_prefix(vps.tag) != "viewpoints":
                continue
            children = list(vps)
            if not children:
                continue
            victim = children[0]
            vps.remove(victim)
            return (
                f"대시보드 '{window.get('name')}'의 viewpoint "
                f"'{victim.get('name')}' 삭제"
            )
    return None


def _r3_dangle_zone(root: Any) -> str | None:
    """R3 — 존의 `name`을 없는 시트로 바꾼다 → dangling 참조."""
    for zone in root.iter():
        if not isinstance(zone.tag, str) or fcp.strip_prefix(zone.tag) != "zone":
            continue
        name = zone.get("name")
        if not name:
            continue
        zone.set("name", f"{name}__twb_lint_dangling__")
        return f"zone name '{name}' → 존재하지 않는 시트로 변조"
    return None


def _r4_move_style_before_column(root: Any) -> str | None:
    """R4 — datasource 자식 순서 위반 → D2E8DA72."""
    for ds in root.iter():
        if not isinstance(ds.tag, str) or fcp.strip_prefix(ds.tag) != "datasource":
            continue
        def child(children: list[Any], tag: str) -> Any:
            return next(
                (c for c in children if isinstance(c.tag, str) and fcp.strip_prefix(c.tag) == tag),
                None,
            )

        children = list(ds)
        style = child(children, "style")
        column = child(children, "column")
        if style is None or column is None:
            continue
        ds.remove(style)
        ds.insert(list(ds).index(column), style)
        return f"datasource '{ds.get('name')}'에서 <style>을 첫 <column> 앞으로 이동"
    return None


def _r7_bad_enum(root: Any) -> str | None:
    """R7 — `param-domain-type='all'` (정답은 'any') → enum 위반, D2E8DA72."""
    for el in root.iter():
        if "param-domain-type" in el.attrib:
            old = el.attrib["param-domain-type"]
            el.attrib["param-domain-type"] = "all"
            return f"param-domain-type '{old}' → 'all' (열거형 밖)"
    return None


# --- 2026-07-30 실측분 (MA_003 매출표가 연달아 낸 3층) ------------------------------
# 한 파일을 고칠 때마다 다음 층이 드러났다. 레시피는 그 역순 — 정상본에서 한 층씩
# 되돌린다. 근거는 docs/05-xsd-spike.md F5-b·F5-c·F5-d·F5-e.


def _r15_drop_parameter_action_item(root: Any) -> str | None:
    """R15 — `ParameterAction` 삭제. `<edit-parameter-action>`은 그대로 둔다."""
    uses = any(
        isinstance(el.tag, str) and fcp.strip_prefix(el.tag) == "edit-parameter-action"
        for el in root.iter()
    )
    if not uses:
        return None
    return _drop_manifest_item(root, lambda tag: fcp.strip_prefix(tag) == "ParameterAction")


def _r16_bare_member_literal(root: Any) -> str | None:
    """R16 — `groupfilter@member`의 따옴표 제거 → 필터가 통째로 무시된다."""
    for el in root.iter():
        if not isinstance(el.tag, str) or fcp.strip_prefix(el.tag) != "groupfilter":
            continue
        member = el.get("member")
        if not member or not (member.startswith('"') and member.endswith('"')):
            continue
        inner = member[1:-1]
        if "].[" not in inner:
            continue
        el.set("member", inner)
        return f"groupfilter member {member} → 따옴표 제거"
    return None


def _r17_unqualify_placeholder(root: Any) -> str | None:
    """R17 — `[ds].[Multiple Values]`에서 한정자 제거 → 그 필드가 워크시트에서 빠진다."""
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        column = el.get("column")
        if column and column.endswith(".[Multiple Values]"):
            el.set("column", "[Multiple Values]")
            return f"{fcp.strip_prefix(el.tag)}@column {column} → 한정자 제거"
        if el.text and el.text.strip().endswith(".[Multiple Values]"):
            old = el.text.strip()
            el.text = "[Multiple Values]"
            return f"<{fcp.strip_prefix(el.tag)}> {old} → 한정자 제거"
    return None


def _r18_bare_parameter_ref(root: Any) -> str | None:
    """R18 — 수식의 `[Parameters].[X]` → `[X]` → 계산필드가 오류 상태가 된다."""
    for el in root.iter():
        if not isinstance(el.tag, str) or fcp.strip_prefix(el.tag) != "calculation":
            continue
        formula = el.get("formula")
        if not formula or "[Parameters].[" not in formula:
            continue
        el.set("formula", formula.replace("[Parameters].[", "["))
        return "수식의 [Parameters]. 한정자 제거"
    return None


def _r19_unwrap_user_aggregation(root: Any) -> str | None:
    """R19 — `usr:` 인스턴스로 올린 계산에서 바깥 집계를 벗긴다 → 시트가 비어 나온다."""
    targets = {
        (ci.get("column") or "").strip("[]")
        for ci in root.iter()
        if isinstance(ci.tag, str)
        and fcp.strip_prefix(ci.tag) == "column-instance"
        and ci.get("derivation") == "User"
    }
    for col in root.iter():
        if not isinstance(col.tag, str) or fcp.strip_prefix(col.tag) != "column":
            continue
        if (col.get("name") or "").strip("[]") not in targets:
            continue
        calc = next(
            (c for c in col if isinstance(c.tag, str) and fcp.strip_prefix(c.tag) == "calculation"),
            None,
        )
        formula = calc.get("formula") if calc is not None else None
        if not formula:
            continue
        for agg in ("MIN(", "MAX(", "SUM(", "AVG("):
            if formula.startswith(agg) and formula.endswith(")"):
                calc.set("formula", formula[len(agg):-1])
                return f"{col.get('name')}의 바깥 {agg[:-1]}() 제거"
    return None


def _r20_empty_set(root: Any) -> str | None:
    """R20 — 집합의 기반 필드를 지운다 → `… IN [집합]`을 쓰는 계산이 전부 깨진다."""
    for group in root.iter():
        if not isinstance(group.tag, str) or fcp.strip_prefix(group.tag) != "group":
            continue
        children = list(group)
        if not children:
            continue
        for child in children:
            group.remove(child)
        placeholder = etree.SubElement(group, "groupfilter")
        placeholder.set("function", "union")
        return f"집합 '{group.get('name')}'의 기반 필드 제거 (빈 union만 남김)"
    return None


def _r21_qualify_filter_level(root: Any) -> str | None:
    """R21 — `groupfilter@level`에 한정자를 붙인다 → 필터가 통째로 버려진다.

    한정자는 감싸는 `<filter>`의 `column`에서 가져온다 — 지어내면 그 필터가
    원래 어느 데이터소스였는지와 무관한 값이 되어 다른 결함이 섞인다.
    """
    for filt in root.iter():
        if not isinstance(filt.tag, str) or fcp.strip_prefix(filt.tag) != "filter":
            continue
        column = filt.get("column") or ""
        if "]." not in column or not column.startswith("["):
            continue
        prefix = column.split("].", 1)[0] + "]."
        for gf in filt.iter():
            if not isinstance(gf.tag, str) or fcp.strip_prefix(gf.tag) != "groupfilter":
                continue
            level = gf.get("level")
            if not level or not level.startswith("[") or level.startswith(prefix):
                continue
            gf.set("level", prefix + level)
            return f"groupfilter@level {level} → {prefix}{level}"
    return None


def _action_commands(root: Any) -> Any:
    """`<actions>` 밑 `<action>`의 `<command>`들. 정의 사본(`<datasources>`)은 뺀다."""
    for container in root.iter():
        if not isinstance(container.tag, str) or fcp.strip_prefix(container.tag) != "actions":
            continue
        for action in container:
            if not isinstance(action.tag, str) or fcp.strip_prefix(action.tag) != "action":
                continue
            for command in action.iter():
                if isinstance(command.tag, str) and fcp.strip_prefix(command.tag) == "command":
                    yield action, command


def _r22_unknown_action_command(root: Any) -> str | None:
    """R22 — 동작 명령을 실재하지 않는 이름으로 바꾼다 → 동작이 편집도 발동도 안 된다."""
    for _action, command in _action_commands(root):
        before = command.get("command")
        if not before or before == "tsc:filter":
            continue
        command.set("command", "tsc:filter")
        return f"동작 명령 {before} → tsc:filter"
    return None


def _r23_drop_filter_link(root: Any) -> str | None:
    """R23 — 필터 동작의 `<link>`를 지운다 → 필드 매핑이 사라져 아무것도 안 걸린다."""
    for action, command in _action_commands(root):
        if command.get("command") != "tsc:tsl-filter":
            continue
        for child in list(action):
            if isinstance(child.tag, str) and fcp.strip_prefix(child.tag) == "link":
                action.remove(child)
                return f"동작 '{action.get('caption') or action.get('name')}'의 <link> 제거"
    return None


def _r26_unqualify_sort(root: Any) -> str | None:
    """R26 — 정렬 참조에서 데이터소스 한정자를 뗀다 → 정렬 지정이 무시된다."""
    surfaces = (("computed-sort", "column"), ("computed-sort", "using"), ("manual-sort", "column"))
    for tag, attr in surfaces:
        for el in root.iter():
            if not isinstance(el.tag, str) or fcp.strip_prefix(el.tag) != tag:
                continue
            value = el.get(attr) or ""
            if not value.startswith("[") or "]." not in value:
                continue
            bare = value.split("].", 1)[1]
            el.set(attr, bare)
            return f"{tag}@{attr} {value} → {bare}"
    return None


def _r27_double_aggregate(root: Any) -> str | None:
    """R27 — 워크시트가 쓰는 `usr:` 인스턴스의 파생을 `Sum`으로 바꾼다 → `SUM(SUM(…))`.

    수식은 건드리지 않는다 — 이 결함은 **수식과 파생의 불일치**이지 수식의 문제가 아니다.
    """
    for worksheet in root.iter():
        if not isinstance(worksheet.tag, str) or fcp.strip_prefix(worksheet.tag) != "worksheet":
            continue
        for ci in worksheet.iter():
            if not isinstance(ci.tag, str) or fcp.strip_prefix(ci.tag) != "column-instance":
                continue
            if ci.get("derivation") != "User":
                continue
            column = (ci.get("column") or "").strip("[]")
            before = ci.get("name") or ""
            ci.set("derivation", "Sum")
            ci.set("name", f"[sum:{column}:qk]")
            return f"{before}의 derivation User → Sum"
    return None

def _r28_strip_corner_radius_prefix(root: Any) -> str | None:
    """R28 — 모서리 반경 서식에서 fcp 접두사만 벗긴다 → `not in enumeration`.

    매니페스트는 건드리지 않는다. 이 결함은 **표기**의 문제이지 선언의 문제가 아니다
    (선언 쪽은 R1a가 따로 본다).
    """
    for el in root.iter():
        if not isinstance(el.tag, str) or fcp.strip_prefix(el.tag) != "format":
            continue
        if fcp.feature_of(el.tag) != "DashboardRoundedCorners":
            continue
        before = el.tag
        el.tag = "format"
        return f"{before}[@attr='{el.get('attr')}'] 접두사 제거"
    return None


def _r29_quote_boolean_member(root: Any) -> str | None:
    """R29 — 불리언 필터 member를 따옴표로 감싼다 → 그 필터가 무시된다.

    R16과 **반대 방향의 같은 속성이다**: R16은 필드 참조에서 따옴표를 벗기고,
    여기는 불리언 리터럴에 따옴표를 씌운다. 어느 쪽이 맞는지는 `level`이 가리키는
    컬럼의 `datatype`이 정한다 (05 F5-k).
    """
    datatypes: dict[str, str] = {}
    for el in root.iter():
        if not isinstance(el.tag, str) or fcp.strip_prefix(el.tag) != "column":
            continue
        name, datatype = el.get("name"), el.get("datatype")
        if name and datatype:
            datatypes[name.strip("[]")] = datatype

    for el in root.iter():
        if not isinstance(el.tag, str) or fcp.strip_prefix(el.tag) != "groupfilter":
            continue
        level, member = el.get("level"), el.get("member")
        if not level or not member or member.startswith('"'):
            continue
        ref = fieldref.parse(level)
        if ref is None or not any(datatypes.get(n) == "boolean" for n in ref.names):
            continue
        el.set("member", f'"{member}"')
        return f"groupfilter[@level='{level}'] member {member} → 따옴표로 감쌈"
    return None


def _r30_break_calc_syntax(root: Any) -> str | None:
    """R30 — 수식 끝의 `)` 하나를 지운다 -> 계산필드가 오류 상태가 된다.

    정상본은 문법 오류 표본을 **원리적으로** 줄 수 없다 (Tableau 편집기를 통과한
    수식만 저장된다). 이 레시피가 규칙 ⑯의 유일한 검출 근거다 (05 F5-l).

    괄호가 둘 이상 있는 수식만 고른다 — 하나뿐이면 지웠을 때 `SUM([a]` 처럼
    함수 호출 자체가 사라져 다른 규칙이 먼저 울 수 있다.
    """
    for el in root.iter():
        if not isinstance(el.tag, str) or fcp.strip_prefix(el.tag) != "calculation":
            continue
        formula = el.get("formula")
        if not formula or formula.count("(") < 2 or not formula.rstrip().endswith(")"):
            continue
        stripped = formula.rstrip()
        el.set("formula", stripped[:-1])
        return f"calc 수식 끝의 ')' 제거: {stripped[-40:]!r}"
    return None


def _is_plain_field_name(name: str) -> bool:
    """`[매출액]` 같은 **한정되지 않은 보통 이름**인가.

    제외 대상이 둘 있고 둘 다 실측으로 걸렸다: `[:Measure Names]`(내장 축)와
    `[__tableau_internal_object_id__].[…]`(내부 객체 네임스페이스). 어느 쪽도 필드
    유니버스에 없어서 주입하면 혼합이 아니라 **dangling**이 만들어진다.
    """
    return (
        name.startswith("[")
        and name.endswith("]")
        and "].[" not in name
        and not name.startswith("[:")
        and ":" not in name
    )


def _r31_mix_aggregation_levels(root: Any) -> str | None:
    """R31 — 집계 수식에 행수준 참조를 하나 더한다 -> 집계/비집계 혼합.

    정상본은 이 결함의 표본을 줄 수 없다 (Tableau 편집기가 막는다) — R30과 같은
    이유로 이 레시피가 규칙 ⑧-c의 유일한 검출 근거다 (05 F5-m).

    행수준 참조는 **그 데이터소스의 원본 컬럼**에서 고른다. 계산필드를 쓰면 그것이
    집계일 수 있어 혼합이 안 만들어진다.
    """
    for ds in root.iter():
        if not isinstance(ds.tag, str) or fcp.strip_prefix(ds.tag) != "datasource":
            continue
        if ds.get("name") == "Parameters":
            continue
        plain = [
            col.get("name")
            for col in ds.iter()
            if isinstance(col.tag, str)
            and fcp.strip_prefix(col.tag) == "column"
            and col.get("name")
            and _is_plain_field_name(col.get("name", ""))
            and col.get("datatype")                        # 실제 데이터 컬럼만
            and col.find("calculation") is None
        ]
        if not plain:
            continue
        victim = plain[0]
        for col in ds.iter():
            if not isinstance(col.tag, str) or fcp.strip_prefix(col.tag) != "column":
                continue
            calc = col.find("calculation")
            if calc is None:
                continue
            formula = calc.get("formula")
            if not formula or "SUM(" not in formula.upper():
                continue
            calc.set("formula", f"({formula}) + {victim}")
            return f"계산 '{col.get('name')}' 수식에 행수준 참조 {victim} 추가"
    return None


def _r32_drop_paramctrl_mode(root: Any) -> str | None:
    """R32 — paramctrl 존에서 `mode`를 지운다.

    ⚠️ **증상이 확인되지 않은 레시피다.** CB5AF9D4를 쫓다 나왔으나 `mode`를 채운
    고침본이 여전히 안 열렸다 (05 F5-n). 모양 불변식(2,475:0)만 선 상태이므로
    이 레시피는 "규칙이 그 모양을 잡는가"만 검증한다.
    """
    for zone in root.iter():
        if not isinstance(zone.tag, str) or fcp.strip_prefix(zone.tag) != "zone":
            continue
        if zone.get("type-v2") != "paramctrl" or zone.get("mode") is None:
            continue
        before = zone.get("mode")
        del zone.attrib["mode"]
        return f"paramctrl 존(param={zone.get('param')})의 mode='{before}' 제거"
    return None


def _r33_drop_datagraph_core(root: Any) -> str | None:
    """R33 — `DatagraphCoreV1` 삭제. `<datagraph>`는 그대로 둔다.

    `<datagraph>`는 **동적 존 표시(Dynamic Zone Visibility)**의 저장 형식이다.
    기능을 쓰면서 항목을 선언하지 않으면 로드 거부된다 (05 F5-o).
    """
    uses = any(
        isinstance(el.tag, str) and fcp.strip_prefix(el.tag) == "datagraph" for el in root.iter()
    )
    if not uses:
        return None
    return _drop_manifest_item(root, lambda tag: fcp.strip_prefix(tag) == "DatagraphCoreV1")


RECIPES: tuple[Recipe, ...] = (
    Recipe(
        id="R1a-drop-fcp-manifest-item",
        rule="manifest.gates",
        expected="로드 거부 (미검증 — 실험 A가 확정한다)",
        source="docs/05-xsd-spike.md F7 / docs/06-rule-candidates.md R1-a",
        mutate=_r1a_drop_fcp_item,
    ),
    Recipe(
        id="R1b-drop-SortTagCleanup",
        rule="manifest.gates",
        expected="로드 거부: no declaration found for element 'manual-sort'",
        source="docs/05-xsd-spike.md F5 (함정 W2)",
        mutate=_r1b_drop_sort_tag_cleanup,
    ),
    Recipe(
        id="R2-drop-viewpoint",
        rule="named.refs",
        expected="내부 오류 2805CF18",
        source="docs/06-rule-candidates.md R2 (함정 S1)",
        mutate=_r2_drop_viewpoint,
    ),
    Recipe(
        id="R3-dangling-zone",
        rule="named.refs",
        expected="로드 거부 또는 존 렌더 실패",
        source="docs/06-rule-candidates.md R3",
        mutate=_r3_dangle_zone,
    ),
    Recipe(
        id="R4-datasource-child-order",
        rule="xsd.schema",
        expected="로드 거부 D2E8DA72 (element not allowed for content model)",
        source="docs/06-rule-candidates.md R4 (함정 W1)",
        mutate=_r4_move_style_before_column,
    ),
    Recipe(
        id="R7-param-domain-type-all",
        rule="xsd.schema",
        expected="로드 거부 D2E8DA72 (value 'all' not in enumeration)",
        source="docs/06-rule-candidates.md R7 (함정 B10)",
        mutate=_r7_bad_enum,
    ),
    Recipe(
        id="R15-drop-ParameterAction",
        rule="manifest.gates",
        expected="로드 거부 D2E8DA72: no declaration found for element 'edit-parameter-action'",
        source="docs/05-xsd-spike.md F5-b (2026-07-30 실측)",
        mutate=_r15_drop_parameter_action_item,
    ),
    Recipe(
        id="R16-bare-member-literal",
        rule="ref.notation",
        expected="열림 + 경고: 필터를 구문 분석하는 동안 오류 — 필터를 무시합니다",
        source="docs/05-xsd-spike.md F5-c",
        mutate=_r16_bare_member_literal,
    ),
    Recipe(
        id="R17-unqualified-placeholder",
        rule="ref.notation",
        expected="열림 + 경고: 이름이 '[Multiple Values]'인 필드가 없습니다 (필드 제거)",
        source="docs/05-xsd-spike.md F5-c",
        mutate=_r17_unqualify_placeholder,
    ),
    Recipe(
        id="R18-bare-parameter-ref",
        rule="ref.notation",
        expected="열림 + 계산필드가 '계산에 오류 있음' → 종속 시트가 빈 화면",
        source="docs/05-xsd-spike.md F5-d",
        mutate=_r18_bare_parameter_ref,
    ),
    Recipe(
        id="R21-qualify-filter-level",
        rule="ref.notation",
        expected="열림 + 경고: 필터링을 위해 포함된 '[ds].[…]' 필드가 없습니다 (필터 제거)",
        source="docs/05-xsd-spike.md F5-f (2026-07-31 /author-loop 실측)",
        mutate=_r21_qualify_filter_level,
    ),
    Recipe(
        id="R19-unwrap-user-aggregation",
        rule="calc.aggregation",
        expected="열림 + '집계되지 않은 수식의 사용자 지정 집계가 필요합니다'",
        source="docs/05-xsd-spike.md F5-e",
        mutate=_r19_unwrap_user_aggregation,
    ),
    Recipe(
        id="R20-empty-set",
        rule="set.definition",
        expected="열림 + 집합을 쓰는 계산이 전부 오류 상태",
        source="docs/05-xsd-spike.md F5-e",
        mutate=_r20_empty_set,
    ),
    Recipe(
        id="R22-unknown-action-command",
        rule="action.shape",
        expected="열림 + 경고 없음 · 동작 대화상자에서 편집 불가, 동작이 발동하지 않는다",
        source="docs/05-xsd-spike.md F5-h (2026-07-31 /author-loop 실측)",
        mutate=_r22_unknown_action_command,
    ),
    Recipe(
        id="R23-drop-filter-link",
        rule="action.shape",
        expected="열림 + 경고 없음 · 동작의 필드 열이 비고 아무 필터도 걸리지 않는다",
        source="docs/05-xsd-spike.md F5-h",
        mutate=_r23_drop_filter_link,
    ),
    Recipe(
        id="R26-unqualify-sort",
        rule="ref.notation",
        expected="열림 + 경고: 필드가 정의되지 않았습니다. 정렬 지정을 무시합니다",
        source="docs/06-rule-candidates.md R26 (2026-08-12 MA_011 실측)",
        mutate=_r26_unqualify_sort,
    ),
    Recipe(
        id="R27-double-aggregate",
        rule="calc.aggregation",
        expected="열림 + 알약이 빨개지고 그 시트가 렌더링되지 않는다",
        source="docs/06-rule-candidates.md R27 (2026-08-12 MA_011 실측)",
        mutate=_r27_double_aggregate,
    ),
    Recipe(
        id="R28-strip-corner-radius-prefix",
        rule="format.fcp_prefix",
        expected="로드 거부 D2E8DA72: value 'corner-radius-top-left' not in enumeration",
        source="docs/05-xsd-spike.md F5-j (2026-09-07 MA_004 실측)",
        mutate=_r28_strip_corner_radius_prefix,
    ),
    Recipe(
        id="R29-quote-boolean-member",
        rule="ref.notation",
        expected="열림 + 경고: 필드의 필터를 구문 분석하는 동안 오류 — 필터를 무시합니다",
        source="docs/05-xsd-spike.md F5-k (2026-09-14 MA_004 손익계산서 실측)",
        mutate=_r29_quote_boolean_member,
    ),
    Recipe(
        id="R30-break-calc-syntax",
        rule="calc.syntax",
        expected="열림 + 그 계산필드가 '계산에 오류 있음' → 종속 시트가 빈 화면",
        source="docs/05-xsd-spike.md F5-l (2026-09-14 구조 문법 실측)",
        mutate=_r30_break_calc_syntax,
    ),
    Recipe(
        id="R31-mix-aggregation-levels",
        rule="calc.aggregation",
        expected="열림 + '집계 및 비집계 인수를 이 함수와 함께 혼합할 수 없습니다' → 시트 빈 화면",
        source="docs/05-xsd-spike.md F5-m (2026-09-14 집계/행수준 실측)",
        mutate=_r31_mix_aggregation_levels,
    ),
    Recipe(
        id="R32-drop-paramctrl-mode",
        rule="zone.shape",
        expected="열림 — 증상 미확인. 모양 불변식만 선 규칙이다 (05 F5-n)",
        source="docs/05-xsd-spike.md F5-n (2026-09-14 MA_004 실측)",
        mutate=_r32_drop_paramctrl_mode,
    ),
    Recipe(
        id="R33-drop-DatagraphCoreV1",
        rule="manifest.gates",
        expected="로드 거부 D2E8DA72: no declaration found for element 'datagraph'",
        source="docs/05-xsd-spike.md F5-o (2026-09-16 MA_004 JWLH 실측)",
        mutate=_r33_drop_datagraph_core,
    ),
)


def experiment_b_recipes(items: list[str]) -> tuple[Recipe, ...]:
    """실험 B — 대응 요소를 모르는 매니페스트 항목을 하나씩 지운다.

    거부 메시지의 `no declaration found for element '<요소>'`가 **대응 요소를 직접
    알려준다.** 열리면 그 표본이 해당 기능을 안 쓴다는 뜻이며 그것도 정보다
    (docs/06-rule-candidates.md §D.1).
    """

    def make(item: str) -> Mutator:
        def mutate(root: Any) -> str | None:
            return _drop_manifest_item(root, lambda tag: fcp.strip_prefix(tag) == item)

        return mutate

    return tuple(
        Recipe(
            id=f"B-drop-{item}",
            rule="manifest.gates",
            expected="거부되면 메시지가 대응 요소를 알려준다 / 열리면 이 표본이 해당 기능 미사용",
            source="docs/06-rule-candidates.md §D.1 (실험 B)",
            mutate=make(item),
        )
        for item in items
    )


# --- 패키징 -------------------------------------------------------------------------


def _twb_entry(zf: zipfile.ZipFile) -> str:
    names = [n for n in zf.namelist() if n.lower().endswith(".twb")]
    if not names:
        raise RuntimeError("아카이브에 .twb가 없다")
    return names[0]


def _write_twbx(source: Path, out: Path, new_twb: bytes) -> None:
    """`.twb`만 교체하고 나머지 엔트리는 **그대로** 복사한다.

    `.hyper`는 읽어서 다시 쓰지 않는다 — 압축 방식까지 원본 엔트리 정보를 따라간다
    (02 S1 무손실 원칙, 07 G6).
    """
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(out, "w") as dst:
        twb_name = _twb_entry(src)
        for info in src.infolist():
            data = new_twb if info.filename == twb_name else src.read(info.filename)
            # 원본 엔트리의 압축 방식·타임스탬프를 유지해 결정론을 지킨다.
            dst.writestr(info, data)


def _load_root(source: Path) -> tuple[Any, str | None]:
    """`.twb`/`.twbx`에서 루트와 (twbx면) 내부 엔트리 이름을 얻는다."""
    parser = safety.make_parser()
    if source.suffix.lower() == ".twb":
        return etree.parse(str(source), parser).getroot(), None
    with zipfile.ZipFile(source) as zf:
        name = _twb_entry(zf)
        with zf.open(name) as fh:
            return etree.parse(fh, parser).getroot(), name


def inject(source: Path, recipe: Recipe, out_dir: Path) -> dict[str, object] | None:
    """레시피 1건을 적용한 고장본을 만든다. 적용 대상이 없으면 None."""
    root, _ = _load_root(source)
    tree = root.getroottree()

    detail = recipe.mutate(root)
    if detail is None:
        return None

    payload = etree.tostring(tree, xml_declaration=True, encoding="utf-8")
    out_path = out_dir / f"{source.stem}__{recipe.id}{source.suffix}"

    if source.suffix.lower() == ".twbx":
        _write_twbx(source, out_path, payload)
    else:
        out_path.write_bytes(payload)

    return {
        "file": out_path.name,
        "recipe": recipe.id,
        "rule": recipe.rule,
        "injected": detail,
        "expected_tableau": recipe.expected,
        "source_doc": recipe.source,
        "origin": source.name,
        # 사용자가 Tableau Desktop에서 열어 보고 채우는 칸 (docs/TODO D 보고 형식).
        "observed": None,
        "error_text": None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="정상본에 결함을 주입해 고장본을 만든다")
    parser.add_argument("--source", type=Path, action="append", help="원본 .twb/.twbx (반복 가능)")
    parser.add_argument("--out", type=Path, help="산출 디렉토리")
    parser.add_argument(
        "--experiment-b",
        action="store_true",
        help="매니페스트 항목을 하나씩 지운 파일도 만든다 (대응표 캐기)",
    )
    parser.add_argument("--list", action="store_true", help="레시피 목록만 출력한다")
    args = parser.parse_args(argv)

    # 레시피 설명에 한글·em dash가 있다. Windows 기본 콘솔(cp949)에서 죽지 않게 한다.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if args.list:
        for r in RECIPES:
            print(f"{r.id:34} rule={r.rule:16} {r.expected}")
        return 0

    if not args.source or not args.out:
        parser.error("--source 와 --out 이 필요하다 (또는 --list)")

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    recipes: tuple[Recipe, ...] = RECIPES
    if args.experiment_b:
        gates_path = Path(__file__).resolve().parent.parent / (
            "src/twb_lint/data/manifest_gates.json"
        )
        items = json.loads(gates_path.read_text(encoding="utf-8"))["known_items_unmapped"]["items"]
        recipes = recipes + experiment_b_recipes(items)

    labels: list[dict[str, object]] = []
    skipped: list[str] = []
    for source in args.source:
        if not source.exists():
            print(f"SKIP 원본 없음: {source}", file=sys.stderr)
            continue
        for recipe in recipes:
            entry = inject(source, recipe, out_dir)
            if entry is None:
                skipped.append(f"{source.name} / {recipe.id}")
                continue
            labels.append(entry)

    labels_path = out_dir / "labels.json"
    labels_path.write_text(
        json.dumps(
            {
                "note": (
                    "각 항목을 Tableau Desktop 2026.1에서 열어 보고 observed/error_text를 "
                    "채운다. 보고 형식: 열림 / 안 열림 + 에러 문구 원문 / 열리는데 이상함 + 무엇이."
                ),
                "cases": labels,
                "not_applicable": skipped,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"OK   generated={len(labels)} skipped={len(skipped)} labels={labels_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
