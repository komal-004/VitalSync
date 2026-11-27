"""VitalSync - Phase 2 Apache Kafka Producer
Module: cloud.kafka_producer

Streams synthetic health events from HealthDataSimulator into an
Apache Kafka topic ('health-events') with message partitioning by device_id.
"""

import sys
import os
import json
import time
import argparse
from typing import Dict, Any, Optional

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from simulator.health_generator import HealthDataSimulator


class VitalSyncKafkaProducer:
    """Publishes streaming health events to Apache Kafka."""

    DEFAULT_TOPIC = "health-events"
    DEFAULT_BOOTSTRAP = "localhost:9092"

    def __init__(
        self,
        bootstrap_servers: str = DEFAULT_BOOTSTRAP,
        topic: str = DEFAULT_TOPIC,
        device_id: str = "FIT-101",
        dry_run: bool = False
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.device_id = device_id
        self.dry_run = dry_run
        self.simulator = HealthDataSimulator(device_id=device_id)
        self.producer = None

        if not dry_run:
            self._init_producer()

    def _init_producer(self) -> None:
        """Initialize the Kafka Producer client."""
        try:
            from kafka import KafkaProducer  # type: ignore
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: str(k).encode("utf-8"),
                acks="all",
                retries=3,
                request_timeout_ms=10000,
            )
            print(f"✅ Connected to Apache Kafka broker at {self.bootstrap_servers}")
            print(f"📦 Target Topic: '{self.topic}' (Key: {self.device_id})")
        except ImportError:
            print("⚠️ 'kafka-python' library is not installed.")
            print("👉 Running in DRY-RUN mode (formatting events without network publishing).")
            print("💡 To install: pip install kafka-python")
            self.dry_run = True
        except Exception as e:
            print(f"⚠️ Could not connect to Kafka broker at {self.bootstrap_servers}: {e}")
            print("👉 Falling back to DRY-RUN mode. (Start broker with: docker-compose -f cloud/docker-compose.yml up -d)")
            self.dry_run = True

    def build_event_envelope(self, reading: Dict[str, Any]) -> Dict[str, Any]:
        """Wrap the reading in the standardized cloud event schema."""
        return {
            "topic": self.topic,
            "key": self.device_id,
            "timestamp": reading.get("timestamp"),
            "data": reading,
            "cloud_metadata": {
                "schema_version": "2.0",
                "producer": "VitalSync-KafkaProducer",
                "target_lambda_arn": "arn:aws:lambda:us-east-1:123456789012:function:vitalsync-anomaly-detector",
            }
        }

    def publish_reading(self, scenario: Optional[str] = None) -> Dict[str, Any]:
        """Generate and publish a single vital reading to Kafka."""
        reading = self.simulator.generate_reading(scenario=scenario)
        event = self.build_event_envelope(reading)

        if not self.dry_run and self.producer:
            future = self.producer.send(
                self.topic,
                key=self.device_id,
                value=event
            )
            # Wait for send acknowledgment
            record_metadata = future.get(timeout=5)
            print(
                f"🚀 [KAFKA PUB] Partition: {record_metadata.partition} | "
                f"Offset: {record_metadata.offset} | "
                f"HR: {reading['heart_rate']} BPM | "
                f"BP: {reading['systolic_bp']}/{reading['diastolic_bp']} | "
                f"SpO2: {reading['spo2']}% | "
                f"Activity: {reading['activity']} | "
                f"Scenario: {reading['scenario']}"
            )
        else:
            print(
                f"📝 [DRY-RUN PUB] Key: {self.device_id} | "
                f"HR: {reading['heart_rate']} BPM | "
                f"BP: {reading['systolic_bp']}/{reading['diastolic_bp']} | "
                f"SpO2: {reading['spo2']}% | "
                f"Activity: {reading['activity']} | "
                f"Scenario: {reading['scenario']}"
            )

        return event

    def start_streaming(self, interval: float = 1.0, max_events: Optional[int] = None) -> None:
        """Stream continuous vital events to the Kafka broker."""
        print("=" * 70)
        print("🫀 VitalSync Phase 2 - Apache Kafka Event Streaming Engine")
        print(f"📡 Device ID : {self.device_id}")
        print(f"📦 Topic     : {self.topic}")
        print(f"⏱️ Interval  : {interval} second(s)")
        print(f"Mode         : {'DRY RUN' if self.dry_run else 'LIVE KAFKA BROKER'}")
        print("=" * 70)
        print("Press Ctrl+C to stop streaming.\n")

        count = 0
        try:
            while True:
                self.publish_reading()
                count += 1
                if max_events and count >= max_events:
                    print(f"\n✅ Finished publishing {count} events.")
                    break
                time.sleep(interval)
        except KeyboardInterrupt:
            print(f"\n⏹️ Streaming stopped by user. Total events emitted: {count}")
        finally:
            if self.producer:
                self.producer.flush()
                self.producer.close()


def main():
    parser = argparse.ArgumentParser(description="VitalSync Kafka Health Event Producer")
    parser.add_argument("--bootstrap", default="localhost:9092", help="Kafka broker bootstrap servers (default: localhost:9092)")
    parser.add_argument("--topic", default="health-events", help="Kafka topic name (default: health-events)")
    parser.add_argument("--device", default="FIT-101", help="Device ID (default: FIT-101)")
    parser.add_argument("--interval", type=float, default=1.0, help="Stream interval in seconds (default: 1.0)")
    parser.add_argument("--scenario", default=None, help="Force specific simulation scenario")
    parser.add_argument("--count", type=int, default=None, help="Number of events to emit before exit (default: infinite)")
    parser.add_argument("--dry-run", action="store_true", help="Format and print events without sending to a live Kafka broker")

    args = parser.parse_args()

    producer = VitalSyncKafkaProducer(
        bootstrap_servers=args.bootstrap,
        topic=args.topic,
        device_id=args.device,
        dry_run=args.dry_run
    )

    if args.scenario:
        producer.simulator.set_scenario(args.scenario)

    producer.start_streaming(interval=args.interval, max_events=args.count)


if __name__ == "__main__":
    main()
