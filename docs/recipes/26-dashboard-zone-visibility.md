# 레시피 26 — 동적 존 표시 (값에 따라 컨테이너·시트·컨트롤 보이기/숨기기)

| 항목 | 값 |
|---|---|
| 판정 표면 | T1(로드 게이트) · T3 · T4 |
| UI 경로 | 대시보드 > 컨테이너/시트/컨트롤 선택 > **값에 따라 표시**(Show/Hide) > 불리언 필드·매개변수 지정 |
| 근거 | 코퍼스 **고유 datagraph 60종 · 존 노드 332개** 전수 (`C:/dev/JW`) · 05 **F5-o**(로드 거부 `D2E8DA72`, 고침본 확인) · MA_015 `…_JWP_260903.twbx` · **2026-10-15 손저작 샘플을 소유자가 열어 동작 확인 + 무수정 재저장 diff** (`관찰_26_저장본.twb`). 등급: 열림·동작·재저장 ✅ / 값 전환 시 직렬화 `추정` |
| Tableau | 2026.1 |

레시피 25가 *값에 따라 시트의 **행**을 거르는* 필터라면, 이쪽은 *값에 따라 **존 자체**를 보이거나
숨기는* 기능이다. **컨테이너째로 갈아 끼우는 "유형 전환 UI"는 이 레시피다.**

## 한 기능이 건드리는 자리 4곳

| # | 자리 | 내용 |
|---|---|---|
| 1 | 매니페스트 | `DatagraphCoreV1` · `DatagraphNodeSingleValueFieldV1` · `DatagraphNodeDashboardZoneVisibilityV1` · `ZoneVisibilityControl` **4항목** (없으면 로드 거부 — 규칙 ⑥ ERROR) |
| 2 | 워크북 직속 `<datagraph>` | `<windows>` **다음** · `<thumbnails>` **앞**. 필드 값 → 존 가시성 그래프 |
| 3 | 대상 `zone` | **`@hidden-by-user='true'`** — 저장 시점에 숨겨진 상태인 존 (아래 ③) |
| 4 | 조건 필드 | 불리언 계산 필드 또는 불리언 매개변수 (레시피 01 · 02 · 25) |

## ① `<datagraph>` — 입력 1 → 출력 1이 한 쌍이다

```xml
<datagraph>
  <graph>
    <properties><default-execution-subgraph-guid value='G0' /></properties>
    <node-execution-subgraphs>
      <pair execution-subgraph-guid='G0' node-guid='NP' />   <!-- 노드마다 1쌍 -->
      <pair execution-subgraph-guid='G0' node-guid='NVA' />
    </node-execution-subgraphs>
    <nodes>
      <single-value-field-node fieldname='[Parameters].[매개 변수 1]'
          fieldname-input-guid='IP' node-guid='NP' value-output-guid='OP' />
      <dashboard-zone-visibility-node dashboard-identifier='{대시보드 simple-id uuid}'
          node-guid='NVA' visibility-input-guid='IVA' zone-id='7' />
    </nodes>
    <edges>
      <edge from='OP' to='IVA' />      <!-- 값 출력 guid → 가시성 입력 guid -->
    </edges>
    <pin-values />
  </graph>
</datagraph>
```

| 자리 | 규칙 (코퍼스 실측) |
|---|---|
| `single-value-field-node@fieldname` | 매개변수 `[Parameters].[이름]` **또는** 데이터 원본 계산 `[federated.…].[Calculation_…]` (2단 표기) |
| 조건 필드의 타입 | **전부 `boolean`** — 계산(dimension) 178 · 매개변수(measure) 5, 다른 타입 0건 |
| `dashboard-zone-visibility-node@dashboard-identifier` | **대상 대시보드의 `<simple-id @uuid>`** (중괄호 포함) — 332 : 0 일치 |
| `@zone-id` | 그 대시보드 안 `zone@id` |
| 입력 수 | 가시성 노드 하나에 **들어오는 edge는 정확히 1개** (332 : 0) |
| guid 3종 | `node-guid` · `*-input-guid` · `*-output-guid` — 소문자 uuid. 값 자체는 노이즈 |
| `node-execution-subgraphs` | 모든 노드가 `pair`로 한 번씩 — 서브그래프 guid는 `default-execution-subgraph-guid`와 같다 |
| 대시보드가 둘 이상 | 같은 존 id라도 `dashboard-identifier`로 갈린다 (MA_015: 두 대시보드가 `zone-id=1801` 공유) |

**동작 의미(소유자 확인됨):** 조건이 **TRUE면 보이고 FALSE면 숨긴다.** MA_015 실측 — `P_LINE/PRD`(=true)에
묶인 컨트롤은 숨김 속성 없음, `NOT P_LINE/PRD`에 묶인 컨트롤은 `hidden-by-user='true'`.

