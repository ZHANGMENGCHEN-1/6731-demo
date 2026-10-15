"""监控指标与近期趋势口径的离线回归检查。"""
from datetime import date, timedelta
import unittest
from unittest.mock import patch
import pandas as pd
import analysis


class MonitoringTests(unittest.TestCase):
    def frames(self):
        dates = [date(2026, 9, 28) + timedelta(days=n) for n in (0, 1, 2, 3, 4, 7)]
        up = [100, 110, 106, 116, 126, 136]
        down = [200, 190, 194, 184, 174, 164]
        spike = [100, 100, 100, 100, 100, 500]
        return {day: pd.DataFrame([
            {"participant_id": pid, "participant_name": pid, "address": "", "shares": values[i], "percentage": values[i] / 100}
            for pid, values in (("B00001", up), ("B00002", down), ("B00003", spike))]) for i, day in enumerate(dates)}

    def test_recent_trend_allows_pullback_but_excludes_one_off(self):
        frames = self.frames()
        up = analysis._persistent_from_frames(frames, "increase")
        down = analysis._persistent_from_frames(frames, "decrease")
        self.assertEqual(up.participant_id.tolist(), ["B00001"])
        self.assertEqual(down.participant_id.tolist(), ["B00002"])
        self.assertEqual(up.iloc[0].shares_change, 36)
        self.assertEqual(up.iloc[0].direction_count, 4)
        self.assertEqual(up.iloc[0].interval_count, 5)
        self.assertAlmostEqual(up.iloc[0].direction_share, 40 / 44 * 100)

    def test_short_window_and_flat_positions(self):
        frames = self.frames()
        self.assertTrue(analysis._persistent_from_frames(dict(list(frames.items())[:3]), "increase").empty)
        flat = {day: frame.assign(shares=100, percentage=1.0) for day, frame in frames.items()}
        self.assertTrue(analysis._persistent_from_frames(flat, "increase").empty)
        self.assertTrue(analysis._persistent_from_frames(flat, "decrease").empty)

    def test_latest_comparison_excludes_weekend(self):
        frames = self.frames()
        frames[date(2026, 10, 10)] = list(frames.values())[-1].assign(shares=999)
        with patch.object(analysis, "discover_snapshots", return_value={day: day for day in frames}), \
             patch.object(analysis, "load_snapshot", side_effect=lambda day: frames[day]):
            result = analysis.get_monitoring_data()
        self.assertEqual(result["workdays"][-1], date(2026, 10, 5))
        pd.testing.assert_frame_equal(result["latest_comparison"], analysis.compare_snapshots(
            frames[date(2026, 10, 2)], frames[date(2026, 10, 5)]))
        self.assertEqual(result["persistent_increases"].participant_id.tolist(), ["B00001"])


if __name__ == "__main__":
    unittest.main()
