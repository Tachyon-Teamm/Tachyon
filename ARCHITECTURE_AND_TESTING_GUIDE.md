# National Unified Material Master (UniMM)
## Architecture, End-to-End Pipeline & Testing Guide

> **Purpose of this Document:**  
> This guide provides a complete, transparent explanation of **how the entire UniMM system works** (from UI input down to the backend database), followed by an actionable, step-by-step **Testing & Verification Playbook** so both humans and AI agents can verify whether every component is functioning properly.

---

## 1. System Mission & Core Principle

In India's public sector, different Central Public Sector Enterprises (CPSEs) such as **CPCL**, **IOCL**, and **BPCL** maintain separate ERP catalogs (e.g. SAP ECC, S/4HANA). The same physical item (e.g., a 6" Class 300# Gate Valve) is described with different part numbers, colloquial jargon, and unit formats.

**UniMM (Unified Material Master)** harmonizes these disparate items into a single authoritative **Common National Material Code (`CNMC-XXXXXXXX-C`)** while preserving local ERP legacy mappings and synthesizing ISO 8000 compliant descriptions.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          ZERO-TRAINING ARCHITECTURE PRINCIPLE                          │
│                                                                                        │
│  ❌ NO Model Re-Training Pipelines       ✅ Out-of-the-box Embeddings (all-MiniLM-L6)  │
│  ❌ NO Opaque Weights / Hallucinations   ✅ Hard Deterministic Safety Guardrails       │
│  ❌ NO Fragile Graph Collapses           ✅ DSU Clustering with Coherence Gating       │
│  ❌ NO Unvalidated Numbers               ✅ Verhoeff Aerospace Typo Checksum           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. System Architecture & Topology

```mermaid
flowchart TD
    subgraph UI ["Layer 1: Frontend Web Application (Next.js 14 + Tailwind)"]
        UI_Ingest["/ingestion (File Upload, Dynamic Preview & Batch History)"]
        UI_Review["/review (7-Relationship Queue, 4 Status Tabs & Dispute Modal)"]
        UI_Crosswalk["/crosswalk (National Registry, Spotlight Search, GeM & SAP Export)"]
        UI_Catalog["/materials (8 CPSEs Catalog, Golden Record Toggle & Detail Modal)"]
    end

    subgraph API ["Layer 2: API Gateway (FastAPI)"]
        API_Ingest["/api/v1/ingestion (Streaming & Batch Profiler)"]
        API_Match["/api/v1/matching (Incremental & Batch Engine)"]
        API_Rev["/api/v1/review (7 Relationships, Disputes & Feedback Telemetry)"]
        API_Cross["/api/v1/crosswalk (Registry & Reverse Lookup)"]
        API_Audit["/api/v1/audit (CERT-In Hash Chain & Verify-Chain)"]
        API_Integ["/api/v1/integration (SAP MATMAS05 & GeM Catalog)"]
    end

    subgraph WORKERS ["Layer 3: Processing & Background Workers"]
        CELERY["Celery Workers / ThreadPool Fallback"]
        LEXICON["DomainLexicon (Multi-Sector Standards & Hinglish)"]
        SPEC_EXT["SpecExtractor (Parametric Engineering Parser)"]
        UOM_NORM["UOMNormalizer (UN/CEFACT Base Multipliers)"]
        EMBED["EmbeddingService (BAAI/bge-base-en-v1.5 + MiniLM + Cross-Encoder + BM25)"]
    end

    subgraph MATCH_CORE ["Layer 4: Zero-Training Matching & Safety Guardrails"]
        BLOCK["Level-1 Category / Noun Blocking Engine"]
        GUARD["SafetyGuardrails (10 Deterministic Invariant Vetoes)"]
        SCORER["CompositeScorer (0.40 Sem + 0.35 Attr + 0.25 Proc Dynamic Rebalancing)"]
        CLUSTER["ClusterEngine (DSU Correlation Graph with Density Gate >= 0.60)"]
    end

    subgraph GOV ["Layer 5: Governance & National Authority"]
        ISO["GoldenRecordService (ISO 8000 Noun-Modifier Standardization)"]
        MINTER["CNMCMinter (Verhoeff D5 Checksum CNMC-XXXXXXXX-C)"]
        CROSSWALK["CrosswalkService (N:1 National Crosswalk Registry)"]
        FEEDBACK["ReviewFeedback (Active Learning Triplet Telemetry)"]
        AUDIT["AuditService (CERT-In HMAC-SHA256 Chained Audit Trail)"]
    end

    subgraph STORAGE ["Layer 6: Persistence & Acceleration"]
        PG[(PostgreSQL 16 + pgvector HNSW)]
        REDIS[(Redis 7 Broker & Cache)]
        DEVICE["Hardware Accelerator (Apple Silicon MPS / NVIDIA CUDA / CPU)"]
    end

    UI --> API
    API --> WORKERS
    WORKERS --> STORAGE
    WORKERS --> DEVICE
    API --> MATCH_CORE
    MATCH_CORE --> STORAGE
    API --> GOV
    GOV --> STORAGE
```

