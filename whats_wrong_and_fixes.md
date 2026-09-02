# What's Wrong & What We're Fixing

> A plain-language mapping of every issue in the current architecture to its fix.

---

## Data Model Issues

| # | What's Wrong Now | Why It's a Problem | What We Fix It With |
|---|---|---|---|
| 1 | **Golden Record table has hardcoded columns** — `nominal_size`, `pressure_class`, `moc` are baked into the database schema. | These columns only make sense for valves and pipes. The moment someone uploads a bearing, a cable, a chemical, or a bolt, these columns are meaningless. Every new material category would need a database migration. | Replace those fixed columns with a **flexible JSONB field** called `technical_attributes` + an **Attribute Dictionary** that tells the system what attributes to expect per material category. Adding a new category = adding a dictionary entry, not changing the database. |
| 2 | **The system is designed for exactly 3 CPSEs** (CPCL, IOCL, BPCL). The `CPSES` table has a hardcoded `code` field expecting only these three values. The UI shows "3-Way Cluster Cards". | The problem statement says this should work across **all CPSEs** — Oil & Gas, Power, Steel, Mining, Heavy Engineering. That's 200+ organizations. You can't hardcode them. | Make the CPSE table **open-ended** — any organization can register. The cluster card UI must show **N materials** (could be 2, could be 15), not a fixed 3-way layout. |
| 3 | **Only 2 relationship types exist** — "identical" and "near_duplicate" in the crosswalk table. | Real materials have many more relationships: substitutes, alternatives, kit-vs-component, different packaging of the same product, superseded/obsolete items, brand equivalents. Forcing everything into 2 buckets loses critical information. | Expand to **6+ relationship types**: Identical, Near-Duplicate, Substitute, Alternative Brand, Kit vs Component, Different Packaging, Incompatible. Store relationship type on the crosswalk/match record. |
| 4 | **Raw data is stored, but there's no "cleaned middle layer"**. Data jumps from `RAW_MATERIALS` straight to `MATERIALS`. | There's no place to inspect what the system understood from the raw data before it tries to match. If the normalization is wrong, you can't easily see or fix it. | Add a **3-layer pipeline** (Bronze → Silver → Gold): Raw as-is → Normalized & extracted → Final golden record. Each layer is inspectable. |
| 5 | **No data quality tracking.** The system doesn't record how complete or messy the incoming data is. | If a CPSE uploads a file where 60% of records have no unit of measure and 40% have no specifications, the system just silently processes bad data. Nobody knows the input was poor. | Add a **data quality profiler** that runs on every upload — reports completeness per field, flags problems, and gives each record a quality score. |

---

## Matching Engine Issues

| # | What's Wrong Now | Why It's a Problem | What We Fix It With |
|---|---|---|---|
| 6 | **The composite score weights are fixed** — always 40% semantic, 35% specs, 25% procurement — for every material. | For a new material with no purchase history, the 25% procurement score is useless. For chemicals where brand names matter more than specs, the weights should be different. One-size-fits-all scoring produces unreliable results. | Make scoring weights **configurable per material category**. Valves might be 30/50/20, chemicals might be 40/40/20, new items with no history might be 50/50/0. |
| 7 | **`all-MiniLM-L6-v2` struggles with heavily abbreviated industrial text.** | "VLV GATE 6IN 300# **CS** FLG" and "VLV GATE 6IN 300# **SS** FLG" are nearly identical in embedding space, but Carbon Steel and Stainless Steel are fundamentally different materials. The semantic score can't tell them apart. | The safety guardrail already catches CS vs SS — that's good. But acknowledge that the **semantic score is less reliable than advertised** for abbreviated text. Long-term: evaluate better models (BGE-M3). Short-term: **increase the weight of parametric matching** over semantic matching. |
| 8 | **Blocking uses only UNSPSC categories.** | UNSPSC is a spend/budget classification ("what budget line is this?"), not a technical classification ("what are the specs?"). It's too broad — a single UNSPSC code covers thousands of different valves. Also, zero-shot UNSPSC prediction can misclassify, causing true matches to never be compared. | Use **multiple blocking strategies together**: UNSPSC category + shared important tokens (part numbers, dimensions) + Locality-Sensitive Hashing on embeddings. This catches matches that single-strategy blocking would miss. |
| 9 | **Matching is pairwise only** — compares material A to material B. | If A matches B and B matches C, the system doesn't automatically know that A, B, and C should form one cluster. Each pair is evaluated independently. | Add **transitive closure / cluster formation**: if A≈B and B≈C, group all three into one cluster. Then present the whole cluster for review. |
| 10 | **No incremental matching.** Adding new materials implies re-running the entire matching process. | When CPSE #4 uploads 10,000 new materials, you shouldn't have to re-compare all existing materials against each other. That's wasteful and slow. | Design for **incremental matching**: new materials get embedded and searched against the existing vector index. Only new-vs-existing pairs are scored. The existing index stays untouched. |