## ② 대상 존 — 무엇을 숨길 수 있나

가시성 노드 332개가 가리키는 존 종류:

| 종류 | 수 |
|---|---|
| 컨테이너 `layout-flow` (`param='horz'`) | 169 |
| 워크시트 존 | 145 |
| `paramctrl` | 10 |

## ③ `zone@hidden-by-user` — 저장 시점의 상태다

- 조건이 **현재 FALSE**라 숨겨진 존에 `hidden-by-user='true'`가 붙는다 (166건). TRUE면 없다 (158건)
- 숨겨진 **컨테이너의 자식**도 같은 속성을 갖는다 (MA_002 표본: 자식 `empty` 존 `hidden-by-user='true'`)
- datagraph가 **안 가리키는** 존에도 이 속성이 있다(732건) — 사용자가 수동으로 숨긴 존과 숨은 컨테이너의
  자식. **이 속성만으로 동적 존 표시라고 판정하지 않는다**
- 값 전환마다 바뀌는 **노이즈**로 취급한다(`@value`와 같은 성질) — 저작 시 기본값에 맞춘다
- `friendly-name`은 컨테이너에 붙는 표시용 이름 (선택)

## ④ 매니페스트 — 속성 게이트가 아니라 요소 게이트

`<datagraph>`·`single-value-field-node`·`dashboard-zone-visibility-node`가 각각 대응 항목을 요구한다
(규칙 ⑥-b). **넷을 같이 선언해야 열린다 — 어느 하나가 `datagraph` 단독 게이트인지는 미분리** (05 F5-o).
`ZoneVisibilityControl`은 `zone@hidden-by-user`를 게이팅하는 것으로 추정(15:0 상관, 속성 게이트 미등재).

## 패턴 — 매개변수 스위치로 컨테이너 2개 갈아 끼우기 (MA_015 형태)

| 대상 | 입력 필드 | 수식 |
|---|---|---|
| 컨테이너 A (스위치 TRUE일 때) | **불리언 매개변수 자체** `[Parameters].[매개 변수 N]` | — |
| 컨테이너 B (스위치 FALSE일 때) | 반전 계산 `C_NOT_…` (`datatype=boolean` · `role=dimension`) | `NOT [Parameters].[매개 변수 N]` |

값에 표시 이름을 붙이는 방법은 레시피 25. 두 컨테이너는 **같은 부모 flow 안에 나란히** 놓는다 —
숨겨진 쪽은 공간을 차지하지 않는 것으로 추정(flow 레이아웃 거동, 미검증).

## 불변 조건

1. **`zone-id` 실존** — 대상 대시보드에 그 id의 존이 있어야 한다. 코퍼스에 **없는 경우 8건**이 있다
   (잔재) — 파일은 열리므로 WARNING 수준의 문제일 것이다(미실측)
2. **반전 계산은 데이터 원본 `<column>`에 있어야** 한다(레시피 01). 대시보드 `datasource-dependencies`에는
   **복제하지 않는다** (MA_015 실측: 대시보드 의존성에 `Parameters`만 있고 반전 계산은 없다)
3. 조건 필드는 **불리언만.** 문자열·숫자로 쓴 표본은 코퍼스에 없다 — 지어내지 않는다 ★
4. 같은 존에 가시성 노드가 **둘 이상** 걸리는 경우는 이 레시피 밖 (미분석)

## 저작 검증 (2026-10-15) — **린트 수준까지만**

`<datagraph>` 샘플(불리언 매개변수 1 · 반전 계산 1 · 컨테이너 2[시트 1씩] · 컨트롤 1)을 손저작:
`twb_validate` → **passed · findings 0** (1회차).

| 음성 대조 | 결과 |
|---|---|
| 매니페스트 `DatagraphCoreV1` 삭제 | `manifest.gates` **ERROR** ✅ |
| `zone-id`를 존재하지 않는 id로 | **findings 0 — 못 잡는다** (datagraph 참조 검사 규칙 없음) |

**소유자 확인 (2026-10-15): Tableau에서 열렸고, `P_VIEW` 전환에 따라 컨테이너가 의도대로
보이고 숨겨졌다.** → "TRUE면 보이고 FALSE면 숨긴다"와 샘플의 `datagraph` 형태는 **열기·동작
수준에서 확인됨.** 단 저장 후 diff는 아직 없다 — 정규화·`hidden-by-user` 토글 여부는 아래 ★가 맞다.

**왜 컨테이너 A는 매개변수 직결, B는 반전 계산인가:** 이 기능은 조건이 **TRUE일 때만** 보이게
한다. "FALSE일 때 보이기"는 직접 못 하므로 `NOT [매개변수]` 계산을 입력으로 쓴다.

