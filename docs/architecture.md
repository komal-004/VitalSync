# VitalSync Architecture Specification

## 1. System Overview

**VitalSync** is a real-time vital sign monitoring and anomaly detection platform designed to continuously ingest physiological telemetric data, identify abnormal health indicators, and trigger priority alerts.

This document details both:
1. **Prototype v1 Architecture** — Fully functional local system.
2. **Phase 2 Cloud Architecture** — Scalable distributed streaming system using Apache Kafka and AWS Serverless services.

---

## 2. Prototype v1 Architecture (Current Implementation)

Prototype v1 is built with a strictly decoupled modular design to ensure zero-friction migration to Apache Kafka and AWS Lambda in Phase 2.

```mermaid
flowchart TD
    subgraph EdgeDevice["Simulated Edge Device"]
        A["HealthDataSimulator<br/>(device_id: FIT-101)"]
        A1["Physiological State Engine<br/>• Brownian Drift<br/>• Noise Injection"]
        A2["Scenario Switcher<br/>• Normal, Exercise, Hypoxia,<br/>Tachycardia, Multiple Anomalies"]
        A --> A1
        A --> A2
    end

    subgraph StreamingLayer["Streaming Abstraction Layer"]
        B["StreamEventPublisher<br/>(Interface Contract)"]
        B1["Topic: health-events<br/>Payload Packaging"]
        B --> B1
    end

    subgraph ProcessingLayer["Data Processing & Detection"]
        C["AnomalyDetector<br/>(Rule Engine)"]
        C1["Data Validation Check"]
        C2["Activity Context Filter"]
        C3["Threshold Evaluation"]
        C4["Temporal Delta / Spike Check"]
        C5["Multi-Parameter Correlation"]
        C6["Persistence Escalation"]
        C --> C1 --> C2 --> C3 --> C4 --> C5 --> C6
        
        D["MonitoringState<br/>(Sliding Buffer & State Service)"]
        C6 --> D
    end

    subgraph VisualizationLayer["Presentation Layer (Streamlit UI)"]
        E["Streamlit Dashboard<br/>(app.py)"]
        E1["KPI Metric Cards"]
        E2["Plotly Time-Series Charts"]
        E3["Alert Banner & Log Table"]
        E4["Cloud Event Inspector"]
        E --> E1
        E --> E2
        E --> E3
        E --> E4
    end

    A1 -->|"Structured Reading"| B
    B1 -->|"Ingest Event"| C
    D -->|"Provide Render State"| E
```

### Component Details

| Module | Location | Responsibility |
|---|---|---|
| **Health Simulator** | `simulator/health_generator.py` | Generates realistic, continuous physiological readings with Brownian variation and scenario triggers. |
| **Detection Engine** | `detection/detection_rules.py` | Standalone rule engine evaluating single, delta, composite, and sustained physiological conditions. |
| **Data Service** | `services/data_service.py` | Maintains a bounded sliding window of readings (`deque(maxlen=60)`), alert history, and statistics. |
| **Streaming Abstraction** | `services/data_service.py` | Stages serialized payloads using the standardized Kafka schema without needing external brokers in v1. |
| **User Interface** | `app.py` & `components/` | Streamlit web application with custom CSS styling, Plotly charts, and live interactive controls. |

---

## 3. Phase 2 Cloud Architecture (Distributed Roadmap)

In Phase 2, the local in-memory event bus is replaced by an enterprise cloud streaming pipeline.

```mermaid
flowchart LR
    subgraph IoT["Edge / Wearables"]
        W1["Wearable Sensor 1<br/>(FIT-101)"]
        W2["Wearable Sensor 2<br/>(FIT-102)"]
        W3["Wearable Sensor N<br/>(FIT-N)"]
    end

    subgraph Ingestion["Distributed Stream Ingestion"]
        KP["Python Kafka Producer<br/>(confluent-kafka)"]
        K1["Apache Kafka Cluster<br/>Topic: health-events<br/>Key: device_id<br/>Partitions: 6"]
        W1 --> KP
        W2 --> KP
        W3 --> KP
        KP -->|"Batch Publish (SSL/SASL)"| K1
    end

    subgraph Compute["Serverless Real-Time Analytics"]
        L["AWS Lambda Function<br/>(vitalsync-anomaly-detector)<br/>• ESM Event Source Mapping<br/>• Batch Size: 50 | Window: 1s"]
        K1 -->|"Event Trigger"| L
    end

    subgraph Notification["Alert & Dispatch Layer"]
        SNS["Amazon SNS Topic<br/>(vitalsync-clinical-alerts)"]
        SMS["SMS to Emergency Contact"]
        EMAIL["Email to Attending Doctor"]
        WEBHOOK["PagerDuty / Hospital Webhook"]
        
        L -->|"High/Critical Severity"| SNS
        SNS --> SMS
        SNS --> EMAIL
        SNS --> WEBHOOK
    end

    subgraph Storage["Storage & Analytics Layer"]
        DDB[("Amazon DynamoDB<br/>Table: VitalSyncReadings<br/>PK: device_id | SK: timestamp")]
        DDB_ALERTS[("Amazon DynamoDB<br/>Table: VitalSyncAlerts<br/>PK: device_id | SK: alert_id")]
        
        L -->|"Write All Readings"| DDB
        L -->|"Write Flagged Anomalies"| DDB_ALERTS
    end

    subgraph Presentation["Clinical Monitoring Dashboard"]
        DASH["Streamlit Cloud / Next.js<br/>Clinician Central Portal"]
        DDB -->|"WebSocket / API Query"| DASH
    end
```

---

## 4. Standard Event Schema (Kafka Topic: `health-events`)

Every event sent to the broker adheres to the following JSON specification:

```json
{
  "topic": "health-events",
  "key": "FIT-101",
  "timestamp": "2026-11-26 12:30:15",
  "data": {
    "device_id": "FIT-101",
    "sequence_number": 42,
    "timestamp": "2026-11-26 12:30:15",
    "heart_rate": 142.5,
    "systolic_bp": 138.0,
    "diastolic_bp": 88.0,
    "spo2": 97.2,
    "temperature": 37.1,
    "activity": "Resting",
    "scenario": "Unusual Heart Rate (Tachycardia)",
    "is_simulated": true
  },
  "cloud_metadata": {
    "schema_version": "1.0",
    "producer": "VitalSync-LocalSimulator",
    "target_lambda_arn": "arn:aws:lambda:us-east-1:123456789012:function:vitalsync-anomaly-detector"
  }
}
```

---

## 5. Architectural Design Principles

1. **Separation of Concerns:**
   The detection rules have zero dependencies on the presentation framework (Streamlit) or data storage layer.
2. **Context-Aware Processing:**
   Rules take into account physiological state (e.g. "Exercise" vs "Resting"), preventing false positives.
3. **Pluggable Event Emitter:**
   The `StreamEventPublisher` class mirrors the API of `kafka-python` / `confluent-kafka`, making the future transition purely a matter of dependency configuration.
4. **Idempotence & Statelessness:**
   The Lambda function in Phase 2 executes as a stateless function, fetching recent time-series state from DynamoDB or ElastiCache Redis for temporal window queries.
