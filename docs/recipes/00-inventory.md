# 레시피 인벤토리 — 코퍼스 관찰 분류

> [`08-authoring-recipes.md`](../08-authoring-recipes.md)의 1단계 산출물.
> 코퍼스: MA_008 저장소, 2026-08-06 기준 68커밋 중 signal 46개.
> 정확한 델타는 항상 `git show <sha> -- xml/` (MA_008 저장소에서).

## 문서 관리

| 항목 | 값 |
|---|---|
| 상태 | ✅ 1차 완료 (2026-08-06) |
| 다음 | 전량 변환 ✅ (레시피 01~19, [`README.md`](./README.md)) → 미관찰 기능 리스트 대조 (08 §7) |

## 근거 유형 2종

| 유형 | 뜻 | 증거력 |
|---|---|---|
| **UI** | 사용자가 Tableau UI로 조작, 저장 전/후 대조 | 정본 그 자체 |
| **AI** | AI가 XML 직접 저작 → Tableau가 열고 수용(정규화 관찰 포함) | "Tableau가 받아들이는 형태" — 정본과 다를 수 있으나 수용은 확인됨 |

---

## T2 — 계산필드·매개변수

| 조작 | 근거 커밋 | 유형 |
|---|---|---|
| 계산필드 생성 | b13bc5a · 7353886 · c3ad388 · ad7cb3f · 57e556a · 8b136bb · a248ae3 · 1d2aa95 · b67ed82 · 23690bc(AI) | UI/AI |
| 수식 편집·교체 | 35911cd · 146f488 · ae0f567 · e6a02cc · 57e556a(FIXED LOD 적용) | UI |
| 계산필드 삭제 | 98fb49c · 7f4e665 · b6256cf | UI |
| 계산필드 개명 (name 유지 = 참조 안 깨짐) | e6a02cc · b6256cf | UI |
| 필드 교체 (삭제+신규+참조 갱신) | 6958d25 | UI |
| 빈 껍데기 생성 → 수식 채움 (`formula=''` 유효) | 7f4e665 · 35db682 | UI |
| 임시(ad-hoc) 계산 — datasource-dependencies에만, `user:unnamed` | 9cac21f · c3ad388 · b63ddda | UI |
| 복사본 name 발급 규칙 (원본 caption 기반, 어긋남 가능) | a248ae3 | UI |
| 테이블 계산 ↔ LOD 전환 (`table-calc`·derivation 동반 변경) | 35911cd · 146f488 | UI |
| 수식 주석 추가 | b63ddda · 57e556a | UI |
| 별칭(aliases) 추가 | ad7cb3f | UI |
| 매개변수 생성 (목록형, members·default-value-field) | b13bc5a | UI |
| 매개변수 타입 변경 (문자열 목록→datetime, members 소멸) | 8b136bb | UI |
| 매개변수 삭제 (paramctrl 존 동시 삭제) | 57e556a · 8b136bb · b6256cf | UI |
| 값 목록 필드 연결 해제 (`source-field` 소멸) | ae0f567 | UI |

## T3 — 집합·동작

| 조작 | 근거 커밋 | 유형 |
|---|---|---|
| 매개변수 동작 생성 (edit-parameter-action 전체 구조) | b13bc5a | UI |
| 하이라이트 동작 생성 (action/tsc:brush, exclude 단일 문자열) | 8b136bb · 1892f8d(AI) · 6154648(AI) · 8df7c57(AI) | UI/AI |
| 하이라이트 소스 시트 다중·동작 병합 (@worksheet → exclude-sheet 방식 전환) | b67ed82 | UI |
| 동작 순서 제약 — `<action>`은 `<edit-parameter-action>` 앞 | 6154648 | AI(XSD 거부 실측) |
| 새 시트 생성 시 exclude-sheet 갱신 여파 | 8fc93fe(AI) · c681161(AI) | AI |
| **집합(`<group>`)·집합 동작** | **관찰 0건** | — |

## T4 — 선반·워크시트 구성

| 조작 | 근거 커밋 | 유형 |
|---|---|---|
| 선반 표현식 (`cols`/`rows`, `*` 교차 · `+` 축 연결, 우결합) | 146f488 · 33052f5 · 1d2aa95 | UI |
| 이중축 + 축 동기화 (`fold`·`synchronized`) | 35db682 · 1d2aa95 · 23690bc(AI) | UI/AI |
| 측정값 이름/측정값 구조 ↔ 개별 연속형 (pane 분리, x/y-axis-name) | 33052f5 · 9cac21f | UI |
| 필터 categorical (Measure Names 멤버 선택 포함) | 7353886 · 146f488 | UI |
| 필터 quantitative (min/max) | 7353886 · 529e436 | UI |
| groupfilter 속성 조합 — UI 경로별 차이 (manual-selection vs ui-domain/enumeration) | e6a02cc · 358c382 · b63e1b1 | UI |
| 필터 filter-group 속성 | 57e556a | UI |
| encodings — text·color 교체/추가 | 5916221 · a248ae3 · 6958d25 | UI |
| computed-sort (필드 기준 정렬) | b13bc5a · 23690bc(AI) | UI/AI |
| manual-sort | 146f488 · 6154648(AI) | UI/AI |
| mark class 변경 (Automatic→Text 등) | 5916221 | UI |
| mark-sizing 해제 · 크기값 | b13bc5a · b6256cf | UI |
| customized-label / customized-tooltip | 35911cd · 8b136bb · 6958d25 | UI |
| 소계 표시 | c3ad388 | UI |
| LOD 참조 컬럼의 datasource-dependencies 자동 등록 | 35db682 | UI |

