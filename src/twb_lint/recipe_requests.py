"""건의함 (MCP `twb_suggestion_box` · CLI `suggestion-box`) — 레시피·검사기 문제를 모아
두었다가 빈도순으로 본다.

`twb_recipe`가 `found: False`를 돌려주거나, 레시피대로 썼는데 `twb_validate`가 실패하거나,
검사 결과와 Tableau가 어긋나면(통과했는데 깨짐 · 경고했는데 정상) 호출자가 여기에 한 줄
접수한다. 종류마다 필수 항목이 다르다 (`KINDS`). **접수는 레시피도 규칙도 아니다** —
레시피는 Tableau에서 관찰한 실측 정답지이고(`docs/recipes/`), 규칙은 코퍼스 대조와 분리
실험을 거친다. 여기 쌓인 것은 "무엇이 부족한가"의 목록일 뿐이다.

저장은 추가 전용 JSONL이다 (`.twb-lint/recipe-requests.jsonl`, gitignore). 접수·해결을
이벤트로 한 줄씩 덧붙이고, 읽을 때 합친다 — 중복을 합치려고 파일을 고쳐 쓰지 않으므로
동시에 접수해도 깨지지 않는다.

기밀: 골든셋은 사내 재무 데이터다. 짧은 글자만 받고 XML 원문은 거부한다.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from twb_lint import recipes

Kind = Literal["missing", "defective", "lint_missed", "lint_false_alarm"]
KINDS: tuple[Kind, ...] = ("missing", "defective", "lint_missed", "lint_false_alarm")
"""건의 종류.

