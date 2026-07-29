"""`twb_lint.calc.extractor` — 어휘 스캐너 (03 D3.7).

파서가 아니라 스캐너라 **실패하지 않는다.** 대신 "무엇을 함수로 세는가"가 전부이므로
경계 조건을 못 박는다: 주석·문자열 안은 세지 않는다, 키워드는 함수가 아니다.
"""

from __future__ import annotations

from twb_lint.calc.extractor import extract


def test_function_names_are_upper_cased() -> None:
    """Tableau 함수는 대소문자를 가리지 않는다. 화이트리스트는 대문자다."""
    refs = extract("sum([a]) + Zn([b])")

    assert refs.functions == {"SUM", "ZN"}


def test_field_refs_keep_their_original_notation() -> None:
    """정규화는 규칙 ②의 몫이다 — 여기서 벗기면 어느 표기였는지가 사라진다 (G8)."""
    refs = extract("[Calculation_1234] + [federated.abc].[usr:x:qk]")

    assert refs.field_refs == {"[Calculation_1234]", "[federated.abc].[usr:x:qk]"}


def test_language_keywords_are_not_functions() -> None:
    """`IF (x) THEN`의 IF를 함수로 세면 화이트리스트에 없어 거짓 WARNING이 난다."""
    refs = extract("IF ([a] > 1) THEN SUM([b]) ELSEIF ([c]) THEN 0 END")

    assert refs.functions == {"SUM"}


def test_line_comments_are_ignored() -> None:
    """실측 `groupfilter@expression`이 `//` 주석을 담고 있었다 (D3.6)."""
    refs = extract("// SUM([ignored])\nMIN([kept])")

    assert refs.functions == {"MIN"}
    assert refs.field_refs == {"[kept]"}


def test_block_comments_are_ignored() -> None:
    refs = extract("/* MAX([gone])\n still gone */ ABS([here])")

    assert refs.functions == {"ABS"}
    assert refs.field_refs == {"[here]"}


def test_string_literals_are_not_scanned() -> None:
    """문자열 안의 대괄호를 필드로 세면 존재하지 않는 참조가 만들어진다."""
    refs = extract("DATEDIFF('year', [a], [b]) + LEN(\"[not a field]\")")

    assert refs.functions == {"DATEDIFF", "LEN"}
    assert refs.field_refs == {"[a]", "[b]"}


def test_lod_expressions_yield_their_inner_refs() -> None:
    """LOD는 표본에 없었지만 문법 범위다 — FIXED는 키워드, 안쪽은 정상 수집."""
    refs = extract("{ FIXED [Calculation_1] : COUNTD(IF [x]=3 THEN [y] END) }")

    assert refs.functions == {"COUNTD"}
    assert refs.field_refs == {"[Calculation_1]", "[x]", "[y]"}


def test_whitespace_between_name_and_paren_still_counts() -> None:
    refs = extract("SUM   ([a])")

    assert refs.functions == {"SUM"}


def test_bare_names_are_not_functions() -> None:
    """`(`가 없으면 호출이 아니다 — 필드명 조각을 함수로 세지 않는다."""
    refs = extract("[a] + notacall")

    assert refs.functions == set()


def test_empty_and_garbage_input_do_not_raise() -> None:
    """스캐너는 실패하지 않는다 — 파싱 실패 WARNING이라는 노이즈 클래스가 없다 (D3.7)."""
    assert extract("").functions == set()
    assert extract("[unterminated").field_refs == set()
    assert extract(")))(((").functions == set()
