# Phase 3: Protocol Library, Triage Engine, Golden Set, LLM Adapter - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-01  
**Phase:** 03-protocol-library-triage-engine-golden-set-llm-adapter  
**Areas discussed:** Protocol step structure & first-aid guidance formatting, Tier 2 LLM provider adapter & timeout resilience, Free-text sanitization & prompt-injection defense, Golden triage dataset composition & CI eval gates  

---

## 1. Protocol Step Structure & First-Aid Guidance Formatting

### Q1: Step and contraindication structure
| Option | Description | Selected |
|--------|-------------|----------|
| Numbered imperative steps with contraindications | Concise steps with title, text, optional icon, and explicit do_not contraindications (Spec §5.5 schema) | ✓ |
| Interactive wizard flow | Step-by-step wizard requiring user to check off each step before advancing | |
| Condensed checklist | High-level bullet checklist with expandable detail accordions | |

**User's choice:** Numbered imperative steps with title, descriptive text, optional icon, and explicit 'do_not' contraindications (Spec §5.5 schema).

### Q2: Clinical citations and disclaimers
| Option | Description | Selected |
|--------|-------------|----------|
| Strict schema with disclaimer banner | Mandate source citation, status ('demo_unreviewed' / 'clinically_reviewed'), and prominent disclaimer banner | ✓ |
| Generic disclaimer footer | Generic footer on the guidance screen with minimal citation text | |
| the agent decides | Follow Spec §5.5 verbatim | |

**User's choice:** Strict schema enforcing status ('demo_unreviewed' / 'clinically_reviewed'), source citation, and a prominent disclaimer banner on each protocol card (Spec §5.5).

