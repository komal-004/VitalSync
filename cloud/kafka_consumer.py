"""VitalSync - Phase 2 Apache Kafka Consumer
Module: cloud.kafka_consumer

Subscribes to the Kafka topic ('health-events'), processes incoming streams
using AnomalyDetector, and simulates the AWS Lambda real-time processing loop locally.
"""

import sys
import os
import json
import argparse
from typing import Dict, Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from detection.detection_rules import AnomalyDetector


def start_consumer(bootstrap_servers: str = "localhost:9092", topic: str = "health-events", group_id: str = "vitalsync-local-group"):
    """Listen to Kafka stream and evaluate anomalies in real time."""
    print("=" * 70)
    print("🎧 VitalSync Phase 2 - Apache Kafka Real-Time Stream Consumer")
    print(f"📡 Broker  : {bootstrap_servers}")
    print(f"📦 Topic   : {topic}")
    print(f"👥 Group ID: {group_id}")
    print("=" * 70)

    try:
        from kafka import KafkaConsumer  # type: ignore
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            key_deserializer=lambda k: k.decode("utf-8") if k else "unknown"
        )
        print("✅ Consumer connected and waiting for health events...\n")
    except ImportError:
        print("❌ 'kafka-python' library is not installed.")
        print("💡 Install using: pip install kafka-python")
        return
    except Exception as e:
        print(f"❌ Failed to connect to Kafka broker at {bootstrap_servers}: {e}")
        print("👉 Start Kafka first with: docker-compose -f cloud/docker-compose.yml up -d")
        return

    detector = AnomalyDetector()

    try:
        for message in consumer:
            payload = message.value
            reading = payload.get("data", payload)
            key = message.key

            eval_res = detector.evaluate_reading(reading, recent_history=[])

            status_icon = "🟢" if eval_res.severity == "NORMAL" else ("⚠️" if eval_res.severity == "WARNING" else "🚨")

            print(
                f"{status_icon} [EVENT RECEIVED] "
                f"Offset: {message.offset:<4} | "
                f"Key: {key:<7} | "
                f"HR: {reading.get('heart_rate', '--'):>5} BPM | "
                f"BP: {reading.get('systolic_bp', '--')}/{reading.get('diastolic_bp', '--')} | "
                f"SpO2: {reading.get('spo2', '--')}% | "
                f"Status: {eval_res.status}"
            )

            if eval_res.is_anomaly:
                print(f"   ↳ 🚨 Alert Reason: {eval_res.reason} (Rule: {eval_res.rule_triggered})")

    except KeyboardInterrupt:
        print("\n⏹️ Consumer stopped by user.")
    finally:
        consumer.close()


def main():
    parser = argparse.ArgumentParser(description="VitalSync Kafka Stream Consumer")
    parser.add_argument("--bootstrap", default="localhost:9092", help="Kafka bootstrap server (default: localhost:9092)")
    parser.add_argument("--topic", default="health-events", help="Kafka topic name (default: health-events)")
    parser.add_argument("--group", default="vitalsync-local-group", help="Consumer Group ID")

    args = parser.parse_args()
    start_consumer(bootstrap_servers=args.bootstrap, topic=args.topic, group_id=args.group)


if __name__ == "__main__":
    main()
