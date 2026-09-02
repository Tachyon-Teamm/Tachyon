import unittest
import sys
import os
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.governance.crosswalk_service import CrosswalkService
from app.services.export.sap_export import SAPExportService

class TestCrosswalkAndExport(unittest.TestCase):

    def setUp(self):
        self.mock_db = MagicMock()

    # 1. Test Reverse Lookup with Empty Input
    def test_reverse_lookup_empty_input(self):
        res = CrosswalkService.reverse_lookup(self.mock_db, "   ")
        self.assertIsNone(res)

    # 2. Test Bidirectional Lookup by National CNMC Code
    def test_bidirectional_lookup_by_cnmc_code(self):
        mock_cnmc = MagicMock()
        mock_cnmc.id = 1
        mock_cnmc.code = "CNMC-00000001-7"
        mock_cnmc.issued_at = datetime.now(timezone.utc)

        mock_golden = MagicMock()
        mock_golden.id = 10
        mock_golden.standardized_description = "VALVE, GATE, 6 INCH, CLASS 300#"
        mock_golden.item_noun = "VALVE, GATE"
        mock_golden.modifier = None
        mock_golden.nominal_size = "6 INCH"
        mock_golden.pressure_class = "CLASS 300#"
        mock_golden.moc = "WCB"
        mock_golden.schedule = None
        mock_golden.end_connection = "FLANGED"
        mock_golden.standard_spec = "ASME B16.34"
        mock_golden.base_uom = "EA"
        mock_golden.created_at = datetime.now(timezone.utc)
        mock_cnmc.golden_record = mock_golden

        # Configure mock query
        mock_query = self.mock_db.query.return_value.options.return_value.filter.return_value
        mock_query.first.return_value = mock_cnmc

        # Mock siblings query in format_cnmc_detail
        self.mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = []
        self.mock_db.query.return_value.filter.return_value.all.return_value = []

        res = CrosswalkService.reverse_lookup(self.mock_db, "CNMC-00000001-7")
        self.assertIsNotNone(res)
        self.assertEqual(res["cnmc_code"], "CNMC-00000001-7")
        self.assertEqual(res["golden_record"]["standardized_description"], "VALVE, GATE, 6 INCH, CLASS 300#")

    # 3. Test Format CNMC Detail Graceful Fallback When Procurement Missing
    def test_format_cnmc_detail_missing_procurement(self):
        mock_cnmc = MagicMock()
        mock_cnmc.id = 1
        mock_cnmc.code = "CNMC-00000001-7"
        mock_cnmc.issued_at = datetime.now(timezone.utc)

        mock_golden = MagicMock()
        mock_golden.id = 10
        mock_golden.standardized_description = "VALVE, GATE, 6 INCH"
        mock_golden.item_noun = "VALVE, GATE"
        mock_golden.modifier = None
        mock_golden.nominal_size = "6 INCH"
        mock_golden.pressure_class = "CLASS 300#"
        mock_golden.moc = "WCB"
        mock_golden.schedule = None
        mock_golden.end_connection = None
        mock_golden.standard_spec = None
        mock_golden.base_uom = "EA"
        mock_golden.created_at = None # Test null timestamp fallback
        mock_cnmc.golden_record = mock_golden

        mock_sib = MagicMock()
        mock_sib.material_id = 101
        mock_sib.local_material_code = "889102"
        mock_sib.mapping_type = "IDENTICAL"

        mock_mat = MagicMock()
        mock_mat.id = 101
        mock_mat.short_description = "VALVE GATE 6IN"
        mock_mat.package_multiplier = 1.0
        mock_mat.uom = "EA"
        mock_sib.material = mock_mat

        mock_cpse = MagicMock()
        mock_cpse.code = "IOCL"
        mock_sib.cpse = mock_cpse

        # Mock siblings return
        self.mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = [mock_sib]
        # Mock empty procurement return
        self.mock_db.query.return_value.filter.return_value.all.return_value = []

        detail = CrosswalkService.format_cnmc_detail(self.mock_db, mock_cnmc)
        self.assertEqual(detail["cnmc_code"], "CNMC-00000001-7")
        self.assertEqual(detail["total_spend"], 0.0)
        self.assertEqual(detail["potential_savings"], 0.0)
        self.assertEqual(len(detail["crosswalk_links"]), 1)
        self.assertEqual(detail["crosswalk_links"][0]["cpse_code"], "IOCL")
        self.assertEqual(detail["crosswalk_links"][0]["last_po_price"], 0.0)
        # Verify created_at fallback was assigned
        self.assertIsNotNone(detail["golden_record"]["created_at"])

    # 4. Test SAP LSMW Export Header and LONG_TEXT_ISO8000 Column
    def test_sap_lsmw_csv_headers_and_content(self):
        mock_cw = MagicMock()
        mock_cw.local_material_code = "889102"
        mock_cw.mapping_type = "IDENTICAL"

        mock_cnmc = MagicMock()
        mock_cnmc.code = "CNMC-00000001-7"
        mock_golden = MagicMock()
        mock_golden.standardized_description = "VALVE, GATE, 6 INCH (150 MM), CLASS 300#, FLANGED RF, ASTM A216 WCB"
        mock_golden.base_uom = "EA"
        mock_golden.category_code = "40141600"
        mock_cnmc.golden_record = mock_golden
        mock_cw.cnmc = mock_cnmc

        mock_mat = MagicMock()
        mock_mat.short_description = "VALVE, GATE, 150MM, CL300, WCB"
        mock_mat.base_uom = "EA"
        mock_mat.package_multiplier = 1.0
        mock_mat.category_code = "40141600"
        mock_cw.material = mock_mat

        mock_cpse = MagicMock()
        mock_cpse.code = "IOCL"
        mock_cw.cpse = mock_cpse

        # Return row for export
        self.mock_db.query.return_value.join.return_value.join.return_value.join.return_value.join.return_value.all.return_value = [mock_cw]

        csv_out = SAPExportService.generate_lsmw_csv(self.mock_db)
        lines = csv_out.strip().split("\r\n") if "\r\n" in csv_out else csv_out.strip().split("\n")
        self.assertGreaterEqual(len(lines), 2)
        
        headers = lines[0].split(",")
        self.assertIn("LONG_TEXT_ISO8000", headers)
        self.assertEqual(headers[13], "LONG_TEXT_ISO8000")

        data_cols = lines[1].split(",")
        self.assertEqual(data_cols[1], "CNMC-00000001-7")
        self.assertEqual(data_cols[2], "889102")
        self.assertEqual(data_cols[3], "IOCL")

    # 5. Test SAP Export Fail-Safe Null Handling (Orphaned Record)
    def test_sap_lsmw_csv_null_safety_orphaned_row(self):
        mock_cw = MagicMock()
        mock_cw.local_material_code = "ORPHAN-001"
        mock_cw.mapping_type = None
        mock_cw.cnmc = None       # Orphaned CNMC
        mock_cw.material = None   # Orphaned Material
        mock_cw.cpse = None       # Orphaned CPSE

        self.mock_db.query.return_value.join.return_value.join.return_value.join.return_value.join.return_value.all.return_value = [mock_cw]

        # Must not raise AttributeError: 'NoneType' object has no attribute 'base_uom'
        try:
            csv_out = SAPExportService.generate_lsmw_csv(self.mock_db)
            self.assertTrue(len(csv_out) > 0)
        except AttributeError as err:
            self.fail(f"SAPExportService crashed on orphaned null relations: {err}")

if __name__ == "__main__":
    unittest.main()
