"""
Unit tests for Warehouse Model and Simulation Logic.
"""

import unittest
from warehouse_model import WarehouseModel, AISLE_MAPPING, AISLES

class TestWarehouseModel(unittest.TestCase):
    def setUp(self):
        self.wm = WarehouseModel()

    def test_satellite_counts_and_boundaries(self):
        # Total suds = 63
        self.assertEqual(len(self.wm.aisle_mapping), 63)
        self.assertIn(1, self.wm.aisle_mapping)
        self.assertIn(63, self.wm.aisle_mapping)
        self.assertNotIn(0, self.wm.aisle_mapping)
        self.assertNotIn(64, self.wm.aisle_mapping)

    def test_aisle_assignments(self):
        # Pasillo A: Sud 1 to 9
        for i in range(1, 10):
            info = self.wm.get_location_info(i)
            self.assertEqual(info["aisle"], "Pasillo A")

        # Pasillo B: Sud 10 to 18 (left), 19 to 27 (right)
        for i in range(10, 19):
            info = self.wm.get_location_info(i)
            self.assertEqual(info["aisle"], "Pasillo B")
            self.assertEqual(info["side"], "left")
        for i in range(19, 28):
            info = self.wm.get_location_info(i)
            self.assertEqual(info["aisle"], "Pasillo B")
            self.assertEqual(info["side"], "right")

        # Pasillo C: Sud 28 to 36 (left), 37 to 45 (right)
        for i in range(28, 37):
            info = self.wm.get_location_info(i)
            self.assertEqual(info["aisle"], "Pasillo C")
            self.assertEqual(info["side"], "left")
        for i in range(37, 46):
            info = self.wm.get_location_info(i)
            self.assertEqual(info["aisle"], "Pasillo C")
            self.assertEqual(info["side"], "right")

        # Pasillo D: Sud 46 to 54
        for i in range(46, 55):
            info = self.wm.get_location_info(i)
            self.assertEqual(info["aisle"], "Pasillo D")

        # Pasillo E: Sud 55 to 63
        for i in range(55, 64):
            info = self.wm.get_location_info(i)
            self.assertEqual(info["aisle"], "Pasillo E")

    def test_popularity_scores(self):
        # Positions with depth 1 (closest to SALIDA: Sud 1, 10, 19, 28, 37, 46, 55) should have max score 1.0
        self.assertEqual(self.wm.get_popularity_score(1), 1.0)
        self.assertEqual(self.wm.get_popularity_score(10), 1.0)

        # Positions with depth 9 (furthest back: Sud 9, 18, 27, 36, 45, 54, 63) should have min score 0.0
        self.assertEqual(self.wm.get_popularity_score(9), 0.0)
        self.assertEqual(self.wm.get_popularity_score(63), 0.0)

    def test_arduino_log_generation(self):
        logs = self.wm.generate_arduino_cmd(14, 2, action="PICK")
        self.assertTrue(any("[ARDUINO]" in log for log in logs))
        self.assertTrue(any("Sud 14" in log for log in logs))
        self.assertTrue(any("Nivel 02" in log for log in logs))

if __name__ == "__main__":
    unittest.main()
