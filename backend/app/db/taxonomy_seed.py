from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.models import TaxonomyNode, AttributeDictionary

MULTI_SECTOR_TAXONOMY = [
    # 1. OIL & GAS
    {
        "standard": "ECLASS_14_0",
        "code": "37-01-01-01",
        "name": "Gate Valve (Industrial Flow Control)",
        "sector": "OIL_AND_GAS",
        "level": 3,
        "description": "Industrial gate valves for refinery and upstream piping systems",
        "attributes": [
            {"key": "nominal_size", "label": "Nominal Pipe Size", "type": "STRING", "uom": "INCH/MM", "is_safety": True},
            {"key": "pressure_class", "label": "Pressure Rating Class", "type": "STRING", "uom": "CLASS/PN", "is_safety": True},
            {"key": "moc", "label": "Material of Construction", "type": "STRING", "uom": "ASTM", "is_safety": True},
            {"key": "end_connection", "label": "End Connection Type", "type": "STRING", "uom": None, "is_safety": False},
            {"key": "standard_spec", "label": "Design Standard Spec", "type": "STRING", "uom": "API/ASME", "is_safety": False}
        ]
    },
    {
        "standard": "ECLASS_14_0",
        "code": "37-02-01-01",
        "name": "Seamless Carbon & Alloy Steel Pipe",
        "sector": "OIL_AND_GAS",
        "level": 3,
        "description": "Seamless steel pipe for high-pressure process fluid transport",
        "attributes": [
            {"key": "nominal_size", "label": "Nominal Pipe Size", "type": "STRING", "uom": "INCH/MM", "is_safety": True},
            {"key": "schedule", "label": "Wall Thickness Schedule", "type": "STRING", "uom": "SCH", "is_safety": True},
            {"key": "moc", "label": "Material Specification", "type": "STRING", "uom": "ASTM", "is_safety": True}
        ]
    },
    {
        "standard": "ECLASS_14_0",
        "code": "23-05-01-01",
        "name": "Deep Groove & Spherical Roller Bearing",
        "sector": "OIL_AND_GAS",
        "level": 3,
        "description": "Rotary anti-friction machinery bearings",
        "attributes": [
            {"key": "clean_part_number", "label": "OEM Basic Part Number", "type": "STRING", "uom": None, "is_safety": True},
            {"key": "clearance_suffix", "label": "Internal Radial Clearance", "type": "STRING", "uom": None, "is_safety": True},
            {"key": "brand", "label": "Manufacturer Brand", "type": "STRING", "uom": None, "is_safety": False}
        ]
    },

    # 2. POWER SECTOR
    {
        "standard": "ECLASS_14_0",
        "code": "27-03-01-01",
        "name": "Step-Down Power & Distribution Transformer",
        "sector": "POWER",
        "level": 3,
        "description": "High-voltage transmission and substation distribution transformers",
        "attributes": [
            {"key": "primary_voltage", "label": "Primary Voltage Rating", "type": "STRING", "uom": "KV/V", "is_safety": True},
            {"key": "secondary_voltage", "label": "Secondary Voltage Rating", "type": "STRING", "uom": "KV/V", "is_safety": True},
            {"key": "power_rating", "label": "Apparent Power Capacity", "type": "STRING", "uom": "MVA/KVA", "is_safety": True},
            {"key": "cooling_type", "label": "Cooling Mechanism", "type": "STRING", "uom": None, "is_safety": False}
        ]
    },
    {
        "standard": "ECLASS_14_0",
        "code": "27-02-01-01",
        "name": "High & Medium Voltage XLPE Armoured Power Cable",
        "sector": "POWER",
        "level": 3,
        "description": "Cross-linked polyethylene insulated armoured transmission cable",
        "attributes": [
            {"key": "voltage_rating", "label": "Rated Operating Voltage", "type": "STRING", "uom": "KV/V", "is_safety": True},
            {"key": "conductor_cross_section", "label": "Cross Section Area", "type": "STRING", "uom": "SQ_MM", "is_safety": True},
            {"key": "core_count", "label": "Number of Conductors / Cores", "type": "STRING", "uom": "CORE", "is_safety": True},
            {"key": "conductor_material", "label": "Conductor Metallurgy (Cu/Al)", "type": "STRING", "uom": None, "is_safety": True}
        ]
    },
    {
        "standard": "ECLASS_14_0",
        "code": "27-37-04-01",
        "name": "Air Circuit Breaker (ACB) & Vacuum Circuit Breaker (VCB)",
        "sector": "POWER",
        "level": 3,
        "description": "Substation switchgear protective circuit breakers",
        "attributes": [
            {"key": "current_rating", "label": "Rated Continuous Current", "type": "STRING", "uom": "A/KA", "is_safety": True},
            {"key": "voltage_rating", "label": "Rated Operational Voltage", "type": "STRING", "uom": "KV/V", "is_safety": True},
            {"key": "breaking_capacity", "label": "Short Circuit Breaking Capacity", "type": "STRING", "uom": "KA", "is_safety": True},
            {"key": "pole_count", "label": "Number of Poles", "type": "STRING", "uom": "POLE", "is_safety": True}
        ]
    },

    # 3. STEEL SECTOR
    {
        "standard": "ECLASS_14_0",
        "code": "21-01-01-01",
        "name": "High-Alumina Refractory Firebrick & Lining",
        "sector": "STEEL",
        "level": 3,
        "description": "Blast furnace and ladle refractory insulation bricks",
        "attributes": [
            {"key": "alumina_content", "label": "Al2O3 Purity Percentage", "type": "STRING", "uom": "%", "is_safety": True},
            {"key": "max_service_temp", "label": "Maximum Service Temperature", "type": "STRING", "uom": "DEG_C", "is_safety": True},
            {"key": "cold_crushing_strength", "label": "Compressive Strength (CCS)", "type": "STRING", "uom": "KG/CM2", "is_safety": False}
        ]
    },
    {
        "standard": "ECLASS_14_0",
        "code": "21-02-01-01",
        "name": "Thermo-Mechanically Treated (TMT) Rebar & Billets",
        "sector": "STEEL",
        "level": 3,
        "description": "Structural reinforcement steel rebar for construction & heavy infrastructure",
        "attributes": [
            {"key": "steel_grade", "label": "Yield Strength Grade (Fe 500D / Fe 550D)", "type": "STRING", "uom": "GRADE", "is_safety": True},
            {"key": "nominal_diameter", "label": "Bar Diameter", "type": "STRING", "uom": "MM", "is_safety": True},
            {"key": "carbon_equivalent", "label": "Max Carbon Equivalent (CE)", "type": "STRING", "uom": "%", "is_safety": True}
        ]
    },

    # 4. MINING SECTOR
    {
        "standard": "ECLASS_14_0",
        "code": "36-01-01-01",
        "name": "Heavy Excavator & Dragline Bucket Tooth",
        "sector": "MINING",
        "level": 3,
        "description": "Wear-resistant ground engaging tools (G.E.T.) for open-cast shovels",
        "attributes": [
            {"key": "adapter_fitment_system", "label": "Tooth Adapter / Pin Profile", "type": "STRING", "uom": None, "is_safety": True},
            {"key": "hardness_rating", "label": "Brinell Hardness (HBW)", "type": "STRING", "uom": "HBW", "is_safety": False},
            {"key": "shovel_capacity", "label": "Compatible Bucket Volume", "type": "STRING", "uom": "CU_MTR", "is_safety": False}
        ]
    },
    {
        "standard": "ECLASS_14_0",
        "code": "36-02-01-01",
        "name": "Steel-Cord Heavy Conveyor Belting",
        "sector": "MINING",
        "level": 3,
        "description": "High-tensile overland coal and mineral haulage conveyor belts",
        "attributes": [
            {"key": "belt_width", "label": "Belt Width", "type": "STRING", "uom": "MM", "is_safety": True},
            {"key": "tensile_rating", "label": "Tensile Strength Rating", "type": "STRING", "uom": "N/MM", "is_safety": True},
            {"key": "cover_grade", "label": "Rubber Abrasion Cover Grade", "type": "STRING", "uom": None, "is_safety": False}
        ]
    },

    # 5. HEAVY ENGINEERING
    {
        "standard": "ECLASS_14_0",
        "code": "38-01-01-01",
        "name": "Superheater & Economizer Boiler Tube",
        "sector": "HEAVY_ENG",
        "level": 3,
        "description": "High-pressure thermal boiler seamless alloy steel heat exchanger tubing",
        "attributes": [
            {"key": "outer_diameter", "label": "Tube Outside Diameter (OD)", "type": "STRING", "uom": "MM", "is_safety": True},
            {"key": "wall_thickness", "label": "Minimum Wall Thickness", "type": "STRING", "uom": "MM", "is_safety": True},
            {"key": "moc", "label": "Boiler Code Metallurgy", "type": "STRING", "uom": "ASME_SA213", "is_safety": True}
        ]
    }
]

def seed_multi_sector_taxonomies(db: Session):
    for item in MULTI_SECTOR_TAXONOMY:
        node = db.query(TaxonomyNode).filter(TaxonomyNode.code == item["code"]).first()
        if not node:
            node = TaxonomyNode(
                standard=item["standard"],
                code=item["code"],
                name=item["name"],
                sector=item["sector"],
                level=item["level"],
                description=item["description"]
            )
            db.add(node)
            db.flush()
            
            for attr in item["attributes"]:
                attr_obj = AttributeDictionary(
                    taxonomy_node_id=node.id,
                    attribute_key=attr["key"],
                    attribute_label=attr["label"],
                    data_type=attr["type"],
                    unit_of_measure=attr.get("uom"),
                    is_critical_safety_invariant=attr.get("is_safety", False)
                )
                db.add(attr_obj)
    db.commit()
