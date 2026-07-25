"""규칙 레지스트리 + 자동 수집.

`@register`로 등록하고, `all_rules()`가 `syntactic/`·`semantic/` 하위 모듈을
자동 import 하여 등록을 촉발한다. **새 규칙 파일을 넣으면 자동으로 잡힌다.**
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import TypeVar

from twb_lint.validation.rule import Rule, Stage

_RULES: list[Rule] = []
_loaded = False

# 자동 스캔 대상 서브패키지 (규칙이 사는 곳).
_RULE_PACKAGES = (
    "twb_lint.validation.syntactic",
    "twb_lint.validation.semantic",
)

R = TypeVar("R", bound=type)


def register(cls: R) -> R:
    """규칙 클래스를 등록하는 데코레이터."""
    _RULES.append(cls())
    return cls


def _discover() -> None:
    """규칙 패키지의 모든 모듈을 import 해 @register를 촉발한다."""
    global _loaded
    if _loaded:
        return
    for pkg_name in _RULE_PACKAGES:
        pkg = importlib.import_module(pkg_name)
        for mod in pkgutil.iter_modules(pkg.__path__):
            importlib.import_module(f"{pkg_name}.{mod.name}")
    _loaded = True


def all_rules() -> list[Rule]:
    """등록된 모든 규칙 (자동 수집 후)."""
    _discover()
    return list(_RULES)


def rules_for(stage: Stage) -> list[Rule]:
    """특정 단계의 규칙만."""
    return [r for r in all_rules() if r.stage is stage]
