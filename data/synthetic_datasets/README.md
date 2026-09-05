# National Unified Material Master (UniMM) — Synthetic Benchmark Datasets
## Problem Statement 26099: AI-Driven Standardization and Harmonization of Material Codes Across CPSEs
**Target Ministry:** Ministry of Petroleum & Natural Gas  
**Host Organization:** Chennai Petroleum Corporation Limited (CPCL)  
**Theme:** Smart Automation / One Nation – One Material Code

---

## 1. Overview of Synthetic Datasets

This directory contains production-representative material master extracts generated specifically to test and demonstrate all 8 core capabilities of Problem Statement 26099.

Each dataset mirrors real-world SAP ECC 6.0 / S/4HANA ERP export schemas with disparate field naming, inconsistent colloquial descriptions, varying units of measurement, different packaging multipliers, and distinct local material numbering.

| Filename | CPSE Organization | Sector | Records | Key Equipment / Materials |
|---|---|---|---|---|
| `cpcl_materials.csv` | Chennai Petroleum Corp Ltd (CPCL) | Oil & Gas (Refining) | 15 | Refinery valves, ASTM A106 pipes, spiral gaskets, SKF bearings, lubricants, pumps |
| `iocl_materials.csv` | Indian Oil Corp Ltd (IOCL) | Oil & Gas (Refining & Mktg) | 15 | Equivalent valves (150MM/CL300), Servo lubricants, mechanical seal spares, 11kV cables |
| `bpcl_materials.csv` | Bharat Petroleum Corp Ltd (BPCL) | Oil & Gas (Refining) | 12 | Flanged valves, MAK lubricants, drum multipliers, differential pressure transmitters |
| `ongc_materials.csv` | Oil & Natural Gas Corp (ONGC) | Oil & Gas (Upstream E&P) | 10 | Wellhead gate valves, downhole pumps, casing tubing, offshore explosion-proof transmitters |
| `ntpc_materials.csv` | NTPC Limited | Power Generation | 8 | 33kV/11kV transformers, HT cables, vacuum circuit breakers, turbine oils, pulverizer rollers |
| `sail_materials.csv` | Steel Authority of India (SAIL) | Steel Production | 8 | TMT rebars (Fe 500D), high-alumina refractory bricks, heavy conveyor belting |
| `bhel_materials.csv` | Bharat Heavy Electricals (BHEL) | Heavy Engineering | 8 | Turbine blades, generator rotors, boiler piping flanges, high-tensile stud bolts |
| `coalindia_materials.csv` | Coal India Limited (CIL) | Mining | 8 | Excavator bucket teeth, 400-bar hydraulic hoses, 49\" dumper haul truck tires, drill bits |

---

## 2. Key Test Scenarios & Expected System Behaviors

### Scenario A: Identical Material Harmonization (\"One Nation – One Code\")
* **Input Items:**
  * CPCL: `CPCL-VLV-401416` (`VLV GATE 6IN 300# CS FLG ASME B16.34 WCB`, ₹14,500, Qty: 250)
  * IOCL: `IOCL-774102` (`VALVE, GATE, 150MM, CLASS 300, WCB, RF`, ₹11,200, Qty: 600)
  * BPCL: `BPCL-889012` (`6 INCH GATE VALVE FLANGED 300# WCB OS&Y`, ₹12,800, Qty: 400)
  * ONGC: `ONGC-VALV-3006` (`VALVE GATE 6\" 300 LBS WCB FLANGED RF`, ₹13,900, Qty: 180)
  * BHEL: `BHEL-VLV-1001` (`VALVE GATE 6 INCH 300# FLANGED WCB ASME B16.34`, ₹13,100, Qty: 90)
* **What to verify in UI:**
  1. Go to **Governance Review Queue** (`/review`).
  2. The AI identifies them into a single high-confidence cluster ($>95\%$ composite score).
  3. Approving mints a unified National CNMC Code (e.g. `CNMC-OIL-401416-XXXX`) with ISO 8000 standardized description:  
     `VALVE, GATE, 6 INCH (150 MM), CLASS 300#, ASTM A216 WCB, FLANGED (RF), ASME B16.34`.
  4. In the **Executive Dashboard** (`/`), the **Demand Aggregation Table** shows:
     * Consolidated demand: **1,520 EA** across 5 CPSEs.
     * Price spread: ₹11,200 (min) to ₹14,500 (max).
     * **Live Collaborative Savings:** Calculated automatically from volume variance.

### Scenario B: Multi-Enterprise Common Spares (Deep Groove Ball Bearings)
* **Input Items:**
  * CPCL: `CPCL-BRG-311715` (`BRG 6205-2RS1 SKF DEEP GROOVE BALL`)
  * IOCL: `IOCL-889501` (`BEARING NO 6205 2RS1 / C3 SKF`)
  * BPCL: `BPCL-445501` (`DEEP GROOVE BALL BEARING 6205-2RS1`)
  * SAIL: `SAIL-BRG-990501` (`BEARING 6205-2RS1 DEEP GROOVE C3 FAG`)
  * BHEL: `BHEL-BRG-1002` (`BALL BEARING 6205-2RS1/C3 SKF`)
* **What to verify in UI:**
  1. BM25 alphanumeric token extractor matches the core bearing designation `6205-2RS1`.
  2. C3 clearance suffix is recognized canonically without penalizing the match.