---

## Ingestion & Normalization Issues

| # | What's Wrong Now | Why It's a Problem | What We Fix It With |
|---|---|---|---|
| 11 | **Column mapper assumes predictable SAP-like headers.** | Real government data exports have headers like "Mat_Desc", "ITEM_SPEC", "Material Text", "Description_1", or even Hindi column names. Some files have the header on row 3, not row 1. Some have merged cells. | Make the column mapper **smarter**: use AI-based semantic matching to suggest mappings for any header name. Add heuristics to auto-detect which row is the actual header. Handle merged cells and multi-sheet workbooks. |
| 12 | **The domain lexicon is Oil & Gas only** — Hinglish terms, abbreviations, and synonyms all target valves, pipes, and refinery materials. | Power sector materials (transformers, insulators), steel sector (billets, TMT bars), mining (explosives, dragline parts) have completely different vocabularies. The system would fail silently on non-O&G data. | Make the domain lexicon **modular and extensible** — organized by sector/category. Start with O&G, but design so that Power, Steel, Mining vocabularies can be added as configuration files, not code changes. |
| 13 | **Safety guardrails are hardcoded for O&G attributes** — pressure class, schedule, MOC, kit-vs-part. | Electrical items need voltage/current mismatch detection. Chemicals need concentration/compatibility checks. Fasteners need thread standard mismatch detection. The current rules only protect O&G materials. | Make safety guardrails **configurable per material category**. Each category defines its own "critical attributes" that trigger a veto on mismatch. New categories bring their own rules. |
| 14 | **Pricing data is assumed to always be available.** The procurement score uses "Price Band ±20%". | Many material exports won't include pricing. Some CPSEs may not share pricing due to commercial sensitivity. The scoring formula breaks if this data is missing. | Make procurement scoring **graceful when data is missing** — if no pricing exists, redistribute the weight to other signals instead of producing a garbage score. |

---

## UI & Workflow Issues

| # | What's Wrong Now | Why It's a Problem | What We Fix It With |
|---|---|---|---|
| 15 | **Review UI shows a fixed "3-Way Cluster Card"** — side-by-side CPCL + IOCL + BPCL. | With N organizations, you could have a cluster of 2, 5, or 20 materials. A fixed 3-column layout doesn't work. | Design the review card as an **N-way dynamic layout** — works for any number of materials in a cluster. Could be a scrollable list, accordion, or responsive grid. |
| 16 | **No bulk review operations.** Every material cluster must be reviewed individually. | If 200 clusters are all high-confidence (>95%) identical valve matches, clicking through each one is painful and slow. Reviewers will burn out. | Add **batch approve/reject** for high-confidence clusters. Let reviewers filter by confidence tier and approve all matching items in one action, while still reviewing medium/low-confidence items individually. |
| 17 | **No conflict resolution workflow.** What happens when CPSE-A's reviewer says "these are the same" but CPSE-B's reviewer disagrees? | In a multi-organization system, disagreements will happen. The current design doesn't account for this. | Add a **conflict resolution process** — escalation to a senior reviewer or a national-level arbiter who can make final decisions, with reasoning recorded in the audit trail. |

---

## Missing Features

| # | What's Missing | Why It Matters | What We Add |
|---|---|---|---|
| 18 | **No feedback loop.** Human review decisions (approve/reject) are recorded but never used to improve future matching. | The system never gets smarter. A reviewer rejects the same bad match type 50 times, but the system keeps proposing it. | **Capture every review decision as labeled training data.** Design the data model so that approved = positive example, rejected = negative example. Even if you don't fine-tune the model in the MVP, you're collecting the data to do it later. |
| 19 | **No version history on Golden Records.** Once a Golden Record is created, there's no record of changes. | Materials change over time — standards get updated, new information comes in, errors are corrected. Without versioning, you can't track what changed or roll back mistakes. | Add **versioning** to Golden Records. Every update creates a new version. Previous versions are preserved. Changes are linked to the audit trail. |
| 20 | **No API for external systems.** The system has a REST API for its own UI, but no structured integration points for GeM, SAP MDG, or other CPSEs' ERPs. | The whole point is that this data flows back to CPSEs' ERPs and to GeM. Without proper integration APIs, the output is a dead-end spreadsheet. | Design a **proper integration API layer** from the start — even if the MVP only implements CSV/Excel export, the API contracts for SAP MDG sync, GeM push, and ERP callbacks should be defined. |

---

> **Bottom line:** The current architecture is a **solid starting concept** for an O&G-only, 3-CPSE demo. But the problem statement asks for a **national platform across all sectors and all CPSEs.** These 20 fixes transform it from a demo that works for one happy path into a foundation that can handle real-world messiness without breaking.
