import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.services.normalization.uom_normalizer import UOMNormalizer

class TestUOMNormalizer(unittest.TestCase):
    def test_uom_standardization(self):
        self.assertEqual(UOMNormalizer.normalize_uom("Nos"), "EA")
        self.assertEqual(UOMNormalizer.normalize_uom("NUMBERS"), "EA")
        self.assertEqual(UOMNormalizer.normalize_uom("pcs"), "EA")
        self.assertEqual(UOMNormalizer.normalize_uom("MTR"), "MTR")
        self.assertEqual(UOMNormalizer.normalize_uom("METER"), "MTR")
        self.assertEqual(UOMNormalizer.normalize_uom("KGS"), "KG")

    def test_packaging_multiplier_extraction(self):
        # 18kg Bucket
        mult1, base1 = UOMNormalizer.extract_packaging_factor("GREASE MOBILITH SHC 100 - 18KG BUCKET", "BKT")
        self.assertEqual(mult1, 18.0)
        self.assertEqual(base1, "KG")

        # 180kg Drum
        mult2, base2 = UOMNormalizer.extract_packaging_factor("MOBILITH SHC 100 - 180KG DRUM", "DRM")
        self.assertEqual(mult2, 180.0)
        self.assertEqual(base2, "KG")

        # Standard piece without packaging
        mult3, base3 = UOMNormalizer.extract_packaging_factor("VALVE GATE 6IN 300# CS FLG", "Nos")
        self.assertEqual(mult3, 1.0)
        self.assertEqual(base3, "EA")

        # Bearing with brass cage suffix M (must not be converted to meters)
        mult4, base4 = UOMNormalizer.extract_packaging_factor("SKF BEARING 6205 M", "EA")
        self.assertEqual(mult4, 1.0)
        self.assertEqual(base4, "EA")

        # Fasteners count pack
        mult5, base5 = UOMNormalizer.extract_packaging_factor("HEX BOLT M16 X 50 PACK OF 100 NOS", "NOS")
        self.assertEqual(mult5, 100.0)
        self.assertEqual(base5, "EA")

if __name__ == "__main__":
    unittest.main()