---

## 3. The Final End-to-End Pipeline (How Data Moves Step-by-Step)

Here is the exact chunk-by-chunk trace from the moment a user uploads a file in the UI to the minting of a national code.

```mermaid
sequenceDiagram
    autonumber
    actor User as Plant Officer / User
    participant UI as Next.js Frontend
    participant API as FastAPI Backend
    participant Norm as Normalization Engine
    participant DB as PostgreSQL (pgvector)
    participant Match as Matcher & Guardrails
    participant Gov as Governance Minter

    User->>UI: Uploads CSV / Excel (or loads sample)
    UI->>API: POST /ingestion/detect-columns
    API->>Norm: Fuzzy-match headers & run 5-row preview
    API-->>UI: Returns detected columns & live preview
    User->>UI: Reviews mapping, clicks "Start Batch"
    UI->>API: POST /ingestion/start-batch
    API->>DB: Saves IngestionBatch & RawMaterial (JSON)
    API->>Norm: Preprocesses via DomainLexicon, SpecExtractor, UOMNormalizer
    Norm->>DB: Stores structured rows in Material table
    Norm->>DB: Generates 384-d vector -> MaterialEmbedding
    User->>UI: Triggers Matching Job
    UI->>API: POST /matching/trigger
    API->>Match: 1. Level-1 Blocking by Noun/Part Number
    API->>Match: 2. Evaluates SafetyGuardrails (SCH, Class, MOC, Assembly)
    API->>Match: 3. Computes Composite Score (0.40 Sem + 0.35 Attr + 0.25 Proc)
    API->>Match: 4. Clusters pairs into ReviewQueue
    Match->>DB: Saves MatchCandidate & ReviewQueue items
    User->>UI: Opens /review queue, inspects 3-way cluster
    User->>UI: Approves cluster (e.g. "Approve as Identical")
    UI->>API: POST /review/action
    API->>Gov: Synthesizes ISO 8000 title & mints Verhoeff CNMC
    Gov->>DB: Writes GoldenRecord, CNMCCode, Crosswalk (N:1), AuditLog
    API-->>UI: Confirmation with new CNMC code
    User->>UI: Searches legacy code in /crosswalk
    UI->>API: GET /crosswalk/lookup?local_code=...
    API-->>UI: Returns National CNMC + sister refinery codes
```

---

### Step-by-Step Data Transformation Walkthrough

Let us trace a real example through every stage:

