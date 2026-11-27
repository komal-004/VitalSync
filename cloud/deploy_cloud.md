# VitalSync Phase 2 — Cloud Deployment & Kafka Setup Guide

This guide explains how to run the **Phase 2 Distributed Streaming & Serverless Architecture** locally using Docker and deploy it to **AWS (Lambda, SNS, DynamoDB)**.

---

## Part A: Running Apache Kafka Locally (Docker)

### 1. Prerequisites
* Docker Desktop installed and running.
* Python dependencies installed:
  ```bash
  pip install kafka-python boto3
  ```

### 2. Start Apache Kafka & Kafka Web UI
Run the Docker Compose stack inside the `VitalSync/` folder:
```bash
docker-compose -f cloud/docker-compose.yml up -d
```
* **Kafka Broker:** Running at `localhost:9092` (KRaft mode, no Zookeeper required).
* **Kafka Web UI:** Open **[http://localhost:8085](http://localhost:8085)** in your browser to inspect topics, partitions, and live JSON messages visually!

### 3. Stream Health Events (Producer)
Open a terminal and start the Kafka Producer:
```bash
python cloud/kafka_producer.py --interval 1.0
```
*(Or pass `--dry-run` to test event formatting without Docker running).*

### 4. Consume & Analyze Events (Local Consumer)
Open a second terminal and run the Consumer:
```bash
python cloud/kafka_consumer.py
```
You will see real-time vital readings streaming through Kafka and evaluated by the Anomaly Detection Engine!

---

## Part B: Deploying to AWS (Lambda + SNS + DynamoDB)

### Step 1: Create DynamoDB Tables
1. Open **AWS Console → DynamoDB → Create table**:
   * **Table 1:** `VitalSyncReadings`
     * Partition Key: `device_id` (String)
     * Sort Key: `timestamp` (String)
   * **Table 2:** `VitalSyncAlerts`
     * Partition Key: `device_id` (String)
     * Sort Key: `alert_id` (String)

### Step 2: Create Amazon SNS Topic for Alerts
1. Open **AWS Console → Simple Notification Service (SNS) → Topics → Create topic**.
2. Type: **Standard**, Name: `vitalsync-clinical-alerts`.
3. Click **Create subscription**:
   * Protocol: **Email** (or **SMS**).
   * Endpoint: Enter your email address or phone number.
4. Confirm the subscription via the email link AWS sends you.
5. Copy the **Topic ARN** (e.g., `arn:aws:sns:us-east-1:123456789012:vitalsync-clinical-alerts`).

### Step 3: Deploy AWS Lambda Function
1. Package `detection/` and `cloud/lambda_function.py` into a `.zip` file:
   ```bash
   zip -r vitalsync_lambda.zip detection/ cloud/lambda_function.py
   ```
   *(Make sure `lambda_function.py` is at the root of the zip or set Handler to `cloud.lambda_function.lambda_handler`)*.
2. Open **AWS Console → Lambda → Create function**:
   * Name: `vitalsync-anomaly-detector`
   * Runtime: **Python 3.12** (or 3.11)
   * Upload `vitalsync_lambda.zip`.
3. Under **Configuration → Environment variables**, add:
   * `SNS_TOPIC_ARN`: `<Your SNS Topic ARN>`
   * `DYNAMODB_READINGS_TABLE`: `VitalSyncReadings`
   * `DYNAMODB_ALERTS_TABLE`: `VitalSyncAlerts`
4. Under **Configuration → Permissions**, attach IAM policies for:
   * `AmazonSNSFullAccess` (or `sns:Publish`)
   * `AmazonDynamoDBFullAccess` (or `dynamodb:PutItem`)
   * `AWSLambdaBasicExecutionRole` (CloudWatch Logs)

### Step 4: Connect Kafka Trigger (Event Source Mapping)
1. In your Lambda function, click **Add trigger**.
2. Select **MSK** (if using AWS Managed Streaming for Kafka) or **Apache Kafka** (self-managed / Confluent Cloud).
3. Set Topic name: `health-events`, Batch size: `10`.
4. Enable the trigger. Lambda will now automatically process every batch of wearable events and send SMS/Email alerts via SNS!
