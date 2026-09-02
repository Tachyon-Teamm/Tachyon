from typing import Dict, Any, List, Optional
try:
    from fastapi import APIRouter, Depends, HTTPException
except ImportError:
    class _DummyRouter:
        def __init__(self, *args, **kwargs): pass
        def get(self, *args, **kwargs): return lambda f: f
        def post(self, *args, **kwargs): return lambda f: f
    APIRouter = _DummyRouter  # type: ignore
    Depends = lambda f: f  # type: ignore
    HTTPException = Exception  # type: ignore

try:
    from app.core.database import get_sync_session
    from app.models.models import Crosswalk, CNMCCode, GoldenRecord, Material, CPSE
except ImportError:
    get_sync_session = None  # type: ignore
    class _DummyCol:
        def in_(self, *args): return True
        def __eq__(self, other): return True
    class Crosswalk:
        local_material_code = _DummyCol()
        cpse = _DummyCol()
    class CNMCCode:
        code = _DummyCol()
    class GoldenRecord: pass  # type: ignore
    class Material: pass  # type: ignore
    class CPSE:
        code = _DummyCol()

router = APIRouter(prefix="/integration/sap", tags=["SAP S/4HANA & MDG Integration"])

@router.get("/lookup/{local_code}")
def lookup_by_local_code(local_code: str, cpse_code: Optional[str] = None, db: Optional[Any] = None) -> Dict[str, Any]:
    """
    Sub-10ms Real-Time Reverse Code Resolution Endpoint for SAP ERP:
    Resolves a CPSE local material code into its canonical CNMC national code.
    """
    close_db = False
    if db is None:
        sync_db = get_sync_session()
        close_db = True
    else:
        sync_db = db

    try:
        query = sync_db.query(Crosswalk).filter(Crosswalk.local_material_code == local_code)
        if cpse_code:
            query = query.join(CPSE).filter(CPSE.code == cpse_code)

        entry = query.first()
        if not entry:
            raise HTTPException(status_code=404, detail=f"No CNMC mapping found for material code: {local_code}")

        cnmc = entry.cnmc
        golden = cnmc.golden_record if cnmc else None

        return {
            "status": "MAPPED",
            "local_material_code": entry.local_material_code,
            "cpse_code": entry.cpse.code if entry.cpse else None,
            "cnmc_code": cnmc.code if cnmc else None,
            "mapping_type": entry.mapping_type,
            "standardized_description": golden.standardized_description if golden else None,
            "base_uom": golden.base_uom if golden else "EA",
            "version": golden.version_number if golden else 1,
            "technical_attributes": golden.technical_attributes if golden else {}
        }
    finally:
        if close_db:
            sync_db.close()

@router.post("/idoc-export")
def generate_matmas_idoc(cnmc_codes: Optional[List[str]] = None, db: Optional[Any] = None) -> Dict[str, Any]:
    """
    SAP S/4HANA Clean Core MATMAS05 IDoc Generator:
    Produces structured SAP XML/JSON segments (E1MARAM, E1MAKTM) for LSMW/LTMC mass ingestion.
    """
    close_db = False
    if db is None:
        sync_db = get_sync_session()
        close_db = True
    else:
        sync_db = db

    try:
        query = sync_db.query(GoldenRecord).join(CNMCCode)
        if cnmc_codes:
            query = query.filter(CNMCCode.code.in_(cnmc_codes))

        records = query.all()
        idocs = []

        for r in records:
            cnmc_str = r.cnmc_code.code if r.cnmc_code else f"CNMC-{r.id}"
            idoc_segment = {
                "IDOC": {
                    "EDI_DC40": {
                        "MESTYP": "MATMAS",
                        "IDOCTYP": "MATMAS05",
                        "SNDPRN": "UNIMM_NATIONAL",
                        "RCVPRN": "SAP_S4HANA"
                    },
                    "E1MARAM": {
                        "MATNR": cnmc_str,
                        "MEINS": r.base_uom or "EA",
                        "MTART": "ERSA", # Spare parts / MRO
                        "E1MAKTM": {
                            "SPRAS": "E",
                            "MAKTX": (r.standardized_description or "")[:40] # SAP 40-char short text
                        },
                        "E1MARA1": {
                            "LONG_TEXT": r.standardized_description,
                            "VERSION": r.version_number,
                            "TECHNICAL_SPECS": r.technical_attributes or {}
                        }
                    }
                }
            }
            idocs.append(idoc_segment)

        return {
            "status": "SUCCESS",
            "idoc_type": "MATMAS05",
            "total_idocs": len(idocs),
            "payloads": idocs
        }
    finally:
        if close_db:
            sync_db.close()
