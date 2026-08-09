# AGENTS.md — BD Agent Only

## Scope

This file applies only to the BD Agent area of this repository.

Primary working scope:

- `src/vietnam_bd/`
- `apps/vietnam_bd_app.py` only when needed for BD UI / flow integration

Do not modify Lead Sensing unless absolutely required for a minimal compatibility fix.

Protected / minimize changes:

- `apps/lead_sensing_app.py`
- Lead Sensing source modules
- Existing A → B handoff behavior

The Lead Sensing Agent is treated as an upstream system. The BD Agent must consume its handoff with minimal coupling.

---

## Product Definition

The BD Agent is not a simple article summarizer.

Its role is:

> Take a selected lead, company, project, URL, text, or PDF as a starting clue, expand the context through research, classify the opportunity using fixed business rules, and help a salesperson decide what to investigate, who to approach, what to ask, and what to do next.

The product should prioritize sales intelligence and next action over report generation.

---

## Target BD Flow

The intended BD v2 pipeline is:

1. Input
2. Quick Research
3. Rule Engine
4. AI Context Interpretation
5. Evidence-based Context Arbitration
6. Stage Gate
7. Deep / Limited / Stop Research
8. Opportunity Workstream selection
9. Can We Enter assessment
10. Information to Confirm
11. Stakeholder / Target guidance
12. OPEN / POWER / WIN Talking Points
13. Next Best Action

Conceptually:

```text
A Lead / Direct Input
        ↓
Quick Research
        ↓
Rule Engine + AI Context Interpretation
        ↓
Evidence-based final Context
        ↓
Stage Gate
        ↓
Deep / Limited / Stop Research
        ↓
Workstream Top 3
        ↓
Can We Enter?
        ↓
Information to Confirm
        ↓
Stakeholder / Target
        ↓
OPEN / POWER / WIN
        ↓
Next Best Action
```

---

## Core Business Classification

The BD Agent must classify opportunities using the following 4-axis framework.

These categories are the governing business taxonomy. AI must map into this framework rather than invent new classifications.

### 1. Customer Needs

Examples include:

- Energy Security / power stability
- Fire safety / permitting / compliance
- High temperature / humidity / corrosion response
- RE100 / ESG / OPEX reduction
- Fast-track / early SOP
- Future expansion / modular design
- Local A/S / operational stability
- Workforce DX / operational digitalization
- Rugged / tablet / field mobility
- CAPEX / TCO optimization

### 2. Building / Project Type

Allowed categories:

- 신축
- 리모델링
- 수평증축
- 수직증축
- 스마트화
- 미확정

### 3. Business / Project Stage

Allowed categories:

- 사업기획
- 타당성 조사
- Master Plan
- 설계 - SD (기본)
- 설계 - DD (기본)
- 설계 - CD (기본)
- 건설 인허가
- 시공
- 운영 인허가
- 프로젝트 종료
- 미확정

### 4. Business Structure

Core categories:

- End Client
- PEF / Capital Structure
- Lead Architect
- GC / EPC
- Government Involvement

If current EPC / GC / Architect information is unavailable, the system may research:

- historical projects by the same project owner
- repeated historical partners
- comparable peer projects
- relevant market benchmarks

Any such candidate must be presented as a candidate / hypothesis, never as confirmed fact.

---

## Stage Gate Rules

Research depth is controlled by project stage.

### Targeting

Typical stages:

- 사업기획
- 타당성 조사

Research mode:

- Deep Research

Focus:

- project owner
- feasibility / PM / architect
- future decision structure
- early relationship entry

### Golden Time

Typical stages:

- Master Plan
- SD
- DD
- CD

Research mode:

- Deep Research, highest priority

Focus:

- Architect / PM / EPC / GC
- specification influence
- tender timing
- buying process
- competitive landscape

### Local Action

Typical stages:

- 건설 인허가
- 시공

Research mode:

- Limited Research

Focus only on remaining openings:

- unawarded packages
- late procurement
- GC / EPC purchasing
- change orders
- add-on scope
- site requirements
- future expansion

Do not spend broad Deep Research effort if the main Golden Time has already passed.

### Closed

Typical stages:

- 운영 인허가
- 프로젝트 종료

Research mode:

- Stop

The current project should normally not receive additional Deep Research.

Possible future directions may include:

- O&M
- retrofit
- future expansion
- next project

