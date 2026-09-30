---
phase: 1
slug: domain-model-migrations-clock-seeds
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-10-01
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio against PostgreSQL 16 |
| **Config file** | `backend/pyproject.toml` |
| **Quick run command** | `docker compose exec -T api pytest backend/tests/test_clock.py backend/tests/test_taxonomy.py` |
| **Full suite command** | `docker compose exec -T api pytest backend/tests/` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick test suite for the modified module
- **After every plan wave:** Run full test suite (`pytest backend/tests/`)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | DATA-01 | — | `shared/taxonomy.json` adheres to strict schema | unit | `pytest backend/tests/test_taxonomy.py` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | DATA-01 | — | Python `StrEnum` classes match `taxonomy.json` exactly | unit | `pytest backend/tests/test_taxonomy.py` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | DATA-01 | — | TypeScript types compile cleanly from `taxonomy.json` | build | `npm --prefix apps/web run build` | ✅ | ⬜ pending |
| 01-02-01 | 02 | 2 | DATA-01 | — | All 11 SQLAlchemy models declared with constraints | unit | `pytest backend/tests/test_models.py` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 2 | DATA-02 | T-01-01 | Duplicate concurrent offers blocked by DB index | integration | `pytest backend/tests/test_constraints.py` | ❌ W0 | ⬜ pending |
| 01-02-03 | 02 | 2 | DATA-03 | T-01-02 | `UPDATE` and `DELETE` on events/audit raise trigger error | integration | `pytest backend/tests/test_constraints.py` | ❌ W0 | ⬜ pending |
| 01-02-04 | 02 | 2 | DATA-01 | — | Alembic migrations support full up/down/up cycle | migration | `pytest backend/tests/test_migrations.py` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 3 | DATA-04 | T-01-03 | Clock resolves virtual offset from `demo_sessions` | unit | `pytest backend/tests/test_clock.py` | ❌ W0 | ⬜ pending |
| 01-03-02 | 03 | 3 | DATA-04 | T-01-03 | AST scanner confirms zero direct `datetime.now()` calls | static | `pytest backend/tests/test_clock.py -k test_no_direct_datetime_now` | ❌ W0 | ⬜ pending |
| 01-03-03 | 03 | 3 | DATA-05 | — | `seed.py` provisions Appendix B cast idempotently | integration | `pytest backend/tests/test_seed.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_taxonomy.py` — taxonomy schema and enum parity tests
- [ ] `backend/tests/test_models.py` — model schema declaration and relation tests
- [ ] `backend/tests/test_constraints.py` — partial indexes and append-only trigger tests
- [ ] `backend/tests/test_migrations.py` — Alembic up/down reversibility tests
- [ ] `backend/tests/test_clock.py` — virtual offset resolution and AST `datetime.now()` ban
- [ ] `backend/tests/test_seed.py` — seed idempotency and coordinate calculation tests
- [ ] `backend/requirements.txt` update — `alembic>=1.14.0`, `argon2-cffi>=23.1.0`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PostgreSQL table catalog inspection | DATA-01 | Physical validation of database schema tables and triggers | Inspect table list and triggers using `\d` and `\d+ emergency_events` in `psql` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** verified 2026-10-01