- `missing` — 레시피가 없다 (`twb_recipe` found=False)
- `defective` — 레시피대로 썼는데 `twb_validate`가 실패했다 (`recipe` 필수)
- `lint_missed` — 검사는 통과했는데 Tableau에서 깨졌다 (`symptom`·`layer` 필수)
- `lint_false_alarm` — 검사가 경고·오류를 냈는데 Tableau에서는 정상이다 (`rule_ids` 필수)
"""

Layer = Literal["load_refused", "setting_dropped", "no_data", "field_error"]
LAYERS: tuple[Layer, ...] = ("load_refused", "setting_dropped", "no_data", "field_error")
"""실패 4층 (01 v2.0) — 1 파일이 안 열린다 · 2 설정이 버려졌다 · 3 데이터가 안 나온다 ·
4 필드가 오류 상태다(빨간 알약·느낌표). `lint_missed`만 쓴다."""

LINT_KINDS = frozenset({"lint_missed", "lint_false_alarm"})

_STORE_ENV = "TWB_LINT_REQUESTS"
_STORE_DEFAULT = Path(__file__).resolve().parents[2] / ".twb-lint" / "recipe-requests.jsonl"

_MAX_TASK = 200
_MAX_NOTE = 300
_MAX_RULE_IDS = 20
_RULE_ID = re.compile(r"^[\w.\-]{1,64}$")
# 태그처럼 보이는 것 — 워크북 XML 조각이 새어 들어오는 경로를 막는다
_XML_LIKE = re.compile(r"</?[A-Za-z_][^>]*>")
_NOTES_KEPT = 3


class RequestError(ValueError):
    """접수를 거절한다 — 메시지는 호출자에게 그대로 돌려준다."""


@dataclass
class Request:
    """같은 요청을 합친 결과."""

    id: str
    kind: str
    task: str
    recipe: str = ""
    count: int = 0
    first_seen: str = ""
    last_seen: str = ""
    rule_ids: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    resolved_by: str | None = None  # None = 열림. 닫히면 레시피 이름 (없으면 "")
    symptom: str = ""
    """Tableau에서 본 것 — 오류 문구 그대로 또는 "정상"."""
    layer: str | None = None
    """`lint_missed`의 실패 층 (`LAYERS`)."""


def store_path() -> Path:
    override = os.environ.get(_STORE_ENV)
    return Path(override) if override else _STORE_DEFAULT


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _normalize(text: str) -> str:
    """대소문자·공백·문장부호 차이는 같은 요청으로 본다."""
    return re.sub(r"[\W_]+", " ", text.lower()).strip()


def _make_id(kind: str, recipe: str, task: str, rule_ids: list[str] | None = None) -> str:
    key = f"{kind}|{recipe}|{_normalize(task)}"
    if kind in LINT_KINDS and rule_ids:
        # 같은 증상이라도 다른 규칙의 문제면 다른 건이다
        key += "|" + ",".join(sorted(rule_ids))
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:8]


def _clean_text(label: str, value: str, limit: int, *, required: bool) -> str:
    text = " ".join(value.split())
    if required and not text:
        raise RequestError(f"{label}가 비었다.")
    if len(text) > limit:
        raise RequestError(f"{label}는 {limit}자 이하여야 한다 ({len(text)}자).")
    if _XML_LIKE.search(text):
        raise RequestError(f"{label}에 XML 조각이 있다 — 워크북 내용은 접수하지 않는다.")
    return text


def _append(event: dict[str, object]) -> None:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def submit(
    kind: str,
    task: str,
    recipe: str = "",
    rule_ids: list[str] | None = None,
    note: str = "",
    symptom: str = "",
    layer: str | None = None,
) -> Request:
    """접수 1건을 덧붙이고, 합쳐진 현재 상태를 돌려준다.

    종류별 필수 항목 (`KINDS` 참조):
    `defective`는 따른 레시피 — 존재하지 않는 레시피는 거절한다.
    `lint_missed`는 `symptom`과 `layer`, `lint_false_alarm`은 울린 규칙(`rule_ids`).
    """
    if kind not in KINDS:
        raise RequestError(f"kind는 {' | '.join(KINDS)} 중 하나여야 한다: {kind!r}")
    if layer is not None and layer not in LAYERS:
        raise RequestError(f"layer는 {' | '.join(LAYERS)} 중 하나여야 한다: {layer!r}")
    if kind == "lint_missed" and layer is None:
        raise RequestError("lint_missed는 layer(어느 층에서 깨졌나)가 필요하다.")
    if kind != "lint_missed" and layer is not None:
        raise RequestError("layer는 lint_missed에만 쓴다.")
    if kind == "lint_false_alarm" and not rule_ids:
        raise RequestError("lint_false_alarm은 울린 규칙(rule_ids)이 필요하다.")
    if not recipes.recipes_dir().is_dir():
        # wheel 설치 — 체크아웃이 아니라서 쓸 곳이 없다 (recipes.py와 같은 전제)
        raise RequestError(
            "레시피 디렉토리(docs/recipes/)가 없다 — 저장소 체크아웃에서만 접수된다."
        )
    task_text = _clean_text("task", task, _MAX_TASK, required=True)
    note_text = _clean_text("note", note, _MAX_NOTE, required=False)
    symptom_text = _clean_text(
        "symptom", symptom, _MAX_NOTE, required=(kind == "lint_missed")
    )

    recipe_name = ""
    if kind == "defective":
        hit = recipes.get(recipe) if recipe.strip() else None
        if hit is None:
            raise RequestError(f"defective는 따른 레시피(번호·파일명)가 필요하다: {recipe!r}")
        recipe_name = hit[0].removesuffix(".md")

    ids = list(dict.fromkeys(rule_ids or []))
    if len(ids) > _MAX_RULE_IDS:
        raise RequestError(f"rule_ids는 {_MAX_RULE_IDS}개 이하여야 한다.")
    for rule_id in ids:
        if not _RULE_ID.match(rule_id):
            raise RequestError(f"rule_id 형식이 아니다: {rule_id!r}")

    req_id = _make_id(kind, recipe_name, task_text, ids)
    event: dict[str, object] = {
        "event": "submit",
        "id": req_id,
        "at": _now(),
        "kind": kind,
        "task": task_text,
        "recipe": recipe_name,
        "rule_ids": ids,
        "note": note_text,
    }
    if symptom_text:
        event["symptom"] = symptom_text
    if layer is not None:
        event["layer"] = layer
    _append(event)
    return next(r for r in load() if r.id == req_id)


def resolve(req_id: str, recipe: str = "") -> Request:
    """건의를 닫는다. `recipe`는 그 건을 메운 레시피(번호·파일명, 생략 가능)."""
    current = {r.id: r for r in load()}
    if req_id not in current:
        raise RequestError(f"그런 건의가 없다: {req_id!r}")
    name = ""
    if recipe.strip():
        hit = recipes.get(recipe)
        if hit is None:
            raise RequestError(f"그런 레시피가 없다: {recipe!r}")
        name = hit[0].removesuffix(".md")
    _append({"event": "resolve", "id": req_id, "at": _now(), "recipe": name})
    return next(r for r in load() if r.id == req_id)


def load() -> list[Request]:
    """이벤트를 합친 건의 목록 — 열린 것 먼저, 많이 접수된 순, 최근 순."""
    path = store_path()
    if not path.is_file():
        return []
    merged: dict[str, Request] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue  # 깨진 줄 하나가 목록 전체를 막으면 안 된다
        req_id = event.get("id")
        if not isinstance(req_id, str):
            continue
        if event.get("event") == "submit":
            req = merged.setdefault(
                req_id,
                Request(
                    id=req_id,
                    kind=event.get("kind", ""),
                    task=event.get("task", ""),
                    recipe=event.get("recipe", ""),
                    first_seen=event.get("at", ""),
                ),
            )
            req.count += 1
            req.last_seen = event.get("at", "")
            if event.get("symptom"):
                req.symptom = event["symptom"]  # 최근 접수의 증상을 보인다
            if event.get("layer"):
                req.layer = event["layer"]
            for rule_id in event.get("rule_ids", []):
                if rule_id not in req.rule_ids:
                    req.rule_ids.append(rule_id)
            note = event.get("note", "")
            if note and note not in req.notes:
                req.notes = [*req.notes, note][-_NOTES_KEPT:]
            req.resolved_by = None  # 닫힌 뒤 다시 접수되면 다시 연다
        elif event.get("event") == "resolve" and req_id in merged:
            merged[req_id].resolved_by = event.get("recipe", "")
    # 안정 정렬 2회 — 최근 순으로 먼저 깔고, 열림·빈도로 다시 묶는다
    by_recent = sorted(merged.values(), key=lambda r: r.last_seen, reverse=True)
    return sorted(by_recent, key=lambda r: (r.resolved_by is not None, -r.count))