but these should not be confused with the current closed opportunity.

---

## Rule Engine + AI Principle

The system must be hybrid.

### Rule Engine

Purpose:

- deterministic business logic
- fixed taxonomy
- obvious signal detection
- cheap / fast filtering
- reproducible decisions

### AI

Purpose:

- semantic interpretation
- chronology understanding
- paraphrase recognition
- context linkage
- relationship inference
- research direction
- comparison across multiple sources

### Important Rule

The fixed business taxonomy is controlled by the Rule Engine / business framework.

AI may interpret meaning, but must not invent a new stage or new classification category outside the allowed taxonomy.

---

## Rule vs AI Conflict Resolution

Do not use a rule where either Rule or AI always wins.

Priority should be:

1. Direct and current factual evidence
2. Rule + AI agreement
3. More recent and more direct evidence
4. AI contextual interpretation when Rule missed a synonym / paraphrase
5. Unknown when evidence remains insufficient

Example:

```text
"Construction will begin next year"
```

must not be classified as current construction simply because the word `construction` exists.

Chronology matters.

When Rule and AI disagree:

- compare evidence
- prefer current direct evidence
- downgrade confidence when conflict remains
- use `unknown` if the stage cannot be supported

---

## Evidence Model

Every important conclusion should carry evidence status.

Allowed statuses:

- `confirmed`
- `likely`
- `hypothesis`
- `unknown`

Meaning:

### confirmed

Direct factual support exists from a credible source.

### likely

Multiple contextual signals strongly support the interpretation.

### hypothesis

Plausible commercial inference requiring field validation.

### unknown

Insufficient evidence.

Never fabricate names, vendor relationships, project stages, amounts, dates, EPC, GC, Architect, or decision makers.

---

## Research Principle

The original URL / text / PDF is only a starting clue.

The BD Agent must not stop at the submitted source.

For a viable opportunity, research can expand into:

- company announcements
- official website
- government sources
- industrial park sources
- recent news
- investment history
- factory history
- capacity expansion
- hiring signals
- architect / PM / EPC / GC
- prior owner projects
- historical project partners
- comparable peer projects
- public competitor / incumbent signals
- tender / procurement clues

Research should prioritize facts that can change sales action.

Do not research broadly for the sake of producing a long report.

---

## Deep Research Principle

Deep Research should answer questions such as:

- What project is actually happening?
- What is the current project stage?
- What is still open?
- Who has influenced similar projects in the past?
- Which EPC / GC / Architect candidates are worth checking?
- What buying signals are visible?
- What commercial route remains open?
- What is still unknown but sales-critical?

If the current EPC is not public, an acceptable output is:

```text
Current EPC: Unknown

Historical candidate:
ABC Engineering

Reason:
The project owner used ABC Engineering repeatedly on similar projects.

Status:
Hypothesis / check candidate
```

Do not turn this into a confirmed relationship.

---

## Workstream Selection

Do not recommend all Samsung products.

Workstream selection must come before product / capability suggestion.

The workstream should be derived from:

```text
Customer Needs
×
Building Type
×
Business Stage
×
Business Structure
```

Maximum recommended workstreams:

- 3

Also show excluded workstreams when useful.

The purpose is to avoid generic AI cross-selling.

Possible capabilities may be shown only after a workstream is justified.

---

## Can We Enter?

Assess commercial entry using four dimensions:

- Timing
- Access
- Openness
- Fit

Prefer qualitative levels:

- high
- medium
- low
- unknown

Avoid fake precision such as `78.4%` unless there is a genuine quantitative model behind it.

Each factor should include rationale / evidence.

---

## Information to Confirm

Do not expose the term `Critical Unknown` as primary UI wording.

Use:

> 확인 필요 정보

This section is not a list of everything unknown.

Only include information where the answer could change:

- Go / No-Go
- target stakeholder
- workstream priority
- research depth
- sales approach
- next action

Examples:

- Has the EPC already been selected?
- Is the key equipment specification already fixed?
- Who owns the vendor shortlist?
- Is the package already awarded?

Each item should explain why it matters and how the next action changes depending on the answer.

---

## Stakeholder / Target Logic

When information is confirmed, show:

- target role
- organization
- why to approach
- what information to obtain

When information is not confirmed:

- do not invent a person
- recommend a role or organization
- use historical relationships as check candidates
- use benchmark candidates when relevant

