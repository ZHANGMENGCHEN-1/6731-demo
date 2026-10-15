"""更新入口离线测试，不访问 HKEX。"""
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import pandas as pd
import requests
import fetch_latest as updater


class UpdateTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame([dict(participant_id="B00001", participant_name="TEST", address="", shares=10, percentage=1.0)])

    @patch.object(updater.time, "sleep")
    @patch.object(updater.fetch_ccass, "fetch_day")
    @patch.object(updater, "latest_available_date", return_value=date(2026, 10, 15))
    def test_backfill_and_no_data(self, latest, fetch, sleep):
        fetch.side_effect = [None, self.frame()]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "ccass_2026-10-13.csv"
            old.write_bytes(b"original")
            self.assertEqual(updater.update_latest(root), 0)
            self.assertEqual([c.args[1] for c in fetch.call_args_list], [date(2026, 10, 14), date(2026, 10, 15)])
            self.assertEqual(old.read_bytes(), b"original")
            self.assertFalse((root / "ccass_2026-10-14.csv").exists())
            self.assertTrue((root / "ccass_2026-10-15.csv").exists())
            self.assertEqual(sleep.call_count, 2)
            fetch.reset_mock()
            self.assertEqual(updater.update_latest(root), 0)
            fetch.assert_not_called()

    @patch.object(updater.fetch_ccass, "fetch_day", side_effect=requests.Timeout("timeout"))
    @patch.object(updater, "latest_available_date", return_value=date(2026, 10, 14))
    def test_failure_preserves_history(self, latest, fetch):
        with TemporaryDirectory() as directory:
            old = Path(directory) / "ccass_2026-10-13.csv"
            old.write_bytes(b"original")
            with self.assertLogs(updater.LOGGER, level="ERROR"):
                self.assertEqual(updater.update_latest(directory), 1)
            self.assertEqual(old.read_bytes(), b"original")
            self.assertEqual(len(list(Path(directory).glob("*.csv"))), 1)

    def test_atomic_save_never_overwrites(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            day = date(2026, 10, 14)
            self.assertTrue(updater.save_new_snapshot(self.frame(), day, root))
            before = (root / f"ccass_{day}.csv").read_bytes()
            self.assertFalse(updater.save_new_snapshot(self.frame().assign(shares=99), day, root))
            self.assertEqual((root / f"ccass_{day}.csv").read_bytes(), before)
            self.assertFalse(list(root.glob("*.tmp")))

    @patch.object(updater.time, "sleep")
    @patch.object(updater.fetch_ccass, "fetch_day", return_value=None)
    @patch.object(updater, "latest_available_date", return_value=date(2026, 9, 29))
    def test_empty_directory_starts_at_listing(self, latest, fetch, sleep):
        with TemporaryDirectory() as directory:
            self.assertEqual(updater.update_latest(directory), 0)
            self.assertEqual(fetch.call_args.args[1], updater.LISTING_DATE)


if __name__ == "__main__":
    unittest.main()
