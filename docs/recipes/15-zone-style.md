# 레시피 15 — 존 스타일 (여백·테두리·모서리·배경)

| 항목 | 값 |
|---|---|
| 판정 표면 | T4(대시보드 서식) |
| UI 경로 | 대시보드 > 개체 우클릭 > 서식 > 음영/여백/테두리 |
| 근거 | MA_008 `7e15b84`·`227b603`(UI·양방향 확인) `c0ca652` `dbe9a1b` `160f5f8`·`3c02011`·`91a21fb`·`89c4724`·`8950148`·`d13373e`(AI 수용) |
| Tableau | 2026.1 |

## 기본 형태

```xml
<zone …>
  <zone-style>
    <format attr='margin' value='4' />        <!-- 바깥쪽 여백. 신규 존 기본 4 -->
    <format attr='padding' value='20' />      <!-- 안쪽 여백 -->
    <format attr='border-color' value='#cbd5e1' />
    <format attr='border-style' value='solid' />  <!-- 제거 = 'none' + width 0 -->
    <format attr='border-width' value='1' />
    <format attr='background-color' value='#f8fafc' />
  </zone-style>
</zone>
```

## 면별 지정 — 균일값과 다른 표기

- 여백: `margin-left`·`margin-right`·`margin-top`·`margin-bottom` 개별 속성.
  **일괄 변경 시 면별 지정 존은 제외한다** — 비대칭이 의도다 (`91a21fb` `8950148` 제외 판단)
- 모서리: `corner-radius-top-left` 등 4면 분리. 좌우 존 2개를 한 카드처럼 보이게 하는 방식
  (`c0ca652` — 좌존은 left 2면, 우존은 right 2면만 16)
- **같은 모양의 2표기 존재** — `corner-radius=16` + `corner-radius-top-right=0` 조합을
  Tableau가 면별 지정으로 다시 쓰기도 한다 (`160f5f8`). AI는 면별 표기를 쓰는 게 안전

## 불변 조건

1. **devicelayouts(Phone) 안은 건드리지 않는다** — `auto-generated='true'` 영역은
   Tableau가 재생성한다. 고쳐도 정규화로 되돌아온다 (`8950148` `d13373e` 제외 판단)
2. 데스크톱과 Phone은 **같은 존이라도 값이 다를 수 있다** — 데스크톱 margin 0/padding 20,
   Phone margin 4/padding 0 (`160f5f8`). 복사할 땐 각 레이아웃의 대응 원본에서
3. 테두리를 컨테이너에서 자식 존으로 옮기면 컨테이너 쪽은 초기화
   (corner-radius=0·padding=0, `c0ca652`)
4. 텍스트 개체를 시트로 교체해도 `zone-style`은 유지된다 (레시피 03)

## 재저장 검증

`227b603` — margin 0↔4 양방향 관찰로 매핑 확정. AI 일괄 변경 6건 전부 수용.
존 좌표(x·y·w·h)는 레이아웃 재계산 노이즈 — **존 개수가 그대로면 좌표 변화는 무시**.
