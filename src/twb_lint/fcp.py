"""`_.fcp.` 접두사 처리 — L-A 전처리와 규칙 ⑥-a가 **함께** 쓰는 유일한 지점.

Tableau는 신기능 요소·속성을 하위호환 접두사로 직렬화한다:

```xml
<_.fcp.DashboardRoundedCorners.true...format />
<extract _.fcp.VConnDownstreamExtractsWithWarnings.true...user-specific='...' />
```

패턴은 `_.fcp.<기능명>.<true|false>...<원래이름>`이다. 구버전 Tableau는 모르는 이름이라
건너뛰고, 지원 버전만 해석한다. **공식 XSD는 이 규칙을 전혀 모델링하지 않아서**
최신 기능을 쓴 워크북은 정규화 없이는 예외 없이 L-A에 실패한다 — 오류의 98%가 이것이었다
(docs/05-xsd-spike.md F2, 파일당 48~55건).

**이 모듈이 코어에 있는 이유**는 접두사가 두 방향으로 쓰이기 때문이다:

| 소비자 | 필요한 것 | 트리 |
|---|---|---|
| L-A (`syntactic/xsd.py`) | 접두사를 **지운** 트리 | 정규화 사본 |
| 규칙 ⑥-a (`semantic/manifest_gates.py`) | 접두사에서 **읽은 기능명** | 정규화 **전** 원본 |

정규화가 소속 기능을 지우므로(`_.fcp.X.true...format` → `format`) 둘은 같은 트리를
쓸 수 없다. `ValidationContext`가 두 트리를 분리해 갖는 근거다 (docs/05-xsd-spike.md F7 함의 2).
"""

from __future__ import annotations

import copy
import re
from typing import Any

# `_.fcp.<기능명>.<true|false>...` — 기능명을 group(1)로 캡처한다.
# 실측 근거: docs/05-xsd-spike.md F2·F7 (표본 10개, 예외 0).
PREFIX_RE = re.compile(r"^_\.fcp\.([^.]+)\.(?:true|false)\.\.\.")

MANIFEST_TAG = "document-format-change-manifest"
"""매니페스트 요소 이름. 규칙 ⑥의 입력."""


def feature_of(name: str) -> str | None:
    """이름에 fcp 접두사가 있으면 그 기능명을 반환한다. 없으면 None.

    >>> feature_of("_.fcp.DashboardRoundedCorners.true...format")
    'DashboardRoundedCorners'
    >>> feature_of("format") is None
    True
    """
    m = PREFIX_RE.match(name)
    return m.group(1) if m else None


def strip_prefix(name: str) -> str:
    """fcp 접두사를 벗긴 원래 이름. 접두사가 없으면 그대로.

    >>> strip_prefix("_.fcp.DashboardRoundedCorners.true...format")
    'format'
    """
    return PREFIX_RE.sub("", name)


def expected_manifest_item(feature: str) -> str:
    """기능명에 대응하는 매니페스트 항목 이름 (규칙 ⑥-a).

    매니페스트 항목 이름 **자체에도** fcp 접두사가 붙고, 접두사를 벗긴 값이 기능명과
    같다 — 표본 10/10 일치 (docs/05-xsd-spike.md F7).

    >>> expected_manifest_item("DashboardRoundedCorners")
    '_.fcp.DashboardRoundedCorners.true...DashboardRoundedCorners'
    """
    return f"_.fcp.{feature}.true...{feature}"


def features_in_tree(root: Any) -> set[str]:
    """트리 전체에서 쓰인 fcp 기능명 집합 (요소 태그 + 속성 키 양쪽).

    **속성 키에도 나타난다** — 요소만 훑으면 놓친다 (docs/05-xsd-spike.md F2 예시 2행).
    매니페스트 요소 자신은 제외한다: 매니페스트 항목은 "선언"이지 "사용"이 아니므로
    포함하면 규칙 ⑥-a가 자기 자신을 근거로 항상 통과한다.

    Args:
        root: lxml element (정규화 **전** 원본이어야 한다).
    """
    found: set[str] = set()
    for el in root.iter():
        tag = el.tag
        if not isinstance(tag, str):  # comment/PI는 tag가 호출가능 객체다
            continue
        if strip_prefix(tag) == MANIFEST_TAG or _within_manifest(el):
            continue
        feature = feature_of(tag)
        if feature is not None:
            found.add(feature)
        for key in el.attrib:
            feature = feature_of(key)
            if feature is not None:
                found.add(feature)
    return found


def manifest_items(root: Any) -> set[str]:
    """`<document-format-change-manifest>`의 자식 항목 이름 집합 (원문 그대로).

    fcp 항목은 접두사가 붙은 채로 들어 있다 (`_.fcp.X.true...X`). 벗기지 않고 반환하는
    이유는 규칙 ⑥-a가 `expected_manifest_item()` 결과와 **원문끼리** 대조하기 때문이다.
    벗겨서 비교하면 `_.fcp.X.true...X`와 `_.fcp.X.false...X`가 구분되지 않는다.
    """
    manifest = _find_manifest(root)
    if manifest is None:
        return set()
    return {c.tag for c in manifest if isinstance(c.tag, str)}


def normalize_tree(root: Any) -> Any:
    """fcp 접두사를 벗긴 **트리 사본**을 만든다 (L-A 입력).

    원본은 건드리지 않는다 — read-only 원칙(02 S1-1)이자, 규칙 ⑥-a가 원본을 필요로 하기
    때문이다. 사본 비용이 있으므로 `ValidationContext`가 결과를 캐시한다.

    요소 태그와 속성 키 **양쪽**에 적용한다.
    """
    clone = copy.deepcopy(root)
    for el in clone.iter():
        if not isinstance(el.tag, str):
            continue
        el.tag = strip_prefix(el.tag)
        for key in list(el.attrib):
            new_key = strip_prefix(key)
            if new_key != key:
                el.attrib[new_key] = el.attrib.pop(key)
    return clone


def _find_manifest(root: Any) -> Any:
    """매니페스트 요소를 찾는다. 정규화 여부와 무관하게 동작한다."""
    for el in root.iter():
        if isinstance(el.tag, str) and strip_prefix(el.tag) == MANIFEST_TAG:
            return el
    return None


def _within_manifest(el: Any) -> bool:
    """이 요소가 매니페스트 안에 있는가 (= 선언이지 사용이 아님)."""
    parent = el.getparent()
    while parent is not None:
        if isinstance(parent.tag, str) and strip_prefix(parent.tag) == MANIFEST_TAG:
            return True
        parent = parent.getparent()
    return False
