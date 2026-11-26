# VitalSync: Academic Project Overview & Defense Guide

**Degree / Course:** B.Tech in Computer Science & Engineering (3rd Year)  
**Project Title:** VitalSync — Real-Time Vital Sign Monitoring & Anomaly Detection System Using Apache Kafka and AWS Lambda  
**Domain:** HealthTech, Internet of Medical Things (IoMT), Distributed Streaming, Serverless Cloud Computing  
**Document Purpose:** Academic project proposal, architectural rationale, and faculty review documentation.

---

## 1. Project Motivation & Problem Statement

### 1.1 Context
In contemporary clinical and outpatient care, continuous patient monitoring is vital for early identification of acute clinical deterioration (such as myocardial infarction, sepsis, hypertensive crises, or respiratory failure). Wearable Internet of Medical Things (IoMT) devices continuously generate streams of physiological time-series data.

### 1.2 The Core Problem
Conventional healthcare telemetry systems suffer from three critical bottlenecks:
1. **Batch Processing Latency:** Traditional systems upload vital data in periodic batches (e.g., every 15–60 minutes), delaying intervention during sudden clinical emergencies.
2. **Alert Fatigue & Inadequate Contextualization:** Naive static threshold triggers generate high rates of false positives because they fail to account for patient activity context (e.g., an elevated heart rate of 145 BPM during vigorous exercise is physiological, whereas the same rate during sleep represents an acute arrhythmia).
3. **Monolithic Ingestion Bottlenecks:** Centralized databases struggle to handle thousands of concurrent streaming wearable sensors without experiencing ingestion bottlenecks or dropped packets.

---

## 2. Project Objectives

1. **Synthetic Physiological Telemetry:** Design a deterministic, mathematically grounded simulation engine generating multi-parameter vitals (Heart Rate, Blood Pressure, SpO2, Temperature, Activity) with realistic temporal continuity.
2. **Context-Aware Anomaly Detection:** Implement a decoupled, rule-based detection engine capable of evaluating:
   - Dynamic thresholds conditioned on user physical activity.
   - Sudden temporal deltas (rate of change between consecutive intervals).
   - Multi-parameter correlated anomalies (e.g., cardiorespiratory distress combining tachycardia with hypoxia).
   - Sustained abnormal readings (persistence-based alert escalation).
   - Telemetry integrity validation (missing values, impossible physical readings).
3. **Real-Time Interactive Dashboard:** Provide an intuitive monitoring interface with interactive time-series plots, active alert feeds, and scenario injection capabilities.
4. **Cloud-Ready Event-Driven Blueprint:** Architect the system using modular interfaces ready to connect to **Apache Kafka** and **AWS Serverless** in Phase 2.

---

## 3. Technology Stack Justification (Why These Technologies?)

When defending this project to a faculty panel, the following justifications explain each architectural decision:

### Why Python?
- **Rich Scientific & Data Ecosystem:** Python provides first-class support for stream manipulation via Pandas, NumPy, and scientific data structures.
- **Native Cloud Integration:** Python is one of the premier first-class runtimes for AWS Lambda, offering near-instant cold-start times (~150ms) and low memory overhead compared to JVM runtimes.
- **Rapid Prototyping:** Streamlit enables reactive, low-latency UI rendering in pure Python without front-end JavaScript overhead.

### Why Apache Kafka?
- **High-Throughput Partitioned Log:** Unlike traditional message brokers (such as RabbitMQ or ActiveMQ) that delete messages upon consumption, Kafka retains data as a durable, ordered distributed commit log.
- **Partitioning by Device ID:** By setting `device_id` as the message key, all events from a specific patient are guaranteed to arrive in strictly ordered sequence within the same Kafka partition.
- **Decoupling Producers & Consumers:** The wearable device only needs to publish to Kafka; it does not know or care how many downstream consumers (analytics, long-term archival, live dashboards) process the stream.
- **Backpressure Handling:** During network spikes or backend throttling, Kafka buffers events reliably without dropping sensor packets.

