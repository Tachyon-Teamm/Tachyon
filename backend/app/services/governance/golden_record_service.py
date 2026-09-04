from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.models import Material

class GoldenRecordService:
    """
    Zero-Shot ISO 8000 Template Synthesizer.
    Synthesizes compliant Noun-Modifier descriptions from extracted engineering attributes.
    """

    @staticmethod
    def synthesize_iso8000_description(materials: List[Any]) -> Dict[str, Any]:
        if not materials:
            return {
                "standardized_description": "UNKNOWN ITEM",
                "item_noun": "ITEM",
                "modifier": None,
                "nominal_size": None,
                "pressure_class": None,
                "moc": None,
                "schedule": None,
                "end_connection": None,
                "standard_spec": None,
                "base_uom": "EA",
                "technical_attributes": {},
                "canonical_attributes": {}
            }

        # Combine attributes across clustered materials, prioritizing most specific values
        item_noun = None
        nominal_size = None
        pressure_class = None
        moc = None
        schedule = None
        end_connection = None
        standard_spec = None
        base_uom = getattr(materials[0], "base_uom", "EA") or "EA"
        
        for m in materials:
            ext = getattr(m, "extracted_attributes", {}) or {}
            if isinstance(ext, dict):
                if not item_noun:
                    item_noun = getattr(m, "item_noun", None) or ext.get("item_noun")
                if not nominal_size:
                    nominal_size = getattr(m, "nominal_size", None) or ext.get("nominal_size")
                if not pressure_class:
                    pressure_class = getattr(m, "pressure_class", None) or ext.get("pressure_class")
                if not moc:
                    moc = getattr(m, "moc", None) or ext.get("moc")
                if not schedule:
                    schedule = getattr(m, "schedule", None) or ext.get("schedule")
                if not end_connection:
                    end_connection = getattr(m, "end_connection", None) or ext.get("end_connection")
                if not standard_spec:
                    standard_spec = getattr(m, "standard_spec", None) or ext.get("standard_spec")
            else:
                if not item_noun and getattr(m, "item_noun", None):
                    item_noun = m.item_noun
                if not nominal_size and getattr(m, "nominal_size", None):
                    nominal_size = m.nominal_size
                if not pressure_class and getattr(m, "pressure_class", None):
                    pressure_class = m.pressure_class
                if not moc and getattr(m, "moc", None):
                    moc = m.moc
                if not schedule and getattr(m, "schedule", None):
                    schedule = m.schedule
                if not end_connection and getattr(m, "end_connection", None):
                    end_connection = m.end_connection
                if not standard_spec and getattr(m, "standard_spec", None):
                    standard_spec = m.standard_spec

        # Default fallback
        item_noun = item_noun or "EQUIPMENT / SPARE"

        # Build ISO 8000 Noun-Modifier representation
        modifiers = []
        if nominal_size:
            modifiers.append(nominal_size)
        if pressure_class:
            modifiers.append(pressure_class)
        if schedule:
            modifiers.append(schedule)
        if end_connection:
            modifiers.append(end_connection)
        if moc:
            modifiers.append(moc)
        if standard_spec:
            modifiers.append(standard_spec)

        # Collect multi-sector modifiers (Steel, Mining, Power, Heavy Eng)
        voltage_rating = None
        current_rating = None
        thread_size = None
        length = None
        steel_grade = None
        alumina_content = None
        belt_width = None
        tensile_rating = None

        for m in materials:
            ext = getattr(m, "technical_attributes", None) or getattr(m, "extracted_attributes", {}) or {}
            if isinstance(ext, dict):
                voltage_rating = voltage_rating or ext.get("voltage_rating")
                current_rating = current_rating or ext.get("current_rating")
                thread_size = thread_size or ext.get("thread_size")
                length = length or ext.get("length")
                steel_grade = steel_grade or ext.get("steel_grade")
                alumina_content = alumina_content or ext.get("alumina_content")
                belt_width = belt_width or ext.get("belt_width")
                tensile_rating = tensile_rating or ext.get("tensile_rating")

        if voltage_rating:
            modifiers.append(voltage_rating)
        if current_rating:
            modifiers.append(current_rating)
        if thread_size:
            modifiers.append(thread_size)
        if length:
            modifiers.append(length)
        if steel_grade:
            modifiers.append(steel_grade)
        if alumina_content:
            modifiers.append(alumina_content)
        if belt_width:
            modifiers.append(belt_width)
        if tensile_rating:
            modifiers.append(tensile_rating)

        # Collect any additional dynamic attributes from technical_attributes
        for m in materials:
            ext = getattr(m, "technical_attributes", None) or {}
            if isinstance(ext, dict):
                for k, v in ext.items():
                    if v and str(v).strip() and not k.startswith("_") and k not in ("item_noun", "raw_preprocessed"):
                        clean_v = f"{k.replace('_', ' ').upper()}: {str(v).strip().upper()}"
                        if clean_v not in modifiers and str(v).strip().upper() not in modifiers:
                            modifiers.append(clean_v)

        if modifiers:
            standardized_desc = f"{item_noun}, {', '.join(modifiers[:8])}"
            mod_str = ", ".join(modifiers)
        else:
            standardized_desc = item_noun
            mod_str = ""

        canon_dict = {
            "item_noun": item_noun,
            "nominal_size": nominal_size,
            "pressure_class": pressure_class,
            "moc": moc,
            "schedule": schedule,
            "end_connection": end_connection,
            "standard_spec": standard_spec,
            "voltage_rating": voltage_rating,
            "current_rating": current_rating,
            "thread_size": thread_size,
            "length": length,
            "steel_grade": steel_grade,
            "alumina_content": alumina_content,
            "belt_width": belt_width,
            "tensile_rating": tensile_rating
        }
        # Filter None
        clean_canon = {k: v for k, v in canon_dict.items() if v is not None}

        return {
            "standardized_description": standardized_desc,
            "item_noun": item_noun,
            "modifier": mod_str,
            "nominal_size": nominal_size,
            "pressure_class": pressure_class,
            "moc": moc,
            "schedule": schedule,
            "end_connection": end_connection,
            "standard_spec": standard_spec,
            "base_uom": base_uom,
            "technical_attributes": clean_canon,
            "canonical_attributes": clean_canon
        }

    @staticmethod
    def create_version_snapshot(
        db,
        golden_record_id: int,
        changed_by_user_id: Optional[int] = None,
        change_summary: str = "Golden Record revision"
    ):
        """
        Captures an immutable snapshot in GoldenRecordVersion and increments version_number.
        """
        from app.models.models import GoldenRecord, GoldenRecordVersion

        gr = db.query(GoldenRecord).filter(GoldenRecord.id == golden_record_id).first()
        if not gr:
            return None

        # Create version record
        version_entry = GoldenRecordVersion(
            golden_record_id=gr.id,
            version_number=gr.version_number,
            standardized_description=gr.standardized_description,
            technical_attributes=gr.technical_attributes or gr.canonical_attributes or {},
            changed_by_user_id=changed_by_user_id,
            change_summary=change_summary
        )
        db.add(version_entry)
        gr.version_number += 1
        db.flush()
        return version_entry

    @staticmethod
    def rollback_to_version(
        db,
        golden_record_id: int,
        target_version_number: int,
        rolled_back_by_user_id: Optional[int] = None
    ) -> Optional[Any]:
        """
        Rolls back a Golden Record to a prior historical version snapshot with audit logging.
        """
        from app.models.models import GoldenRecord, GoldenRecordVersion

        gr = db.query(GoldenRecord).filter(GoldenRecord.id == golden_record_id).first()
        if not gr:
            return None

        ver = db.query(GoldenRecordVersion).filter(
            GoldenRecordVersion.golden_record_id == golden_record_id,
            GoldenRecordVersion.version_number == target_version_number
        ).first()

        if not ver:
            return None

        # Snapshot current state before rolling back
        GoldenRecordService.create_version_snapshot(
            db, golden_record_id, rolled_back_by_user_id,
            f"Automated pre-rollback snapshot before restoring v{target_version_number}"
        )

        # Restore state
        gr.standardized_description = ver.standardized_description
        gr.technical_attributes = ver.technical_attributes
        gr.canonical_attributes = ver.technical_attributes
        db.flush()
        return gr

    @classmethod
    def promote_singleton_materials(
        cls,
        db,
        cpse_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Singleton Canonical Promotion for Single-CPSE Mode:
        For active materials not in any cluster and not yet mapped in Crosswalk,
        synthesizes ISO 8000 standardized description, mints an authoritative
        Verhoeff CNMC code, and registers the local code in Crosswalk with mapping_type="IDENTICAL".
        Ensures 100% of single-CPSE items get standardized without manual review intervention.
        """
        from app.models.models import Material, ReviewQueue, MatchCandidate, GoldenRecord, CNMCCode, Crosswalk
        from app.services.governance.cnmc_minter import CNMCMinter
        from app.services.governance.crosswalk_service import CrosswalkService
        from app.services.governance.audit_service import AuditService

        # 1. Existing crosswalked material IDs
        crosswalked_mat_ids = set(
            r[0] for r in db.query(Crosswalk.material_id).filter(Crosswalk.material_id.isnot(None)).all()
        )

        # 2. Material IDs that are part of pending ReviewQueue clusters
        pending_rq_clusters = [
            rq.cluster_group_id for rq in db.query(ReviewQueue).filter(ReviewQueue.status == "PENDING").all()
        ]
        pending_cluster_mat_ids = set()
        if pending_rq_clusters:
            cands = db.query(MatchCandidate).filter(MatchCandidate.cluster_group_id.in_(pending_rq_clusters)).all()
            for c in cands:
                pending_cluster_mat_ids.add(c.material_a_id)
                pending_cluster_mat_ids.add(c.material_b_id)

        # 3. Active materials query
        query = db.query(Material).filter(Material.status == "ACTIVE")
        if cpse_id:
            query = query.filter(Material.cpse_id == cpse_id)
        materials = query.all()

        promoted = []
        for m in materials:
            if m.id in crosswalked_mat_ids or m.id in pending_cluster_mat_ids:
                continue

            # Synthesize ISO 8000 description
            synth = cls.synthesize_iso8000_description([m])
            final_desc = synth["standardized_description"]
            if len(final_desc) > 500:
                final_desc = final_desc[:497] + "..."

            golden = GoldenRecord(
                review_queue_id=None,
                standardized_description=final_desc,
                item_noun=synth["item_noun"],
                modifier=synth["modifier"],
                category_code=m.category_code or "GENERAL",
                nominal_size=synth["nominal_size"],
                pressure_class=synth["pressure_class"],
                moc=synth["moc"],
                schedule=synth["schedule"],
                end_connection=synth["end_connection"],
                standard_spec=synth["standard_spec"],
                base_uom=synth["base_uom"],
                technical_attributes=synth.get("technical_attributes", {}),
                canonical_attributes=synth.get("canonical_attributes", {})
            )
            db.add(golden)
            db.flush()

            # Mint single-authority Verhoeff CNMC code
            cnmc_code_str = CNMCMinter.mint_next_cnmc(db, golden.id)
            cnmc_obj = db.query(CNMCCode).filter(CNMCCode.code == cnmc_code_str).first()

            # Register in Crosswalk as IDENTICAL
            CrosswalkService.register_mappings(db, cnmc_obj.id, [m], mapping_type="IDENTICAL")

            # Audit trail
            try:
                AuditService.log_action(
                    db,
                    action="SINGLETON_CANONICAL_PROMOTION",
                    entity_type="CNMC_CODE",
                    entity_id=cnmc_code_str,
                    user_id=1,
                    evidence={
                        "material_id": m.id,
                        "material_code": m.material_code,
                        "cpse_id": m.cpse_id,
                        "mapping_type": "IDENTICAL",
                        "golden_record": final_desc
                    }
                )
            except Exception:
                pass

            crosswalked_mat_ids.add(m.id)
            promoted.append({"material_id": m.id, "material_code": m.material_code, "cnmc": cnmc_code_str})

        db.commit()
        return {
            "status": "SUCCESS",
            "promoted_count": len(promoted),
            "items": promoted
        }
