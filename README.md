# National Unified Material Master Framework (UniMM)
## "One Nation — One Material Code" (CPCL, IOCL, BPCL)
### Zero-Training Architecture: Pre-Trained Zero-Shot AI + Deterministic Engineering Logic

---

## 🌟 Overview
UniMM is an enterprise material harmonization platform built for Central Public Sector Enterprises (CPSEs) in the Indian Oil & Gas sector (**CPCL**, **IOCL**, and **BPCL**).

It unifies disparate material taxonomies into a single **Common National Material Code (`CNMC-XXXXXXXX`)** while preserving local ERP mappings and generating ISO 8000 standardized descriptions.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    ZERO ML TRAINING / FINE-TUNING PRINCIPLE                             │
│                                                                                                         │
│  ❌ NO Model Training Pipelines          ✅ Pre-Trained Out-of-the-Box Embeddings (all-MiniLM-L6-v2)    │
│  ❌ NO Gradient Descent / Fine-Tuning    ✅ Deterministic Regex & Parametric Engineering Tokenizers     │
│  ❌ NO Labeled Training Data Overhead    ✅ Hard Invariant Safety Guardrail Rules (Refinery Safety)     │
│  ❌ NO Black-Box Weights / Drift         ✅ 100% Transparent, Explainable Formula-Based Scoring         │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ System Architecture & 7 Core Layers

1. **Batch Ingestion & Interactive Column Mapper**:
   - Auto-detects legacy column headers with confidence scores and provides 5-row live normalization previews.
2. **Deterministic Engineering Spec Extractor**:
   - Regex-based parametric parsing for Size, Pressure Class, Metallurgy (MOC), Schedule, End Connection, and OEM Bearing Part Numbers (`/C3`, `-2RS` clearance logic).
3. **Universal UOM & Packaging Normalizer**:
   - Standardizes UOM (`EA`, `MTR`, `KG`) and calculates packaging multipliers (e.g. `18kg bucket` $\rightarrow$ `18.0 x KG`).
4. **Indian Domain & Hinglish Lexicon**:
   - Converts Indian plant terms (e.g. `jaali wala` $\rightarrow$ `spiral wound`, `churi` $\rightarrow$ `threaded`) and equates legacy standards (`ANSI B16.5` $\equiv$ `ASME B16.5`).
5. **Zero-Training Neuro-Symbolic Matching Engine**:
   - pgvector HNSW search + Hard Invariant Safety Guardrail Vetoes (pressure class, wall thickness schedule, kit vs spare) + Composite Formula:
     $$\text{Composite Score} = 0.40 \times S_{\text{sem}} + 0.35 \times S_{\text{attr}} + 0.25 \times S_{\text{proc}}$$
6. **Human-in-the-Loop 3-Way Governance**:
   - Side-by-side CPCL + IOCL + BPCL cluster card review with explainable score math, ISO 8000 golden record synthesis, and atomic `CNMC-XXXXXXXX` minter.
7. **Unified Crosswalk Hub & SAP Migration Export**:
   - Reverse code lookup and SAP S/4HANA & ECC LSMW/LTMC compliant CSV exports.

---

## 🚀 Quickstart & Docker Execution

### 1. Start Full Topology via Docker Compose
```bash
docker-compose up --build
```

Services will be available at:
- **Web Frontend (Next.js 15)**: [http://localhost:3000](http://localhost:3000)
- **Backend Swagger API (FastAPI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **PostgreSQL 16 + pgvector**: `localhost:5432` (`unimm_db`)
- **Redis 7 Broker**: `localhost:6379`

### 2. Run Automated Pytest Test Suite
```bash
cd backend
pytest -v
```

---

## 📊 Synthetic CPSE Scenarios Verified in Seeds
The platform seeds pre-configured scenarios representing real CPSE challenges:
1. **Commodity Spec Variation**: 6" Class 300# Gate Valve across CPCL (`VLV GATE 6IN 300# CS FLG`), IOCL (`VALVE, GATE, 150MM, CL300, WCB`), and BPCL (`6 INCH GATE VALVE FLANGED 300#`).
2. **Safety-Critical Wall Thickness Trap**: 4" Pipe SCH 40 vs SCH 80 $\rightarrow$ **Vetoed for wall thickness mismatch**.
3. **Safety-Critical Pressure Class Trap**: 2" Valve 150# vs 300# $\rightarrow$ **Vetoed for pressure rating conflict**.
4. **Bearing Clearance Modifiers**: `6205-2RS1 SKF` vs `SKF BEARING NO. 6205 2RS1 / C3` $\rightarrow$ **Routed as Substitute / Near-Duplicate**.
5. **Assembly vs Component Spare**: Mechanical Seal Cartridge Kit vs Rotary Seal Ring $\rightarrow$ **Vetoed by assembly token rule**.
6. **Packaging Multipliers**: Grease Mobilith SHC 100 in 18KG Bucket, 180KG Drum, and KG $\rightarrow$ **Harmonized to base KG unit**.
7. **Hinglish Plant Slang**: `4" Spiral Gasket Jaali Wala` $\rightarrow$ **Standardized to Spiral Wound**.
8. **Standards Equivalence**: `ANSI B16.5` vs `ASME B16.5` $\rightarrow$ **Harmonized to common standard**.
