from sqlalchemy.orm import Session
from app.models.models import (
    CPSE, Material, MaterialEmbedding, ProcurementHistory,
    MatchJob, MatchCandidate, ReviewQueue, GoldenRecord, CNMCCode, Crosswalk
)
from app.services.normalization.uom_normalizer import UOMNormalizer
from app.services.normalization.spec_extractor import SpecExtractor
from app.services.normalization.vendor_normalizer import VendorNormalizer
from app.services.matching.embeddings import EmbeddingService
from app.services.matching.matcher_engine import MatcherEngine
from app.services.governance.golden_record_service import GoldenRecordService
from app.services.governance.cnmc_minter import CNMCMinter
from app.services.governance.crosswalk_service import CrosswalkService

def seed_enterprise_scenarios(db: Session):
    # Check if materials already seeded
    existing_mat_count = db.query(Material).count()
    if existing_mat_count > 0:
        return

    cpcl = db.query(CPSE).filter(CPSE.code == "CPCL").first()
    iocl = db.query(CPSE).filter(CPSE.code == "IOCL").first()
    bpcl = db.query(CPSE).filter(CPSE.code == "BPCL").first()

    raw_items = [
        # Scenario 1: Identical 6" Gate Valve across 3 CPSEs (Different descriptions, units, vendors)
        {"cpse": cpcl, "code": "100234", "desc": "VLV GATE 6IN 300# CS FLG", "uom": "Nos", "price": 12500.0, "qty": 500, "vendor": "L&T Valves Ltd", "hsn": "84818030"},
        {"cpse": iocl, "code": "889102", "desc": "VALVE, GATE, 150MM, CL300, WCB", "uom": "EA", "price": 10800.0, "qty": 2000, "vendor": "Larsen & Toubro Ltd - Valve Div", "hsn": "84818030"},
        {"cpse": bpcl, "code": "445511", "desc": "6 INCH GATE VALVE FLANGED 300#", "uom": "Numbers", "price": 11200.0, "qty": 1500, "vendor": "Microfinish Valves", "hsn": "84818030"},

        # Scenario 2: Safety-Critical Wall Thickness / Schedule Mismatch (SCH 40 vs SCH 80)
        {"cpse": cpcl, "code": "100888", "desc": "PIPE CS SMLS 4\" SCH 40 ASTM A106", "uom": "MTR", "price": 2450.0, "qty": 1200, "vendor": "Jindal Saw Ltd", "hsn": "73041910"},
        {"cpse": iocl, "code": "889555", "desc": "PIPE CS 4\" SCH 80 A106", "uom": "M", "price": 3800.0, "qty": 4500, "vendor": "Maharashtra Seamless", "hsn": "73041910"},
        {"cpse": bpcl, "code": "445888", "desc": "4 INCH SEAMLESS PIPE SCH40 A106", "uom": "MTR", "price": 2520.0, "qty": 3000, "vendor": "Jindal Saw", "hsn": "73041910"},

        # Scenario 3: Safety-Critical Pressure Class Mismatch (150# vs 300#)
        {"cpse": cpcl, "code": "100999", "desc": "VALVE 2\" 150# CS FLG", "uom": "EA", "price": 4200.0, "qty": 300, "vendor": "L&T Valves", "hsn": "84818030"},
        {"cpse": iocl, "code": "889999", "desc": "VALVE 2\" 300# CS FLG", "uom": "EA", "price": 6800.0, "qty": 450, "vendor": "L&T Valves", "hsn": "84818030"},

        # Scenario 4: Bearing OEM Part No. Clearance Suffix (Standard vs /C3)
        {"cpse": cpcl, "code": "100501", "desc": "BEARING 6205-2RS1 SKF", "uom": "EA", "price": 850.0, "qty": 400, "vendor": "SKF India Ltd", "hsn": "84821010"},
        {"cpse": iocl, "code": "889501", "desc": "SKF BEARING NO. 6205 2RS1 / C3", "uom": "EA", "price": 920.0, "qty": 600, "vendor": "SKF Bearings", "hsn": "84821010"},
        {"cpse": bpcl, "code": "445501", "desc": "BRG SKF 6205-2RS1", "uom": "PCS", "price": 870.0, "qty": 500, "vendor": "SKF", "hsn": "84821010"},

        # Scenario 5: Assembly / Kit vs Component Spare (Veto test)
        {"cpse": cpcl, "code": "100777", "desc": "MECH SEAL CARTRIDGE PUMP P-101A (SET)", "uom": "SET", "price": 45000.0, "qty": 10, "vendor": "Flowserve India", "hsn": "84841000"},
        {"cpse": iocl, "code": "889777", "desc": "ROTARY SEAL RING FOR PUMP P-101A", "uom": "EA", "price": 8500.0, "qty": 50, "vendor": "Flowserve", "hsn": "84841000"},

        # Scenario 6: Packaging Multipliers (Grease 18kg Bucket vs 180kg Drum vs KG)
        {"cpse": cpcl, "code": "100612", "desc": "GREASE MOBILITH SHC 100 - 18KG BUCKET", "uom": "BKT", "price": 11700.0, "qty": 200, "vendor": "ExxonMobil", "hsn": "27101980"},
        {"cpse": iocl, "code": "889612", "desc": "GREASE MOBILITH SHC 100", "uom": "KG", "price": 630.0, "qty": 8000, "vendor": "Mobil Oil", "hsn": "27101980"},
        {"cpse": bpcl, "code": "445612", "desc": "MOBILITH SHC 100 - 180KG DRUM", "uom": "DRM", "price": 108000.0, "qty": 50, "vendor": "ExxonMobil", "hsn": "27101980"},

        # Scenario 7: Indian Plant Colloquial Term (Hinglish) - Spiral Gasket Jaali Wala
        {"cpse": iocl, "code": "889333", "desc": "4\" SPIRAL GASKET JAALI WALA 300#", "uom": "EA", "price": 450.0, "qty": 8000, "vendor": "Champion Seals", "hsn": "84841000"},
        {"cpse": cpcl, "code": "100333", "desc": "GASKET SPIRAL WOUND 4\" 300# CS/SS", "uom": "Nos", "price": 480.0, "qty": 2000, "vendor": "Champion Seals Ltd", "hsn": "84841000"},
        {"cpse": bpcl, "code": "445333", "desc": "GASKET SPIRAL 4 INCH 300#", "uom": "EA", "price": 460.0, "qty": 5000, "vendor": "Champion", "hsn": "84841000"},

        # Scenario 8: Standards Equivalence (ANSI B16.5 vs ASME B16.5)
        {"cpse": cpcl, "code": "100444", "desc": "FLANGE 6\" 300# WNRF ANSI B16.5 CS", "uom": "Nos", "price": 3200.0, "qty": 300, "vendor": "EIL Approved Vendor", "hsn": "73072100"},
        {"cpse": iocl, "code": "889444", "desc": "FLANGE 6\" 300# WNRF ASME B16.5 A105", "uom": "EA", "price": 3100.0, "qty": 600, "vendor": "Engineers India Ltd Vendor", "hsn": "73072100"},
    ]

    saved_materials = []

    for item in raw_items:
        desc = item["desc"]
        raw_uom = item["uom"]
        multiplier, base_uom = UOMNormalizer.extract_packaging_factor(desc, raw_uom)
        norm_uom = UOMNormalizer.normalize_uom(raw_uom)
        specs = SpecExtractor.extract_specs(desc)
        specs["base_uom"] = base_uom
        specs["package_multiplier"] = multiplier
        norm_vendor = VendorNormalizer.normalize_vendor(item["vendor"])

        mat = Material(
            cpse_id=item["cpse"].id,
            material_code=item["code"],
            short_description=desc,
            uom=norm_uom,
            base_uom=base_uom,
            package_multiplier=multiplier,
            item_noun=specs["item_noun"],
            nominal_size=specs["nominal_size"],
            pressure_class=specs["pressure_class"],
            moc=specs["moc"],
            schedule=specs["schedule"],
            end_connection=specs["end_connection"],
            standard_spec=specs["standard_spec"],
            part_number=specs["part_number"],
            clean_part_number=specs["clean_part_number"],
            clearance_suffix=specs["clearance_suffix"],
            is_kit_or_assembly=specs["is_kit_or_assembly"],
            extracted_attributes=specs,
            status="ACTIVE"
        )
        db.add(mat)
        db.flush()
        saved_materials.append(mat)

        # Embedding
        emb = EmbeddingService.generate_embedding(desc)
        db.add(MaterialEmbedding(material_id=mat.id, embedding=emb))

        # Procurement History
        db.add(ProcurementHistory(
            material_id=mat.id,
            cpse_id=item["cpse"].id,
            po_number=f"PO-{item['code']}-2026",
            vendor_name=item["vendor"],
            vendor_normalized=norm_vendor,
            hsn_code=item["hsn"],
            unit_price=item["price"],
            quantity=float(item["qty"]),
            total_spend=item["price"] * float(item["qty"])
        ))

    db.commit()

    # Pre-mint a sample Golden Record & Crosswalk for the 6" Gate Valve to give immediate dashboard data
    valve_mats = [m for m in saved_materials if m.material_code in ["100234", "889102", "445511"]]
    if valve_mats:
        synth = GoldenRecordService.synthesize_iso8000_description(valve_mats)
        golden = GoldenRecord(
            standardized_description="VALVE, GATE, 6 INCH (150 MM), CLASS 300#, FLANGED RF, ASTM A216 WCB",
            item_noun="VALVE, GATE",
            modifier="6 INCH (150 MM), CLASS 300#, FLANGED RF, ASTM A216 WCB",
            nominal_size="6 INCH (150 MM)",
            pressure_class="CLASS 300#",
            moc="ASTM A216 WCB",
            end_connection="FLANGED RF",
            standard_spec="ASME B16.34",
            base_uom="EA",
            canonical_attributes=synth["canonical_attributes"]
        )
        db.add(golden)
        db.flush()

        cnmc_code = CNMCMinter.mint_next_cnmc(db, golden.id)
        cnmc_obj = db.query(CNMCCode).filter(CNMCCode.code == cnmc_code).first()
        CrosswalkService.register_mappings(db, cnmc_obj.id, valve_mats, mapping_type="IDENTICAL")

    # Pipe 4" Sch 40 Crosswalk
    pipe_mats = [m for m in saved_materials if m.material_code in ["100888", "445888"]]
    if pipe_mats:
        pipe_synth = GoldenRecordService.synthesize_iso8000_description(pipe_mats)
        golden_pipe = GoldenRecord(
            standardized_description="PIPE, 4 INCH (100 MM), SCH 40, ASTM A106 GR.B",
            item_noun="PIPE",
            modifier="4 INCH (100 MM), SCH 40, ASTM A106 GR.B",
            nominal_size="4 INCH (100 MM)",
            schedule="SCH 40",
            moc="ASTM A106 GR.B",
            base_uom="MTR",
            canonical_attributes=pipe_synth["canonical_attributes"]
        )
        db.add(golden_pipe)
        db.flush()
        cnmc_pipe = CNMCMinter.mint_next_cnmc(db, golden_pipe.id)
        cnmc_p_obj = db.query(CNMCCode).filter(CNMCCode.code == cnmc_pipe).first()
        CrosswalkService.register_mappings(db, cnmc_p_obj.id, pipe_mats, mapping_type="IDENTICAL")

    # Run matching engine to generate review queue items for remaining candidates
    job = MatchJob(status="PENDING")
    db.add(job)
    db.commit()
    MatcherEngine.execute_cross_cpse_matching(db, job.id)
