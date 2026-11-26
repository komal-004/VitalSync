"""VitalSync - Anomaly Detection Engine
Module: detection.detection_rules

Provides modular, rule-based anomaly detection for streamed vital signs.
Evaluates single-parameter thresholds, multi-parameter correlations,
sudden temporal deltas, sustained persistence, and activity context.

NOTE: All rules and thresholds are designed for technical demonstration
and educational purposes only; they do not constitute medical advice or diagnosis.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class EvaluationResult:
    """Structured result returned by the anomaly detection engine."""
    is_anomaly: bool
    severity: str  # "NORMAL", "WARNING", "HIGH"
    parameter: str
    value: Any
    reason: str
    status: str
    rule_triggered: str
    timestamp: str
    details: List[str] = field(default_factory=list)
    rules_triggered: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_anomaly": self.is_anomaly,
            "severity": self.severity,
            "parameter": self.parameter,
            "value": self.value,
            "reason": self.reason,
            "status": self.status,
            "rule_triggered": self.rule_triggered,
            "timestamp": self.timestamp,
            "details": self.details,
            "rules_triggered": self.rules_triggered,
        }


class AnomalyDetector:
    """Rule-based Vital Sign Anomaly Detection Engine."""

    # Default baseline thresholds (configurable)
    DEFAULT_THRESHOLDS = {
        # Resting Heart Rate (BPM)
        "hr_resting_min_warn": 50,
        "hr_resting_max_warn": 100,
        "hr_resting_max_crit": 130,
        # Exercise Heart Rate (BPM)
        "hr_exercise_max_warn": 165,
        "hr_exercise_max_crit": 185,
        # Blood Pressure Resting (mmHg)
        "bp_systolic_warn": 130,
        "bp_systolic_crit": 150,
        "bp_diastolic_warn": 85,
        "bp_diastolic_crit": 95,
        # Blood Pressure Exercise (physiological exertion ceiling)
        "bp_exercise_systolic_warn": 160,
        "bp_exercise_systolic_crit": 180,
        # Oxygen Saturation SpO2 (%)
        "spo2_warn": 94.0,   # 90-94% is mild hypoxia / warning
        "spo2_crit": 90.0,   # <90% is critical hypoxia / emergency
        # Temperature (°C)
        "temp_fever_warn": 37.6,
        "temp_fever_crit": 38.5,
        "temp_hypo_crit": 35.0,
        # Temporal Delta Spikes
        "delta_hr_spike": 25.0,        # Sudden jump >25 bpm without activity change
        "delta_spo2_drop": 4.0,        # Sudden drop >=4% in SpO2
        "delta_systolic_spike": 20.0,  # Sudden systolic surge >=20 mmHg
        # Persistence
        "consecutive_anomaly_escalate": 3,  # Escalate warning to HIGH if 3 consecutive
    }

    def __init__(self, custom_thresholds: Optional[Dict[str, Any]] = None):
        self.thresholds = dict(self.DEFAULT_THRESHOLDS)
        if custom_thresholds:
            self.thresholds.update(custom_thresholds)

    def update_thresholds(self, new_thresholds: Dict[str, Any]) -> None:
        """Update active detection thresholds dynamically."""
        self.thresholds.update(new_thresholds)

    def evaluate_reading(
        self,
        reading: Dict[str, Any],
        recent_history: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> EvaluationResult:
        """Evaluates a vital reading against all rule engines.

        Args:
            reading: Dictionary of current vital signs.
            recent_history: Optional list of past readings (most recent first or last).
            history: Backwards-compatible alias for recent_history.

        Returns:
            EvaluationResult detailing the severity, trigger, and explanation.
        """
        timestamp = reading.get("timestamp", "N/A")
        if recent_history is None and history is not None:
            recent_history = history
        recent_history = recent_history or []

        # -------------------------------------------------------------
        # 1. DATA VALIDATION CHECK (Missing, null, or out-of-bounds)
        # -------------------------------------------------------------
        validation_issue = self._validate_payload(reading)
        if validation_issue:
            return EvaluationResult(
                is_anomaly=True,
                severity="HIGH",
                parameter=validation_issue["parameter"],
                value=validation_issue["value"],
                reason=validation_issue["reason"],
                status="SENSOR INVALID",
                rule_triggered="RULE_DATA_VALIDATION_ERROR",
                timestamp=timestamp,
                details=[validation_issue["reason"]],
                rules_triggered=["RULE_DATA_VALIDATION_ERROR"]
            )

        hr = float(reading["heart_rate"])
        systolic = float(reading["systolic_bp"])
        diastolic = float(reading["diastolic_bp"])
        spo2 = float(reading["spo2"])
        temp = float(reading["temperature"])
        activity = str(reading.get("activity", "Resting")).capitalize()

        findings: List[Dict[str, Any]] = []

        # -------------------------------------------------------------
        # 2. ACTIVITY-AWARE THRESHOLD CHECKS
        # -------------------------------------------------------------
        # Heart Rate checks based on activity context
        if activity == "Exercise":
            if hr > self.thresholds["hr_exercise_max_crit"]:
                findings.append({
                    "severity": "HIGH",
                    "parameter": "Heart Rate",
                    "value": f"{hr} BPM",
                    "reason": f"Heart rate of {hr} BPM exceeds safe exercise ceiling ({self.thresholds['hr_exercise_max_crit']} BPM). Risk of extreme cardiac strain.",
                    "rule": "RULE_EXERCISE_EXTREME_TACHYCARDIA"
                })
            elif hr > self.thresholds["hr_exercise_max_warn"]:
                findings.append({
                    "severity": "WARNING",
                    "parameter": "Heart Rate",
                    "value": f"{hr} BPM",
                    "reason": f"Heart rate of {hr} BPM is elevated above normal workout zone ({self.thresholds['hr_exercise_max_warn']} BPM).",
                    "rule": "RULE_EXERCISE_ELEVATED_HEART_RATE"
                })
        else:  # Resting or Walking
            if hr > self.thresholds["hr_resting_max_crit"]:
                findings.append({
                    "severity": "HIGH",
                    "parameter": "Heart Rate",
                    "value": f"{hr} BPM",
                    "reason": f"Severe tachycardia ({hr} BPM) while {activity}. Well above resting critical ceiling ({self.thresholds['hr_resting_max_crit']} BPM).",
                    "rule": "RULE_RESTING_CRITICAL_TACHYCARDIA"
                })
            elif hr > self.thresholds["hr_resting_max_warn"]:
                findings.append({
                    "severity": "WARNING",
                    "parameter": "Heart Rate",
                    "value": f"{hr} BPM",
                    "reason": f"Elevated resting heart rate ({hr} BPM) exceeds resting threshold ({self.thresholds['hr_resting_max_warn']} BPM).",
                    "rule": "RULE_RESTING_ELEVATED_TACHYCARDIA"
                })
            elif hr < self.thresholds["hr_resting_min_warn"]:
                findings.append({
                    "severity": "WARNING",
                    "parameter": "Heart Rate",
                    "value": f"{hr} BPM",
                    "reason": f"Bradycardia detected ({hr} BPM below {self.thresholds['hr_resting_min_warn']} BPM threshold).",
                    "rule": "RULE_BRADYCARDIA_LOW_HEART_RATE"
                })

        # Oxygen Saturation (SpO2) checks
        if spo2 < self.thresholds["spo2_crit"]:
            findings.append({
                "severity": "HIGH",
                "parameter": "Oxygen Saturation (SpO2)",
                "value": f"{spo2}%",
                "reason": f"Critical Hypoxia: SpO2 of {spo2}% is below emergency threshold ({self.thresholds['spo2_crit']}%). Severe oxygen desaturation.",
                "rule": "RULE_CRITICAL_HYPOXIA"
            })
        elif spo2 <= self.thresholds["spo2_warn"]:
            findings.append({
                "severity": "WARNING",
                "parameter": "Oxygen Saturation (SpO2)",
                "value": f"{spo2}%",
                "reason": f"Mild Hypoxia: SpO2 of {spo2}% is below optimal baseline ({self.thresholds['spo2_warn']}%).",
                "rule": "RULE_MILD_HYPOXIA"
            })

        # Blood Pressure checks (Activity Context-Aware)
        sys_warn = self.thresholds["bp_exercise_systolic_warn"] if activity == "Exercise" else self.thresholds["bp_systolic_warn"]
        sys_crit = self.thresholds["bp_exercise_systolic_crit"] if activity == "Exercise" else self.thresholds["bp_systolic_crit"]

        if systolic >= sys_crit or diastolic >= self.thresholds["bp_diastolic_crit"]:
            findings.append({
                "severity": "HIGH",
                "parameter": "Blood Pressure",
                "value": f"{systolic}/{diastolic} mmHg",
                "reason": f"Hypertensive crisis: Blood pressure {systolic}/{diastolic} mmHg exceeds critical threshold ({sys_crit}/{self.thresholds['bp_diastolic_crit']} mmHg).",
                "rule": "RULE_CRITICAL_HYPERTENSION"
            })
        elif systolic >= sys_warn or diastolic >= self.thresholds["bp_diastolic_warn"]:
            findings.append({
                "severity": "WARNING",
                "parameter": "Blood Pressure",
                "value": f"{systolic}/{diastolic} mmHg",
                "reason": f"Elevated blood pressure ({systolic}/{diastolic} mmHg) above normal upper limit ({sys_warn}/{self.thresholds['bp_diastolic_warn']} mmHg).",
                "rule": "RULE_STAGE_1_HYPERTENSION"
            })

        # Body Temperature checks
        if temp >= self.thresholds["temp_fever_crit"]:
            findings.append({
                "severity": "HIGH",
                "parameter": "Body Temperature",
                "value": f"{temp}°C",
                "reason": f"High fever detected ({temp}°C >= {self.thresholds['temp_fever_crit']}°C). High metabolic stress.",
                "rule": "RULE_HIGH_FEVER"
            })
        elif temp >= self.thresholds["temp_fever_warn"]:
            findings.append({
                "severity": "WARNING",
                "parameter": "Body Temperature",
                "value": f"{temp}°C",
                "reason": f"Mild fever detected ({temp}°C >= {self.thresholds['temp_fever_warn']}°C).",
                "rule": "RULE_MILD_FEVER"
            })
        elif temp < self.thresholds["temp_hypo_crit"]:
            findings.append({
                "severity": "HIGH",
                "parameter": "Body Temperature",
                "value": f"{temp}°C",
                "reason": f"Hypothermia alert: Body temperature {temp}°C is below {self.thresholds['temp_hypo_crit']}°C.",
                "rule": "RULE_HYPOTHERMIA"
            })

        # -------------------------------------------------------------
        # 3. SUDDEN TEMPORAL CHANGE / DELTA SPIKE DETECTION
        # -------------------------------------------------------------
        if recent_history:
            prev_reading = recent_history[-1]
            prev_hr = prev_reading.get("heart_rate")
            prev_spo2 = prev_reading.get("spo2")
            prev_activity = str(prev_reading.get("activity", "")).capitalize()

            # Sudden HR jump without activity transition
            if (
                prev_hr is not None
                and prev_activity == activity
                and abs(hr - float(prev_hr)) >= self.thresholds["delta_hr_spike"]
            ):
                findings.append({
                    "severity": "WARNING",
                    "parameter": "Heart Rate Delta",
                    "value": f"Δ {round(hr - float(prev_hr), 1):+} BPM",
                    "reason": f"Sudden change: Heart rate jumped by {round(abs(hr - float(prev_hr)), 1)} BPM in a single step without activity change (from {prev_hr} to {hr} BPM).",
                    "rule": "RULE_SUDDEN_HR_SPIKE"
                })

            # Sudden SpO2 plunge
            if prev_spo2 is not None and (float(prev_spo2) - spo2) >= self.thresholds["delta_spo2_drop"]:
                findings.append({
                    "severity": "HIGH",
                    "parameter": "SpO2 Delta",
                    "value": f"-{round(float(prev_spo2) - spo2, 1)}%",
                    "reason": f"Rapid desaturation: SpO2 plunged by {round(float(prev_spo2) - spo2, 1)}% in a single step (from {prev_spo2}% to {spo2}%).",
                    "rule": "RULE_SUDDEN_SPO2_PLUNGE"
                })

        # -------------------------------------------------------------
        # 4. MULTI-PARAMETER CORRELATION (Complex Anomaly)
        # -------------------------------------------------------------
        # Correlation 1: Cardiorespiratory Distress (High HR + Low SpO2)
        if hr > 115 and spo2 < 93.0:
            findings.append({
                "severity": "HIGH",
                "parameter": "Multi-Parameter (HR + SpO2)",
                "value": f"HR: {hr} BPM, SpO2: {spo2}%",
                "reason": "Cardiorespiratory distress pattern: Compensatory tachycardia combined with oxygen desaturation.",
                "rule": "RULE_MULTI_CARDIORESPIRATORY_DISTRESS",
                "is_composite": True
            })

        # Correlation 2: Hypertensive Crisis + Fever (Severe Systemic Stress)
        if systolic >= 150 and temp >= 38.2:
            findings.append({
                "severity": "HIGH",
                "parameter": "Multi-Parameter (BP + Temp)",
                "value": f"BP: {systolic}/{diastolic}, Temp: {temp}°C",
                "reason": "Systemic crisis: High febrile state combined with critical hypertension.",
                "rule": "RULE_MULTI_HYPERTENSION_FEVER",
                "is_composite": True
            })

        # -------------------------------------------------------------
        # 5. REPEATED UNUSUAL READINGS ESCALATION (Persistence)
        # -------------------------------------------------------------
        if len(recent_history) >= (self.thresholds["consecutive_anomaly_escalate"] - 1):
            past_subset = recent_history[-(self.thresholds["consecutive_anomaly_escalate"] - 1):]
            all_past_flagged = all(item.get("is_anomaly", False) for item in past_subset)

            # If current reading also has findings and all recent were anomalies, escalate
            if findings and all_past_flagged:
                has_high = any(f["severity"] == "HIGH" for f in findings)
                if not has_high:
                    findings.append({
                        "severity": "HIGH",
                        "parameter": "Persistence Escalation",
                        "value": f"{self.thresholds['consecutive_anomaly_escalate']} Consecutive Flags",
                        "reason": f"Sustained anomaly: Abnormal readings persisted for {self.thresholds['consecutive_anomaly_escalate']} consecutive evaluation intervals. Escalated to HIGH.",
                        "rule": "RULE_SUSTAINED_ANOMALY_ESCALATION"
                    })

        # -------------------------------------------------------------
        # 6. AGGREGATION & SEVERITY RESOLUTION
        # -------------------------------------------------------------
        if not findings:
            return EvaluationResult(
                is_anomaly=False,
                severity="NORMAL",
                parameter="All Vitals",
                value="In Range",
                reason=f"All monitored parameters are within safe thresholds for '{activity}' activity.",
                status="Normal",
                rule_triggered="RULE_NORMAL_OPERATION",
                timestamp=timestamp,
                details=["Vitals normal."],
                rules_triggered=["RULE_NORMAL_OPERATION"]
            )

        # Determine overall severity (HIGH takes precedence over WARNING)
        overall_severity = "HIGH" if any(f["severity"] == "HIGH" for f in findings) else "WARNING"

        # Prioritize composite multi-parameter findings first if present
        composite_finding = next((f for f in findings if f.get("is_composite") and f["severity"] == overall_severity), None)
        if composite_finding:
            primary = composite_finding
        else:
            primary = next((f for f in findings if f["severity"] == overall_severity), findings[0])

        all_reasons = [f["reason"] for f in findings]
        all_rules = [f["rule"] for f in findings]

        if len(findings) > 1 and not primary.get("is_composite"):
            primary_param = f"{primary['parameter']} (+{len(findings) - 1} other alerts)"
        else:
            primary_param = primary["parameter"]

        return EvaluationResult(
            is_anomaly=True,
            severity=overall_severity,
            parameter=primary_param,
            value=primary["value"],
            reason=primary["reason"],
            status="CRITICAL ALERT" if overall_severity == "HIGH" else "WARNING FLAGGED",
            rule_triggered=primary["rule"],
            timestamp=timestamp,
            details=all_reasons,
            rules_triggered=all_rules
        )

    def _validate_payload(self, reading: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate structure, types, and physical limits of incoming reading."""
        required_keys = ["heart_rate", "systolic_bp", "diastolic_bp", "spo2", "temperature"]

        for k in required_keys:
            if k not in reading or reading[k] is None:
                return {
                    "parameter": k,
                    "value": "Missing / Null",
                    "reason": f"Corrupt sensor payload: Parameter '{k}' is missing or null."
                }
            try:
                val = float(reading[k])
            except (ValueError, TypeError):
                return {
                    "parameter": k,
                    "value": str(reading[k]),
                    "reason": f"Invalid data format: Parameter '{k}' is not a numeric value."
                }

        hr = float(reading["heart_rate"])
        systolic = float(reading["systolic_bp"])
        diastolic = float(reading["diastolic_bp"])
        spo2 = float(reading["spo2"])
        temp = float(reading["temperature"])

        # Physiological sanity checks (hardware malfunction / impossible values)
        if hr <= 0 or hr > 260:
            return {
                "parameter": "Heart Rate",
                "value": hr,
                "reason": f"Hardware sensor out-of-range: Heart rate {hr} BPM is biologically impossible."
            }
        if spo2 < 40 or spo2 > 100:
            return {
                "parameter": "SpO2",
                "value": f"{spo2}%",
                "reason": f"Sensor glitch: SpO2 reading of {spo2}% is outside the physical range (40%-100%)."
            }
        if systolic <= 30 or systolic > 280 or diastolic <= 20 or diastolic > 180:
            return {
                "parameter": "Blood Pressure",
                "value": f"{systolic}/{diastolic}",
                "reason": f"Invalid blood pressure: Reading of {systolic}/{diastolic} mmHg is outside physical limits."
            }
        if systolic <= diastolic:
            return {
                "parameter": "Blood Pressure",
                "value": f"{systolic}/{diastolic}",
                "reason": f"Physiological impossibility: Systolic pressure ({systolic}) must be strictly greater than diastolic ({diastolic})."
            }
        if temp < 28 or temp > 46:
            return {
                "parameter": "Body Temperature",
                "value": f"{temp}°C",
                "reason": f"Sensor error: Temperature {temp}°C is outside survivable measurement bounds."
            }

        return None
