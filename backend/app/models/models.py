from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, 
    Text, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base
from app.core.config import settings

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class CPSE(Base):
    __tablename__ = "cpses"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True) # Supports 200+ CPSEs across all sectors
    name = Column(String(100), nullable=False)
    sector = Column(String(50), nullable=False, default="GENERAL") # OIL_AND_GAS, POWER, STEEL, MINING, CHEMICALS, HEAVY_ENG, GENERAL
    erp_system = Column(String(50), default="SAP_S4HANA") # SAP_ECC, SAP_S4HANA, ORACLE, CUSTOM
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    
    users = relationship("User", back_populates="cpse")
    materials = relationship("Material", back_populates="cpse")
    ingestion_batches = relationship("IngestionBatch", back_populates="cpse")
    crosswalk_entries = relationship("Crosswalk", back_populates="cpse")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="viewer") # admin, reviewer, data_steward, viewer
    cpse_id = Column(Integer, ForeignKey("cpses.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    cpse = relationship("CPSE", back_populates="users")
    reviews = relationship("ReviewQueue", back_populates="reviewer")
    audit_logs = relationship("AuditLog", back_populates="user")

class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"
    
    id = Column(Integer, primary_key=True, index=True)
    cpse_id = Column(Integer, ForeignKey("cpses.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, default=0)
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    status = Column(String(30), default="PENDING") # PENDING, PROCESSING, COMPLETED, FAILED
    quality_score = Column(Float, default=1.0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    cpse = relationship("CPSE", back_populates="ingestion_batches")
    raw_materials = relationship("RawMaterial", back_populates="batch", cascade="all, delete-orphan")

class ColumnMapping(Base):
    __tablename__ = "column_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    cpse_id = Column(Integer, ForeignKey("cpses.id"), nullable=False)
    name = Column(String(100), nullable=False)
    mapping_config = Column(JSON, nullable=False) # e.g. {"MATERIAL_NO": "material_code", "ITEM_SPEC": "short_description"}
    is_default = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

class RawMaterial(Base):
    __tablename__ = "raw_materials"
    
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("ingestion_batches.id"), nullable=False)
    cpse_id = Column(Integer, ForeignKey("cpses.id"), nullable=False)
    row_index = Column(Integer, nullable=False)
    raw_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    
    batch = relationship("IngestionBatch", back_populates="raw_materials")
    material = relationship("Material", back_populates="raw_material", uselist=False)
    normalized_material = relationship("NormalizedMaterial", back_populates="raw_material", uselist=False)

class NormalizedMaterial(Base):
    """
    Silver Staging Layer: Cleansed, tokenized, and structured attributes 
    with quality score before promotion to active Material or Golden Record.
    """
    __tablename__ = "normalized_materials"
    
    id = Column(Integer, primary_key=True, index=True)
    raw_material_id = Column(Integer, ForeignKey("raw_materials.id"), nullable=True, index=True)
    cpse_id = Column(Integer, ForeignKey("cpses.id"), nullable=False, index=True)
    material_code = Column(String(50), nullable=False, index=True)
    cleaned_description = Column(String(500), nullable=False)
    base_uom = Column(String(20), default="EA")
    package_multiplier = Column(Float, default=1.0)
    category_code = Column(String(50), nullable=True, index=True)
    technical_attributes = Column(JSON, default=dict)
    quality_score = Column(Float, default=1.0) # 0.0 to 1.0 completeness/quality score
    status = Column(String(30), default="STAGED") # STAGED, NORMALIZED, PROMOTED, ERROR
    created_at = Column(DateTime, default=utc_now)
    
    cpse = relationship("CPSE")
    raw_material = relationship("RawMaterial", back_populates="normalized_material")

class TaxonomyCategory(Base):
    __tablename__ = "taxonomy_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    unspsc_code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    level = Column(Integer, default=1)
    parent_id = Column(Integer, ForeignKey("taxonomy_categories.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    parent = relationship("TaxonomyCategory", remote_side=[id])

class TaxonomyNode(Base):
    """
    Multi-Sector Hierarchical Taxonomy Node supporting eCl@ss 14.0, UNSPSC v26, and sector schemas.
    Sectors: OIL_AND_GAS, POWER, STEEL, MINING, HEAVY_ENG, CHEMICALS, GENERAL
    """
    __tablename__ = "taxonomy_nodes"
    
    id = Column(Integer, primary_key=True, index=True)
    standard = Column(String(50), default="ECLASS_14_0", index=True) # ECLASS_14_0, UNSPSC_V26, CUSTOM
    code = Column(String(50), unique=True, index=True, nullable=False) # e.g. "27-27-01-01", "401416"
    name = Column(String(200), nullable=False)
    sector = Column(String(50), default="GENERAL", index=True)
    level = Column(Integer, default=1)
    parent_id = Column(Integer, ForeignKey("taxonomy_nodes.id"), nullable=True)
    description = Column(Text, nullable=True)
    vector_embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    parent = relationship("TaxonomyNode", remote_side=[id])
    attributes = relationship("AttributeDictionary", back_populates="taxonomy_node", cascade="all, delete-orphan")

class AttributeDictionary(Base):
    """
    Dynamic attribute definitions and safety invariant rules per taxonomy node.
    """
    __tablename__ = "attribute_dictionaries"
    
    id = Column(Integer, primary_key=True, index=True)
    taxonomy_node_id = Column(Integer, ForeignKey("taxonomy_nodes.id"), nullable=True, index=True)
    attribute_key = Column(String(100), nullable=False, index=True) # e.g. "pressure_class", "primary_voltage", "tensile_strength"
    attribute_label = Column(String(150), nullable=False)
    data_type = Column(String(50), default="STRING") # STRING, NUMERIC, ENUM
    unit_of_measure = Column(String(50), nullable=True) # e.g. "BAR", "KV", "MM", "KG"
    is_critical_safety_invariant = Column(Boolean, default=False)
    veto_threshold = Column(Float, default=0.0) # 0.0 for exact equality match
    allowed_values = Column(JSON, default=list)
    created_at = Column(DateTime, default=utc_now)
    
    taxonomy_node = relationship("TaxonomyNode", back_populates="attributes")

class Material(Base):
    __tablename__ = "materials"
    
    id = Column(Integer, primary_key=True, index=True)
    raw_material_id = Column(Integer, ForeignKey("raw_materials.id"), nullable=True, index=True)
    cpse_id = Column(Integer, ForeignKey("cpses.id"), nullable=False, index=True)
    material_code = Column(String(50), nullable=False, index=True)
    short_description = Column(String(500), nullable=False)
    long_description = Column(Text, nullable=True)
    
    # Normalized Fields
    uom = Column(String(20), default="EA")
    base_uom = Column(String(20), default="EA")
    package_multiplier = Column(Float, default=1.0) # e.g. 18.0 for 18kg bucket
    
    # Extracted Deterministic Parametric Specs
    item_noun = Column(String(100), nullable=True, index=True) # e.g. VALVE, GATE / PIPE / BEARING
    nominal_size = Column(String(50), nullable=True) # e.g. 6 INCH (150 MM)
    pressure_class = Column(String(50), nullable=True) # e.g. CLASS 300#
    moc = Column(String(100), nullable=True) # e.g. ASTM A216 WCB / CS / SS316
    schedule = Column(String(50), nullable=True) # e.g. SCH 40 / SCH 80
    end_connection = Column(String(100), nullable=True) # e.g. FLANGED RF
    standard_spec = Column(String(100), nullable=True) # e.g. ASME B16.34
    part_number = Column(String(100), nullable=True)
    clean_part_number = Column(String(100), nullable=True, index=True)
    clearance_suffix = Column(String(20), nullable=True) # e.g. C3, 2RS1
    is_kit_or_assembly = Column(Boolean, default=False)
    
    category_code = Column(String(50), nullable=True, index=True)
    category_confidence = Column(Float, default=1.0)
    predicted_category_name = Column(String(200), nullable=True)
    technical_attributes = Column(JSON, default=dict)
    extracted_attributes = Column(JSON, default=dict)
    status = Column(String(30), default="ACTIVE") # ACTIVE, MERGED, SUPERSEDED
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    cpse = relationship("CPSE", back_populates="materials")
    raw_material = relationship("RawMaterial", back_populates="material")
    embedding = relationship("MaterialEmbedding", back_populates="material", uselist=False, cascade="all, delete-orphan")
    classifications = relationship("MaterialClassification", back_populates="material", cascade="all, delete-orphan")
    procurement_records = relationship("ProcurementHistory", back_populates="material", cascade="all, delete-orphan")
    crosswalk_entries = relationship("Crosswalk", back_populates="material")

    __table_args__ = (
        UniqueConstraint("cpse_id", "material_code", name="uq_cpse_material_code"),
    )

class MaterialEmbedding(Base):
    __tablename__ = "material_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, unique=True, index=True)
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=False)
    sparse_vector = Column(JSON, default=dict) # Learned sparse representation (SPLADE-v3 / BM25)
    model_name = Column(String(50), default=settings.EMBEDDING_MODEL)
    created_at = Column(DateTime, default=utc_now)
    
    material = relationship("Material", back_populates="embedding")

class MaterialClassification(Base):
    __tablename__ = "material_classifications"
    
    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("taxonomy_categories.id"), nullable=False, index=True)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=utc_now)
    
    material = relationship("Material", back_populates="classifications")
    category = relationship("TaxonomyCategory")

class ProcurementHistory(Base):
    __tablename__ = "procurement_history"
    
    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    cpse_id = Column(Integer, ForeignKey("cpses.id"), nullable=False, index=True)
    po_number = Column(String(50), nullable=True)
    po_date = Column(DateTime, nullable=True)
    vendor_name = Column(String(200), nullable=True)
    vendor_normalized = Column(String(200), nullable=True, index=True) # Normalized vendor name
    hsn_code = Column(String(20), nullable=True, index=True)
    unit_price = Column(Float, nullable=False, default=0.0)
    quantity = Column(Float, nullable=False, default=1.0)
    currency = Column(String(10), default="INR")
    total_spend = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utc_now)
    
    material = relationship("Material", back_populates="procurement_records")

class LegacyMigrationState(Base):
    __tablename__ = "legacy_migration_states"
    
    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    cpse_id = Column(Integer, ForeignKey("cpses.id"), nullable=False, index=True)
    legacy_code = Column(String(50), nullable=False)
    migration_status = Column(String(30), default="PENDING") # PENDING, MIGRATED, EXCLUDED
    notes = Column(Text, nullable=True)
    synced_at = Column(DateTime, nullable=True)

class MatchJob(Base):
    __tablename__ = "match_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    triggered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    status = Column(String(30), default="PENDING") # PENDING, RUNNING, COMPLETED, FAILED
    total_pairs_evaluated = Column(Integer, default=0)
    candidates_found = Column(Integer, default=0)
    parameters = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)
    
    candidates = relationship("MatchCandidate", back_populates="job", cascade="all, delete-orphan")

class MatchCandidate(Base):
    __tablename__ = "match_candidates"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("match_jobs.id"), nullable=False, index=True)
    material_a_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    material_b_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    
    semantic_score = Column(Float, nullable=False) # 0.0 to 1.0
    attribute_score = Column(Float, nullable=False) # 0.0 to 1.0
    procurement_score = Column(Float, nullable=False) # 0.0 to 1.0
    composite_score = Column(Float, nullable=False) # 0.0 to 1.0
    
    safety_veto = Column(Boolean, default=False)
    veto_reason = Column(String(255), nullable=True)
    suggested_route = Column(String(30), default="IDENTICAL") # IDENTICAL, SUBSTITUTE, REJECT
    confidence_tier = Column(String(20), default="LOW") # HIGH (>=90%), MEDIUM (70-89%), LOW (<70%)
    cluster_group_id = Column(String(50), nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now)
    
    job = relationship("MatchJob", back_populates="candidates")
    material_a = relationship("Material", foreign_keys=[material_a_id])
    material_b = relationship("Material", foreign_keys=[material_b_id])
    review_entry = relationship("ReviewQueue", back_populates="candidate", uselist=False)

