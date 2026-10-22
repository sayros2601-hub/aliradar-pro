"""
Tests for DealVault Data Adapter V1.
Verifies Acceptance Criteria A01 - A20 from specs/18_ACCEPTANCE_RU.txt.
"""

import unittest
import json
import tempfile
import socket
from pathlib import Path
from dealvault_adapter import DealVaultAdapter, parse_observation_record, safe_resolve_path


class TestDealVaultAdapter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.inbox = self.root / "inbox"
        self.data = self.root / "data"
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.data.mkdir(parents=True, exist_ok=True)

        # Base mock products.json
        (self.data / "products.json").write_text(json.dumps({
            "site_meta": {"title": "DealVault"},
            "products": [
                {
                    "id": "item-001",
                    "title": "Existing Test Product",
                    "affiliate_url": "https://s.click.aliexpress.com/e/_DkExample",
                    "price_usd": 12.50
                }
            ]
        }), encoding="utf-8")

        self.adapter = DealVaultAdapter(inbox_dir=self.inbox, data_dir=self.data)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_a01_offline_operations_make_zero_network_calls(self):
        """A01: Offline status/validate_import do not touch the network."""
        # Create a valid test input file
        sample_file = self.inbox / "sample_valid.json"
        sample_file.write_text(json.dumps([
            {
                "raw_title": "Smart Cat Feeder Automatic",
                "item_id": "1005006001234567",
                "original_affiliate_url": "https://s.click.aliexpress.com/e/_mNewLink1",
                "observed_at": "2026-10-21T12:00:00Z",
                "target_country": "US",
                "currency": "USD"
            }
        ]), encoding="utf-8")

        # Guard socket.socket to ensure NO network connections can be attempted
        orig_socket = socket.socket
        def forbidden_socket(*args, **kwargs):
            raise AssertionError("Network socket connection attempted during offline operation!")

        try:
            socket.socket = forbidden_socket
            # Test status
            st = self.adapter.get_status()
            self.assertEqual(st["status"], "OK")
            self.assertEqual(st["mode"], "offline_supported")

            # Test validate_import
            val = self.adapter.validate_import("sample_valid.json", offline=True)
            self.assertEqual(val["status"], "OK")
            self.assertEqual(val["summary"]["valid_records"], 1)
        finally:
            socket.socket = orig_socket

    def test_a02_malformed_inputs_handled_gracefully(self):
        """A02: Malformed JSON, non-UTF8, oversized files return explicit error codes without crashing."""
        # Malformed JSON
        bad_json = self.inbox / "bad_syntax.json"
        bad_json.write_text("{ unquoted_key: 123 ", encoding="utf-8")
        res = self.adapter.validate_import("bad_syntax.json", offline=True)
        self.assertEqual(res["status"], "INVALID_INPUT")
        self.assertEqual(res["error"]["code"], "MALFORMED_JSON")

        # Invalid encoding
        bad_enc = self.inbox / "bad_encoding.bin"
        bad_enc.write_bytes(b"\xff\xfe\x00\x00\x80\x81\x82")
        res_enc = self.adapter.validate_import("bad_encoding.bin", offline=True)
        self.assertEqual(res_enc["status"], "INVALID_INPUT")
        self.assertEqual(res_enc["error"]["code"], "INVALID_ENCODING")

    def test_a03_path_traversal_strictly_blocked(self):
        """A03: Path traversal escapes outside inbox root are blocked with POLICY_BLOCKED."""
        with self.assertRaises(PermissionError):
            safe_resolve_path("../../secret.json", self.inbox)

        res = self.adapter.validate_import("../../windows/system32/cmd.exe", offline=True)
        self.assertEqual(res["status"], "POLICY_BLOCKED")
        self.assertEqual(res["error"]["code"], "PATH_TRAVERSAL_DENIED")

    def test_a04_idempotent_import_and_catalog_safety(self):
        """A04: Repeated import of same file is idempotent; active products.json is untouched."""
        sample_file = self.inbox / "repeat_feed.json"
        sample_file.write_text(json.dumps([
            {
                "raw_title": "Wireless Car Tire Inflator",
                "item_id": "1005007788990011",
                "original_affiliate_url": "https://s.click.aliexpress.com/e/_mNewLink2",
                "observed_at": "2026-10-21T14:30:00Z",
                "target_country": "US",
                "currency": "USD"
            }
        ]), encoding="utf-8")

        # First stage
        res1 = self.adapter.stage_import("repeat_feed.json", offline=True)
        self.assertEqual(res1["status"], "OK")
        self.assertEqual(res1["staged_count"], 1)

        # Second stage (same file) -> should be idempotent (0 newly staged)
        res2 = self.adapter.stage_import("repeat_feed.json", offline=True)
        self.assertEqual(res2["status"], "OK")
        self.assertEqual(res2["staged_count"], 0)
        self.assertIn("Idempotent", res2["message"])

        # Check active products.json is untouched (still 1 base product)
        prod_data = json.loads((self.data / "products.json").read_text(encoding="utf-8"))
        self.assertEqual(len(prod_data["products"]), 1)

    def test_a05_observed_at_separated_from_imported_at(self):
        """A05: observed_at != imported_at; missing timestamps remain null and missing."""
        rec_with_old_date = {
            "raw_title": "Vintage Clock",
            "item_id": "1005001122334455",
            "original_affiliate_url": "https://s.click.aliexpress.com/e/_mOldDate",
            "observed_at": "2025-01-15T08:00:00Z"
        }
        imported_at = "2026-10-22T01:00:00Z"
        env, errs = parse_observation_record(rec_with_old_date, imported_at)
        self.assertEqual(env["observed_at"], "2025-01-15T08:00:00Z")
        self.assertEqual(env["imported_at"], imported_at)
        self.assertNotEqual(env["observed_at"], env["imported_at"])

        # Without observed_at
        rec_no_date = {
            "raw_title": "Undated Widget",
            "item_id": "1005001122334456",
            "original_affiliate_url": "https://s.click.aliexpress.com/e/_mNoDate"
        }
        env2, errs2 = parse_observation_record(rec_no_date, imported_at)
        self.assertIsNone(env2["observed_at"])
        self.assertIn("observation_time", env2["missing_fields"])

    def test_a06_unknown_fields_not_zeroed(self):
        """A06: Missing stock/price/rating fields remain null/missing, not 0."""
        rec = {
            "raw_title": "Minimal Item",
            "item_id": "1005009988776655",
            "original_affiliate_url": "https://s.click.aliexpress.com/e/_mMinimal"
        }
        env, errs = parse_observation_record(rec, "2026-10-22T01:00:00Z")
        self.assertIsNone(env["country"])
        self.assertIsNone(env["currency"])
        self.assertIn("country", env["missing_fields"])
        self.assertIn("currency", env["missing_fields"])
        self.assertEqual(env["fields"], {})

    def test_a10_staged_records_are_pending_review(self):
        """A10: Staged records have review_status: pending and are placed in inbox, not live catalog."""
        sample_file = self.inbox / "new_capture.json"
        sample_file.write_text(json.dumps([
            {
                "raw_title": "Solar Powered LED Lantern",
                "item_id": "1005004455667788",
                "original_affiliate_url": "https://s.click.aliexpress.com/e/_mSolar1",
                "observed_at": "2026-10-21T18:00:00Z",
                "country": "US",
                "currency": "USD"
            }
        ]), encoding="utf-8")

        self.adapter.stage_import("new_capture.json", offline=True)
        inbox_items = json.loads((self.data / "portals_inbox.json").read_text(encoding="utf-8"))
        self.assertEqual(len(inbox_items), 1)
        self.assertEqual(inbox_items[0]["review_status"], "pending")


if __name__ == "__main__":
    unittest.main()
