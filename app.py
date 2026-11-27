"""VitalSync - Real-Time Vital Sign Monitoring & Anomaly Detection System
Prototype v1 - Interactive Streamlit Dashboard

Author: 3rd-Year B.Tech Computer Science Student
Project: VitalSync (HealthTech / IoT Stream Processing)
"""

import sys
import os
import time
import json
import base64
import streamlit as st
import pandas as pd

# Add project root directory to path for clean modular imports
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from simulator.health_generator import HealthDataSimulator
from detection.detection_rules import AnomalyDetector
from services.data_service import MonitoringState
from cloud.lambda_function import lambda_handler
from components.dashboard_components import (
    get_custom_css,
    render_header,
    render_vital_cards,
    render_alert_banner,
    create_plotly_chart,
    THEME_TEAL,
    THEME_RED,
    THEME_AMBER,
    THEME_CYAN,
    THEME_GREEN,
)

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="VitalSync - Health Anomaly Monitor",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom CSS
st.markdown(get_custom_css(), unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
if "simulator" not in st.session_state:
    st.session_state.simulator = HealthDataSimulator(device_id="FIT-101")

if "detector" not in st.session_state:
    st.session_state.detector = AnomalyDetector()

if "monitoring_state" not in st.session_state:
    st.session_state.monitoring_state = MonitoringState(max_history=50)

if "is_simulating" not in st.session_state:
    st.session_state.is_simulating = False

if "simulation_speed" not in st.session_state:
    st.session_state.simulation_speed = 1.0

# Generate first initial reading if buffer is completely empty
if st.session_state.monitoring_state.total_readings_generated == 0:
    first_reading = st.session_state.simulator.generate_reading()
    first_eval = st.session_state.detector.evaluate_reading(first_reading, recent_history=[])
    st.session_state.monitoring_state.record_reading(first_reading, first_eval.to_dict())


# -----------------------------------------------------------------------------
# HELPER ACTIONS
# -----------------------------------------------------------------------------
def step_simulation() -> None:
    """Generate one discrete reading and evaluate it."""
    simulator: HealthDataSimulator = st.session_state.simulator
    detector: AnomalyDetector = st.session_state.detector
    state: MonitoringState = st.session_state.monitoring_state

    reading = simulator.generate_reading()
    history = state.get_recent_history()
    eval_res = detector.evaluate_reading(reading, recent_history=history)
    state.record_reading(reading, eval_res.to_dict())


def reset_simulation() -> None:
    """Reset the simulator, state buffers, and counters."""
    st.session_state.simulator.reset_state()
    st.session_state.monitoring_state.reset_all()
    # Generate fresh baseline reading
    first_reading = st.session_state.simulator.generate_reading()
    first_eval = st.session_state.detector.evaluate_reading(first_reading, recent_history=[])
    st.session_state.monitoring_state.record_reading(first_reading, first_eval.to_dict())
    st.session_state.is_simulating = False


# -----------------------------------------------------------------------------
# SIDEBAR CONTROLS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="padding: 10px 0 16px 0;">
        <h2 style="color: #00D2BE; margin: 0; font-size: 1.6rem; letter-spacing: -0.02em;">🫀 VitalSync</h2>
        <span style="font-size: 0.8rem; color: #94A3B8;">Real-Time Health Stream Processing</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🎮 Simulation Controls")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.session_state.is_simulating:
            if st.button("⏸ Pause", use_container_width=True, type="secondary"):
                st.session_state.is_simulating = False
                st.rerun()
        else:
            if st.button("▶ Start Live", use_container_width=True, type="primary"):
                st.session_state.is_simulating = True
                st.rerun()

    with col_btn2:
        if st.button("⏩ Step (+1)", use_container_width=True, help="Generate a single simulated reading"):
            step_simulation()
            st.rerun()

    if st.button("🔄 Reset All Data", use_container_width=True, help="Clear history and reset baseline"):
        reset_simulation()
        st.rerun()

    st.session_state.simulation_speed = st.slider(
        "Simulation Interval (Seconds)",
        min_value=0.5,
        max_value=3.0,
        value=float(st.session_state.simulation_speed),
        step=0.5,
        help="Controls how fast simulated readings stream in"
    )

    st.markdown("---")
    st.markdown("### 🧪 Simulation Scenarios")
    scenario_options = {
        "NORMAL_RESTING": "🟢 Normal Resting (HR ~72 BPM, BP ~118/78)",
        "WALKING": "🚶 Walking Activity (HR ~95 BPM, BP ~125/81)",
        "EXERCISE": "🏃 Exercise Cardio (HR ~140 BPM, BP ~142/84)",
        "HR_BRADYCARDIA": "⚠️ Low Heart Rate (Bradycardia: 44 BPM Warning)",
        "HR_ELEVATED": "⚠️ Elevated Heart Rate (Tachycardia: 108 BPM Warning)",
        "HR_CRITICAL": "🚨 Extreme Heart Rate (Severe Tachycardia: 168 BPM Critical)",
        "UNUSUAL_BP_STAGE1": "⚠️ High Blood Pressure (Stage 1 Warning: 136/88)",
        "UNUSUAL_BP_STAGE2": "🚨 Severe Blood Pressure (Stage 2 Crisis: 168/104)",
        "UNUSUAL_SPO2": "🚨 Unusual Oxygen SpO2 (Hypoxia: 87.5% Critical)",
        "MULTIPLE_ANOMALIES": "🚨 Multiple Crisis (High HR + High BP + Hypoxia + Fever)",
        "SUDDEN_SPIKE": "⚡ Sudden Vital Spike (+40 BPM Delta)",
        "INVALID_DATA": "❌ Sensor Glitch / Out-of-Bounds Data",
    }

    if "current_scenario_key" not in st.session_state:
        st.session_state.current_scenario_key = "NORMAL_RESTING"

    current_idx = list(scenario_options.keys()).index(st.session_state.current_scenario_key) if st.session_state.current_scenario_key in scenario_options else 0

    selected_scenario = st.selectbox(
        "Inject Scenario",
        options=list(scenario_options.keys()),
        format_func=lambda k: scenario_options[k],
        index=current_idx,
        help="Switch scenarios to demonstrate anomaly detection rules live"
    )

    # Immediately step simulation upon switching scenarios so the user sees the alert instantly
    if selected_scenario != st.session_state.current_scenario_key:
        st.session_state.current_scenario_key = selected_scenario
        st.session_state.simulator.set_scenario(selected_scenario)
        step_simulation()
        st.rerun()

    st.markdown("---")
    st.markdown("### 🎛️ Manual Vital Override (Drag & Test Any Value)")
    use_manual_vitals = st.checkbox(
        "Enable Manual Sliders",
        value=False,
        help="Directly drag Heart Rate, Blood Pressure, or SpO2 to see live alert changes instantly"
    )

    state_obj = st.session_state.monitoring_state
    latest_r = state_obj.latest_reading or {}

    if use_manual_vitals:
        manual_hr = st.slider("Heart Rate (BPM)", min_value=35, max_value=200, value=int(latest_r.get("heart_rate", 75)), step=1)
        col_m_bp1, col_m_bp2 = st.columns(2)
        with col_m_bp1:
            manual_sys = st.slider("Systolic BP", min_value=90, max_value=210, value=int(latest_r.get("systolic_bp", 120)), step=1)
        with col_m_bp2:
            manual_dia = st.slider("Diastolic BP", min_value=50, max_value=125, value=int(latest_r.get("diastolic_bp", 80)), step=1)
        manual_spo2 = st.slider("Oxygen SpO2 (%)", min_value=70, max_value=100, value=int(latest_r.get("spo2", 98)), step=1)
        manual_temp = st.slider("Body Temp (°C)", min_value=34.0, max_value=41.5, value=float(latest_r.get("temperature", 36.8)), step=0.1)
        manual_activity = st.radio("Activity Context", ["Resting", "Walking", "Exercise"], horizontal=True)

        if st.button("⚡ Apply Manual Values", type="primary", use_container_width=True):
            custom_reading = {
                "device_id": "FIT-101",
                "sequence_number": state_obj.total_readings_generated + 1,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "heart_rate": float(manual_hr),
                "systolic_bp": float(manual_sys),
                "diastolic_bp": float(manual_dia),
                "spo2": float(manual_spo2),
                "temperature": float(manual_temp),
                "activity": manual_activity,
                "scenario": f"Manual Override ({manual_hr} BPM)",
                "is_simulated": True,
            }
            eval_res = st.session_state.detector.evaluate_reading(
                custom_reading,
                recent_history=state_obj.get_recent_history()
            )
            state_obj.record_reading(custom_reading, eval_res.to_dict())
            st.rerun()

    st.markdown("---")
    with st.expander("⚙️ Configurable Detection Thresholds"):
        st.caption("Demonstration rules (not medical diagnostic criteria)")
        curr_thresh = st.session_state.detector.thresholds

        new_hr_rest_min = st.slider("Resting HR Minimum / Bradycardia (BPM)", 40, 65, int(curr_thresh.get("hr_resting_min_warn", 50)))
        new_hr_rest_warn = st.slider("Resting HR Warning (BPM)", 50, 120, int(curr_thresh["hr_resting_max_warn"]))
        new_hr_rest_crit = st.slider("Resting HR Critical (BPM)", 110, 170, int(curr_thresh["hr_resting_max_crit"]))
        new_sys_warn = st.slider("Systolic BP Warning (mmHg)", 115, 145, int(curr_thresh["bp_systolic_warn"]))
        new_sys_crit = st.slider("Systolic BP Critical (mmHg)", 135, 185, int(curr_thresh["bp_systolic_crit"]))
        new_spo2_warn = st.slider("SpO2 Warning Threshold (%)", 85, 96, int(curr_thresh["spo2_warn"]))
        new_spo2_crit = st.slider("SpO2 Critical Threshold (%)", 80, 92, int(curr_thresh["spo2_crit"]))

        # Apply threshold updates live and re-evaluate immediately
        new_thresh_dict = {
            "hr_resting_min_warn": new_hr_rest_min,
            "hr_resting_max_warn": new_hr_rest_warn,
            "hr_resting_max_crit": new_hr_rest_crit,
            "spo2_warn": float(new_spo2_warn),
            "spo2_crit": float(new_spo2_crit),
            "bp_systolic_warn": new_sys_warn,
            "bp_systolic_crit": new_sys_crit,
        }
        st.session_state.detector.update_thresholds(new_thresh_dict)
        if st.session_state.monitoring_state.latest_reading:
            re_eval = st.session_state.detector.evaluate_reading(
                st.session_state.monitoring_state.latest_reading,
                recent_history=st.session_state.monitoring_state.get_recent_history()[:-1]
            )
            st.session_state.monitoring_state.latest_evaluation = re_eval.to_dict()

    st.markdown("---")
    st.markdown("### ☁️ Streaming Status")
    st.markdown(
        """
        <div style="background: rgba(0, 210, 190, 0.08); border-left: 3px solid #00D2BE; padding: 10px; border-radius: 6px; font-size: 0.78rem;">
            <b>Local Stream Abstraction:</b> Active<br>
            <b>Target Topic:</b> <code>health-events</code><br>
            <b>Cloud Backend (Kafka & Lambda):</b> Phase 2 Roadmap
        </div>
        """,
        unsafe_allow_html=True
    )


# -----------------------------------------------------------------------------
# MAIN CONTENT AREA
# -----------------------------------------------------------------------------
state: MonitoringState = st.session_state.monitoring_state
latest_reading = state.latest_reading or {}
latest_eval = state.latest_evaluation or {}

# Top Brand & Status Banner
render_header(latest_reading, latest_eval)

# Main Navigation Tabs
tab_live, tab_alerts, tab_history, tab_architecture = st.tabs([
    "📊 Live Monitoring",
    "🚨 Anomaly & Alert Center",
    "📈 History & Analytics",
    "☁️ Kafka & Cloud Architecture"
])

# =============================================================================
# TAB 1: LIVE MONITORING
# =============================================================================
with tab_live:
    # Vital KPI Cards
    render_vital_cards(latest_reading, latest_eval)

    # Active Alert / Status Explanation Banner
    render_alert_banner(latest_eval)

    # Historical DataFrame for Charts
    df_readings = state.get_readings_dataframe()
    curr_thresh = st.session_state.detector.thresholds

    # Real-Time Charts 2x2 Grid
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        fig_hr = create_plotly_chart(
            df=df_readings,
            y_col="heart_rate",
            title="Heart Rate (BPM)",
            y_label="BPM",
            line_color=THEME_TEAL,
            threshold_warn=float(curr_thresh["hr_resting_max_warn"]),
            threshold_crit=float(curr_thresh["hr_resting_max_crit"]),
            threshold_label_warn="Resting Max",
            threshold_label_crit="Critical Max"
        )
        st.plotly_chart(fig_hr, use_container_width=True)

    with col_chart2:
        fig_bp = create_plotly_chart(
            df=df_readings,
            y_col="systolic_bp",
            title="Blood Pressure (Systolic & Diastolic)",
            y_label="mmHg",
            line_color="#E879F9",
            secondary_col="diastolic_bp",
            secondary_color=THEME_CYAN,
            secondary_label="Diastolic",
            threshold_warn=float(curr_thresh["bp_systolic_warn"]),
            threshold_crit=float(curr_thresh["bp_systolic_crit"]),
            threshold_label_warn="Systolic Warn",
            threshold_label_crit="Stage 2 Crisis"
        )
        st.plotly_chart(fig_bp, use_container_width=True)

    col_chart3, col_chart4 = st.columns(2)

    with col_chart3:
        fig_spo2 = create_plotly_chart(
            df=df_readings,
            y_col="spo2",
            title="Oxygen Saturation (SpO2)",
            y_label="%",
            line_color=THEME_GREEN,
            threshold_warn=float(curr_thresh["spo2_warn"]),
            threshold_crit=float(curr_thresh["spo2_crit"]),
            threshold_label_warn="Mild Hypoxia",
            threshold_label_crit="Critical Hypoxia"
        )
        st.plotly_chart(fig_spo2, use_container_width=True)

    with col_chart4:
        fig_temp = create_plotly_chart(
            df=df_readings,
            y_col="temperature",
            title="Body Temperature (°C)",
            y_label="°C",
            line_color="#F97316",
            threshold_warn=float(curr_thresh["temp_fever_warn"]),
            threshold_crit=float(curr_thresh["temp_fever_crit"]),
            threshold_label_warn="Fever",
            threshold_label_crit="High Fever"
        )
        st.plotly_chart(fig_temp, use_container_width=True)


# =============================================================================
# TAB 2: ANOMALY & ALERT CENTER
# =============================================================================
with tab_alerts:
    stats = state.get_summary_statistics()

    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        st.metric("Total Readings Evaluated", stats["total_generated"])
    with col_s2:
        st.metric("Total Flagged Events", stats["total_flagged"], delta=f"{stats['anomaly_rate']}% rate", delta_color="inverse")
    with col_s3:
        st.metric("Warning Alerts", stats["warning_count"])
    with col_s4:
        st.metric("Critical Alerts (High)", stats["high_count"])

    st.markdown("### 📋 Anomaly Log & Rule Decisions")
    df_alerts = state.get_alerts_dataframe()

    if df_alerts.empty:
        st.info("No anomalies flagged yet. System operating normally, or trigger a scenario from the sidebar to demonstrate detection rules.")
    else:
        # Style and render alert table
        st.dataframe(
            df_alerts[[
                "sequence", "timestamp", "severity", "parameter",
                "value", "reason", "status", "activity"
            ]],
            column_config={
                "sequence": st.column_config.NumberColumn("#", width="small"),
                "timestamp": st.column_config.TextColumn("Timestamp", width="medium"),
                "severity": st.column_config.TextColumn("Severity", width="small"),
                "parameter": st.column_config.TextColumn("Parameter Involved", width="medium"),
                "value": st.column_config.TextColumn("Trigger Value", width="small"),
                "reason": st.column_config.TextColumn("Detection Reason & Clinical Context", width="large"),
                "status": st.column_config.TextColumn("Status", width="medium"),
                "activity": st.column_config.TextColumn("Activity", width="small"),
            },
            use_container_width=True,
            hide_index=True
        )


# =============================================================================
# TAB 3: MONITORING HISTORY & ANALYTICS
# =============================================================================
with tab_history:
    st.markdown("### 📊 Time-Series Readings History")
    df_history = state.get_readings_dataframe()

    if df_history.empty:
        st.info("No readings recorded yet.")
    else:
        st.dataframe(
            df_history[[
                "sequence_number", "timestamp", "heart_rate", "systolic_bp",
                "diastolic_bp", "spo2", "temperature", "activity", "severity", "scenario"
            ]].iloc[::-1],
            use_container_width=True,
            hide_index=True
        )

        csv_data = df_history.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Readings History as CSV",
            data=csv_data,
            file_name=f"vitalsync_readings_{int(time.time())}.csv",
            mime="text/csv",
        )