class ReviewQueue(Base):
    __tablename__ = "review_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("match_candidates.id"), nullable=True, index=True)
    cluster_group_id = Column(String(50), nullable=False, index=True)
    category_code = Column(String(50), nullable=True)
    status = Column(String(30), default="PENDING") # PENDING, APPROVED, REJECTED, SPLIT
    confidence_tier = Column(String(20), default="HIGH")
    
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    decision_type = Column(String(30), nullable=True) # IDENTICAL, NEAR_DUPLICATE, SUBSTITUTE, REJECTED
    reviewer_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    candidate = relationship("MatchCandidate", back_populates="review_entry")
    reviewer = relationship("User", back_populates="reviews")
    golden_record = relationship("GoldenRecord", back_populates="review_queue", uselist=False)

class GoldenRecord(Base):
    __tablename__ = "golden_records"
    
    id = Column(Integer, primary_key=True, index=True)
    review_queue_id = Column(Integer, ForeignKey("review_queue.id"), nullable=True, index=True)
    
    # ISO 8000 Noun-Modifier standard description
    standardized_description = Column(String(500), nullable=False)
    item_noun = Column(String(100), nullable=False)
    modifier = Column(String(100), nullable=True)
    category_code = Column(String(50), nullable=True, index=True)
    nominal_size = Column(String(50), nullable=True)
    pressure_class = Column(String(50), nullable=True)
    moc = Column(String(100), nullable=True)
    schedule = Column(String(50), nullable=True)
    end_connection = Column(String(100), nullable=True)
    standard_spec = Column(String(100), nullable=True)
    base_uom = Column(String(20), default="EA")
    
    # Dynamic Schema-on-Read properties (PIM standard)
    technical_attributes = Column(JSON, default=dict)
    canonical_attributes = Column(JSON, default=dict)
    
    # Temporal Versioning (SCD-2)
    version_number = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    review_queue = relationship("ReviewQueue", back_populates="golden_record")
    cnmc_code = relationship("CNMCCode", back_populates="golden_record", uselist=False)
    versions = relationship("GoldenRecordVersion", back_populates="golden_record", cascade="all, delete-orphan")

