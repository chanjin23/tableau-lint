# functions/

버전별 Tableau calc 함수 화이트리스트 (`functions_<YYYY.R>.json`).

소스 = help.tableau.com 함수 레퍼런스(alphabetical/categorical). 공식 machine-readable
목록이 없어 스크랩→JSON으로 유지한다. `config.FUNCTIONS_BY_VERSION` 매핑 참조.

포맷(안): `{"version": "2026.1", "functions": ["SUM", "AVG", "DATEADD", ...]}`.

채우기: `tools/scrape_functions.py` (구현 단계).
