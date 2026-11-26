"""VitalSync - Simulator and Service Integration Tests
Module: tests.test_services

Verifies:
1. Simulator scenarios output valid structured dictionaries.
2. MonitoringState buffers, counters, and DataFrame conversion.
3. StreamEventPublisher schema and Kafka payload generation.
"""

import sys
import os
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from simulator.health_generator import HealthDataSimulator
from services.data_service import MonitoringState, StreamEventPublisher
from detection.detection_rules import AnomalyDetector


class TestSimulatorAndServices(unittest.TestCase):

    def setUp(self):
        self.simulator = HealthDataSimulator(device_id="FIT-UNIT-01")
        self.state = MonitoringState(max_history=10)
        self.detector = AnomalyDetector()

    def test_all_simulator_scenarios(self):
        """Ensure all defined simulation scenarios generate non-empty payloads."""
        for key in HealthDataSimulator.SCENARIOS.keys():
            reading = self.simulator.generate_reading(scenario=key)
            self.assertEqual(reading["device_id"], "FIT-UNIT-01")
            self.assertIn("timestamp", reading)
            self.assertIn("activity", reading)

    def test_state_sliding_buffer_and_summary(self):
        """Verifies buffer limits and statistics aggregation."""
        for _ in range(15):
            reading = self.simulator.generate_reading(scenario="NORMAL_RESTING")
            eval_res = self.detector.evaluate_reading(reading)
            self.state.record_reading(reading, eval_res.to_dict())

        # Buffer should respect max_history = 10
        self.assertEqual(len(self.state.readings_buffer), 10)
        # Total generated counter should be 15
        self.assertEqual(self.state.total_readings_generated, 15)

        stats = self.state.get_summary_statistics()
        self.assertEqual(stats["total_generated"], 15)
        self.assertGreater(stats["avg_heart_rate"], 0.0)

        df = self.state.get_readings_dataframe()
        self.assertEqual(len(df), 10)

    def test_kafka_stream_publisher_payload(self):
        """Verifies that StreamEventPublisher formats the standardized cloud schema."""
        reading = self.simulator.generate_reading()
        publisher = StreamEventPublisher()
        event = publisher.publish_event(reading)

        self.assertEqual(event["topic"], "health-events")
        self.assertEqual(event["key"], "FIT-UNIT-01")
        self.assertIn("cloud_metadata", event)
        self.assertEqual(event["cloud_metadata"]["schema_version"], "1.0")
        self.assertIn("vitalsync-anomaly-detector", event["cloud_metadata"]["target_lambda_arn"])


if __name__ == "__main__":
    unittest.main()