class GoldenRecordVersion(Base):
    """
    Immutable historical audit snapshot for point-in-time rollback and lineage tracking.
    """
    __tablename__ = "golden_record_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    golden_record_id = Column(Integer, ForeignKey("golden_records.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    standardized_description = Column(String(500), nullable=False)
    technical_attributes = Column(JSON, default=dict)
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    change_summary = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    golden_record = relationship("GoldenRecord", back_populates="versions")
    changed_by = relationship("User")

class CNMCCode(Base):
    __tablename__ = "cnmc_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True) # e.g. CNMC-00001042-8
    golden_record_id = Column(Integer, ForeignKey("golden_records.id"), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    issued_at = Column(DateTime, default=utc_now)
    
    golden_record = relationship("GoldenRecord", back_populates="cnmc_code")
    crosswalk_links = relationship("Crosswalk", back_populates="cnmc", cascade="all, delete-orphan")
    source_substitutions = relationship("MaterialSubstitution", foreign_keys="[MaterialSubstitution.source_cnmc_id]", back_populates="source_cnmc")
    target_substitutions = relationship("MaterialSubstitution", foreign_keys="[MaterialSubstitution.target_cnmc_id]", back_populates="target_cnmc")

class Crosswalk(Base):
    __tablename__ = "crosswalk"
    
    id = Column(Integer, primary_key=True, index=True)
    cnmc_id = Column(Integer, ForeignKey("cnmc_codes.id"), nullable=False, index=True)
    cpse_id = Column(Integer, ForeignKey("cpses.id"), nullable=False, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    local_material_code = Column(String(50), nullable=False, index=True)
    # 7 Standardized Relationship Types (ISO 22745 / GS1 GDSN)
    mapping_type = Column(String(50), default="IDENTICAL") 
    # IDENTICAL, NEAR_DUPLICATE, FUNCTIONAL_EQUIVALENT, SUBSTITUTE, ALTERNATIVE_BRAND, KIT_COMPONENT, INCOMPATIBLE
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    
    cnmc = relationship("CNMCCode", back_populates="crosswalk_links")
    cpse = relationship("CPSE", back_populates="crosswalk_entries")
    material = relationship("Material", back_populates="crosswalk_entries")

    __table_args__ = (
        UniqueConstraint("cnmc_id", "cpse_id", "local_material_code", name="uq_cnmc_cpse_local_code"),
    )

class ReviewFeedback(Base):
    """
    Active Learning Telemetry Store: captures (pair, features, reviewer decision, reason)
    to auto-tune rules and export fine-tuning datasets.
    """
    __tablename__ = "review_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("match_candidates.id"), nullable=True, index=True)
    material_a_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    material_b_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    feature_vector = Column(JSON, default=dict)
    human_decision = Column(String(50), nullable=False) # APPROVED_IDENTICAL, APPROVED_SUBSTITUTE, REJECTED, SPLIT
    reviewer_notes = Column(Text, nullable=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    candidate = relationship("MatchCandidate")
    reviewer = relationship("User")

class MaterialSubstitution(Base):
    __tablename__ = "material_substitutions"
    
    id = Column(Integer, primary_key=True, index=True)
    source_cnmc_id = Column(Integer, ForeignKey("cnmc_codes.id"), nullable=False, index=True)
    target_cnmc_id = Column(Integer, ForeignKey("cnmc_codes.id"), nullable=False, index=True)
    substitution_type = Column(String(50), default="DIRECT_EQUIVALENT") # DIRECT_EQUIVALENT, UPGRADED_MATERIAL, HIGHER_PRESSURE
    engineering_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    source_cnmc = relationship("CNMCCode", foreign_keys=[source_cnmc_id], back_populates="source_substitutions")
    target_cnmc = relationship("CNMCCode", foreign_keys=[target_cnmc_id], back_populates="target_substitutions")

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True) # INGESTION, MATCHING, REVIEW_APPROVAL, CNMC_MINTED, EXPORT
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(50), nullable=True)
    evidence = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)
    
    user = relationship("User", back_populates="audit_logs")