Future internal integration may include:

- OSP Account Owner
- SFDC Account Owner
- internal install base
- past deals
- internal references

Do not assume those internal systems are available unless the code actually provides them.

---

## Meeting Intelligence

Meeting Intelligence is a core BD function.

The goal is not to generate a pretty meeting script.

The goal is:

> Help the salesperson leave the first meeting with information that improves the company's position.

Use the following three categories.

### OPEN

Meaning:

> 아직 무엇이 열려 있는가?

Questions should uncover:

- open scope
- undecided specification
- unselected vendor
- unresolved design
- unawarded package
- remaining budget
- schedule flexibility

### POWER

Meaning:

> 누가 실제로 결정하는가?

Questions should uncover:

- real decision maker
- influence structure
- HQ vs local authority
- Architect / EPC / GC influence
- procurement gatekeeper
- technical approval owner

### WIN

Meaning:

> 무엇을 해야 우리가 들어갈 수 있는가?

Questions should uncover:

- selection criteria
- technical qualification
- reference requirement
- price / TCO requirement
- local service requirement
- delivery requirement
- approval path
- incumbent advantage

---

## Talking Point Model

A Talking Point must not contain only a question.

Each Talking Point should include:

- question
- information goal
- why it matters
- next action if positive
- next action if negative / unknown

Example:

```text
Question:
현재 주요 설비 Spec은 어느 정도 확정됐습니까?

Information Goal:
Spec-in 가능 여부 확인

Why It Matters:
Specification is still open only in early stages.

If Positive:
Presales / technical engagement immediately

If Negative:
Check vendor lock-in, VE, alternative package, or move the workstream down
```

---

## Next Best Action

Maximum actions:

- 3

Each action should include:

- action
- target
- purpose
- done criteria
- priority

Avoid vague outputs such as:

- "contact the customer"
- "conduct further research"
- "prepare a proposal"

Prefer:

```text
Action:
Confirm EPC selection status with local facility contact.

Done Criteria:
EPC name, selection status, and responsible organization confirmed.
```

---

## Current Implementation Strategy

Do not delete the existing BD implementation immediately.

Keep the current `analyze_opportunity()` and old UI working while BD v2 is built alongside it.

Current / expected new BD files include:

- `src/vietnam_bd/models.py`
- `src/vietnam_bd/rule_engine.py`
- `src/vietnam_bd/research.py`
- `src/vietnam_bd/context_interpreter.py`
- `src/vietnam_bd/analysis.py`
- `src/vietnam_bd/prompts.py`
- `src/vietnam_bd/ui_components.py`

The new path should be added incrementally.

Preferred migration pattern:

```text
Existing BD
    +
New BD v2 engine
    ↓
Runtime validation
    ↓
UI validation
    ↓
Switch main BD flow only after stable
```

---

## Coding Safety Rules

Before making large changes:

1. Read the existing BD files.
2. Inspect imports and dependencies.
3. Check for circular imports.
4. Check Pydantic model compatibility.
5. Identify old UI / prompt code that still expects the old `AnalysisResult`.
6. Make the smallest coherent change.
7. Run syntax / import tests.
8. Run relevant app or unit tests.
9. Report changed files and why.

Do not rewrite the entire BD module in one pass unless explicitly requested.

---

## Testing Expectations

At minimum, run:

```bash
python -m py_compile src/vietnam_bd/models.py
python -m py_compile src/vietnam_bd/rule_engine.py
python -m py_compile src/vietnam_bd/research.py
python -m py_compile src/vietnam_bd/context_interpreter.py
python -m py_compile src/vietnam_bd/analysis.py
```

Also test imports where relevant.

Example:

```bash
python -c "from src.vietnam_bd.research import research_opportunity; print('research import OK')"
```

Before UI migration, verify that existing Streamlit integration still starts.

---

## Development Behavior for Codex

When asked to continue BD v2 work:

1. Read this `AGENTS.md`.
2. Read current BD files before editing.
3. Preserve existing working behavior unless the requested step explicitly replaces it.
4. Prefer plan → small edit → test → report.
5. Explain:
   - files changed
   - logic changed
   - tests run
   - remaining risks
6. Do not modify Lead Sensing unless a concrete compatibility issue requires it.
7. Do not invent business logic that is not defined here or in the repository's BD rule data.