### Scenario C: Packaging Multiplier & Unit of Measure (UOM) Normalization
* **Input Items:**
  * CPCL: `CPCL-LUB-151215` (`GREASE MOBILITH SHC 100 - 18KG BUCKET`, UOM: BKT, ₹12,600)
  * IOCL: `IOCL-889612` (`GREASE MOBILITH SHC 100 SYNTHETIC`, UOM: KG, ₹750)
  * BPCL: `BPCL-445612` (`MOBILITH SHC 100 - 180KG DRUM`, UOM: DRM, ₹117,000)
* **What to verify in UI:**
  1. The system detects packaging multipliers:
     * Bucket = `18.0 KG` (effective ₹700/kg)
     * Drum = `180.0 KG` (effective ₹650/kg)
  2. Normalizes all quantities to base UOM `KG`.
  3. Prevents false volume spikes in collaborative demand calculation.

### Scenario D: Functionally Equivalent Brand Alternatives
* **Input Items:**
  * CPCL: `CPCL-OIL-151216` (`SHELL OMALA S2 G 220 INDUSTRIAL GEAR OIL 209L`, ₹46,000)
  * IOCL: `IOCL-889700` (`SERVOMESH SP 220 INDUSTRIAL GEAR OIL 210L`, ₹41,500)
  * BPCL: `BPCL-445700` (`MAK AMOCAM 220 INDUSTRIAL GEAR OIL 210L`, ₹42,200)
* **What to verify in UI:**
  1. System extracts ISO VG `220` viscosity and industrial gear lubrication classification.
  2. Proposes relationship as **BRAND_ALTERNATIVE** or **FUNCTIONAL_EQUIVALENT** between Shell, Servo, and MAK.

### Scenario E: Deterministic Safety Invariants (Hard Vetoes)
* **Test Case 1 (Pressure Class Mismatch):**
  * `CPCL-VLV-401417` (2\" 150# CS FLANGED GATE) vs `IOCL-889999` (2\" 300# CS FLG GATE)
  * **Result:** **HARD VETO APPLIED.** System automatically flags:  
    `VETO: Pressure class mismatch (150# vs 300#) violates ASME B16.34 pipeline safety invariant.`
* **Test Case 2 (Pipe Schedule / Wall Thickness Mismatch):**
  * `IOCL-889716` (6\" SCH 80 ASTM A106) vs `CPCL-PIP-401716` (6\" SCH 40 ASTM A106)
  * **Result:** **HARD VETO APPLIED.** Schedule 40 (standard) vs Schedule 80 (extra heavy) cannot interchange in high-pressure steam service.
* **Test Case 3 (Assembly Kit vs Individual Spare):**
  * `CPCL-MCH-401418` (`MECH SEAL CARTRIDGE PUMP P-101A (SET)`) vs `IOCL-889777` (`ROTARY SEAL RING FOR PUMP P-101A`)
  * **Result:** **HARD VETO APPLIED.** Assembly kit cannot be merged with single component replacement.

---

## 3. How to Test Tomorrow

### Method 1: Web UI Step-by-Step Flow (Recommended for Live Demo)
1. **Start Backend & Frontend Services:**
   ```bash
   # Terminal 1: Backend
   PYTHONPATH=backend backend/.venv/bin/uvicorn app.main:app --reload --port 8000

   # Terminal 2: Frontend
   cd frontend && npm run dev
   ```
2. Open browser at `http://localhost:3000`.
3. Log in using `steward` / `password` or `admin` / `password`.
4. Navigate to **Data Ingestion** (`/ingestion`).
5. Under **Multi-CPSE Ingestion**, you can:
   * Select **CPCL** and upload `data/synthetic_datasets/cpcl_materials.csv`.
   * Click **Inspect & Map Columns** -> Observe the 2-pass column detection matching SAP fields.
   * Click **Start Ingestion Batch** -> Watch the real-time progress bar.
   * Repeat for **IOCL** (`iocl_materials.csv`) and **BPCL** (`bpcl_materials.csv`).
6. Click **Run Cross-CPSE Matching** -> The background engine evaluates candidate pairs across the CPSEs using neural embeddings and safety guardrails.
7. Navigate to **Governance Review** (`/review`):
   * Inspect the AI-proposed clusters and score math.
   * Verify safety vetoes on the 150# vs 300# valve.
   * Click **Approve (IDENTICAL)** -> Observe the instant issuance of Verhoeff-checksummed CNMC Golden Records.
8. Navigate to **Executive Dashboard** (`/`):
   * Watch the live standardization coverage gauge rise.
   * Inspect the **Demand Aggregation & Procurement Savings Table**.
9. Navigate to **Crosswalk Hub** (`/crosswalk`):
   * Enter an IOCL code like `IOCL-774102` to test sub-10ms reverse lookup back to CPCL and BPCL sister records.

---

### Method 2: Instant 1-Click Automated Ingestion (Fast Demo Setup)
Run the automated ingestion script:
```bash
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/ingest_synthetic_data.py
```
This script automatically:
* Ingests all 8 CPSE datasets into PostgreSQL.
* Generates 384-d dense embeddings on Apple MPS GPU.
* Executes cross-enterprise blocking and pairwise scoring.
* Pre-populates the review queue and crosswalk hub for immediate demonstration.
