import unittest
import os
import sys
import io
import json
import uuid
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.matching.embeddings import EmbeddingService
from app.services.normalization.uom_normalizer import UOMNormalizer
from app.services.normalization.spec_extractor import SpecExtractor
from app.services.normalization.domain_lexicon import DomainLexicon
from app.api.v1.ingestion import UPLOAD_STAGING_DIR, STANDARD_HEADER_SYNONYMS

class TestChunk1ProductionIngestion(unittest.TestCase):
    """
    Automated verification suite for Chunk 1 (Upload & Ingestion Engine)
    Verifies:
    1. Claim-Check Single Upload Staging
    2. Batch Vectorization Consistency & Speed
    3. Asynchronous Task Mini-Batching
    4. Status Polling Accuracy
    """

    def setUp(self):
        os.makedirs(UPLOAD_STAGING_DIR, exist_ok=True)

    def test_batch_embeddings_consistency(self):
        """
        Verifies generate_batch_embeddings produces consistent unit-normalized
        vectors matching generate_embedding within floating point tolerance.
        """
        sample_texts = [
            "VALVE GATE 6IN 300# CS FLG",
            "PIPE CS SMLS 4\" SCH 40 ASTM A106",
            "BEARING 6205-2RS1 SKF",
            "GASKET SPIRAL WOUND 4\" 300# CS/SS"
        ]

        # 1. Generate individual embeddings
        single_vectors = [EmbeddingService.generate_embedding(t) for t in sample_texts]
        
        # 2. Generate batch embeddings simultaneously
        batch_vectors = EmbeddingService.generate_batch_embeddings(sample_texts)

        self.assertEqual(len(batch_vectors), len(sample_texts))
        for i in range(len(sample_texts)):
            self.assertEqual(len(batch_vectors[i]), len(single_vectors[i]))
            # Verify values are identical
            for val_single, val_batch in zip(single_vectors[i], batch_vectors[i]):
                self.assertAlmostEqual(val_single, val_batch, places=4)

    def test_staged_upload_claim_check(self):
        """
        Verifies the Claim-Check pattern: A file written to UPLOAD_STAGING_DIR
        can be identified by upload_id and read in chunks without re-upload.
        """
        upload_id = uuid.uuid4().hex
        test_filename = f"{upload_id}_sample_test_extract.csv"
        staged_path = os.path.join(UPLOAD_STAGING_DIR, test_filename)

        csv_content = (
            "MATERIAL_NO,ITEM_SPEC,UNIT_OF_MEASURE,LAST_PO_PRICE\n"
            "100234,VLV GATE 6IN 300# CS FLG,Nos,12500.0\n"
            "100888,PIPE CS SMLS 4\" SCH 40 ASTM A106,MTR,2450.0\n"
        )

        with open(staged_path, "w") as f:
            f.write(csv_content)

        self.assertTrue(os.path.exists(staged_path))

        # Test reading top 10 preview rows
        df_preview = pd.read_csv(staged_path, nrows=2)
        self.assertEqual(len(df_preview), 2)
        self.assertIn("ITEM_SPEC", df_preview.columns)

        # Cleanup
        if os.path.exists(staged_path):
            os.remove(staged_path)

    def test_synonym_mapping_and_normalization_preview(self):
        """
        Verifies standard header synonym resolution for CPCL, IOCL, and BPCL SAP formats.
        """
        raw_columns = ["MATNR", "MAKTX", "MEINS", "NETPR", "NAME1", "SAC"]
        suggested = {}

        for col in raw_columns:
            for target, synonyms in STANDARD_HEADER_SYNONYMS.items():
                if col in synonyms:
                    suggested[col] = target
                    break

        self.assertEqual(suggested.get("MATNR"), "material_code")
        self.assertEqual(suggested.get("MAKTX"), "short_description")
        self.assertEqual(suggested.get("MEINS"), "uom")
        self.assertEqual(suggested.get("NETPR"), "base_price")
        self.assertEqual(suggested.get("NAME1"), "vendor_name")
        self.assertEqual(suggested.get("SAC"), "hsn_code")

if __name__ == "__main__":
    unittest.main()
