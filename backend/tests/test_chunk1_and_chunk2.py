import io
import pytest
from httpx import AsyncClient
from app.main import app
from app.api.v1.ingestion import STANDARD_HEADER_SYNONYMS

from starlette.testclient import TestClient

def test_chunk2_expanded_synonyms():
    assert "voltage_rating" in STANDARD_HEADER_SYNONYMS
    assert "current_rating" in STANDARD_HEADER_SYNONYMS
    assert "part_number" in STANDARD_HEADER_SYNONYMS
    assert "VOLTAGE" in STANDARD_HEADER_SYNONYMS["voltage_rating"]
    assert "AMPS" in STANDARD_HEADER_SYNONYMS["current_rating"]

def test_chunk1_samples_endpoint():
    client = TestClient(app)
    res = client.get("/api/v1/ingestion/samples")
    assert res.status_code == 200
    data = res.json()
    assert "CPCL" in data
    assert "IOCL" in data
    assert "BPCL" in data
    assert "NTPC" in data
    assert "SAIL" in data
    assert data["NTPC"]["sector"] == "POWER"
    assert data["SAIL"]["sector"] == "STEEL"

def test_chunk1_detect_columns_streaming():
    client = TestClient(app)
    csv_content = (
        "MATERIAL_NO,ITEM_SPEC,UNIT_OF_MEASURE,LAST_PO_PRICE,VENDOR_NAME,HSN_CODE\n"
        "100234,VLV GATE 6IN 300# CS FLG,Nos,12500.0,L&T Valves Ltd,84818030\n"
    ).encode("utf-8")
    
    files = {"file": ("test_upload.csv", io.BytesIO(csv_content), "text/csv")}
    data = {"cpse_code": "IOCL"}
    res = client.post("/api/v1/ingestion/detect-columns", files=files, data=data)
    assert res.status_code == 200
    payload = res.json()
    assert "upload_id" in payload
    assert "detected_columns" in payload
    assert "suggested_mappings" in payload
    assert payload["suggested_mappings"]["MATERIAL_NO"] == "material_code"
    assert payload["suggested_mappings"]["ITEM_SPEC"] == "short_description"

def test_chunk2_recalculate_preview():
    client = TestClient(app)
    req_payload = {
        "preview_rows": [
            {
                "RAW_CODE": "889102",
                "RAW_DESC": "VALVE, GATE, 150MM, CL300, WCB",
                "RAW_UOM": "EA"
            }
        ],
        "mapping_config": {
            "RAW_CODE": "material_code",
            "RAW_DESC": "short_description",
            "RAW_UOM": "uom"
        }
    }
    res = client.post("/api/v1/ingestion/preview", json=req_payload)
    assert res.status_code == 200
    data = res.json()
    assert "preview_rows" in data
    assert len(data["preview_rows"]) == 1
    row = data["preview_rows"][0]
    assert "_preview_specs" in row
    assert row["_preview_specs"]["item_noun"] == "VALVE, GATE"
    assert row["_preview_specs"]["pressure_class"] == "CLASS 300#"

