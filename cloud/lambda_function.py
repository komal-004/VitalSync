"""VitalSync - Phase 2 Serverless Analytics Engine
Module: cloud.lambda_function

AWS Lambda Function Handler that processes batches of health events
from Apache Kafka (via Event Source Mapping / ESM), validates data integrity,
executes the 6-stage anomaly detection engine, dispatches critical alerts
to Amazon SNS, and persists time-series history to Amazon DynamoDB.
"""

import sys
import os
import json
import base64
from typing import Dict, Any, List, Optional
from decimal import Decimal

# Ensure project root is available for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from detection.detection_rules import AnomalyDetector, EvaluationResult

# Initialize the detector instance outside the handler (persists across warm invocations)
detector = AnomalyDetector()

# AWS Configuration from environment variables
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:vitalsync-clinical-alerts")
DYNAMODB_READINGS_TABLE = os.environ.get("DYNAMODB_READINGS_TABLE", "VitalSyncReadings")
DYNAMODB_ALERTS_TABLE = os.environ.get("DYNAMODB_ALERTS_TABLE", "VitalSyncAlerts")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def _get_boto3_clients():
    """Lazily initialize AWS SDK clients (boto3) with safe error handling."""
    try:
        import boto3  # type: ignore
        sns = boto3.client("sns", region_name=AWS_REGION)
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        return sns, dynamodb
    except Exception as e:
        # Gracefully handle local testing without AWS credentials configured
        return None, None


def _float_to_decimal(obj: Any) -> Any:
    """Helper to convert float values to Decimal for Amazon DynamoDB compliance."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: _float_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_float_to_decimal(v) for v in obj]
    return obj


def dispatch_sns_alert(sns_client, evaluation: EvaluationResult, reading: Dict[str, Any]) -> bool:
    """Publish an urgent alert message to the Amazon SNS topic."""
    device_id = reading.get("device_id", "UNKNOWN")
    subject = f"🚨 VitalSync ALERT: {evaluation.severity} on {device_id}"
    message_body = (
        f"VITALS-SYNC CLINICAL MONITORING ALERT\n"
        f"-------------------------------------\n"
        f"Severity   : {evaluation.severity}\n"
        f"Device ID  : {device_id}\n"
        f"Timestamp  : {evaluation.timestamp}\n"
        f"Parameter  : {evaluation.parameter}\n"
        f"Trigger Val: {evaluation.value}\n"
        f"Rule ID    : {evaluation.rule_triggered}\n"
        f"Explanation: {evaluation.reason}\n\n"
        f"Current Vitals:\n"
        f"• Heart Rate    : {reading.get('heart_rate')} BPM\n"
        f"• Blood Pressure: {reading.get('systolic_bp')}/{reading.get('diastolic_bp')} mmHg\n"
        f"• Oxygen SpO2   : {reading.get('spo2')}%\n"
        f"• Temperature   : {reading.get('temperature')} °C\n"
        f"• Activity      : {reading.get('activity')}\n\n"
        f"Action: Please review patient immediately.\n"
    )

    if sns_client and "123456789012" not in SNS_TOPIC_ARN:
        try:
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=subject,
                Message=message_body
            )
            print(f"📬 [SNS DISPATCH] Published alert to SNS topic {SNS_TOPIC_ARN}")
            return True
        except Exception as e:
            print(f"⚠️ [SNS ERROR] Failed to publish to SNS: {e}")
            return False
    else:
        print(f"📬 [MOCK SNS DISPATCH] {subject}\n{message_body}")
        return True


def persist_to_dynamodb(dynamodb_resource, reading: Dict[str, Any], evaluation: EvaluationResult) -> bool:
    """Store raw readings and flagged alerts in Amazon DynamoDB."""
    if not dynamodb_resource:
        return False

    try:
        # 1. Save reading to time-series table
        readings_table = dynamodb_resource.Table(DYNAMODB_READINGS_TABLE)
        reading_item = _float_to_decimal(dict(reading))
        reading_item["is_anomaly"] = evaluation.is_anomaly
        reading_item["severity"] = evaluation.severity
        readings_table.put_item(Item=reading_item)

        # 2. If flagged, save alert to dedicated alerts table
        if evaluation.is_anomaly:
            alerts_table = dynamodb_resource.Table(DYNAMODB_ALERTS_TABLE)
            alert_item = _float_to_decimal({
                "device_id": reading.get("device_id", "UNKNOWN"),
                "alert_id": f"{reading.get('device_id')}_{reading.get('timestamp')}",
                "timestamp": reading.get("timestamp"),
                "severity": evaluation.severity,
                "parameter": evaluation.parameter,
                "value": str(evaluation.value),
                "reason": evaluation.reason,
                "rule": evaluation.rule_triggered,
                "reading": reading
            })
            alerts_table.put_item(Item=alert_item)

        return True
    except Exception as e:
        print(f"⚠️ [DYNAMODB ERROR] Failed to persist item: {e}")
        return False


def decode_kafka_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Decode an incoming Kafka record from AWS Event Source Mapping (ESM)."""
    raw_val = record.get("value", "")

    # In AWS ESM, Kafka message value is base64-encoded
    if isinstance(raw_val, str):
        try:
            decoded_bytes = base64.b64decode(raw_val)
            payload = json.loads(decoded_bytes.decode("utf-8"))
        except Exception:
            # If not base64, try direct JSON
            try:
                payload = json.loads(raw_val)
            except Exception:
                payload = {"data": record}
    elif isinstance(raw_val, dict):
        payload = raw_val
    else:
        payload = {"data": record}

    # Extract inner physiological data dictionary
    if "data" in payload and isinstance(payload["data"], dict):
        return payload["data"]
    return payload