### Q3: Offline protocol delivery
| Option | Description | Selected |
|--------|-------------|----------|
| Shared single source of truth | shared/protocols/*.json loaded by FastAPI and bundled statically by Vite for 100% offline access | ✓ |
| Backend API only | Served dynamically with client localStorage/IndexedDB caching | |
| the agent decides | Bundle in shared/ for dual loading | |

**User's choice:** Shared single source of truth in shared/protocols/*.json, loaded server-side by FastAPI and bundled client-side by Vite for 100% offline guidance.

### Q4: Initial protocol catalog
| Option | Description | Selected |
|--------|-------------|----------|
| Core 7 MVP protocols | Exactly the 7 core MVP protocols from Spec §5.5 (UNRESPONSIVE, SEVERE_BLEEDING, CHOKING, SEIZURE, BURNS, TRAUMA_FALL, GENERAL) | ✓ |
| Expand with CHEST_PAIN | Add dedicated PROT_CHEST_PAIN protocol | |
| the agent decides | 7 spec protocols plus CHEST_PAIN | |

**User's choice:** Exactly the 7 core MVP protocols from Spec §5.5.

---

## 2. Tier 2 LLM Provider Adapter & Timeout Resilience

### Q1: Supported LLM providers
| Option | Description | Selected |
|--------|-------------|----------|
| Multi-provider adapter | Support both 'gemini' and 'openai' (compatible with Groq/Ollama) with 'none' as default | ✓ |
| Google Gemini only | Using official SDK plus 'none' default | |
| OpenAI-compatible only | Covering OpenAI, Groq, Ollama plus 'none' default | |

**User's choice:** Multi-provider adapter: support both 'gemini' and 'openai' (compatible with Groq/Ollama) with 'none' as default (Spec §5.6).

### Q2: Timeout and retry policy
| Option | Description | Selected |
|--------|-------------|----------|
| Strict 4s with 1 fast retry | 4s total budget with 1 fast retry (1.5s); on failure log TRIAGE_LLM_FALLBACK and rely on rules | ✓ |
| Single 4s timeout zero retries | Fail fast immediately on any latency spike | |
| the agent decides | 4s limit and immediate non-blocking fallback | |

**User's choice:** Strict 4s total budget with 1 fast retry (1.5s); on any timeout/error immediately log TRIAGE_LLM_FALLBACK and rely on Tier 1 rules (Spec §5.6).

### Q3: Demo session LLM behavior
| Option | Description | Selected |
|--------|-------------|----------|
| DEMO_DISABLE_LLM=true by default | Deterministic scenarios with zero quota risk, optional live toggle | ✓ |
| Always query live LLM | Always run live LLM if API key is set | |
| Mocked responses in demo | Pre-baked mocked responses matching 19-step script | |

**User's choice:** DEMO_DISABLE_LLM=true by default for demo sessions (deterministic scenarios, zero quota risk) with optional toggle (Spec §5.6).

### Q4: Escalate-only safety invariant
| Option | Description | Selected |
|--------|-------------|----------|
| Programmatic union with rules-first baseline | LLM can only add candidate condition tokens; priority calculated by deterministic rules over union | ✓ |
| Parallel min-priority score | Evaluate in parallel and pick min priority integer | |
| the agent decides | Union of conditions with rule-driven priority selection | |

**User's choice:** Programmatic union with rules-first baseline: LLM can only add detected condition tokens; priority calculated by deterministic rules over the union of conditions (Spec §2, §5.4).

---

## 3. Free-Text Sanitization & Prompt-Injection Defense

### Q1: Input sanitization
| Option | Description | Selected |
|--------|-------------|----------|
| Strict input sanitizer | Clamp to 500 chars, strip control chars/HTML, normalize whitespace, strictly exclude PII/location | ✓ |
| Simple length truncation | 500 char cutoff with standard strip | |
| the agent decides | 500 char clamp, tag stripping, zero PII | |

**User's choice:** Strict input sanitizer: clamp to 500 chars, strip control chars/HTML tags, normalize whitespace, and strictly exclude any PII/location from LLM payload (Spec §5.6).

### Q2: Prompt-injection framing
| Option | Description | Selected |
|--------|-------------|----------|
| XML containment tags | Untrusted description tag (<untrusted_emergency_description>) with strict system prompt | ✓ |
| Markdown code blocks | Fenced code blocks without explicit XML isolation | |
| the agent decides | XML containment tags with closed-label system instructions | |

**User's choice:** XML data containment tag (<untrusted_emergency_description>) with strict system prompt instructing model to treat content purely as data (Spec §5.6).

### Q3: Output validation
| Option | Description | Selected |
|--------|-------------|----------|
| Strict Pydantic schema | extra='forbid' against closed ConditionCode and EmergencyType enums; unknown tokens discarded | ✓ |
| Lenient regex keyword search | Regex search over free-form model response text | |
| the agent decides | Pydantic schema validation with closed enum enforcement | |

**User's choice:** Strict Pydantic schema validation with extra='forbid' against closed ConditionCode and EmergencyType enums; unknown tokens discarded (Spec §5.6).

### Q4: Negation and ambiguity
| Option | Description | Selected |
|--------|-------------|----------|
| Safe over-triggering | Structured yes/no answers are definitive ground truth; free-text can only escalate | ✓ |
| Heuristic negation parsing | Strip condition if preceded by 'not', 'no', 'without' | |
| the agent decides | Structured questions take precedence, fail-safe upward escalation | |

**User's choice:** Safe over-triggering invariant: structured yes/no answers are definitive ground truth; free-text can only add conditions and escalate, never suppress or de-escalate (Spec §5.4).

---

## 4. Golden Triage Dataset Composition & CI Eval Gates

### Q1: Case distribution
| Option | Description | Selected |
|--------|-------------|----------|
| Balanced 45-case set | 20 P1 red-flags, 10 P2 urgent, 5 P3 minor, 10 adversarial (injections, typos, Hinglish, 'not sure') | ✓ |
| Strict 40-case set | Evenly divided across 8 emergency types | |
| the agent decides | 45+ case suite covering taxonomy and edge cases | |

**User's choice:** Balanced 45-case set: 20 P1 red-flags, 10 P2 urgent, 5 P3 minor, 10 adversarial (injections, typos, Hinglish, 'not sure' answers) (Spec §5.7).

### Q2: Evaluation runner & test gates
| Option | Description | Selected |
|--------|-------------|----------|
| Dual interface | Standalone CLI script 'python -m app.triage.eval' with summary table, plus pytest CI test gate | ✓ |
| Pytest test case only | No standalone CLI runner | |
| the agent decides | Standalone CLI module plus pytest gate | |

**User's choice:** Dual interface: standalone CLI script 'python -m app.triage.eval' with summary table, plus pytest test gate enforcing 0 downgrades and >=0.95 recall (Spec §5.7).

### Q3: Evaluation documentation
| Option | Description | Selected |
|--------|-------------|----------|
| Comprehensive docs/AI_EVAL.md | Metrics table, adversarial test evidence, 0-downgrade proof, judge reproduction steps | ✓ |
| Brief section in README | No separate AI_EVAL.md document | |
| the agent decides | Dedicated docs/AI_EVAL.md showcasing technical depth | |

**User's choice:** Comprehensive docs/AI_EVAL.md with metrics table, adversarial test evidence, 0-downgrade proof, and judge reproduction steps (Spec §5.7).

### Q4: Unsafe downgrade definition
| Option | Description | Selected |
|--------|-------------|----------|
| Strict 3-point definition | Priority downgrade (P1->P2/P3 or P2->P3), ambulance omission (true->false), or missing red-flag | ✓ |
| Priority downgrade only | P1 -> P2/P3 only | |
| the agent decides | Strict safety definition permitting safe upward escalation while banning any downgrade | |

**User's choice:** Strict 3-point definition: priority downgrade (P1->P2/P3 or P2->P3), ambulance omission (true->false), or missing red-flag condition (Spec §5.7).

---

## Deferred Ideas
- Multilingual first-aid step translations (Hindi/Marathi): Deferred to stretch Phase 12c.
- Fine-tuned local classification models (e.g. BioClinicalBERT on ONNX): Out of scope for MVP; prompt-delimited few-shot LLM with rules engine is sufficient.