## 워크시트 수명주기

| 조작 | 근거 커밋 | 유형 |
|---|---|---|
| 생성·복제·개명·삭제 — `<worksheet>`·`<window>`·`<thumbnail>` 3곳 동시 | b63e1b1 · b13bc5a · 7353886 · 35911cd · ad7cb3f · c3ad388 · b63ddda · 7e15b84 | UI |
| AI 복제 시 window `simple-id` uuid unique 제약 | 8df7c57 · 8fc93fe(AI) · c681161(AI) | AI(XSD 거부 실측) |
| 범례 카드 이동/제거 (window/cards/edge/strip) | b6256cf · 8fc93fe(AI) | UI/AI |
| 범례 시트 패턴 (색상 상속 — 데이터소스 팔레트) | 358c382 · 6154648(AI) · 8df7c57(AI) · b67ed82 | UI/AI |

## 대시보드

| 조작 | 근거 커밋 | 유형 |
|---|---|---|
| 워크시트 배치 (zone+viewpoint+devicelayout 양쪽, 텍스트 존 교체 시 속성 이전) | b63e1b1 · b13bc5a · ad7cb3f · 8fc93fe(AI) · c681161(AI) · 8df7c57(AI) | UI/AI |
| zone-style — margin/padding | 7e15b84 · 227b603 · dbe9a1b · 91a21fb(AI) · 89c4724(AI) · 8950148(AI) · d13373e(AI) | UI/AI |
| zone-style — border·corner-radius (면별 분리, 동일 모양 2표기) | c0ca652 · 160f5f8(AI) · dbe9a1b · 3c02011(AI) | UI/AI |
| 래퍼 컨테이너 추가 (fixed-size 이전) | c0ca652 | UI |
| Phone devicelayout — 평면 배치, auto-generated 재생성 | c681161(AI) · 8950148(AI) | AI |
| paramctrl 존 표시/제거 | b13bc5a · 35b2505 · 57e556a | UI |

## 데이터소스

| 조작 | 근거 커밋 | 유형 |
|---|---|---|
| 사용자 지정 SQL 편집 (relation, 내부 id 해시 재생성) | e6a02cc · 7f4e665 · c7baad9 | UI |
| 추출 해제/재생성 — zip 구조 변화, `<extract @enabled>`, .hyper 경로 규칙 | 7f4e665 · c7baad9 | UI |
| 폴더 생성·필드 이동 (folders-common/folder-item) | b13bc5a · 7f4e665 · 57e556a · b6256cf · 23690bc(AI) | UI/AI |
| 데이터소스 색상 팔레트 (style-rule mark/encoding color map) | 23690bc(AI) · 57e556a · b6256cf · b67ed82 | UI/AI |

## 서식

| 조작 | 근거 커밋 | 유형 |
|---|---|---|
| 기본값은 XML에 안 적힌다 — 글꼴 명시는 누락 채우기 | 75da540(AI) | AI |
| 글꼴 일괄 변경 (format/run 4표면, auto-generated 제외 판단) | 8950148(AI) · d13373e(AI) | AI |
| style-rule label/header/cell 서식 (font·color·text-format·border) | c6bdf15 · a248ae3 · 146f488 · 9cac21f | UI |

---

## `?` 신호 (대응 불확실 — 레시피 승격 전 재관찰 필요)

| 커밋 | 내용 |
|---|---|
| 7e15b84 | 시트 복제 신호를 XML로 역추론 (사용자 미기억) |
| 35b2505 | `mark-labels-show`/`mark-labels-cull` 추가 |
| 5916221 | `style-rule[@element='axis']` @scope='cols' (rows 선례에서 유추) |
| 6958d25 | 도구 설명 run @bold 제거 · customized-label 추가 |
| b6256cf | 글꼴 명시 33곳 소실 — 사용자 해제 vs Tableau 제거 판별 불가 |

## 미관찰 구멍 (현 시점 확인분)

- 집합(`<group>`) · 집합 동작 — T3 직결
- 필터 동작·URL 동작·시트 이동 동작 (하이라이트·매개변수 외)
- 페이지 선반 · 참조선/추세선 · 계층(hierarchy) 생성 · 그룹 필드 · 스토리
- 여백 4면 개별 지정 (UI-XML매핑.md 미관찰란과 동일)

**전체 기능 리스트 대조는 레시피 전량 변환 후** — 미관찰 항목을 표시하면
소유자가 관찰 모드로 공급한다 (08 §7).
