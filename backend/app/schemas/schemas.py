from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# ----------------- Auth & User -----------------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    cpse_code: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    cpse_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

# ----------------- CPSE -----------------
class CPSEResponse(BaseModel):
    id: int
    code: str
    name: str

    class Config:
        from_attributes = True

# ----------------- Ingestion & Mapping -----------------
class ColumnMappingItem(BaseModel):
    source_column: str
    target_field: str
    confidence: float = 1.0
    is_validated: bool = True

class ColumnMappingDetectResponse(BaseModel):
    file_name: str
    detected_columns: List[str]
    suggested_mappings: Dict[str, str] # source -> target
    confidence_scores: Dict[str, float]
    preview_rows: List[Dict[str, Any]]

class IngestionBatchResponse(BaseModel):
    id: int
    cpse_id: int
    cpse_code: Optional[str] = None
    file_name: str
    total_rows: int
    processed_rows: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# ----------------- Normalization & Extracted Specs -----------------
class ExtractedSpecs(BaseModel):
    item_noun: Optional[str] = None
    nominal_size: Optional[str] = None
    pressure_class: Optional[str] = None
    moc: Optional[str] = None
    schedule: Optional[str] = None
    end_connection: Optional[str] = None
    standard_spec: Optional[str] = None
    part_number: Optional[str] = None
    clean_part_number: Optional[str] = None
    clearance_suffix: Optional[str] = None
    is_kit_or_assembly: bool = False
    package_multiplier: float = 1.0
    base_uom: str = "EA"
    extra_attributes: Dict[str, Any] = Field(default_factory=dict)

class MaterialResponse(BaseModel):
    id: int
    cpse_id: int
    cpse_code: Optional[str] = None
    material_code: str
    short_description: str
    uom: str
    base_uom: str
    package_multiplier: float
    item_noun: Optional[str] = None
    nominal_size: Optional[str] = None
    pressure_class: Optional[str] = None
    moc: Optional[str] = None
    schedule: Optional[str] = None
    end_connection: Optional[str] = None
    standard_spec: Optional[str] = None
    clean_part_number: Optional[str] = None
    clearance_suffix: Optional[str] = None
    is_kit_or_assembly: bool
    status: str
    last_po_price: Optional[float] = None
    vendor_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# ----------------- Matching & Scoring -----------------
class ScoreBreakdown(BaseModel):
    semantic_score: float
    attribute_score: float
    procurement_score: float
    composite_score: float
    safety_veto: bool
    veto_reason: Optional[str] = None
    confidence_tier: str

class MatchCandidateResponse(BaseModel):
    id: int
    cluster_group_id: str
    material_a: MaterialResponse
    material_b: MaterialResponse
    scores: ScoreBreakdown
    created_at: datetime

class ClusterMaterialItem(BaseModel):
    material: MaterialResponse
    vendor_name: Optional[str] = None
    last_po_price: Optional[float] = None
    po_quantity: Optional[float] = None
    specs: ExtractedSpecs

class ClusterCardResponse(BaseModel):
    cluster_group_id: str
    category_code: Optional[str] = None
    category_name: Optional[str] = None
    confidence_tier: str
    composite_score: float
    scores: ScoreBreakdown
    status: str
    materials: List[ClusterMaterialItem]
    proposed_golden_record: Optional[str] = None
    reviewer_notes: Optional[str] = None
    decision_type: Optional[str] = None

class ReviewActionRequest(BaseModel):
    cluster_group_id: str
    decision_type: str # IDENTICAL, SUBSTITUTE, REJECT, SPLIT
    custom_golden_description: Optional[str] = None
    selected_material_ids: Optional[List[int]] = None
    reviewer_notes: Optional[str] = None

# ----------------- Golden Record & CNMC -----------------
class GoldenRecordResponse(BaseModel):
    id: int
    standardized_description: str
    item_noun: str
    modifier: Optional[str] = None
    nominal_size: Optional[str] = None
    pressure_class: Optional[str] = None
    moc: Optional[str] = None
    schedule: Optional[str] = None
    end_connection: Optional[str] = None
    standard_spec: Optional[str] = None
    base_uom: str
    created_at: datetime

    class Config:
        from_attributes = True

class CrosswalkItem(BaseModel):
    cpse_code: str
    local_material_code: str
    short_description: str
    mapping_type: str
    last_po_price: Optional[float] = None
    uom: str

class CNMCDetailResponse(BaseModel):
    cnmc_code: str
    golden_record: GoldenRecordResponse
    crosswalk_links: List[CrosswalkItem]
    total_spend: float = 0.0
    total_volume: float = 0.0
    potential_savings: float = 0.0
    issued_at: datetime

class ReverseLookupResponse(BaseModel):
    query_code: str
    cpse_code: str
    found: bool
    cnmc_details: Optional[CNMCDetailResponse] = None

# ----------------- Dashboard & Analytics -----------------
class DashboardSummaryResponse(BaseModel):
    standardization_coverage: Dict[str, float] # National, CPCL, IOCL, BPCL
    duplicate_detection: Dict[str, int] # identical, near_dupes, substitutes, total_resolved
    review_queue_counts: Dict[str, int] # pending_high, pending_med, approved_today, rejected
    collaborative_savings_total_lakhs: float
    active_batch_count: int
    total_materials_ingested: int
    total_cnmc_minted: int
    material_group_distribution: Dict[str, float] = {}

class DemandSavingsItem(BaseModel):
    cnmc_code: str
    material_description: str
    cpcl_volume: float
    iocl_volume: float
    bpcl_volume: float
    total_volume: float
    base_uom: str
    avg_price: float
    max_price: float
    min_price: float
    estimated_savings_lakhs: float

class QualityHeatmapItem(BaseModel):
    field_name: str
    cpcl_pct: float
    iocl_pct: float
    bpcl_pct: float

class VennOverlapData(BaseModel):
    cpcl_only: int
    iocl_only: int
    bpcl_only: int
    cpcl_iocl: int
    iocl_bpcl: int
    cpcl_bpcl: int
    all_three: int
