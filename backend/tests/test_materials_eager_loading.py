import pytest
from starlette.testclient import TestClient
from app.main import app

def test_materials_catalog_endpoint_performance():
    client = TestClient(app)
    res = client.get("/api/v1/materials?limit=20")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    if data:
        first = data[0]
        assert "material_code" in first
        assert "cpse_code" in first
        assert "short_description" in first

def test_materials_catalog_cpse_filter():
    client = TestClient(app)
    res = client.get("/api/v1/materials?cpse_code=IOCL&limit=5")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    for item in data:
        assert item["cpse_code"] == "IOCL"
