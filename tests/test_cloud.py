"""VitalSync - Phase 2 Cloud & Streaming Unit Tests
Module: tests.test_cloud

Verifies:
1. VitalSyncKafkaProducer event envelope formatting and dry-run publishing.
2. AWS Lambda handler processing of direct JSON events (normal and critical).
3. AWS Lambda handler processing of base64-encoded Kafka Event Source Mapping (ESM) batches.
4. DynamoDB float-to-Decimal conversion helper.
"""

import sys
import os
import json
import base64
import unittest
from decimal import Decimal

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cloud.kafka_producer import VitalSyncKafkaProducer
from cloud.lambda_function import lambda_handler, _float_to_decimal


class TestPhase2CloudPipeline(unittest.TestCase):

    def test_kafka_producer_dry_run_envelope(self):
        """Verifies that KafkaProducer formats the standardized event envelope cleanly."""
        producer = VitalSyncKafkaProducer(device_id="FIT-CLOUD-01", dry_run=True)
        event = producer.publish_reading(scenario="NORMAL_RESTING")

        self.assertEqual(event["topic"], "health-events")
        self.assertEqual(event["key"], "FIT-CLOUD-01")
        self.assertIn("data", event)
        self.assertEqual(event["data"]["device_id"], "FIT-CLOUD-01")
        self.assertEqual(event["cloud_metadata"]["schema_version"], "2.0")

    def test_lambda_handler_direct_critical_event(self):
        """Verifies AWS Lambda handler detects critical anomaly and triggers mock SNS dispatch."""
        event = {
            "data": {
                "device_id": "FIT-101",
                "timestamp": "2026-11-27 12:00:00",
                "heart_rate": 168.0,
                "systolic_bp": 170.0,
                "diastolic_bp": 102.0,
                "spo2": 87.0,
                "temperature": 38.9,
                "activity": "Resting"
            }
        }
        response = lambda_handler(event)
        self.assertEqual(response["statusCode"], 200)
        body = response["body"]
        self.assertEqual(body["batch_size"], 1)
        self.assertEqual(body["anomalies_detected"], 1)
        self.assertEqual(body["alerts_dispatched"], 1)
        self.assertEqual(body["evaluations"][0]["severity"], "HIGH")

    def test_lambda_handler_kafka_esm_base64_batch(self):
        """Verifies Lambda decodes base64 AWS MSK / Kafka Event Source Mapping batch records."""
        normal_payload = {
            "topic": "health-events",
            "key": "FIT-101",
            "data": {
                "device_id": "FIT-101",
                "timestamp": "2026-11-27 12:00:01",
                "heart_rate": 72.0,
                "systolic_bp": 118.0,
                "diastolic_bp": 78.0,
                "spo2": 98.5,
                "temperature": 36.8,
                "activity": "Resting"
            }
        }
        anomaly_payload = {
            "topic": "health-events",
            "key": "FIT-101",
            "data": {
                "device_id": "FIT-101",
                "timestamp": "2026-11-27 12:00:02",
                "heart_rate": 76.0,
                "systolic_bp": 168.0,
                "diastolic_bp": 104.0,
                "spo2": 98.0,
                "temperature": 36.8,
                "activity": "Resting"
            }
        }

        esm_event = {
            "eventSource": "aws:kafka",
            "records": {
                "health-events-0": [
                    {
                        "topic": "health-events",
                        "partition": 0,
                        "offset": 10,
                        "value": base64.b64encode(json.dumps(normal_payload).encode("utf-8")).decode("utf-8"),
                    },
                    {
                        "topic": "health-events",
                        "partition": 0,
                        "offset": 11,
                        "value": base64.b64encode(json.dumps(anomaly_payload).encode("utf-8")).decode("utf-8"),
                    },
                ]
            }
        }

        response = lambda_handler(esm_event)
        self.assertEqual(response["statusCode"], 200)
        body = response["body"]
        self.assertEqual(body["batch_size"], 2)
        self.assertEqual(body["anomalies_detected"], 1)
        self.assertEqual(body["alerts_dispatched"], 1)
        self.assertEqual(body["evaluations"][0]["severity"], "NORMAL")
        self.assertEqual(body["evaluations"][1]["severity"], "HIGH")
        self.assertEqual(body["evaluations"][1]["rule"], "RULE_CRITICAL_HYPERTENSION")

    def test_dynamodb_float_to_decimal_helper(self):
        """Verifies float values are converted to Decimal for DynamoDB compatibility."""
        sample = {"heart_rate": 72.5, "nested": {"spo2": 98.4}, "list": [1.2, 3.4]}
        converted = _float_to_decimal(sample)
        self.assertIsInstance(converted["heart_rate"], Decimal)
        self.assertIsInstance(converted["nested"]["spo2"], Decimal)
        self.assertIsInstance(converted["list"][0], Decimal)


if __name__ == "__main__":
    unittest.main()
