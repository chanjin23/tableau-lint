# 레시피 20 — 빈 워크북 만들기 (워크북 골격)

| 항목 | 값 |
|---|---|
| 판정 표면 | T1 |
| UI 경로 | Tableau 실행 > 새 통합 문서 > (아무것도 안 함) > 저장 |
| 근거 | 2026-08-10 관찰 `관찰_A_빈워크북.twb` (소유자 조작, UI) |
| Tableau | 2026.1.1 (20261.26.0410.0924) |

**AI가 `.twb`를 빈 손에서 만들 때 첫 번째로 필요한 레시피다.** 이 골격이 틀리면
데이터도 뷰도 못 올린다. 실제로 이 레시피 없이 손저작한 파일이 로드 거부됐다
(아래 §함정 참조).

## 전체 골격 — 순서가 곧 문법이다

```xml
<?xml version='1.0' encoding='utf-8' ?>

<!-- build 20261.26.0410.0924                               -->
<workbook original-version='18.1' source-build='2026.1.1 (20261.26.0410.0924)'
          source-platform='win' version='18.1'
          xmlns:user='http://www.tableausoftware.com/xml/user'>
  <document-format-change-manifest>
    <AnimationOnByDefault />
    <MarkAnimation />
    <SheetIdentifierTracking />
    <WindowsPersistSimpleIdentifiers />
  </document-format-change-manifest>
  <preferences>
    <preference name='ui.encoding.shelf.height' value='24' />
    <preference name='ui.shelf.height' value='26' />
  </preferences>
  <datasources />
  <worksheets>
    <worksheet name='시트 1'>
      <table>
        <view>
          <datasources />
          <aggregation value='true' />
        </view>
        <style />
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Automatic' />
          </pane>
        </panes>
        <rows />
        <cols />
      </table>
      <simple-id uuid='{FBCD0C77-1ED1-4070-B59A-49002B1E7BAC}' />
    </worksheet>
  </worksheets>
  <windows saved-dpi-scale-factor='1.25'>
    <window class='worksheet' maximized='true' name='시트 1'>
      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='marks' />
          </strip>
        </edge>
        <edge name='top'>
          <strip size='2147483647'><card type='columns' /></strip>
          <strip size='2147483647'><card type='rows' /></strip>
          <strip size='30'><card type='title' /></strip>
        </edge>
      </cards>
      <simple-id uuid='{42E3E626-5367-40F5-83C2-FF11DA90149A}' />
    </window>
  </windows>
  <thumbnails>
    <thumbnail height='192' name='시트 1' width='192'>…base64 PNG…</thumbnail>
  </thumbnails>
</workbook>
```

## 매니페스트 — **최소 4항목**이다

| 항목 | 빈 워크북에 |
|---|---|
| `AnimationOnByDefault` | ✅ |
| `MarkAnimation` | ✅ |
| `SheetIdentifierTracking` | ✅ **`worksheet/simple-id`의 게이트** |
| `WindowsPersistSimpleIdentifiers` | ✅ (`window/simple-id` 게이트로 추정) |

**매니페스트는 쓰는 기능만큼만 늘어난다.** 데이터 원본을 붙이면 3항목이 더 붙는다
(레시피 21). 실파일에서 22항목짜리를 봤다고 그걸 그대로 복사하면 **쓰지도 않는
기능을 선언한 파일**이 된다 — 열리기는 하지만 정본이 아니다.

## 속성 규칙

| 속성 | 값 | 비고 |
|---|---|---|
| `version` / `original-version` | `18.1` | **최소 호환 버전.** 실제 버전이 아니다 |
| `source-build` | `2026.1.1 (20261.26.0410.0924)` | **여기가 진짜 버전 키다** |
| `source-platform` | `win` | |
| `xmlns:user` | `http://www.tableausoftware.com/xml/user` | 루트에 선언 |
| 첫 줄 주석 | `<!-- build 20261.26.0410.0924 -->` | 공백 패딩 포함. 없어도 열린다(미검증) |

## 불변 조건

1. **자식 순서 고정** — `document-format-change-manifest` → `preferences` →
   `datasources` → `worksheets` → `windows` → `thumbnails`
2. **워크시트 1개 = 3곳** — `worksheets/worksheet@name` · `windows/window@name` ·
   `thumbnails/thumbnail@name`. 이름은 셋이 같다
3. **`simple-id`는 worksheet와 window 둘 다** 갖는다. `</table>` 다음, `</cards>` 다음
4. `uuid`는 중괄호 포함 대문자 GUID. 파일 안 유일하면 된다(값 자체는 노이즈)
5. 데이터 원본이 없어도 `<datasources />` **빈 요소는 있어야 한다**

## 함정 — 이걸로 실제로 로드 거부됐다 (2026-08-10)

`<document-format-change-manifest>` 블록을 통째로 빠뜨리고 `<simple-id>`를 쓰면
Tableau가 로드를 거부한다 (오류 코드 `D2E8DA72`):

```
Error(98,66): no declaration found for element 'simple-id'
Error(98,66): attribute 'uuid' is not declared for element 'simple-id'
Error(99,17): element 'simple-id' is not allowed for content model
              '(((layout-options?)|(repository-location?)),table)'
```

분리 실험 실측: `SheetIdentifierTracking`만 빼면 **거부**,
`WindowsPersistSimpleIdentifiers`만 빼면 **열린다**. `worksheet/simple-id`의
게이트는 SIT 단독이다.

## 노이즈 (diff에서 무시)

`saved-dpi-scale-factor` · `source-height` · `title` strip의 `size`
(30 → 29 → 28로 저장할 때마다 흔들린다) · `thumbnail` base64 · `uuid` 값

## 재저장 검증 · twb-lint

관찰 원본 그대로면 정규화 없음. `twb_validate` → `passed=true`, findings 0.
twb-lint: `manifest.gates`(⑥-b)가 `simple-id` ↔ `SheetIdentifierTracking`을 잡는다.
