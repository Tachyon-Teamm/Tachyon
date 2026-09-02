import unittest
import sys
import os
import io
import re
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.v1.ingestion import STANDARD_HEADER_SYNONYMS, read_dataframe_resilient
from app.tasks.ingestion_tasks import sanitize_price

class TestChunk2ColumnMapping(unittest.TestCase):
    """
    Dedicated test suite for Chunk 2 (Column Mapping, Delimiter/Encoding Resilience,
    Two-Pass Word-Boundary Matching, Price Sanitization, and 1:1 Invariant Validation).
    """

    def test_two_pass_synonym_matching_exact_over_substring(self):
        """
        Verify that exact matches (e.g. HSN_CODE, UNIT_PRICE) are NOT hijacked
        by substring matches of earlier categories (material_code with CODE, uom with UNIT).
        """
        test_columns = [
            ("MATERIAL_NO", "material_code"),
            ("MATNR", "material_code"),
            ("MATERIAL_NUMBER", "material_code"),
            ("ITEM_SPEC", "short_description"),
            ("MAKTX", "short_description"),
            ("SHORT_TEXT", "short_description"),
            ("UNIT_OF_MEASURE", "uom"),
            ("MEINS", "uom"),
            ("PURCHASE_ORDER_UNIT", "uom"),
            ("LAST_PO_PRICE", "base_price"),
            ("NETPR", "base_price"),
            ("UNIT_PRICE", "base_price"),  # Crucial: should map to base_price, NOT uom!
            ("VENDOR_NAME", "vendor_name"),
            ("NAME1", "vendor_name"),
            ("HSN_CODE", "hsn_code"),      # Crucial: should map to hsn_code, NOT material_code!
            ("SAC_CODE", "hsn_code"),
            ("TAX_CODE", "hsn_code"),
        ]

        columns = [c[0] for c in test_columns]
        suggested = {}
        confidences = {}

        # Pass 1: Strict Exact Match
        for col in columns:
            col_clean = re.sub(r'[^A-Z0-9]', '_', str(col).strip().upper())
            col_clean = re.sub(r'_+', '_', col_clean).strip('_')
            matched = False
            for target_field, synonyms in STANDARD_HEADER_SYNONYMS.items():
                for syn in synonyms:
                    syn_clean = re.sub(r'[^A-Z0-9]', '_', syn.upper()).strip('_')
                    if col_clean == syn_clean or str(col).strip().upper() == syn:
                        suggested[col] = target_field
                        confidences[col] = 0.98
                        matched = True
                        break
                if matched:
                    break

        # Pass 2: Word-Boundary Regex Disambiguation
        category_order = ["hsn_code", "base_price", "vendor_name", "short_description", "uom", "material_code"]
        for col in columns:
            if col in suggested:
                continue
            col_upper = str(col).strip().upper()
            matched = False
            for target_field in category_order:
                synonyms = STANDARD_HEADER_SYNONYMS[target_field]
                for syn in synonyms:
                    pattern = r'\b' + re.escape(syn.upper()) + r'\b'
                    if re.search(pattern, col_upper):
                        suggested[col] = target_field
                        confidences[col] = 0.90
                        matched = True
                        break
                if matched:
                    break
            if not matched:
                suggested[col] = "unmapped"
                confidences[col] = 0.50

        for col_name, expected_target in test_columns:
            self.assertEqual(
                suggested.get(col_name), 
                expected_target, 
                f"Column '{col_name}' mapped to '{suggested.get(col_name)}', expected '{expected_target}'"
            )

    def test_price_sanitizer_robustness(self):
        """
        Verify that price sanitizer cleanly extracts numeric values from messy real-world strings.
        """
        self.assertEqual(sanitize_price("12500.0"), 12500.0)
        self.assertEqual(sanitize_price("12,500.00"), 12500.0)
        self.assertEqual(sanitize_price("₹ 10,800.50"), 10800.5)
        self.assertEqual(sanitize_price("$450.00"), 450.0)
        self.assertEqual(sanitize_price(""), 0.0)
        self.assertEqual(sanitize_price("N/A"), 0.0)
        self.assertEqual(sanitize_price(None), 0.0)
        self.assertEqual(sanitize_price(float("nan")), 0.0)

    def test_one_to_one_mapping_validation(self):
        """
        Verify detection of duplicate target assignments.
        """
        valid_mapping = {
            "MATERIAL_NO": "material_code",
            "ITEM_SPEC": "short_description",
            "UOM": "uom",
            "PRICE": "base_price",
            "VENDOR": "vendor_name",
            "HSN": "hsn_code",
            "EXTRA_COL": "unmapped"
        }
        active_valid = {k: v for k, v in valid_mapping.items() if v != "unmapped"}
        target_counts_valid = {}
        for s, t in active_valid.items():
            target_counts_valid.setdefault(t, []).append(s)
        duplicates_valid = {t: cols for t, cols in target_counts_valid.items() if len(cols) > 1}
        self.assertEqual(len(duplicates_valid), 0)

        # Invalid: both MATERIAL_NO and HSN_CODE mapped to material_code
        invalid_mapping = {
            "MATERIAL_NO": "material_code",
            "HSN_CODE": "material_code",
            "ITEM_SPEC": "short_description"
        }
        active_invalid = {k: v for k, v in invalid_mapping.items() if v != "unmapped"}
        target_counts_invalid = {}
        for s, t in active_invalid.items():
            target_counts_invalid.setdefault(t, []).append(s)
        duplicates_invalid = {t: cols for t, cols in target_counts_invalid.items() if len(cols) > 1}
        self.assertIn("material_code", duplicates_invalid)
        self.assertEqual(len(duplicates_invalid["material_code"]), 2)

if __name__ == "__main__":
    unittest.main()