## 재저장 diff (2026-10-15, 소유자: 열기 → 아무것도 안 하고 다른 이름 저장) — 구조 기준 239줄

저장본도 `twb_validate` **passed · findings 0**.

**✅ 수용 — 내용 그대로 살아남았다 (신호)**

| 항목 | 결과 |
|---|---|
| `<datagraph>` 노드·edge·필드명·`dashboard-identifier`·`zone-id` | **내용 동일.** `pair`·`edge`의 **나열 순서만** 재배열 (순서는 의미 없음 — 노이즈) |
| `hidden-by-user` (컨테이너 9 + 자식 시트 존 10) | **그대로 유지** — 숨김 컨테이너의 자식에도 붙이는 형태가 수용됐다 |
| `friendly-name` · `fieldname` 2단 표기 · 반전 계산 · 최소 골격(`devicelayouts` 없음) | 수용 (V1 일부 해소 — `devicelayouts` 없이 열렸다) |

**정규화 — Tableau가 고쳐 쓴 것 (손저작 시 미리 맞추면 diff가 준다)**

| 항목 | 변화 |
|---|---|
| 매니페스트 | `+SetMembershipControl` `+ZoneFriendlyName` 자동 추가 |
| **`friendly-name`의 매니페스트** | 코퍼스 **682 : 0 / 297 : 0** — `friendly-name` 속성이 있으면 `ZoneFriendlyName`이 **항상** 있다. 그런데 **이 항목 없이 쓴 파일이 열렸다.** → **로드 게이트가 아니다** (소유자 열림 확인). 상관은 *Tableau가 저장 시 붙이는 것*으로 읽는다. ERROR 게이트로 만들면 거짓양성 |
| **데이터 원본 안 `datasource-dependencies`** | 반전 계산이 매개변수를 참조하므로 `<datasource>` 안 `<semantic-values>` 뒤·`<object-graph>` 앞에 `<datasource-dependencies datasource='Parameters'>`(P_VIEW 사본, **`members` 제외**)가 생겼다 — 레시피 25 불변 5 |
| **대시보드 의존성의 매개변수 사본** | `<members>`가 **붙었다** (워크시트 사본은 `members` 제외 — 대시보드 쪽은 포함) |
| 대시보드 | `+<style />` · `datasources`에서 쓰지 않는 `federated` 항목 제거(Parameters만 남음) |
| 존 | `show-title='true'`(기본값) 제거 · paramctrl `w`/`h`·배경색 · `layout-cache` 재계산 — 노이즈 |
| 시트·창·썸네일 | 워크시트 **이름순 재정렬**(`Target…` < `공정…`) · 대시보드 창이 앞으로 · **대시보드에 놓인 숨김 시트의 썸네일 삭제** |
| 레시피 21 | 문자열 컬럼 `metadata-record` 자식 순서가 `scale·width·**contains-null·collation**·object-id`로 바뀜 (`collation`이 `contains-null` 뒤) |

⚠️ **값을 바꾸지 않고 저장**했으므로 **전환 시 `hidden-by-user` 토글**과 자식 전파는 아직 미관찰(V3).

## ★ 미관찰 — 소유자 관찰 시나리오

한 저장 = 한 조작.

| # | 조작 | 알고 싶은 것 |
|---|---|---|
| ~~V1~~ | ~~대시보드 최소 골격~~ | ✅ **일부 해소** — `devicelayouts` 없이 열리고 재저장됐다. 다만 Phone 레이아웃 자동 생성은 안 일어났다 |
| V2 | 컨테이너 선택 > **값에 따라 표시** > 불리언 매개변수 지정, 저장 | datagraph 직렬화 원형 · 매니페스트 4항목이 **그 한 조작으로** 붙는가 · `hidden-by-user` 위치 |
| V3 | 같은 컨테이너의 조건 값을 반대로 전환 후 저장 | `hidden-by-user`가 **자식까지** 토글되는가 (노이즈 판정) |
| V4 | 컨트롤(paramctrl)·시트 존에도 같은 설정 | 대상 종류별 직렬화 차이 |
| V5 | 데이터 원본 계산 필드로 지정(매개변수 아님) | `fieldname` 표기 — 대시보드 의존성에 계산이 복제되는가 |
| V6 | 컨테이너를 **삭제**하고 저장 | 가시성 노드·edge가 같이 정리되는가 (`zone-id` 잔재 8건의 원인) |

## twb-lint 연계

`manifest.gates`(⑥-b) — 매니페스트 4항목 ERROR. `named.refs`(③) — 시트 존 4자 일치.
**없는 것:** `zone-id` 실존 · `dashboard-identifier` ↔ `simple-id` 일치 · `fieldname` 실존 · edge guid 배선 —
관찰(V1~V6) 전이라 규칙화하지 않는다(ERROR는 확신할 때만).