### Why AWS Lambda?
- **Event-Driven Serverless Compute:** Lambda executes code only when events arrive from Kafka topics via AWS EventBridge or Kafka Event Source Mapping (ESM).
- **Cost Efficiency:** No persistent EC2 instances need to run 24/7. When patient devices are idle or disconnected, compute costs are exactly $0.00.
- **Sub-Second Auto-Scaling:** As the number of monitored patients increases from 10 to 10,000, AWS automatically provisions concurrent micro-instances to handle the incoming event batches.

### Why Amazon SNS (Simple Notification Service)?
- **Pub/Sub Fan-Out:** When the detection engine flags a critical event (e.g., SpO2 < 90%), a single publish to an SNS topic can instantly fan out to multiple subscribers simultaneously: SMS messages to the patient's caregiver, email notifications to the attending physician, and webhook alerts to a hospital triage board.

---

## 4. Anomaly Detection Methodology

The detection module (`detection/detection_rules.py`) uses a tiered multi-stage rule engine:

```
Raw Reading 
  → [Stage 1: Hardware & Range Validation]
  → [Stage 2: Activity Context Normalization]
  → [Stage 3: Configurable Threshold Check]
  → [Stage 4: Temporal Delta (Spike) Analysis]
  → [Stage 5: Multi-Parameter Correlation]
  → [Stage 6: Persistence & Severity Resolution]
  → Structured Evaluation Result
```

### Detection Criteria Matrix

| Anomaly Type | Condition / Trigger | Clinical Rationalization |
|---|---|---|
| **Resting Tachycardia** | HR > 100 BPM (Warning), HR > 130 BPM (High) | Risk of supraventricular arrhythmia or acute stress during rest. |
| **Exercise Exertion** | HR > 165 BPM (Warning), HR > 185 BPM (High) | Activity context prevents false alerts while jogging, but flags overexertion. |
| **Hypoxia** | SpO2: 90%–94% (Mild), SpO2 < 90% (Critical) | Oxygen desaturation requiring supplemental oxygen or clinical intervention. |
| **Hypertensive Crisis** | Systolic ≥ 150 mmHg or Diastolic ≥ 95 mmHg | Acute risk of stroke or cardiovascular compromise. |
| **Cardiorespiratory Distress** | HR > 115 BPM **AND** SpO2 < 93% | Compensatory tachycardia in response to systemic hypoxia. |
| **Sudden Vital Spike** | ΔHR > 25 BPM in 1 step without activity transition | Paroxysmal arrhythmia or physical trauma. |
| **Sustained Anomaly** | 3 consecutive flagged readings | Escalates low-level warnings to high priority if sustained over time. |

---

## 5. Scope of Prototype v1 vs. Phase 2 Cloud Roadmap

To maintain engineering integrity, the prototype explicitly distinguishes between working local functionality and future cloud extensions:

| Dimension | Prototype v1 (Working Local System) | Phase 2 (Planned Cloud Deployment) |
|---|---|---|
| **Data Ingestion** | Local in-memory state engine | Apache Kafka cluster (AWS MSK / Confluent Cloud) |
| **Detection Compute** | Local Python module | AWS Lambda microservice triggered on Kafka topic |
| **Persistence** | Sliding in-memory circular buffer (`deque`) | Amazon DynamoDB (NoSQL single-table time-series design) |
| **Alert Dispatch** | Interactive UI banner & styled log table | Amazon SNS (SMS text alerts, email, hospital webhooks) |
| **Device Source** | Multi-scenario synthetic generator | Real wearable (ESP32 / Raspberry Pi IoT device) |

---

## 6. Safety & Educational Disclaimer

> [!IMPORTANT]
> **Academic & Technical Demonstration Notice:**  
> VitalSync is developed exclusively for academic, engineering, and educational purposes to demonstrate stream processing and serverless event-driven architectures. It is **not** a certified medical diagnostic device and must not be used for medical decision-making or diagnosis.
