"""Tests for page-aware PDF import and grounded AI suggestion filtering."""
import json
import unittest
from unittest.mock import patch
from io import BytesIO

from backend.pdf_ingest import extract_pdf_pages
from backend.local_ai import suggest_questions

class PDFTests(unittest.TestCase):
    def test_rejects_non_pdf(self):
        with self.assertRaises(ValueError):
            extract_pdf_pages(b"not a pdf")

class AIValidationTests(unittest.TestCase):
    @patch("backend.local_ai.urllib.request.urlopen")
    def test_discards_ungrounded_suggestions(self, urlopen):
        fake = {"message": {"content": json.dumps({"questions": [
            {"kind": "choose", "difficulty": "easy", "prompt": "Choose the animal",
             "answer": "cat", "options": ["cat", "dog"], "evidence_quote": "cat"},
            {"kind": "choose", "difficulty": "easy", "prompt": "Choose the color",
             "answer": "blue", "options": ["blue", "red"], "evidence_quote": "not in the page"}
        ]})}}
        urlopen.return_value.__enter__.return_value = BytesIO(json.dumps(fake).encode())
        result = suggest_questions("A cat is here.", 1, "Primary 3", 5)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_page"], 1)

if __name__ == "__main__":
    unittest.main()
