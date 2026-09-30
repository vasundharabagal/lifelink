# Architecture Research

**Domain:** Community First-Aid & Emergency Dispatcher (SDG 3, Good Health & Well-being)  
**Researched:** 2026-09-30  
**Confidence:** HIGH (Derived strictly from canonical `docs/LIFELINK_MASTER_SPEC.md`)

## Standard Architecture

### System Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                              │
├────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────┐         ┌──────────────────────────────┐  │
│  │ React SPA (Citizen /    │         │ Demo Director & Authority    │  │
│  │ Responder / Ambulance)  │         │ Console (Split View)         │  │
│  └────────────┬────────────┘         └──────────────┬───────────────┘  │
│               │                                     │                  │
│               │ HTTP Polling (2s/5s)                │                  │
│               v                                     v                  │
├────────────────────────────────────────────────────────────────────────┤
│                        SERVERLESS API LAYER                            │
├────────────────────────────────────────────────────────────────────────┤
│  FastAPI Application (/api/v1/*) via api/index.py                     │
│  ┌────────────────────┐   ┌────────────────────┐   ┌────────────────┐ │
│  │ Auth & RBAC        │   │ Central Authz      │   │ Error & Audit  │ │
│  │ (argon2id / JWT)   │   │ (services/authz.py)│   │ Middleware     │ │
│  └─────────┬──────────┘   └─────────┬──────────┘   └───────┬────────┘ │
├────────────┼────────────────────────┼──────────────────────┼──────────┤
│            v                        v                      v          │
│  ┌────────────────────┐   ┌────────────────────┐   ┌────────────────┐ │
│  │ Triage Engine      │   │ Orchestration      │   │ State Machine  │ │
│  │ - Rules Engine     │   │ - Eligibility (6.3)│   │ - Lifecycle    │ │
│  │ - Protocol Map     │   │ - Scoring (6.4)    │   │ - Volunteer    │ │
│  │ - Sanitizer/LLM    │   │ - Explainability   │   │ - Ambulance    │ │
│  └────────────────────┘   │ - Lazy advance()   │   └────────────────┘ │
│                           └────────────────────┘                      │
├────────────────────────────────────────────────────────────────────────┤
│                        PERSISTENCE LAYER                               │
├────────────────────────────────────────────────────────────────────────┤
│  PostgreSQL (Neon / Supabase Managed Instance)                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ 11 Tables: users, responder_profiles, responder_skills,           │  │
│  │ responder_credentials, ambulance_units, medical_profiles,         │  │
│  │ emergencies, emergency_events, dispatch_offers, audit_logs,       │  │
│  │ demo_sessions                                                    │  │
│  │ Guaranteed by: FOR UPDATE Row Locks, Partial Unique Indexes,     │  │
│  │ Append-Only Triggers, Check Constraints                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| `api/v1/` Routers | Thin HTTP request termination and response serialization | FastAPI APIRouter handlers invoking domain services |
| `services/authz.py` | Central object-level access control (preventing IDOR) | Pure decision functions checking user role, ownership, and demo session scope |
| `triage/rules.py` | Deterministic priority, red-flag detection, protocol assignment | Pure table-driven rules engine versioned in `RULES_VERSION` |
| `triage/llm_adapter.py` | Tier 2 closed-enum NLP feature extraction | Pluggable client (fake provider for tests) with 4 s timeout and escalate-only merge |
| `orchestration/engine.py` | Hard eligibility filtering and multi-factor ranking | Pure pipeline returning ordered candidate lists and rejection audit data |
| `domain/state_machine.py` | Top-level emergency and dual-track status transitions | Pure state transition functions writing immutable `emergency_events` |
| `services/emergencies.py` | Transactional coordination, idempotency, deduplication | Database transactions wrapping state transitions, event writes, and dispatch plans |
| `services/offers.py` | Candidate offer lifecycle and atomic status updates | Conditional SQL updates (`WHERE status='OFFERED' AND expires_at > now`) |
| `core/clock.py` | Injectable time reference | Provides current UTC time with optional demo session offset |

## Recommended Project Structure

```
/
├── apps/
│   └── web/                     # Vite + React + TS + Tailwind SPA
│       ├── src/
│       │   ├── app/             # Application entry, router, root providers
│       │   ├── routes/          # Page route components
│       │   ├── features/        # Feature domains (citizen, responder, ambulance, authority, demo)
│       │   ├── components/      # Shared accessible UI components (SosButton, EmergencyMap, etc.)
│       │   ├── lib/             # API client, polling hook, date utilities
│       │   └── protocols/       # Copied/imported shared protocols for offline rendering
│       └── package.json
├── api/
│   └── index.py                 # Vercel serverless function entry exporting FastAPI app
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application bootstrap, middleware, routers
│   │   ├── core/                # Config, DB engine, security, clock, error envelopes
│   │   ├── domain/              # Enums, skills, protocols, state machine pure logic
│   │   ├── triage/              # Sanitizer, rule extractor, LLM adapter, golden eval
│   │   ├── orchestration/       # Eligibility filters, scoring, explanation, ETA maths
│   │   ├── services/            # Transactional business services (auth, emergencies, offers, demo)
│   │   ├── models/              # SQLAlchemy 2.0 ORM models for the 11 tables
│   │   ├── schemas/             # Pydantic v2 strict request/response DTOs
│   │   └── api/v1/              # Versioned API endpoints
│   ├── alembic/                 # Database migration scripts
│   ├── tests/                   # Unit, integration, concurrency, golden triage, and authz suites
│   └── requirements.txt
├── shared/
│   ├── protocols/               # JSON files: single source of truth for first-aid protocols
│   └── taxonomy.json            # JSON file: emergency types, conditions, and skill taxonomy
├── e2e/                         # Playwright end-to-end tests (19-step scenario)
├── docs/                        # Architecture specs, ADRs, AI eval report, verification evidence
├── docker-compose.yml           # Local PostgreSQL container and runner script
└── vercel.json                  # Routing rewrites, CSP, and security headers
```

## Architectural Patterns

### Pattern 1: Lazy Deterministic Evaluation (`advance()`)

**What:** Timed state changes (e.g., offer expiration after 30 seconds) are evaluated on-demand during client polling rather than by a background cron worker.  
**When to use:** In serverless environments where persistent background daemons cannot run reliably.  
**Trade-offs:** If all clients close their browsers, state evaluation pauses until the next request; perfectly acceptable for active emergency sessions where clients poll every 2–5 seconds.

```python
def advance(db: Session, emergency_id: UUID, clock: Clock) -> Emergency:
    # Cheap unindexed/indexed check before taking lock
    now = clock.now()
    with db.begin_nested():
        emergency = db.query(Emergency).filter_by(id=emergency_id).with_for_update().one()
        for track in [emergency.community_track, emergency.professional_track]:
            expire_overdue_offers(emergency, track, now)
            if track.needs_next_offer():
                create_next_offer_from_plan(emergency, track, now)
        emergency.status = derive_top_level_status(emergency)
    return emergency
```

### Pattern 2: Escalate-Only Safety Invariant

**What:** The AI triage tier is permitted to discover conditions and raise incident priority, but is mathematically forbidden from reducing priority or stripping detected red flags.  
**When to use:** Any safety-critical healthcare or emergency AI triage layer.  
**Trade-offs:** May occasionally over-trigger higher priority for ambiguous cases; guarantees zero dangerous false negatives.

```python
def merge_triage(rules_result: TriageResult, llm_result: Optional[LLMExtraction]) -> TriageResult:
    if not llm_result:
        return rules_result
    # Union observed conditions
    merged_conditions = set(rules_result.observed_conditions).union(llm_result.conditions)
    # Re-run deterministic rules engine on merged set
    final_result = evaluate_deterministic_rules(merged_conditions)
    # Strict safety invariant check
    assert priority_rank(final_result.priority) >= priority_rank(rules_result.priority)
    return final_result
```

### Pattern 3: Scoped Multi-Tenant Demo Sessions

**What:** Every database entity (users, emergencies, offers, units) carries an optional `demo_session_id`. Real records have `NULL`. Demo requests carry a session ID in their cookie.  
**When to use:** Hackathon judging and live demonstrations where multiple judges evaluate the system concurrently.  
**Trade-offs:** Requires strict scope filtering in every database query; completely prevents data leakage between judges or into production records.

## Data Flow

### Citizen SOS Creation & Cascading Dispatch

```
1. Citizen triggers SOS (POST /emergencies with Idempotency-Key)
2. FastAPI runs Triage Rules Engine -> creates Emergency row (P1, protocol, required skills)
3. Orchestration Engine filters eligible responders & ranks them (scores 0-100)
4. Dispatch Plan persisted on Emergency; first offer created (status=OFFERED, expires_at=now+30s)
5. Ambulance track starts in parallel; ambulance offer created
6. First responder declines or expires -> advance() creates offer for candidate #2
7. Candidate #2 accepts -> offer status=ACCEPTED, location coarsening lifted, map updates
8. Professional ambulance arrives -> handover snapshot finalized
```

---
*Architecture research for: Community First-Aid & Emergency Dispatcher (LIFELINK)*  
*Researched: 2026-09-30*