def lambda_handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """AWS Lambda entry point for Apache Kafka batch processing.

    Args:
        event: Dict containing Kafka ESM records or direct JSON invocation payload.
        context: AWS Lambda context object.

    Returns:
        Structured HTTP/Lambda response detailing processing counts and findings.
    """
    sns_client, dynamodb_resource = _get_boto3_clients()

    raw_readings: List[Dict[str, Any]] = []

    # -----------------------------------------------------------------
    # Case 1: Invocation from AWS Kafka Event Source Mapping (MSK / Self-Managed)
    # -----------------------------------------------------------------
    if "records" in event and isinstance(event["records"], dict):
        for topic_partition, record_list in event["records"].items():
            for rec in record_list:
                reading = decode_kafka_record(rec)
                raw_readings.append(reading)

    # -----------------------------------------------------------------
    # Case 2: Direct API Gateway / Test Event invocation
    # -----------------------------------------------------------------
    elif "data" in event and isinstance(event["data"], dict):
        raw_readings.append(event["data"])
    elif "heart_rate" in event:
        raw_readings.append(event)
    elif "body" in event:
        try:
            body_dict = json.loads(event["body"])
            if "data" in body_dict:
                raw_readings.append(body_dict["data"])
            else:
                raw_readings.append(body_dict)
        except Exception:
            pass

    processed_summary = []
    anomalies_count = 0
    alerts_dispatched = 0

    # -----------------------------------------------------------------
    # Process each vital reading through the Anomaly Detector
    # -----------------------------------------------------------------
    for reading in raw_readings:
        eval_result = detector.evaluate_reading(reading, recent_history=[])

        is_anomaly = eval_result.is_anomaly
        severity = eval_result.severity

        if is_anomaly:
            anomalies_count += 1
            # Dispatch SNS notification for HIGH priority critical conditions
            if severity == "HIGH":
                dispatched = dispatch_sns_alert(sns_client, eval_result, reading)
                if dispatched:
                    alerts_dispatched += 1

        # Save to DynamoDB
        persist_to_dynamodb(dynamodb_resource, reading, eval_result)

        processed_summary.append({
            "device_id": reading.get("device_id"),
            "timestamp": reading.get("timestamp"),
            "heart_rate": reading.get("heart_rate"),
            "bp": f"{reading.get('systolic_bp')}/{reading.get('diastolic_bp')}",
            "spo2": reading.get("spo2"),
            "is_anomaly": is_anomaly,
            "severity": severity,
            "rule": eval_result.rule_triggered,
            "reason": eval_result.reason
        })

    print(
        f"✅ [LAMBDA EXECUTION] Batch Size: {len(raw_readings)} | "
        f"Anomalies Flagged: {anomalies_count} | "
        f"SNS Alerts Sent: {alerts_dispatched}"
    )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": {
            "status": "SUCCESS",
            "batch_size": len(raw_readings),
            "anomalies_detected": anomalies_count,
            "alerts_dispatched": alerts_dispatched,
            "evaluations": processed_summary
        }
    }


if __name__ == "__main__":
    # Local CLI test of the Lambda function with mock event
    sample_test_event = {
        "data": {
            "device_id": "FIT-101",
            "sequence_number": 1,
            "timestamp": "2026-11-27 12:00:00",
            "heart_rate": 168.0,
            "systolic_bp": 172.0,
            "diastolic_bp": 105.0,
            "spo2": 88.0,
            "temperature": 38.8,
            "activity": "Resting",
            "scenario": "Multiple Anomalies (Critical Crisis)"
        }
    }
    result = lambda_handler(sample_test_event)
    print("\nLambda Execution Result:")
    print(json.dumps(result, indent=2, default=str))
