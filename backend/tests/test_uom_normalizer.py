import pytest
from app.services.normalization.uom_normalizer import UOMNormalizer

def test_uom_standardization():
    assert UOMNormalizer.normalize_uom("Nos") == "EA"
    assert UOMNormalizer.normalize_uom("NUMBERS") == "EA"
    assert UOMNormalizer.normalize_uom("pcs") == "EA"
    assert UOMNormalizer.normalize_uom("MTR") == "MTR"
    assert UOMNormalizer.normalize_uom("METER") == "MTR"
    assert UOMNormalizer.normalize_uom("KGS") == "KG"

def test_packaging_multiplier_extraction():
    # 18kg Bucket
    mult1, base1 = UOMNormalizer.extract_packaging_factor("GREASE MOBILITH SHC 100 - 18KG BUCKET", "BKT")
    assert mult1 == 18.0
    assert base1 == "KG"

    # 180kg Drum
    mult2, base2 = UOMNormalizer.extract_packaging_factor("MOBILITH SHC 100 - 180KG DRUM", "DRM")
    assert mult2 == 180.0
    assert base2 == "KG"

    # Standard piece without packaging
    mult3, base3 = UOMNormalizer.extract_packaging_factor("VALVE GATE 6IN 300# CS FLG", "Nos")
    assert mult3 == 1.0
    assert base3 == "EA"
