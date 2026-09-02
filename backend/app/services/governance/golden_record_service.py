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

        mod_str = ", ".join(modifiers)
        standardized_desc = f"{item_noun}, {mod_str}" if mod_str else item_noun

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
            "canonical_attributes": {
                "item_noun": item_noun,
                "nominal_size": nominal_size,
                "pressure_class": pressure_class,
                "moc": moc,
                "schedule": schedule,
                "end_connection": end_connection,
                "standard_spec": standard_spec,
            }
        }
