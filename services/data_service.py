"""VitalSync - Data Service & Streaming Architecture Preparation
Module: services.data_service

Manages in-memory time-series state, sliding window historical buffers,
alert logging, and provides a clean streaming abstraction ready for
Apache Kafka producer integration in Phase 2.
"""

import json
from collections import deque
from typing import Dict, Any, List, Optional
import pandas as pd


class StreamEventPublisher:
    """Kafka Streaming Architecture Preparation Interface.

    In Prototype v1: Operates as an in-memory event channel.
    In Phase 2 (Cloud): Directly substituted with `confluent_kafka.Producer`
    or `kafka.KafkaProducer` without modifying the core simulator or detection engine.
    """

    DEFAULT_TOPIC = "health-events"

    def __init__(self, topic: str = DEFAULT_TOPIC, is_kafka_enabled: bool = False):
        self.topic = topic
        # Accurately reflects connection status - never claims Kafka is connected when it's not
        self.is_kafka_enabled = is_kafka_enabled
        self.last_published_payload: Optional[Dict[str, Any]] = None

    def publish_event(self, reading: Dict[str, Any]) -> Dict[str, Any]:
        """Publishes the health event payload.

        In Prototype v1, serializes and stages the event in the standardized
        cloud payload schema.
        """
        payload = {
            "topic": self.topic,
            "key": reading.get("device_id", "FIT-101"),
            "timestamp": reading.get("timestamp"),
            "data": reading,
            "cloud_metadata": {
                "schema_version": "1.0",
                "producer": "VitalSync-LocalSimulator",
                "target_lambda_arn": "arn:aws:lambda:us-east-1:123456789012:function:vitalsync-anomaly-detector",
            }
        }
        self.last_published_payload = payload
        return payload

    def get_kafka_sample_json(self) -> str:
        """Returns pretty-printed JSON of the latest message payload formatted for Kafka."""
        if not self.last_published_payload:
            return json.dumps({"status": "No event published yet"}, indent=2)
        return json.dumps(self.last_published_payload, indent=2)


class MonitoringState:
    """Maintains active session state, historical time-series buffers, and alert logs."""

    def __init__(self, max_history: int = 60):
        self.max_history = max_history
        self.readings_buffer: deque = deque(maxlen=max_history)
        self.alerts_buffer: deque = deque(maxlen=max_history)
        self.stream_publisher = StreamEventPublisher()

        # Cumulative counters
        self.total_readings_generated: int = 0
        self.total_flagged_anomalies: int = 0
        self.total_warning_alerts: int = 0
        self.total_high_alerts: int = 0
        self.latest_reading: Optional[Dict[str, Any]] = None
        self.latest_evaluation: Optional[Dict[str, Any]] = None

    def record_reading(
        self,
        reading: Dict[str, Any],
        evaluation_result: Dict[str, Any]
    ) -> None:
        """Records a new reading and its anomaly evaluation into the state buffers."""
        self.total_readings_generated += 1
        self.latest_reading = reading
        self.latest_evaluation = evaluation_result

        # Stream abstraction event publication
        self.stream_publisher.publish_event(reading)

        # Merge evaluation metadata for charting/filtering
        merged_record = dict(reading)
        merged_record["is_anomaly"] = evaluation_result["is_anomaly"]
        merged_record["severity"] = evaluation_result["severity"]
        merged_record["alert_reason"] = evaluation_result["reason"]
        merged_record["alert_status"] = evaluation_result["status"]

        self.readings_buffer.append(merged_record)

        # Log alerts if flagged
        if evaluation_result["is_anomaly"]:
            self.total_flagged_anomalies += 1
            if evaluation_result["severity"] == "HIGH":
                self.total_high_alerts += 1
            else:
                self.total_warning_alerts += 1

            alert_entry = {
                "sequence": reading.get("sequence_number", self.total_readings_generated),
                "timestamp": reading.get("timestamp"),
                "device_id": reading.get("device_id"),
                "severity": evaluation_result["severity"],
                "parameter": evaluation_result["parameter"],
                "value": str(evaluation_result["value"]),
                "reason": evaluation_result["reason"],
                "rule": evaluation_result["rule_triggered"],
                "status": evaluation_result["status"],
                "activity": reading.get("activity"),
            }
            self.alerts_buffer.append(alert_entry)

    def get_recent_history(self) -> List[Dict[str, Any]]:
        """Return list of recent readings for anomaly delta calculations."""
        return list(self.readings_buffer)

    def get_readings_dataframe(self) -> pd.DataFrame:
        """Convert readings deque to a Pandas DataFrame."""
        if not self.readings_buffer:
            return pd.DataFrame(columns=[
                "timestamp", "heart_rate", "systolic_bp", "diastolic_bp",
                "spo2", "temperature", "activity", "is_anomaly", "severity"
            ])
        return pd.DataFrame(list(self.readings_buffer))

    def get_alerts_dataframe(self) -> pd.DataFrame:
        """Convert alerts deque to a Pandas DataFrame."""
        if not self.alerts_buffer:
            return pd.DataFrame(columns=[
                "sequence", "timestamp", "severity", "parameter",
                "value", "reason", "status", "activity"
            ])
        df = pd.DataFrame(list(self.alerts_buffer))
        # Reverse so newest alerts appear at the top
        return df.iloc[::-1].reset_index(drop=True)

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Compute live summary metrics."""
        df = self.get_readings_dataframe()
        anomaly_rate = (
            (self.total_flagged_anomalies / self.total_readings_generated * 100.0)
            if self.total_readings_generated > 0 else 0.0
        )

        avg_hr = round(float(df["heart_rate"].dropna().mean()), 1) if not df.empty and "heart_rate" in df else 0.0
        avg_spo2 = round(float(df["spo2"].dropna().mean()), 1) if not df.empty and "spo2" in df else 0.0

        current_status = "NORMAL"
        if self.latest_evaluation:
            current_status = self.latest_evaluation.get("severity", "NORMAL")

        return {
            "total_generated": self.total_readings_generated,
            "total_flagged": self.total_flagged_anomalies,
            "warning_count": self.total_warning_alerts,
            "high_count": self.total_high_alerts,
            "anomaly_rate": round(anomaly_rate, 1),
            "avg_heart_rate": avg_hr,
            "avg_spo2": avg_spo2,
            "current_status": current_status,
        }

    def reset_all(self) -> None:
        """Reset all historical buffers and statistical counters."""
        self.readings_buffer.clear()
        self.alerts_buffer.clear()
        self.total_readings_generated = 0
        self.total_flagged_anomalies = 0
        self.total_warning_alerts = 0
        self.total_high_alerts = 0
        self.latest_reading = None
        self.latest_evaluation = None
