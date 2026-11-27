"""VitalSync - Health Data Simulator
Module: simulator.health_generator

Generates synthetic vital signs with realistic physiological dynamics,
smooth variations, and configurable simulation scenarios for real-time
streaming demonstration.
"""

import datetime
import random
from typing import Dict, Any, Optional


class HealthDataSimulator:
    """Simulates real-time vital signs from a wearable device (e.g. FIT-101).

    Maintains physiological state across consecutive readings to provide realistic
    time-series continuity rather than disconnected random values.
    """

    SCENARIOS = {
        "AUTO_REALTIME": "🔄 Live Real-Time Stream (Progressive)",
        "NORMAL_RESTING": "🟢 Normal Resting (HR ~65-85 BPM)",
        "WALKING": "🚶 Walking Activity (HR ~95 BPM, BP ~125/81)",
        "EXERCISE": "🏃 Exercise Cardio (HR ~140 BPM, BP ~142/84)",
        "HR_BRADYCARDIA": "⚠️ Low Heart Rate (Bradycardia: 44 BPM Warning)",
        "HR_ELEVATED": "⚠️ Elevated Heart Rate (Tachycardia: 108 BPM Warning)",
        "HR_CRITICAL": "🚨 Extreme Heart Rate (Severe Tachycardia: 168 BPM Critical)",
        "UNUSUAL_HEART_RATE": "🚨 Unusual Heart Rate (Tachycardia: 168 BPM Critical)",
        "UNUSUAL_BP_STAGE1": "⚠️ High Blood Pressure (Stage 1 Warning: 136/88)",
        "UNUSUAL_BP_STAGE2": "🚨 Severe Blood Pressure (Stage 2 Crisis: 168/104)",
        "UNUSUAL_SPO2": "🚨 Unusual Oxygen SpO2 (Hypoxia: 87.5% Critical)",
        "MULTIPLE_ANOMALIES": "🚨 Multiple Crisis (High HR + High BP + Hypoxia + Fever)",
        "SUDDEN_SPIKE": "⚡ Sudden Vital Spike (+40 BPM Delta)",
        "INVALID_DATA": "❌ Sensor Glitch (Out-of-Bounds Data)",
    }

    def __init__(self, device_id: str = "FIT-101"):
        self.device_id = device_id
        self.current_scenario = "AUTO_REALTIME"
        self.sequence_number = 0
        self.reset_state()

    def reset_state(self) -> None:
        """Reset physiological state back to baseline resting conditions."""
        self.sequence_number = 0
        self._current_hr = 72.0
        self._current_systolic = 118.0
        self._current_diastolic = 78.0
        self._current_spo2 = 98.5
        self._current_temp = 36.8
        self._current_activity = "Resting"

    def set_scenario(self, scenario_key: str) -> None:
        """Update active simulation scenario."""
        if scenario_key in self.SCENARIOS:
            self.current_scenario = scenario_key
        else:
            self.current_scenario = "NORMAL_RESTING"

    def _drift(self, current: float, target: float, speed: float = 0.25, noise: float = 0.5) -> float:
        """Smoothly drift the current value toward a target baseline with minor noise."""
        delta = (target - current) * speed
        random_noise = random.uniform(-noise, noise)
        return current + delta + random_noise

    def generate_reading(
        self,
        scenario: Optional[str] = None,
        custom_timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate the next synthetic health reading.

        Args:
            scenario: Optional override for the scenario.
            custom_timestamp: Optional ISO timestamp override.

        Returns:
            Dictionary containing structured reading payload.
        """
        active_scenario = scenario if scenario in self.SCENARIOS else self.current_scenario
        self.sequence_number += 1

        timestamp = custom_timestamp or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # -------------------------------------------------------------
        # Scenario 0: Live Real-Time Progressive Stream (Default)
        # Gradually climbs on each step: Normal (72-95) -> Warning (100+) -> Alert (132+) -> Recovery
        # -------------------------------------------------------------
        if active_scenario == "AUTO_REALTIME":
            self._current_activity = "Resting"
            cycle_pos = (self.sequence_number - 1) % 14  # 14-step realistic physiological wave

            if cycle_pos == 0:
                target_hr, target_sys, target_dia, target_spo2, target_temp = 72.0, 118.0, 78.0, 98.5, 36.8
            elif cycle_pos < 5:
                # Progressive climb: ~79 -> 86 -> 94 -> 102 (crosses 100+ -> WARNING)
                target_hr = 72.0 + cycle_pos * 7.5
                target_sys = 118.0 + cycle_pos * 3.5
                target_dia = 78.0 + cycle_pos * 2.0
                target_spo2 = 98.5 - cycle_pos * 0.4
                target_temp = 36.8 + cycle_pos * 0.08
            elif cycle_pos < 9:
                # Escalation to critical: ~112 -> 122 -> 134 -> 144 (crosses 130+ -> CRITICAL ALERT)
                step_in_phase = cycle_pos - 4
                target_hr = 102.0 + step_in_phase * 10.5
                target_sys = 132.0 + step_in_phase * 4.5
                target_dia = 86.0 + step_in_phase * 2.5
                target_spo2 = 96.9 - step_in_phase * 1.1
                target_temp = 37.1 + step_in_phase * 0.15
            else:
                # Gradual recovery back to normal: ~128 -> 112 -> 96 -> 82 -> 74
                step_in_phase = cycle_pos - 8
                target_hr = max(72.0, 144.0 - step_in_phase * 14.0)
                target_sys = max(118.0, 150.0 - step_in_phase * 6.5)
                target_dia = max(78.0, 96.0 - step_in_phase * 3.5)
                target_spo2 = min(98.5, 92.5 + step_in_phase * 1.2)
                target_temp = max(36.8, 37.7 - step_in_phase * 0.18)

            self._current_hr = round(target_hr + random.uniform(-1.5, 1.5), 1)
            self._current_systolic = round(target_sys + random.uniform(-1.5, 1.5), 1)
            self._current_diastolic = round(target_dia + random.uniform(-1.0, 1.0), 1)
            self._current_spo2 = round(min(100.0, target_spo2 + random.uniform(-0.2, 0.2)), 1)
            self._current_temp = round(target_temp + random.uniform(-0.05, 0.05), 1)

        # -------------------------------------------------------------
        # Scenario 1: Normal Resting (natural variation 64 - 88 BPM)
        # -------------------------------------------------------------
        elif active_scenario == "NORMAL_RESTING":
            import math
            self._current_activity = "Resting"
            # Gently oscillate baseline between 68 and 84 BPM so it doesn't stay stuck at 72
            dynamic_target_hr = 76.0 + 8.0 * math.sin(self.sequence_number * 0.45)
            self._current_hr = self._drift(self._current_hr, target=dynamic_target_hr, speed=0.3, noise=2.5)
            self._current_hr = max(62.0, min(90.0, self._current_hr))

            dynamic_target_sys = 119.0 + 4.0 * math.cos(self.sequence_number * 0.3)
            self._current_systolic = self._drift(self._current_systolic, target=dynamic_target_sys, speed=0.25, noise=1.8)
            self._current_systolic = max(110.0, min(127.0, self._current_systolic))

            self._current_diastolic = self._drift(self._current_diastolic, target=78.0, speed=0.2, noise=1.2)
            self._current_diastolic = max(70.0, min(84.0, self._current_diastolic))

            self._current_spo2 = self._drift(self._current_spo2, target=98.4, speed=0.15, noise=0.3)
            self._current_spo2 = max(96.5, min(100.0, self._current_spo2))

            self._current_temp = self._drift(self._current_temp, target=36.8, speed=0.1, noise=0.06)
            self._current_temp = max(36.4, min(37.2, self._current_temp))

        # -------------------------------------------------------------
        # Scenario 2: Walking
        # -------------------------------------------------------------
        elif active_scenario == "WALKING":
            self._current_activity = "Walking"
            self._current_hr = self._drift(self._current_hr, target=95.0, speed=0.2, noise=1.8)
            self._current_hr = max(85.0, min(110.0, self._current_hr))

            self._current_systolic = self._drift(self._current_systolic, target=125.0, speed=0.15, noise=1.5)
            self._current_systolic = max(118.0, min(132.0, self._current_systolic))

            self._current_diastolic = self._drift(self._current_diastolic, target=81.0, speed=0.15, noise=1.0)
            self._current_diastolic = max(75.0, min(86.0, self._current_diastolic))

            self._current_spo2 = self._drift(self._current_spo2, target=98.0, speed=0.1, noise=0.3)
            self._current_spo2 = max(96.0, min(99.5, self._current_spo2))

            self._current_temp = self._drift(self._current_temp, target=37.0, speed=0.08, noise=0.05)
            self._current_temp = max(36.7, min(37.3, self._current_temp))

        # -------------------------------------------------------------
        # Scenario 3: Exercise (Cardio Workout)
        # -------------------------------------------------------------
        elif active_scenario == "EXERCISE":
            self._current_activity = "Exercise"
            self._current_hr = self._drift(self._current_hr, target=140.0, speed=0.25, noise=2.5)
            self._current_hr = max(120.0, min(160.0, self._current_hr))

            self._current_systolic = self._drift(self._current_systolic, target=142.0, speed=0.2, noise=2.0)
            self._current_systolic = max(130.0, min(155.0, self._current_systolic))

            self._current_diastolic = self._drift(self._current_diastolic, target=84.0, speed=0.15, noise=1.2)
            self._current_diastolic = max(78.0, min(90.0, self._current_diastolic))

            self._current_spo2 = self._drift(self._current_spo2, target=96.5, speed=0.1, noise=0.3)
            self._current_spo2 = max(95.0, min(98.5, self._current_spo2))

            self._current_temp = self._drift(self._current_temp, target=37.5, speed=0.1, noise=0.05)
            self._current_temp = max(37.1, min(37.8, self._current_temp))

        # -------------------------------------------------------------
        # Scenario 4A: Unusual Blood Pressure - Stage 1 Warning (136/88)
        # -------------------------------------------------------------
        elif active_scenario == "UNUSUAL_BP_STAGE1":
            self._current_activity = "Resting"
            self._current_systolic = self._drift(self._current_systolic, target=136.0, speed=0.4, noise=1.2)
            self._current_systolic = max(132.0, min(142.0, self._current_systolic))

            self._current_diastolic = self._drift(self._current_diastolic, target=88.0, speed=0.35, noise=1.0)
            self._current_diastolic = max(86.0, min(92.0, self._current_diastolic))

            # Other parameters normal resting
            self._current_hr = self._drift(self._current_hr, target=74.0, speed=0.2, noise=1.0)
            self._current_hr = max(65.0, min(82.0, self._current_hr))
            self._current_spo2 = self._drift(self._current_spo2, target=98.5, speed=0.1, noise=0.2)
            self._current_temp = self._drift(self._current_temp, target=36.8, speed=0.08, noise=0.05)

        # -------------------------------------------------------------
        # Scenario 4B: Unusual Blood Pressure - Stage 2 Hypertensive Crisis (168/104)
        # -------------------------------------------------------------
        elif active_scenario == "UNUSUAL_BP_STAGE2":
            self._current_activity = "Resting"
            self._current_systolic = self._drift(self._current_systolic, target=168.0, speed=0.45, noise=2.0)
            self._current_systolic = max(156.0, min(182.0, self._current_systolic))

            self._current_diastolic = self._drift(self._current_diastolic, target=104.0, speed=0.4, noise=1.5)
            self._current_diastolic = max(96.0, min(112.0, self._current_diastolic))

            # Other parameters normal resting
            self._current_hr = self._drift(self._current_hr, target=78.0, speed=0.2, noise=1.5)
            self._current_hr = max(68.0, min(86.0, self._current_hr))
            self._current_spo2 = self._drift(self._current_spo2, target=98.0, speed=0.1, noise=0.3)
            self._current_temp = self._drift(self._current_temp, target=36.8, speed=0.08, noise=0.05)

        # -------------------------------------------------------------
        # Scenario 5A: Low Heart Rate (Bradycardia Warning: 44 BPM)
        # -------------------------------------------------------------
        elif active_scenario == "HR_BRADYCARDIA":
            self._current_activity = "Resting"
            self._current_hr = self._drift(self._current_hr, target=44.0, speed=0.55, noise=1.0)
            self._current_hr = max(38.0, min(48.0, self._current_hr))
            self._current_systolic = 115.0
            self._current_diastolic = 75.0
            self._current_spo2 = 98.5
            self._current_temp = 36.7

        # -------------------------------------------------------------
        # Scenario 5B: Elevated Heart Rate (Tachycardia Warning: 108 BPM)
        # -------------------------------------------------------------
        elif active_scenario == "HR_ELEVATED":
            self._current_activity = "Resting"
            self._current_hr = self._drift(self._current_hr, target=108.0, speed=0.55, noise=1.5)
            self._current_hr = max(102.0, min(116.0, self._current_hr))
            self._current_systolic = 124.0
            self._current_diastolic = 82.0
            self._current_spo2 = 98.0
            self._current_temp = 36.8

        # -------------------------------------------------------------
        # Scenario 5C: Extreme Heart Rate (Severe Tachycardia Critical: 168 BPM)
        # -------------------------------------------------------------
        elif active_scenario in ("HR_CRITICAL", "UNUSUAL_HEART_RATE"):
            self._current_activity = "Resting"  # Resting with dangerous tachycardia
            self._current_hr = self._drift(self._current_hr, target=168.0, speed=0.55, noise=2.0)
            self._current_hr = max(152.0, min(185.0, self._current_hr))

            # Blood pressure slightly elevated due to strain
            self._current_systolic = self._drift(self._current_systolic, target=138.0, speed=0.2, noise=1.5)
            self._current_diastolic = self._drift(self._current_diastolic, target=88.0, speed=0.2, noise=1.2)
            self._current_spo2 = self._drift(self._current_spo2, target=97.0, speed=0.1, noise=0.4)
            self._current_temp = self._drift(self._current_temp, target=37.1, speed=0.08, noise=0.05)

        # -------------------------------------------------------------
        # Scenario 5: Unusual Oxygen Saturation (Hypoxia Event)
        # -------------------------------------------------------------
        elif active_scenario == "UNUSUAL_SPO2":
            self._current_activity = "Resting"
            self._current_spo2 = self._drift(self._current_spo2, target=87.5, speed=0.3, noise=0.4)
            self._current_spo2 = max(84.0, min(91.0, self._current_spo2))

            # Heart compensates for low oxygen by beating faster
            self._current_hr = self._drift(self._current_hr, target=112.0, speed=0.2, noise=2.0)
            self._current_systolic = self._drift(self._current_systolic, target=128.0, speed=0.15, noise=1.5)
            self._current_diastolic = self._drift(self._current_diastolic, target=82.0, speed=0.15, noise=1.0)
            self._current_temp = self._drift(self._current_temp, target=36.9, speed=0.08, noise=0.05)

        # -------------------------------------------------------------
        # Scenario 6: Multiple Unusual Readings (Critical Distress)
        # -------------------------------------------------------------
        elif active_scenario == "MULTIPLE_ANOMALIES":
            self._current_activity = "Resting"
            # Crisis scenario: High HR + Severe Hypertension + Hypoxia + High Fever
            self._current_hr = self._drift(self._current_hr, target=172.0, speed=0.4, noise=3.0)
            self._current_hr = max(160.0, min(190.0, self._current_hr))

            self._current_systolic = self._drift(self._current_systolic, target=175.0, speed=0.3, noise=3.0)
            self._current_systolic = max(160.0, min(190.0, self._current_systolic))

            self._current_diastolic = self._drift(self._current_diastolic, target=108.0, speed=0.3, noise=2.0)
            self._current_diastolic = max(100.0, min(118.0, self._current_diastolic))

            self._current_spo2 = self._drift(self._current_spo2, target=86.0, speed=0.3, noise=0.5)
            self._current_spo2 = max(82.0, min(89.0, self._current_spo2))

            self._current_temp = self._drift(self._current_temp, target=39.1, speed=0.2, noise=0.1)
            self._current_temp = max(38.6, min(39.8, self._current_temp))

        # -------------------------------------------------------------
        # Scenario 7: Sudden Spike (Instant physiological spike)
        # -------------------------------------------------------------
        elif active_scenario == "SUDDEN_SPIKE":
            self._current_activity = "Resting"
            # Instantaneous jump of 40 BPM from normal
            self._current_hr = 135.0 + random.uniform(5.0, 15.0)
            self._current_systolic = 145.0 + random.uniform(2.0, 8.0)
            self._current_diastolic = 92.0 + random.uniform(1.0, 5.0)
            self._current_spo2 = 93.0 - random.uniform(1.0, 3.0)
            self._current_temp = 37.0

        # -------------------------------------------------------------
        # Scenario 8: Sensor Glitch / Missing / Invalid Data
        # -------------------------------------------------------------
        elif active_scenario == "INVALID_DATA":
            self._current_activity = "Resting"
            # Produces an out-of-range impossible reading (e.g., HR = -1 or 290)
            glitch_choice = random.choice(["negative_hr", "extreme_bp", "impossible_spo2", "missing_value"])
            if glitch_choice == "negative_hr":
                hr_val = -5.0
            elif glitch_choice == "extreme_bp":
                hr_val = 75.0
                return {
                    "device_id": self.device_id,
                    "sequence_number": self.sequence_number,
                    "timestamp": timestamp,
                    "heart_rate": hr_val,
                    "systolic_bp": 320.0,  # Physically absurd
                    "diastolic_bp": 40.0,
                    "spo2": 98.0,
                    "temperature": 36.8,
                    "activity": self._current_activity,
                    "scenario": self.SCENARIOS[active_scenario],
                    "is_simulated": True,
                }
            elif glitch_choice == "impossible_spo2":
                hr_val = 75.0
                return {
                    "device_id": self.device_id,
                    "sequence_number": self.sequence_number,
                    "timestamp": timestamp,
                    "heart_rate": hr_val,
                    "systolic_bp": 120.0,
                    "diastolic_bp": 80.0,
                    "spo2": 115.0,  # Impossible percentage
                    "temperature": 36.8,
                    "activity": self._current_activity,
                    "scenario": self.SCENARIOS[active_scenario],
                    "is_simulated": True,
                }
            else:  # missing_value
                return {
                    "device_id": self.device_id,
                    "sequence_number": self.sequence_number,
                    "timestamp": timestamp,
                    "heart_rate": None,  # Missing sensor read
                    "systolic_bp": 120.0,
                    "diastolic_bp": 80.0,
                    "spo2": 98.0,
                    "temperature": 36.8,
                    "activity": self._current_activity,
                    "scenario": self.SCENARIOS[active_scenario],
                    "is_simulated": True,
                }
            self._current_hr = hr_val

        # Assemble standard structured reading
        reading = {
            "device_id": self.device_id,
            "sequence_number": self.sequence_number,
            "timestamp": timestamp,
            "heart_rate": round(float(self._current_hr), 1),
            "systolic_bp": round(float(self._current_systolic), 1),
            "diastolic_bp": round(float(self._current_diastolic), 1),
            "spo2": round(float(self._current_spo2), 1),
            "temperature": round(float(self._current_temp), 1),
            "activity": self._current_activity,
            "scenario": self.SCENARIOS.get(active_scenario, "Normal"),
            "is_simulated": True,
        }

        return reading
