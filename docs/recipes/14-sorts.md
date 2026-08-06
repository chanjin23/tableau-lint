# 레시피 14 — 정렬 (computed-sort · manual-sort)

| 항목 | 값 |
|---|---|
| 판정 표면 | T4 |
| UI 경로 | 필드 우클릭 > 정렬 > 필드 기준 / 수동 |
| 근거 | MA_008 `b13bc5a`(UI·확인) `23690bc`(AI 수용) `146f488` `6154648`(AI) |
| Tableau | 2026.1 |

## 필드 기준 정렬 (`b13bc5a`)

```xml
<view>
  <computed-sort column='[none:accs_nm:nk]' direction='ASC' using='[min:scrn_seq:qk]' />
</view>
```

`using` = 정렬 기준 집계 인스턴스. 정렬 대상(`column`)·기준(`using`) 모두 인스턴스 표기.

## 수동 정렬 (`146f488` `6154648`)

`<manual-sort>` + dictionary bucket 목록 — bucket 순서가 표시 순서.
그래프 색 순서와 맞추는 용도 관찰 (`6154648` bucket "실적","계획").

주의 — 필터에서 멤버를 빼도 manual-sort dictionary에는 **옛 bucket이 남을 수 있다**
(`9cac21f` 달성률 bucket 잔존, 무해).

## 매니페스트

`SortTagCleanup` 항목이 manual-sort 계열 게이트다 (05 실측 쌍: `<manual-sort>` ↔
`SortTagCleanup`) — 매니페스트 없이 쓰면 로드 거부. 이 코퍼스 파일엔 이미 선언돼 있다.

## 재저장 검증

정규화 관찰 없음. twb-lint: `manifest.gates`(⑥-a) · `shelf.refs`(⑪).
