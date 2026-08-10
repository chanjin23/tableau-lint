# 저작 레시피 인덱스

> 문제정의: [`../08-authoring-recipes.md`](../08-authoring-recipes.md).
> 작업 요청을 받으면 여기서 레시피를 찾아 **정본 형태로** 쓴다. 없으면 만들지 말고
> 미관찰로 기록한다 (08 §6 — 거짓 레시피보다 없음이 낫다).

## 작업 → 레시피

| 하려는 작업 | 레시피 |
|---|---|
| **빈 손에서 `.twb` 만들기 (워크북 골격·매니페스트)** | [20](./20-empty-workbook.md) |
| **CSV(텍스트 파일) 데이터 원본 연결** | [21](./21-datasource-csv.md) |
| **빈 시트에 첫 뷰 만들기 (동반 변경 전량)** | [22](./22-first-field-placement.md) |
| 계산 필드 만들기 | [01](./01-calc-field-create.md) |
| 계산 필드 수식 고치기 · 이름 바꾸기 · 지우기 · LOD↔테이블계산 | [04](./04-calc-field-lifecycle.md) |
| 선반에서 즉석 수식(임시 계산) | [05](./05-calc-adhoc.md) |
| 매개변수 만들기 (목록) | [02](./02-parameter-create-list.md) |
| 매개변수 타입 바꾸기 · 지우기 | [06](./06-parameter-lifecycle.md) |
| 클릭으로 매개변수 바꾸는 동작 | [07](./07-action-parameter.md) |
| 클릭 하이라이트 동작 | [08](./08-action-highlight.md) |
| 워크시트 만들기 · 복제 · 개명 · 삭제 | [09](./09-worksheet-lifecycle.md) |
| 범례 시트 · 범례 카드 | [10](./10-legend-sheets.md) |
| 열/행 선반 배치 · 이중축 · 마크 카드 분리 | [11](./11-shelf-expressions.md) |
| 필터 걸기/고치기 | [12](./12-filters.md) |
| 마크 유형 · 색/텍스트 인코딩 · 레이블 · 도구설명 | [13](./13-marks-encodings.md) |
| 정렬 | [14](./14-sorts.md) |
| 대시보드에 시트 놓기 | [03](./03-dashboard-place-worksheet.md) |
| 존 여백·테두리·모서리·배경 | [15](./15-zone-style.md) |
| 컨테이너 구조 · Phone 레이아웃 · 매개변수 컨트롤 | [16](./16-dashboard-containers.md) |
| 사용자 지정 SQL · 추출 켜고 끄기 | [17](./17-datasource-sql-extract.md) |
| 필드 폴더 · 색상 팔레트 | [18](./18-datasource-folders-palette.md) |
| 글꼴 · 서식 규칙 | [19](./19-format-fonts.md) |

## 전 레시피 공통 원칙

1. **name으로 참조, caption은 표시용** — 개명은 caption만 바뀐다
2. **동반 변경을 빠뜨리지 않는다** — 워크시트 3곳(+배치 시 5곳), 필드는 쓰는 시트의
   datasource-dependencies, 동작의 exclude 목록
3. **datasource `<column>` 정의는 name 문자열 오름차순** — 정렬 위치에 삽입 (E2E-1)
4. **auto-generated(Phone)·파생값(fixed-size)은 안 쓰거나 대략 쓴다** — Tableau가 재계산
5. 저장 후 diff 판독: 존 개수 불변이면 좌표는 노이즈. 갈래 판별은 MA_008 `신호노이즈.md`
6. 마지막은 항상 `twb_validate` — passed여도 **findings를 읽는다** (02 AC9)
7. **매니페스트는 쓰는 기능만큼만 선언한다** — 빈 워크북 4항목, 데이터 원본을
   붙이면 3항목 추가. 실파일의 22항목짜리를 통째로 복사하지 않는다 (20·21)

## 관리

- [00-inventory.md](./00-inventory.md) — 코퍼스 관찰 분류 (근거 커밋 원장)
- [90-e2e-log.md](./90-e2e-log.md) — E2E 실측 로그
- 근거 코퍼스: MA_008 저장소 `git show <sha> -- xml/`. `추정`·`?` 항목은 관찰 승격 전 신뢰 금지