# =============================================================================
# TAB 4: KAFKA & CLOUD ARCHITECTURE (PHASE 2)
# =============================================================================
with tab_architecture:
    st.markdown("### ☁️ Phase 2: Apache Kafka & AWS Serverless Architecture")
    st.markdown("""
    VitalSync includes complete **Phase 2 Cloud Scripts** inside `cloud/`:
    `docker-compose.yml` (Kafka + Kafka UI), `kafka_producer.py`, `kafka_consumer.py`, and `lambda_function.py` (AWS Lambda + SNS + DynamoDB).
    """)

    col_arch1, col_arch2 = st.columns([1, 1])

    with col_arch1:
        st.markdown("#### 📦 Active Kafka Topic Payload (`health-events`)")
        st.caption("Standardized JSON payload published by `kafka_producer.py`")
        kafka_sample = state.stream_publisher.get_kafka_sample_json()
        st.code(kafka_sample, language="json")

    with col_arch2:
        st.markdown("#### ⚡ Test AWS Lambda Handler Live (Mock ESM)")
        st.caption("Simulates AWS MSK triggering `cloud/lambda_function.py` with base64-encoded Kafka records.")
        if st.button("🚀 Invoke AWS Lambda Handler on Current Reading", type="primary", use_container_width=True):
            envelope = state.stream_publisher.last_published_payload or state.stream_publisher.publish_event(latest_reading)
            encoded_val = base64.b64encode(json.dumps(envelope).encode("utf-8")).decode("utf-8")
            mock_esm_event = {
                "eventSource": "aws:kafka",
                "records": {
                    "health-events-0": [
                        {
                            "topic": "health-events",
                            "partition": 0,
                            "offset": latest_reading.get("sequence_number", 1),
                            "value": encoded_val,
                        }
                    ]
                }
            }
            lambda_resp = lambda_handler(mock_esm_event)
            st.success("✅ AWS Lambda Execution Complete (HTTP 200)")
            st.json(lambda_resp)

    st.markdown("---")
    st.markdown("#### 🐳 Quick-Start Commands for Local Kafka (Docker)")
    st.code("""# 1. Start Apache Kafka & Kafka Web UI (http://localhost:8085)
docker-compose -f cloud/docker-compose.yml up -d

# 2. Stream live events from simulator to Kafka topic 'health-events'
python cloud/kafka_producer.py --interval 1.0

# 3. Consume & evaluate events in real time
python cloud/kafka_consumer.py""", language="bash")

    st.markdown("---")
    st.markdown("#### 🔄 Architecture Matrix: Prototype v1 vs. Phase 2 Cloud")
    st.markdown("""
    | Component | Prototype v1 (Local) | Phase 2 (Implemented Scripts in `cloud/`) |
    |---|---|---|
    | **Producer** | In-Memory `HealthDataSimulator` | `cloud/kafka_producer.py` (`KafkaProducer`) |
    | **Message Broker** | `StreamEventPublisher` abstraction | `cloud/docker-compose.yml` (**Apache Kafka** + **Kafka UI** on `:8085`) |
    | **Compute / Rules** | Local `AnomalyDetector` module | `cloud/lambda_function.py` (**AWS Lambda** ESM batch handler) |
    | **Alert Routing** | Local Streamlit UI banner | **Amazon SNS** (`sns.publish` for HIGH severity alerts) |
    | **Persistence** | In-memory circular buffer | **Amazon DynamoDB** (`VitalSyncReadings` & `VitalSyncAlerts`) |
    """)


# -----------------------------------------------------------------------------
# AUTO-SIMULATION RUNNER
# -----------------------------------------------------------------------------
if st.session_state.is_simulating:
    time.sleep(float(st.session_state.simulation_speed))
    step_simulation()
    st.rerun()
