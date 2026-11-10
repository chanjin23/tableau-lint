# twb-lint

**Tableau 파일(`.twb` / `.twbx`)을 Tableau 없이 미리 검사해 주는 도구입니다.**

AI한테 Tableau 워크북을 만들거나 고치라고 시키면, 겉보기엔 멀쩡한데 막상 열어 보면
깨져 있는 경우가 정말 많습니다. twb-lint는 그런 파일을 **Tableau를 켜기 전에** 걸러 냅니다.
그리고 애초에 틀리지 않도록 "이 기능은 XML을 이렇게 쓰면 된다"는 **정답 예시(레시피)**도 함께 제공합니다.

---

## 어떤 문제를 잡나요?

Tableau 파일이 깨지는 방식은 크게 네 가지입니다. 아래로 갈수록 눈치채기 어렵습니다.

| | 이런 일이 생겨요 | twb-lint의 대응 |
|---|---|---|
| 1 | 파일이 아예 안 열린다 | ❌ **오류(ERROR)** — 막는다 |
| 2 | 열리긴 하는데 필터나 정렬이 슬쩍 사라졌다 → 숫자가 틀린다 | ⚠️ 경고(WARNING) |
| 3 | 열리는데 화면에 데이터가 하나도 안 나온다 | ⚠️ 경고 |
| 4 | 열리는데 필드에 빨간 느낌표가 떠 있다 | ⚠️ 경고 |

재미있는 점은, **앞의 문제를 고쳐야 다음 문제가 보인다**는 겁니다.
파일이 열리게 고치고 나서야 "어? 필터가 없네?"를 알게 되는 식이죠.

Tableau가 제공하는 공식 스키마(XSD)는 문법만 봅니다. 위 네 가지는 문법은 맞는데
**의미가 틀린** 경우라서 스키마로는 못 잡습니다. 그 빈틈을 메우는 게 twb-lint입니다.

> 💡 **꼭 기억해 주세요.** 결과가 `passed=true`여도 "완벽하다"는 뜻은 아닙니다.
> "파일은 열린다"는 뜻일 뿐이에요. 2~4번은 경고로만 알려 주니 **경고 목록도 꼭 읽어 보세요.**

---

## 지금 어디까지 왔나요?

- 검사 규칙 **17개**가 돌아갑니다
- 잘 열리는 걸 확인한 회사 워크북 61개에서 **잘못된 오류를 하나도 내지 않습니다**
- 새 규칙을 넣을 때마다 실파일 1,544개 전체로 다시 확인합니다
- 일부러 망가뜨린 파일 **27종을 전부** 잡아냅니다
- 기능별 정답 예시(레시피)가 **27개** 있습니다
- 대상 버전: **Tableau 2026.1**, 인터넷 없이 로컬에서 동작합니다

> 오류(ERROR)는 **확실할 때만** 냅니다. 멀쩡한 파일을 한 번이라도 막으면
> 아무도 이 도구를 믿지 않을 테니까요.

---

## 설치

```bash
uv sync
```

`uv`를 쓸 수 없는 PC라면 이렇게 하면 됩니다.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
```

---

## 사용법

### 파일 검사하기

```bash
twb-lint validate 내워크북.twbx
```

### Claude Code에 연결하기 (MCP)

```bash
claude mcp add --scope user twb-lint -- /path/to/tableau-lint/.venv/Scripts/twb-lint-mcp.exe
```

venv 안의 실행 파일을 바로 등록하세요. `uv run`으로 등록하면 켤 때마다 17초쯤 걸립니다.

연결하면 Claude가 다음 도구를 쓸 수 있습니다.

| 도구 | 언제 쓰나요 |
|---|---|
| `twb_unpack` | `.twbx`(압축 파일)를 풀 때 — 항상 이것부터 |
| `twb_inspect` | 파일 구조만 훑어볼 때 (필드, 시트 목록 등) |
| `twb_recipe` | XML을 쓰기 **전에** 정답 예시를 찾아볼 때 |
| `twb_validate` | 다 만든 뒤 검사할 때 — 통과 못 하면 내보내지 않아요 |
| `twb_recipe_request` | 찾는 레시피가 없거나, 레시피대로 했는데도 실패했을 때 "이거 필요해요" 하고 남겨 두는 건의함 |

### 건의함 확인하기

```bash
twb-lint recipe-requests                              # 아직 처리 안 된 건의 (많이 요청된 순)
twb-lint recipe-requests --all                        # 처리된 것까지 전부
twb-lint recipe-requests --resolve <ID> --recipe 14   # 처리 완료 표시
```

건의함은 내 PC에만 저장됩니다(`.twb-lint/recipe-requests.jsonl`, git에 올라가지 않아요).
워크북 내용이나 데이터 값은 받지 않으니 안심하셔도 됩니다.

---

## 워크북을 만들 때는 이 순서로

검사는 다 만든 뒤에 하는 일입니다. 처음부터 틀리지 않으려면 이 순서를 따라 주세요.

1. [`docs/recipes/README.md`](./docs/recipes/README.md)에서 하려는 작업의 레시피를 찾습니다
2. 레시피대로 XML을 씁니다
3. `twb_validate`로 검사하고, 경고까지 읽어 봅니다
4. 마지막으로 Tableau에서 한 번 열어 봅니다

**레시피에 없는 작업은 추측해서 쓰지 마세요.** 대신 건의함에 남겨 주세요.
실제 Tableau에서 확인한 뒤 레시피로 추가합니다.

---

## 개발에 참여한다면

Claude Code용 명령 세 가지로 작업합니다.

| 명령 | 하는 일 |
|---|---|
| `/defect-loop` | Tableau에서 깨진 파일 하나를 받아 원인을 찾고, **새 검사 규칙**으로 만듭니다 |
| `/author-loop` | 레시피대로 워크북을 만들고, 검사가 통과할 때까지 고칩니다 |
| `/impl-loop` | 계획서에 있는 다음 작업 하나를 구현합니다 |

커밋하기 전에 아래 두 가지는 꼭 통과해야 합니다.

```bash
.venv/Scripts/python -m pytest -q       # 446 passed, 14 skipped
.venv/Scripts/python -m ruff check .    # All checks passed
```

> ⚠️ 테스트에 쓰는 실제 워크북(골든셋)은 **저장소에 없습니다.** 회사 재무 데이터라서요.
> 실파일 테스트까지 돌리려면 `TWB_LINT_GOLDEN_NORMAL` 환경변수에 경로를 걸어 주세요
> (그러면 460 passed가 나옵니다).

---

## 더 읽어 보기

| 문서 | 무엇이 있나요 |
|---|---|
| [`docs/09-usage.md`](./docs/09-usage.md) | 도구 사용법 자세히, 한계, 규칙 추가하는 법 |
| [`docs/recipes/README.md`](./docs/recipes/README.md) | 레시피 목록 (작업 → 레시피 찾기) |
| [`docs/01-problem-definition.md`](./docs/01-problem-definition.md) | 이 도구가 무엇을, 왜 판정하는지 |
| [`docs/05-xsd-spike.md`](./docs/05-xsd-spike.md) | 규칙마다 실제로 확인한 기록 (오류 문구, 근거 수치) |
| [`docs/impl-progress.md`](./docs/impl-progress.md) | 지금까지의 진행 기록 |
| [`docs/tableau-ai-sor.md`](./docs/tableau-ai-sor.md) | 전체 문서 안내 |
