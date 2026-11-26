"""VitalSync - Dashboard UI Components
Module: components.dashboard_components

Renders modern HealthTech styled metric cards, Plotly real-time vital graphs,
alert badges, and educational cloud-streaming panels.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# Color Palette for HealthTech Dashboard
THEME_BG = "#0A1128"
THEME_CARD = "#101D42"
THEME_BORDER = "#1E2D5A"
THEME_TEAL = "#00D2BE"
THEME_CYAN = "#00B4D8"
THEME_GREEN = "#10B981"
THEME_AMBER = "#F59E0B"
THEME_RED = "#EF4444"
THEME_TEXT_MUTED = "#94A3B8"
THEME_TEXT = "#F1F5F9"


def get_custom_css() -> str:
    """Returns custom CSS for a modern, rounded, dark navy health dashboard."""
    return f"""
    <style>
        /* Main container styling */
        .stApp {{
            background-color: {THEME_BG};
            color: {THEME_TEXT};
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        
        /* Metric card container */
        .vital-card {{
            background: linear-gradient(135deg, {THEME_CARD} 0%, #152554 100%);
            border: 1px solid {THEME_BORDER};
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}
        .vital-card:hover {{
            border-color: {THEME_TEAL};
        }}
        
        .vital-label {{
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: {THEME_TEXT_MUTED};
            margin-bottom: 6px;
            font-weight: 600;
        }}
        
        .vital-value {{
            font-size: 1.85rem;
            font-weight: 700;
            color: {THEME_TEXT};
            line-height: 1.1;
        }}
        
        .vital-unit {{
            font-size: 0.85rem;
            color: {THEME_TEXT_MUTED};
            font-weight: 500;
            margin-left: 4px;
        }}
        
        .vital-subtitle {{
            font-size: 0.75rem;
            margin-top: 6px;
            color: {THEME_TEAL};
            font-weight: 500;
        }}
        
        /* Status badge */
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
        .status-normal {{
            background-color: rgba(16, 185, 129, 0.15);
            color: {THEME_GREEN};
            border: 1px solid {THEME_GREEN};
        }}
        .status-warning {{
            background-color: rgba(245, 158, 11, 0.15);
            color: {THEME_AMBER};
            border: 1px solid {THEME_AMBER};
        }}
        .status-high {{
            background-color: rgba(239, 68, 68, 0.15);
            color: {THEME_RED};
            border: 1px solid {THEME_RED};
        }}
        
        /* Header Banner */
        .header-bar {{
            background: linear-gradient(90deg, #0d1b3e 0%, #0a1128 100%);
            border-bottom: 2px solid {THEME_TEAL};
            padding: 14px 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        /* Alert Box */
        .alert-banner {{
            padding: 14px 18px;
            border-radius: 10px;
            margin-bottom: 18px;
            border-left: 5px solid;
            font-size: 0.9rem;
            line-height: 1.4;
        }}
        .alert-banner-normal {{
            background-color: rgba(16, 185, 129, 0.1);
            border-color: {THEME_GREEN};
            color: #d1fae5;
        }}
        .alert-banner-warning {{
            background-color: rgba(245, 158, 11, 0.12);
            border-color: {THEME_AMBER};
            color: #fef3c7;
        }}
        .alert-banner-high {{
            background-color: rgba(239, 68, 68, 0.15);
            border-color: {THEME_RED};
            color: #fee2e2;
        }}
    </style>
    """


def render_header(reading: Dict[str, Any], evaluation: Dict[str, Any]) -> None:
    """Render top brand and live device status banner."""
    device_id = reading.get("device_id", "FIT-101")
    timestamp = reading.get("timestamp", "N/A")
    severity = evaluation.get("severity", "NORMAL")
    scenario = reading.get("scenario", "Normal")

    status_class = "status-normal"
    status_label = "NORMAL"
    if severity == "HIGH":
        status_class = "status-high"
        status_label = "CRITICAL ALERT"
    elif severity == "WARNING":
        status_class = "status-warning"
        status_label = "WARNING"

    header_html = f"""
    <div class="header-bar">
        <div>
            <span style="font-size: 1.6rem; font-weight: 800; color: {THEME_TEAL}; letter-spacing: -0.02em;">
                VitalSync
            </span>
            <span style="font-size: 0.85rem; color: {THEME_TEXT_MUTED}; margin-left: 12px; font-weight: 500;">
                Real-Time Health Monitoring & Anomaly Detection
            </span>
        </div>
        <div style="text-align: right;">
            <span style="font-size: 0.75rem; color: {THEME_TEXT_MUTED}; margin-right: 12px;">
                DEVICE: <b style="color: {THEME_TEXT};">{device_id}</b> | SCENARIO: <b style="color: {THEME_CYAN};">{scenario}</b>
            </span>
            <span class="status-badge {status_class}">● {status_label}</span>
            <div style="font-size: 0.72rem; color: {THEME_TEXT_MUTED}; margin-top: 4px;">
                TIMESTAMP: {timestamp}
            </div>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)


def render_vital_cards(reading: Dict[str, Any], evaluation: Dict[str, Any]) -> None:
    """Render 6 vital sign metric cards in columns."""
    hr = reading.get("heart_rate", "--")
    sys_bp = reading.get("systolic_bp", "--")
    dia_bp = reading.get("diastolic_bp", "--")
    spo2 = reading.get("spo2", "--")
    temp = reading.get("temperature", "--")
    activity = reading.get("activity", "Resting")
    status = evaluation.get("status", "Normal")
    severity = evaluation.get("severity", "NORMAL")

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    # Helper to pick accent color based on flagged parameters
    def get_color_for_metric(metric_names: List[str]) -> str:
        param_flagged = evaluation.get("parameter", "")
        if any(name.lower() in param_flagged.lower() for name in metric_names):
            return THEME_RED if severity == "HIGH" else THEME_AMBER
        return THEME_TEAL

    hr_color = get_color_for_metric(["Heart Rate", "HR", "Tachycardia", "Bradycardia"])
    bp_color = get_color_for_metric(["Blood Pressure", "BP", "Systolic", "Diastolic", "Hypertension"])
    spo2_color = get_color_for_metric(["Oxygen", "SpO2", "Hypoxia", "Desaturation"])
    temp_color = get_color_for_metric(["Temperature", "Temp", "Fever", "Hypothermia"])

    with col1:
        st.markdown(f"""
        <div class="vital-card">
            <div class="vital-label">Heart Rate</div>
            <div class="vital-value" style="color: {hr_color};">{hr}<span class="vital-unit">BPM</span></div>
            <div class="vital-subtitle">Normal: 60-100</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="vital-card">
            <div class="vital-label">Blood Pressure</div>
            <div class="vital-value" style="color: {bp_color}; font-size: 1.55rem;">{sys_bp}/{dia_bp}<span class="vital-unit">mmHg</span></div>
            <div class="vital-subtitle">Normal: &lt;125/85</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="vital-card">
            <div class="vital-label">Oxygen Saturation</div>
            <div class="vital-value" style="color: {spo2_color};">{spo2}<span class="vital-unit">%</span></div>
            <div class="vital-subtitle">Normal: &ge;95%</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="vital-card">
            <div class="vital-label">Temperature</div>
            <div class="vital-value" style="color: {temp_color};">{temp}<span class="vital-unit">&deg;C</span></div>
            <div class="vital-subtitle">Normal: 36.1-37.2</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="vital-card">
            <div class="vital-label">Current Activity</div>
            <div class="vital-value" style="font-size: 1.55rem; color: {THEME_CYAN};">{activity}</div>
            <div class="vital-subtitle">Context Filter</div>
        </div>
        """, unsafe_allow_html=True)

    with col6:
        status_color = THEME_GREEN if severity == "NORMAL" else (THEME_AMBER if severity == "WARNING" else THEME_RED)
        st.markdown(f"""
        <div class="vital-card">
            <div class="vital-label">Detection Status</div>
            <div class="vital-value" style="font-size: 1.25rem; color: {status_color};">{status}</div>
            <div class="vital-subtitle">Rule Engine Active</div>
        </div>
        """, unsafe_allow_html=True)


def render_alert_banner(evaluation: Dict[str, Any]) -> None:
    """Render an active notification explaining triggered rules or showing normal health state."""
    severity = evaluation.get("severity", "NORMAL")
    reason = evaluation.get("reason", "Vitals operating within expected physiological parameters.")
    rule = evaluation.get("rule_triggered", "RULE_NORMAL_OPERATION")
    details = evaluation.get("details", [])

    if severity == "HIGH":
        banner_class = "alert-banner-high"
        icon = "🚨 <b>CRITICAL HEALTH ALERT:</b>"
    elif severity == "WARNING":
        banner_class = "alert-banner-warning"
        icon = "⚠️ <b>WARNING ANOMALY DETECTED:</b>"
    else:
        banner_class = "alert-banner-normal"
        icon = "✅ <b>NORMAL SYSTEM STATUS:</b>"

    details_html = ""
    if len(details) > 1:
        details_html = "<ul style='margin: 6px 0 0 18px; padding: 0;'>" + "".join(f"<li>{d}</li>" for d in details) + "</ul>"

    st.markdown(f"""
    <div class="alert-banner {banner_class}">
        <div>{icon} {reason}</div>
        <div style="font-size: 0.76rem; opacity: 0.85; margin-top: 4px;">
            Triggered Rule ID: <code>{rule}</code>
        </div>
        {details_html}
    </div>
    """, unsafe_allow_html=True)


def create_plotly_chart(
    df: pd.DataFrame,
    y_col: str,
    title: str,
    y_label: str,
    line_color: str,
    threshold_warn: Optional[float] = None,
    threshold_crit: Optional[float] = None,
    threshold_label_warn: str = "Warning",
    threshold_label_crit: str = "Critical",
    secondary_col: Optional[str] = None,
    secondary_color: Optional[str] = None,
    secondary_label: Optional[str] = None,
) -> go.Figure:
    """Generates a styled, dark-mode Plotly time-series chart with reference threshold zones."""
    fig = go.Figure()

    if df.empty or y_col not in df.columns:
        fig.add_annotation(
            text="Waiting for streaming data...",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(color=THEME_TEXT_MUTED, size=13)
        )
        fig.update_layout(
            paper_bgcolor=THEME_CARD,
            plot_bgcolor=THEME_CARD,
            height=250,
            margin=dict(l=40, r=20, t=40, b=30),
        )
        return fig

    x_vals = df["timestamp"].apply(lambda t: str(t).split()[-1] if " " in str(t) else str(t))

    # Main primary line
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=df[y_col],
        mode="lines+markers",
        name=title,
        line=dict(color=line_color, width=2.5),
        marker=dict(size=5, color=line_color),
        hovertemplate="Time: %{x}<br>" + title + ": %{y} " + y_label + "<extra></extra>"
    ))

    # Optional secondary line (e.g. Diastolic BP)
    if secondary_col and secondary_col in df.columns:
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=df[secondary_col],
            mode="lines+markers",
            name=secondary_label or secondary_col,
            line=dict(color=secondary_color or THEME_CYAN, width=2.0, dash="dot"),
            marker=dict(size=4),
            hovertemplate="Time: %{x}<br>" + (secondary_label or secondary_col) + ": %{y}<extra></extra>"
        ))

    # Warning Threshold Line
    if threshold_warn is not None:
        fig.add_hline(
            y=threshold_warn,
            line_dash="dash",
            line_color=THEME_AMBER,
            annotation_text=f"{threshold_label_warn} ({threshold_warn})",
            annotation_position="top right",
            annotation_font=dict(size=10, color=THEME_AMBER)
        )

    # Critical Threshold Line
    if threshold_crit is not None:
        fig.add_hline(
            y=threshold_crit,
            line_dash="dot",
            line_color=THEME_RED,
            annotation_text=f"{threshold_label_crit} ({threshold_crit})",
            annotation_position="bottom right",
            annotation_font=dict(size=10, color=THEME_RED)
        )

    # Layout styling for modern dark UI
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(color=THEME_TEXT, size=13),
            x=0.03, y=0.92
        ),
        paper_bgcolor=THEME_CARD,
        plot_bgcolor="#0c1635",
        height=260,
        margin=dict(l=45, r=25, t=35, b=30),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10, color=THEME_TEXT_MUTED)
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="#1b2a52",
            tickfont=dict(color=THEME_TEXT_MUTED, size=9),
            showticklabels=True,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#1b2a52",
            tickfont=dict(color=THEME_TEXT_MUTED, size=9),
            title=dict(text=y_label, font=dict(color=THEME_TEXT_MUTED, size=10)),
        ),
    )

    return fig
