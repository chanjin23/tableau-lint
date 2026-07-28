# Tableau 저작 AI — SOR 인덱스

> **이 디렉토리가 System of Record (SOR)다.** 문제정의·스펙의 단일 권위본. 세션 플랜 파일(`~/.claude/plans/compiled-shimmying-gem.md`)은 임시 사본 → 상충 시 **여기 문서 우선**.

## 문서

| # | 문서 | 상태 |
|---|---|---|
| 01 | [문제정의 (Problem Definition)](./01-problem-definition.md) | ✅ 확정 v1.1 |
| 02 | [스펙 (Specification)](./02-specification.md) | ✅ 확정 v1.1 |
| 03 | [설계 (Design)](./03-design.md) | ✅ 확정 v1.1 |
| 04 | [스캐폴딩 (Scaffolding)](./04-scaffolding.md) | ✅ 완료 |
| 05 | [XSD 스파이크 실측 (Spike Report)](./05-xsd-spike.md) | ✅ 완료 |
| 06 | [규칙 후보 인벤토리 (Rule Candidates)](./06-rule-candidates.md) | 🔄 living |

## 진행 순서

① 문제정의 ✅ → ② 스펙 ✅ → ③ 설계 ✅ → ④ 스캐폴딩 ✅ → ⑤ 스파이크 ✅ → ⑥ **구현 MVP (다음)**

**05 스파이크가 01·02·03을 v1.1로 개정시켰다.** 실측이 문서를 고친 것이므로
05·06을 근거 문서로 함께 본다 (01 §7.1·§8.1, 02 S1-6·S4 AC7·S7, 03 D0.1·D3·D3.5·D5·D8).

코드: 루트 `twb-lint` 패키지 (`src/twb_lint/`, `pyproject.toml`, `README.md`).

## 프로젝트 한줄 요약

로컬 `.twb/.twbx`를 에러 없이 저작·편집·쿼리하는 AI 도구. 핵심 산출물 = 공식 XSD 위에 얹는 **(B) 시맨틱 검증기**(calc 문법·참조무결성·메타↔hyper 대조) — 사용자의 느린 E2E 검증을 대체.

## 메타

- 소유자: ax3didim@gmail.com
- 최종 갱신: 2026-07-28 (01·02·03 v1.1, 05·06 신규)
- 변경 이력: 각 문서의 "문서 관리" 블록 참조.
- 대상 환경 고정: **Tableau 2026.1 · 로컬 전용** (02 S7).