| Stage | Input / Operation | Output Result |
|---|---|---|
| **Raw CPCL Input** | `VLV GATE 6IN 300# CS FLG`, UOM: `Nos`, Price: `₹12,500` | Stored in `raw_materials` table as raw JSON. |
| **Raw IOCL Input** | `VALVE, GATE, 150MM, CL300, WCB`, UOM: `EA`, Price: `₹10,800` | Stored in `raw_materials` table as raw JSON. |
| **Raw BPCL Input** | `6 INCH GATE VALVE FLANGED 300#`, UOM: `Numbers`, Price: `₹11,200` | Stored in `raw_materials` table as raw JSON. |
| **UOM Normalization** | `UOMNormalizer.normalize_uom()` | All normalized to `EA`. |
| **Spec Extraction** | `SpecExtractor.extract_specs()` | **Noun:** `VALVE, GATE`<br/>**Size:** `6 INCH (150 MM)`<br/>**Pressure:** `CLASS 300#`<br/>**MOC:** `WCB` / `CS` |
| **Safety Invariants** | `SafetyGuardrails.evaluate_pair()` | **PASSED:** Nominal sizes (150mm = 6") and pressure ratings (300#) match. Zero veto. |
| **Composite Score** | `CompositeScorer.compute_composite()` | **Score:** `0.93` (High Confidence). Routed to Review Queue. |
| **ISO 8000 Golden Record** | `GoldenRecordService.synthesize_iso8000_description()` | `VALVE, GATE, 6 INCH (150 MM), CLASS 300#, FLANGED RF, ASTM A216 WCB` |
| **CNMC Minting** | `CNMCMinter.mint_next_cnmc()` | **`CNMC-00000001-7`** (with Verhoeff checksum) |
| **Crosswalk Linkage** | `CrosswalkService.register_mappings()` | CPCL `100234` $\leftrightarrow$ `CNMC-00000001-7`<br/>IOCL `889102` $\leftrightarrow$ `CNMC-00000001-7`<br/>BPCL `445511` $\leftrightarrow$ `CNMC-00000001-7` |

---

## 4. How to Test If Things Are Working (Testing Playbook)

You can verify the entire system at four different levels:
1. **Automated Test Suite (Fastest, 10 seconds)**
2. **Docker Multi-Container Stack (Full local topology)**
3. **Step-by-Step API / cURL Commands (Direct backend verification)**
4. **Interactive UI Walkthrough (Visual smoke test)**

---

### Level 1: Automated Unit & Integration Test Suite

The repository contains a dedicated test suite verifying every component from normalization to safety guardrails and full end-to-end pipeline trace.

#### 1. Activate Environment
Open your terminal in the project root:
```bash
cd /Users/rupesh/Documents/Arc-1
source .venv/bin/activate
cd backend
```
*(If using `uv`: `uv run pytest -v` from the project root)*

#### 2. Run All Tests
```bash
pytest -v
```

#### 3. Run Specific Component Tests
- **Verify End-to-End Pipeline Trace (Stages 1 through 6):**
  ```bash
  pytest tests/test_pipeline_trace_integration.py -v
  ```
- **Verify Refinery Safety Guardrails & False-Positive Vetoes:**
  ```bash
  pytest tests/test_guardrails.py -v
  ```
- **Verify Deterministic Spec Extractor:**
  ```bash
  pytest tests/test_spec_extractor.py -v
  ```
- **Verify Universal UOM & Packaging Factor Normalizer:**
  ```bash
  pytest tests/test_uom_normalizer.py -v
  ```
- **Verify Tri-Factor Scorer & Adaptive Rebalancing:**
  ```bash
  pytest tests/test_scorer.py -v
  ```
- **Verify Production Upgrades (Verhoeff Checksum, Audit Hash Chaining, SCD-2):**
  ```bash
  pytest tests/test_audit_precision_upgrades.py -v
  ```

---

### Level 2: Run Full Topology via Docker Compose

Run the entire multi-service stack with a single command:

```bash
docker-compose up --build
```

#### Verify Container Health:
| Service | URL / Port | How to Check Health |
|---|---|---|
| **Web Frontend** | `http://localhost:3000` | Open in browser (should show Dashboard) |
| **FastAPI Backend** | `http://localhost:8000/docs` | Open in browser (Swagger UI should load) |
| **PostgreSQL 16** | `localhost:5432` | `pg_isready -h localhost -p 5432` |
| **Redis 7** | `localhost:6379` | `redis-cli ping` (returns `PONG`) |

---

### Level 3: Step-by-Step API / cURL Verification

You can execute these terminal commands sequentially to test each backend phase:

#### 1. Check API Health & Connectivity
```bash
curl -s http://localhost:8000/api/v1/analytics/summary | jq .
```
*Expected Output:* Returns JSON with `total_raw_materials`, `active_golden_records`, `average_quality_score`.

#### 2. Test Column Detection & Normalization Preview
```bash
curl -s -X POST "http://localhost:8000/api/v1/ingestion/detect-columns" \
  -F "file=@samples/sample_materials.csv" \
  -F "cpse_code=IOCL" | jq .
```
*Expected Output:* Returns `detected_columns`, `suggested_mappings`, and `preview_rows` showing normalized description and UOM.

#### 3. Start Batch Ingestion
```bash
curl -s -X POST "http://localhost:8000/api/v1/ingestion/start-batch" \
  -F "file=@samples/sample_materials.csv" \
  -F "cpse_code=IOCL" \
  -F 'mapping_config_json={"MATERIAL_NO":"material_code","ITEM_SPEC":"short_description","UNIT_OF_MEASURE":"uom","LAST_PO_PRICE":"base_price","VENDOR_NAME":"vendor_name","HSN_CODE":"hsn_code"}' | jq .
```
*Expected Output:* Returns batch response with status `"COMPLETED"` or `"PROCESSING"`.

#### 4. Trigger Cross-CPSE Matching Engine
```bash
curl -s -X POST "http://localhost:8000/api/v1/matching/trigger" | jq .
```
*Expected Output:*
```json
{
  "job_id": 1,
  "status": "COMPLETED",
  "result": {
    "status": "COMPLETED",
    "candidates_found": 8,
    "pairs_evaluated": 12
  }
}
```

#### 5. Inspect Governance Review Queue
```bash
curl -s "http://localhost:8000/api/v1/review/queue?status_filter=PENDING" | jq .
```
*Expected Output:* Returns a list of pending cluster objects with `cluster_group_id`, `composite_score`, and `confidence_tier`.

#### 6. Mint National Code or Record 7-Relationship Action
```bash
# Supports all 7 relationships: IDENTICAL, FUNCTIONAL_EQUIVALENT, BRAND_ALTERNATIVE,
# KIT_COMPONENT, PACKAGING_VARIANT, SUPERSEDED, SUBSTITUTE (+ REJECT, SPLIT)
curl -s -X POST "http://localhost:8000/api/v1/review/action" \
  -H "Content-Type: application/json" \
  -d '{
    "cluster_group_id": "cluster_gate_valve_6in_300",
    "decision_type": "IDENTICAL",
    "reviewer_notes": "Verified identical 6in gate valve across CPCL, IOCL, BPCL"
  }' | jq .
```
*Expected Output:* Returns `"status": "SUCCESS"` and `"minted_cnmc": "CNMC-00000001-7"`.

#### 7. Verify CERT-In Cryptographic Audit Hash Chain
```bash
curl -s "http://localhost:8000/api/v1/audit/verify-chain" | jq .
```
*Expected Output:*
```json
{
  "is_valid": true,
  "total_entries_verified": 75,
  "status": "VERIFIED",
  "genesis_hash": "...",
  "latest_hash": "...",
  "tampered_entry_id": null
}
```

#### 8. Export Active Learning Telemetry Dataset
```bash
curl -s "http://localhost:8000/api/v1/review/feedback/export" | jq .
```
*Expected Output:* Returns exported labeled training pairs from `ReviewFeedback` table with feature vectors (`semantic_score`, `attribute_score`, `procurement_score`, `reviewer_decision`).

#### 9. Test Reverse Code Lookup in Crosswalk Hub
```bash
curl -s "http://localhost:8000/api/v1/crosswalk/lookup?local_code=889102" | jq .
```
*Expected Output:* Returns:
- `cnmc_code`: `CNMC-00000001-7`
- `golden_description`: `VALVE, GATE, 6 INCH (150 MM), CLASS 300#...`
- `sister_mappings`: CPCL `100234` and BPCL `445511`.

#### 10. Test SAP S/4HANA Export
```bash
curl -s "http://localhost:8000/api/v1/export/sap-lsmw-csv" | head -n 5
```
*Expected Output:* First line is the SAP LSMW header (`CNMC_CODE,LOCAL_MATERIAL_NO,PLANT,MAKTX_ISO8000,BASE_UOM...`).

---

### Level 4: Interactive UI Walkthrough (5-Minute Visual Smoke Test)

1. **Ingestion Page (`http://localhost:3000/ingestion`)**:
   - Select **IOCL** (or any of the 8 CPSEs) from the dropdown.
   - Click **"Load Sample"** (dynamically loaded via `api.getSamples()`).
   - Verify: The system auto-detects `MATERIAL_NO`, `ITEM_SPEC`, etc.
   - Inspect the **Live Normalization Preview** table: verify dimension standardization (e.g. `150MM` $\rightarrow$ `6 INCH (150 MM)`).
   - Click **"Confirm & Start Batch"**: verify batch completion badge and the **Batch History Audit Table** displaying row counts, quality score badge (e.g., `0.92`), and the **"Proceed to Review Queue"** action button.

2. **Governance Review Queue (`http://localhost:3000/review`)**:
   - Filter clusters using the 4 status tabs: **PENDING**, **DISPUTED**, **APPROVED**, **REJECTED**.
   - Click a cluster card: the right pane displays the **Multi-CPSE Comparison Card**.
   - Check the **Score Breakdown**:
     - Semantic Score ($S_{\text{sem}}$)
     - Attribute Overlap ($S_{\text{attr}}$)
     - Procurement Correlation ($S_{\text{proc}}$)
   - Inspect the **Safety Badge**:
     - Commodity items display `Passed Invariants`.
     - Trap items (e.g. 4" Pipe SCH 40 vs SCH 80) display `Safety Veto: Wall Thickness Schedule Mismatch`.
   - Take action: Choose any of the **7 Approved Relationships** (`IDENTICAL`, `FUNCTIONAL_EQUIVALENT`, etc.).
   - Raise a dispute: Click **"Raise Dispute"** to launch the in-app arbitration dialog, specify the dissenting CPSE, and escalate directly to the National Data Steward.

3. **National Crosswalk Registry (`http://localhost:3000/crosswalk`)**:
   - Master Crosswalk Registry table loads automatically on mount via `api.getCrosswalkRegistry()`.
   - Perform spotlight search by typing any CPSE local code (e.g. `100234` or `889102`):
     - Displays the authoritative **CNMC National Authority** card and cross-enterprise sister mappings.
   - Click **"Syndicate to GeM"**: triggers catalog packaging and returns compliance signature feedback.
   - Click **"Export SAP IDoc"**: triggers MATMAS05 payload generation.
   - Click **"Verify Audit Chain"**: runs live cryptographic verification against the database hash chain.

4. **Master Materials Catalog (`http://localhost:3000/materials`)**:
   - Switch between **"CPSE Local Records"** and **"National Golden (CNMC)"** views.
   - Filter by any of the **8 CPSEs** (`CPCL`, `IOCL`, `BPCL`, `NTPC`, `SAIL`, `ONGC`, `COALINDIA`, `BHEL`).
   - Click on any row to open the **Technical Details Slideover Modal**, displaying raw fields alongside deterministic extracted attributes (nominal size, pressure class, metallurgy, standard specs).

---

## 5. Verification Checklist & Troubleshooting

| Checkpoint | What "Working Correctly" Looks Like | What "Failure" Looks Like & How to Fix |
|---|---|---|
| **Python Test Suite** | All 102 pytest tests + 22 unittests pass with green `PASSED`. | `ModuleNotFoundError`: Run with `PYTHONPATH=backend` or activate `.venv`. |
| **Backend API** | `http://localhost:8000/docs` renders OpenAPI interactive docs. | Connection Refused: Backend server is not running (`uvicorn app.main:app --reload`). |
| **Database & pgvector** | `SELECT 1;` succeeds and `\dx` in psql lists extension `vector`. | Missing extension: Run `CREATE EXTENSION IF NOT EXISTS vector;` in PostgreSQL. |
| **Safety Guardrail Check** | 4" Pipe SCH 40 vs SCH 80 is rejected from identical merge. | If merged identically: Ensure `SafetyGuardrails.evaluate_pair()` was executed before scoring. |
| **CNMC Checksum** | Code ends with a valid Verhoeff digit: `CNMC-00000001-7`. | If plain sequential without checksum: Check `CNMCMinter.mint_next_cnmc()`. |
| **Audit Hash Security** | `GET /api/v1/audit/verify-chain` returns `is_valid: true` and `status: VERIFIED`. | If invalid: Check `AuditService.verify_chain()` or inspect `tampered_entry_id`. |

---

## 6. The 8 Real-World Stress-Testing Scenarios & Invariant Verification

These 8 real-world engineering scenarios serve as the core benchmark for UniMM's zero-training neuro-symbolic engine and safety invariants. They are directly verified by [`backend/tests/test_e2e_scenarios.py`](file:///Users/rupesh/Documents/Arc-1/backend/tests/test_e2e_scenarios.py).

| # | Real-World Scenario | Real CPSE Input Examples | Zero-Training Engineered Behavior | Guardrail / Rule Mechanism | Verification Test |
|---|---|---|---|---|---|
| **1** | **Commodity Spec Variation** | CPCL: `VLV GATE 6IN 300# CS FLG`<br/>IOCL: `VALVE, GATE, 150MM, CL300, WCB`<br/>BPCL: `6 INCH GATE VALVE FLANGED 300#` | ✅ **Resolved**: UOM normalizer converts to `EA`; Regex extracts `6" = 150mm`, `300# = CL300`, `CS = WCB`. | Deterministic unit conversion + Regex spec extraction (`SpecExtractor`). | `test_scenario_1_commodity_spec_variation` |
| **2** | **Safety-Critical Minor Variations (False Positive Trap)** | CPCL: `PIPE CS 4" SCH 40 A106`<br/>IOCL: `PIPE CS 4" SCH 80 A106`<br/>CPCL: `VALVE 2" 150#` vs IOCL: `VALVE 2" 300#` | 🛡️ **Protected**: Pre-trained embeddings yield high similarity, but **Hard Invariant Veto** blocks merging different pressure classes or wall thicknesses. | Boolean mismatch on `extracted_attributes['pressure_class']` or `['schedule']`. | `test_scenario_2_safety_critical_variations` |
| **3** | **OEM Part No. Punctuation & Clearance Suffixes** | CPCL: `BEARING 6205-2RS1 SKF`<br/>IOCL: `SKF BEARING NO. 6205 2RS1 / C3`<br/>BPCL: `BRG SKF 6205-2RS1` | ⚙️ **Part Number Canonicalizer**: Strips punctuation noise (`62052RS1`) and isolates `C3` clearance suffix via regex to route as Near-Duplicate / Substitute. | String normalization + Regex clearance suffix splitter (`/C3`, `-2RS`, `-ZZ`). | `test_scenario_3_bearing_part_no_clearance` |
| **4** | **Vendor / Mfr Name Discrepancies** | CPCL: `L&T VALVES LTD`<br/>IOCL: `LARSEN & TOUBRO LTD - VALVE DIV`<br/>BPCL: `AUDCO INDIA / L&T` | 🏢 **Petroleum Vendor Alias Map**: Normalizes vendor variations to parent corporate entity (`LARSEN & TOUBRO`) via dictionary lookup + RapidFuzz string comparison. | Built-in CPSE approved vendor dictionary (`VendorNormalizer`) + RapidFuzz Token Set Ratio. | `test_scenario_4_vendor_alias_normalization` |
| **5** | **Assemblies / Kits vs Component Spares** | CPCL: `MECH SEAL CARTRIDGE PUMP P-101A (SET)`<br/>IOCL: `ROTARY SEAL RING FOR PUMP P-101A` | 🛑 **Assembly Token Veto**: Regex detects `SET/KIT/ASSY` vs `RING/SPARE/PART` and blocks identical merge. | Keyword rule list (`SET`, `KIT`, `ASSY`, `COMPLETE` vs `SPARE`, `RING`, `IMPELLER`). | `test_scenario_5_assembly_vs_spare_part` |
| **6** | **Packaging UOM vs Base UOM Discrepancy** | CPCL: `GREASE MOBILITH SHC 100 - 18KG BUCKET`<br/>IOCL: `GREASE MOBILITH SHC 100` (Unit: KG)<br/>BPCL: `MOBILITH SHC 100 - 180KG DRUM` | ⚖️ **Packaging Factor Normalizer**: Regex extracts numeric multipliers (`18 KG`, `180 KG`), converts to `Base UOM: KG`, and computes true ₹/KG unit price and total weight. | Regex pattern `(\d+(?:\.\d+)?)\s*(KG\|LTR\|GM\|ML)\s*(BUCKET\|DRUM\|CAN\|BKT\|DRM)` in `UOMNormalizer`. | `test_scenario_6_packaging_multiplier_consolidation` |
| **7** | **Indian Plant Colloquial Terms (Hinglish)** | IOCL: `4" SPIRAL GASKET JAALI WALA`<br/>CPCL: `GASKET SPIRAL WOUND 4" CS/SS` | 📖 **Domain Lexicon**: Built-in Oil & Gas synonym dictionary maps `jaali wala` $\rightarrow$ `spiral wound / mesh`, `churi` $\rightarrow$ `threaded`. | Static dictionary replacement table before tokenization (`DomainLexicon`). | `test_scenario_7_hinglish_colloquial_refinery_terms` |
| **8** | **Legacy Obsolete Standards** | CPCL: `FLANGE 6" 300# ANSI B16.5`<br/>IOCL: `FLANGE 6" 300# ASME B16.5` | 📜 **Standards Synonym Map**: Recognizes ANSI B16.5 and ASME B16.5 as historical standard equivalents. | Static engineering standard equivalence mapping table. | `test_scenario_8_standards_equivalence` |

---

### Key File Reference

- **API Routes:** [`backend/app/api/v1/`](file:///Users/rupesh/Documents/Arc-1/backend/app/api/v1/)
- **Normalization Services:** [`backend/app/services/normalization/`](file:///Users/rupesh/Documents/Arc-1/backend/app/services/normalization/)
- **Matching & Safety Guardrails:** [`backend/app/services/matching/`](file:///Users/rupesh/Documents/Arc-1/backend/app/services/matching/)
- **Governance & Authority Minting:** [`backend/app/services/governance/`](file:///Users/rupesh/Documents/Arc-1/backend/app/services/governance/)
- **Frontend Pages:** [`frontend/src/app/`](file:///Users/rupesh/Documents/Arc-1/frontend/src/app/)
- **Automated Test Suite:** [`backend/tests/`](file:///Users/rupesh/Documents/Arc-1/backend/tests/)

