---
phase: 01-domain-model-migrations-clock-seeds
plan: 01
subsystem: data
tags: [taxonomy, enums, typescript, pydantic, json-schema]

requires: []
provides:
  - Canonical 5-block shared/taxonomy.json defining emergency types, conditions, skills, responder categories, and protocol mappings
  - Strongly typed Python StrEnum classes in backend/app/domain/enums.py
  - TypeScript type declarations and union types in apps/web/src/types/taxonomy.ts
  - Automated parity and schema validation test suite in backend/tests/test_taxonomy.py
affects: [01-02, 01-03, phase-3, phase-4, phase-6]

tech-stack:
  added: []
  patterns: [monorepo shared taxonomy single source of truth, bijective enum parity testing, TypeScript derived literal union types]

key-files:
  created:
    - shared/taxonomy.json
    - backend/app/domain/__init__.py
    - backend/app/domain/enums.py
    - apps/web/src/types/taxonomy.ts
    - backend/tests/test_taxonomy.py

key-decisions:
  - "D-21: Canonical single source of truth at monorepo root shared/taxonomy.json"
  - "D-22: Strongly typed Python StrEnum classes matching taxonomy.json backed by CI parity tests"
  - "D-23: Type-safe frontend TypeScript declarations in apps/web/src/types/taxonomy.ts"
  - "D-24: Complete 5-block taxonomy structure (emergency_types, conditions, skills 1-3, responder_categories, protocol_skill_requirements)"

patterns-established:
  - "Taxonomy parity: Automated tests assert exact 100% bijective correspondence between JSON values and Python enum members"
  - "Type-safe frontend taxonomy imports: Vite bundles shared taxonomy JSON directly for zero-latency offline protocol lookup"

requirements-completed: [DATA-01, DATA-05]

duration: 5min
completed: 2026-10-01
---

# Phase 01: Plan 01 Summary

**Defined canonical monorepo medical/dispatch taxonomy in `shared/taxonomy.json`, created strongly typed Python domain enums with parity tests, and exported frontend TypeScript declarations.**

## Performance
- **Duration:** 5 min
- **Tasks completed:** 3 of 3
- **Files modified/created:** 5 files

## Accomplishments
- Created canonical 5-block `shared/taxonomy.json` containing 8 emergency types, 9 condition codes (with red-flag indicators), 5 skills (with levels 1–3), 9 responder categories, and 7 protocol skill requirement mappings.
- Implemented Python `StrEnum` classes in `backend/app/domain/enums.py` covering roles, types, skills, readiness, statuses, priorities, and audit outcomes.
- Implemented comprehensive parity test suite in `backend/tests/test_taxonomy.py` (6/6 tests passing in 0.04s).
- Authoring type-safe TypeScript declarations in `apps/web/src/types/taxonomy.ts` and verified clean compilation (`npm --prefix apps/web run build` completed in 2.44s).

## Verification Evidence
- `python -m pytest backend/tests/test_taxonomy.py`: 6 passed in 0.04s
- `npm --prefix apps/web run build`: 1582 modules transformed, built in 2.44s with exit code 0
