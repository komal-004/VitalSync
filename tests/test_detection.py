"""VitalSync - Unit Test Suite
Module: tests.test_detection

Automated test cases covering:
1. Normal synthetic reading
2. Unusual heart rate reading (Tachycardia & Bradycardia)
3. Unusual blood pressure reading (Hypertension)
4. Unusual SpO2 reading (Hypoxia)
5. Missing data validation
6. Invalid data (out-of-bounds / physically impossible values)
7. Sudden change (delta spike) detection
8. Repeated unusual readings (persistence escalation)
9. Activity context awareness (exercise vs resting)
10. Multi-parameter correlation detection
"""

import sys
import os
import unittest

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from simulator.health_generator import HealthDataSimulator
from detection.detection_rules import AnomalyDetector
from services.data_service import MonitoringState


class TestVitalSyncAnomalyDetection(unittest.TestCase):

    def setUp(self):
        """Set up fresh detector and simulator instances before each test."""
        self.detector = AnomalyDetector()
        self.simulator = HealthDataSimulator(device_id="FIT-TEST-01")
        self.state = MonitoringState(max_history=20)

    # -------------------------------------------------------------------------
    # 1. Normal Synthetic Reading
    # -------------------------------------------------------------------------
    def test_normal_synthetic_reading(self):
        """Verifies that standard resting baseline vitals produce NORMAL status."""
        reading = {
            "device_id": "FIT-TEST-01",
            "timestamp": "2026-11-26 12:00:00",
            "heart_rate": 72.0,
            "systolic_bp": 118.0,
            "diastolic_bp": 78.0,
            "spo2": 98.5,
            "temperature": 36.8,
            "activity": "Resting"
        }
        result = self.detector.evaluate_reading(reading, recent_history=[])
        self.assertFalse(result.is_anomaly)
        self.assertEqual(result.severity, "NORMAL")
        self.assertEqual(result.rule_triggered, "RULE_NORMAL_OPERATION")

    # -------------------------------------------------------------------------
    # 2. Unusual Heart Rate (Tachycardia and Bradycardia)
    # -------------------------------------------------------------------------
    def test_unusual_heart_rate_tachycardia(self):
        """Verifies that an elevated heart rate at rest triggers tachycardia alert."""
        # Critical Tachycardia (>130 BPM)
        reading = {
            "device_id": "FIT-TEST-01",
            "timestamp": "2026-11-26 12:00:01",
            "heart_rate": 145.0,  # Resting HR > 130
            "systolic_bp": 120.0,
            "diastolic_bp": 80.0,
            "spo2": 98.0,
            "temperature": 36.8,
            "activity": "Resting"
        }
        result = self.detector.evaluate_reading(reading, recent_history=[])
        self.assertTrue(result.is_anomaly)
        self.assertEqual(result.severity, "HIGH")
        self.assertEqual(result.rule_triggered, "RULE_RESTING_CRITICAL_TACHYCARDIA")

        # Warning Elevated Tachycardia (101 - 130 BPM)
        warn_reading = dict(reading, heart_rate=108.0)
        warn_result = self.detector.evaluate_reading(warn_reading, recent_history=[])
        self.assertTrue(warn_result.is_anomaly)
        self.assertEqual(warn_result.severity, "WARNING")
        self.assertEqual(warn_result.rule_triggered, "RULE_RESTING_ELEVATED_TACHYCARDIA")

    def test_unusual_heart_rate_bradycardia(self):
        """Verifies that an abnormally low resting heart rate triggers a WARNING."""
        reading = {
            "device_id": "FIT-TEST-01",
            "timestamp": "2026-11-26 12:00:02",
            "heart_rate": 44.0,  # Below resting min 50 BPM
            "systolic_bp": 115.0,
            "diastolic_bp": 75.0,
            "spo2": 99.0,
            "temperature": 36.7,
            "activity": "Resting"
        }
        result = self.detector.evaluate_reading(reading, recent_history=[])
        self.assertTrue(result.is_anomaly)
        self.assertEqual(result.severity, "WARNING")
        self.assertEqual(result.rule_triggered, "RULE_BRADYCARDIA_LOW_HEART_RATE")

    # -------------------------------------------------------------------------
    # 3. Unusual Blood Pressure (Hypertension - Stage 1 & Stage 2 Crisis)
    # -------------------------------------------------------------------------
    def test_unusual_blood_pressure(self):
        """Verifies that high systolic and diastolic BP triggers hypertension alert."""
        # Stage 1 Warning
        warn_reading = {
            "device_id": "FIT-TEST-01",
            "timestamp": "2026-11-26 12:00:03",
            "heart_rate": 74.0,
            "systolic_bp": 136.0,  # Warning threshold >= 130
            "diastolic_bp": 88.0,  # Warning threshold >= 85
            "spo2": 98.0,
            "temperature": 36.8,
            "activity": "Resting"
        }
        res_warn = self.detector.evaluate_reading(warn_reading, recent_history=[])
        self.assertTrue(res_warn.is_anomaly)
        self.assertEqual(res_warn.severity, "WARNING")
        self.assertEqual(res_warn.rule_triggered, "RULE_STAGE_1_HYPERTENSION")

        # Stage 2 Hypertensive Crisis
        crit_reading = {
            "device_id": "FIT-TEST-01",
            "timestamp": "2026-11-26 12:00:03",
            "heart_rate": 78.0,
            "systolic_bp": 165.0,  # Critical systolic >= 145
            "diastolic_bp": 102.0, # Critical diastolic >= 95
            "spo2": 98.0,
            "temperature": 36.8,
            "activity": "Resting"
        }
        result = self.detector.evaluate_reading(crit_reading, recent_history=[])
        self.assertTrue(result.is_anomaly)
        self.assertEqual(result.severity, "HIGH")
        self.assertEqual(result.rule_triggered, "RULE_CRITICAL_HYPERTENSION")

    # -------------------------------------------------------------------------
    # 4. Unusual SpO2 (Hypoxia)
    # -------------------------------------------------------------------------
    def test_unusual_spo2_hypoxia(self):
        """Verifies that low oxygen saturation flags hypoxia correctly."""
        # Mild hypoxia (90-94%)
        mild_reading = {
            "device_id": "FIT-TEST-01",
            "timestamp": "2026-11-26 12:00:04",
            "heart_rate": 75.0,
            "systolic_bp": 120.0,
            "diastolic_bp": 80.0,
            "spo2": 92.0,
            "temperature": 36.8,
            "activity": "Resting"
        }
        mild_res = self.detector.evaluate_reading(mild_reading)
        self.assertTrue(mild_res.is_anomaly)
        self.assertEqual(mild_res.severity, "WARNING")
        self.assertEqual(mild_res.rule_triggered, "RULE_MILD_HYPOXIA")

        # Critical hypoxia (<90%)
        crit_reading = dict(mild_reading, spo2=87.0)
        crit_res = self.detector.evaluate_reading(crit_reading)
        self.assertTrue(crit_res.is_anomaly)
        self.assertEqual(crit_res.severity, "HIGH")
        self.assertEqual(crit_res.rule_triggered, "RULE_CRITICAL_HYPOXIA")

    # -------------------------------------------------------------------------
    # 5. Missing Data Validation
    # -------------------------------------------------------------------------
    def test_missing_data_validation(self):
        """Verifies that missing or None fields are caught by payload validation."""
        corrupt_reading = {
            "device_id": "FIT-TEST-01",
            "timestamp": "2026-11-26 12:00:05",
            "heart_rate": None,  # Missing sensor read
            "systolic_bp": 120.0,
            "diastolic_bp": 80.0,
            "spo2": 98.0,
            "temperature": 36.8,
            "activity": "Resting"
        }
        result = self.detector.evaluate_reading(corrupt_reading)
        self.assertTrue(result.is_anomaly)
        self.assertEqual(result.severity, "HIGH")
        self.assertEqual(result.rule_triggered, "RULE_DATA_VALIDATION_ERROR")
        self.assertIn("missing or null", result.reason)

    # -------------------------------------------------------------------------
    # 6. Invalid / Out-of-Bounds Data
    # -------------------------------------------------------------------------
    def test_invalid_out_of_bounds_data(self):
        """Verifies rejection of biologically impossible sensor measurements."""
        # Negative HR
        invalid_hr = {
            "device_id": "FIT-TEST-01",
            "timestamp": "2026-11-26 12:00:06",
            "heart_rate": -10.0,
            "systolic_bp": 120.0,
            "diastolic_bp": 80.0,
            "spo2": 98.0,
            "temperature": 36.8,
            "activity": "Resting"
        }
        res_hr = self.detector.evaluate_reading(invalid_hr)
        self.assertTrue(res_hr.is_anomaly)
        self.assertEqual(res_hr.rule_triggered, "RULE_DATA_VALIDATION_ERROR")

        # Inverted blood pressure (systolic < diastolic)
        invalid_bp = dict(invalid_hr, heart_rate=72.0, systolic_bp=70.0, diastolic_bp=90.0)
        res_bp = self.detector.evaluate_reading(invalid_bp)
        self.assertTrue(res_bp.is_anomaly)
        self.assertIn("greater than diastolic", res_bp.reason)

        # SpO2 > 100%
        invalid_spo2 = dict(invalid_hr, heart_rate=72.0, spo2=125.0)
        res_spo2 = self.detector.evaluate_reading(invalid_spo2)
        self.assertTrue(res_spo2.is_anomaly)
        self.assertIn("outside the physical range", res_spo2.reason)

    # -------------------------------------------------------------------------
    # 7. Sudden Change Detection (Delta Spike)
    # -------------------------------------------------------------------------
    def test_sudden_change_detection(self):
        """Verifies that an abrupt change between consecutive readings triggers delta rule."""
        prev_reading = {
            "timestamp": "2026-11-26 12:00:10",
            "heart_rate": 70.0,
            "systolic_bp": 118.0,
            "diastolic_bp": 78.0,
            "spo2": 98.0,
            "temperature": 36.8,
            "activity": "Resting",
            "is_anomaly": False
        }
        # Sudden jump of 35 BPM while still Resting
        curr_reading = {
            "timestamp": "2026-11-26 12:00:12",
            "heart_rate": 105.0,
            "systolic_bp": 118.0,
            "diastolic_bp": 78.0,
            "spo2": 98.0,
            "temperature": 36.8,
            "activity": "Resting"
        }
        result = self.detector.evaluate_reading(curr_reading, recent_history=[prev_reading])
        self.assertTrue(result.is_anomaly)
        all_rules = result.rules_triggered + [result.rule_triggered]
        self.assertTrue("RULE_SUDDEN_HR_SPIKE" in all_rules or "RULE_RESTING_ELEVATED_TACHYCARDIA" in all_rules)

    # -------------------------------------------------------------------------
    # 8. Repeated Unusual Readings Escalation (Persistence)
    # -------------------------------------------------------------------------
    def test_repeated_unusual_readings_escalation(self):
        """Verifies that consecutive mild anomalies escalate severity to HIGH."""
        # 2 prior consecutive anomalies
        history = [
            {"heart_rate": 104.0, "spo2": 97.0, "is_anomaly": True},
            {"heart_rate": 106.0, "spo2": 97.0, "is_anomaly": True},
        ]
        # 3rd consecutive anomaly
        current = {
            "timestamp": "2026-11-26 12:00:15",
            "heart_rate": 105.0,  # Elevated resting HR (normally WARNING)
            "systolic_bp": 120.0,
            "diastolic_bp": 80.0,
            "spo2": 97.0,
            "temperature": 36.8,
            "activity": "Resting"
        }
        result = self.detector.evaluate_reading(current, recent_history=history)
        self.assertTrue(result.is_anomaly)
        # Escalated to HIGH due to persistence
        self.assertEqual(result.severity, "HIGH")
        all_rules = result.rules_triggered + [result.rule_triggered]
        self.assertIn("RULE_SUSTAINED_ANOMALY_ESCALATION", all_rules)

    # -------------------------------------------------------------------------
    # 9. Activity Context Awareness
    # -------------------------------------------------------------------------
    def test_activity_context_awareness(self):
        """Verifies that elevated heart rate during exercise is NOT treated as an anomaly."""
        exercise_reading = {
            "device_id": "FIT-TEST-01",
            "timestamp": "2026-11-26 12:00:20",
            "heart_rate": 142.0,  # 142 BPM would be critical at rest, but normal during exercise
            "systolic_bp": 135.0,
            "diastolic_bp": 82.0,
            "spo2": 97.0,
            "temperature": 37.3,
            "activity": "Exercise"
        }
        result = self.detector.evaluate_reading(exercise_reading, recent_history=[])
        self.assertFalse(result.is_anomaly)
        self.assertEqual(result.severity, "NORMAL")

        # Same 142 BPM at rest MUST be flagged as an anomaly
        resting_reading = dict(exercise_reading, activity="Resting")
        resting_result = self.detector.evaluate_reading(resting_reading, recent_history=[])
        self.assertTrue(resting_result.is_anomaly)
        self.assertEqual(resting_result.severity, "HIGH")

    # -------------------------------------------------------------------------
    # 10. Multi-Parameter Correlation Detection
    # -------------------------------------------------------------------------
    def test_multi_parameter_combination(self):
        """Verifies detection of combined cardiorespiratory distress (HR + low SpO2)."""
        combined_reading = {
            "device_id": "FIT-TEST-01",
            "timestamp": "2026-11-26 12:00:25",
            "heart_rate": 128.0,
            "systolic_bp": 125.0,
            "diastolic_bp": 82.0,
            "spo2": 89.0,         # Both HR elevated and SpO2 in hypoxia
            "temperature": 37.0,
            "activity": "Resting"
        }
        result = self.detector.evaluate_reading(combined_reading, recent_history=[])
        self.assertTrue(result.is_anomaly)
        self.assertEqual(result.severity, "HIGH")
        all_rules = result.rules_triggered + [result.rule_triggered]
        self.assertIn("RULE_MULTI_CARDIORESPIRATORY_DISTRESS", all_rules)


if __name__ == "__main__":
    unittest.main()
