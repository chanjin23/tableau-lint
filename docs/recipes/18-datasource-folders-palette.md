# 레시피 18 — 필드 폴더 · 데이터소스 색상 팔레트

| 항목 | 값 |
|---|---|
| 판정 표면 | T2(정리)·T4(색) |
| UI 경로 | 데이터 패널 > 필드 드래그로 폴더 이동 / 마크 카드 > 색상 편집 |
| 근거 | MA_008 `b13bc5a` `7f4e665` `57e556a` `b6256cf` `23690bc`(AI 수용) `b67ed82` |
| Tableau | 2026.1 |

## 폴더 (`b13bc5a` `57e556a` `b6256cf`)

```xml
<datasource>
  <folders-common>
    <folder name='01_공통'>
      <folder-item name='[Calculation_…]' type='field' />
    </folder>
  </folders-common>
</datasource>
```

- 폴더 신설 = `+<folder @name>` (빈 요소 가능, `b6256cf` — 비어 있다가 나중에 채움)
- 필드 이동 = 대상 폴더에 `+<folder-item>` (원 폴더에서 제거)
- `folder-item@name`은 필드의 **내부 name** (caption 아님)

## 색상 팔레트 — 데이터소스 수준이 정본 (`23690bc` `b6256cf` `b67ed82`)

```xml
<datasource>
  <style>
    <style-rule element='mark'>
      <encoding attr='color' field='[none:Calculation_7200000000000003:nk]' type='palette'>
        <map to='#002c63'><bucket>&quot;실적&quot;</bucket></map>
        <map to='#a0cbe8'><bucket>&quot;계획&quot;</bucket></map>
      </encoding>
    </style-rule>
  </style>
</datasource>
```

- 값→색 매핑은 여기 한 곳. 시트들은 인코딩 참조만 하고 **상속**받는다 (레시피 10·13)
- 색 변경 = `map@to`만 교체 (`b6256cf` 6건)
- 필드별 `encoding` 블록 추가로 새 필드 팔레트 정의 (`b67ed82` 상수 차원 검정)

## 재저장 검증

정규화 관찰 없음 (AI 저작 `23690bc` 수용). folder-item 정렬 규칙 미관찰 —
데이터소스 column처럼 정렬될 가능성 있음(`추정`), diff에 위치 이동 나오면 기록할 것.
