# 레시피 17 — 사용자 지정 SQL 편집 · 추출 토글

| 항목 | 값 |
|---|---|
| 판정 표면 | T2(데이터) |
| UI 경로 | 데이터 원본 > 사용자 지정 SQL 편집 / 연결 '추출'·'라이브' |
| 근거 | MA_008 `e6a02cc` `7f4e665` `c7baad9` (전부 UI·확인) |
| Tableau | 2026.1 |

## SQL 편집 (`e6a02cc` `7f4e665` `c7baad9`)

SQL 본문은 `<relation type='text'>` 요소 텍스트 (CRLF `&#13;` 이스케이프).

- **FROM 테이블 교체** 시 `<object caption>`·`<column datatype='table'>`의
  내부 id 해시가 **함께 재생성**된다 (`…_F1C84BDC…` → `…_2008A3B1…`, `e6a02cc`)
- SELECT 절에 컬럼 추가 → 대응 `<column caption='<Title Case>' name='[<소문자>]'>` 생성 (`7f4e665`)
- 결과 컬럼명이 중복되면 Tableau 생성 쿼리가 `column reference "…" is ambiguous`로
  실패한다 — XML은 유효, 층 3 실패 (`c7baad9`). 서브쿼리 `T.*`와 조인 컬럼 중복 주의

## 추출 해제/재생성 — zip 구조가 바뀐다 (`7f4e665` `c7baad9`)

| 상태 | XML | .twbx zip |
|---|---|---|
| 추출 해제 | `<extract @enabled='false'>` — **요소는 남는다** (재추출 설정 보존) | `.hyper`·`Data/` 멤버 소멸, `.twb`만 |
| 추출 재생성 | `@enabled='true'` | `Data/<twb명>개 파일/<데이터소스명>.hyper` 재생성 |

- 추출/라이브는 `<connection>`이 아니라 `<extract @enabled>`가 결정한다
- `.hyper` 경로의 `<twb명>`은 통합문서 파일명을 따라간다 — 파일명 변경 후
  재추출하면 경로도 갱신 (`c7baad9`)
- `dbname` 경로는 저장 위치 기준으로 재작성된다 — 절대경로화 관찰 (E2E-1, 노이즈)

## 재저장 검증

추출 `update-time`·`.hyper` MD5는 노이즈 (데이터 변경 아님). twb-lint 연계:
메타↔hyper 대조는 hyperapi 영역(01 A.5).
