import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_manager import load_exams, status_color, status_emoji

st.set_page_config(page_title="Exames Laboratoriais", page_icon="🧪", layout="wide")

st.markdown("""
<style>
.section-header{font-size:22px;font-weight:700;color:#1E8449;border-bottom:3px solid #1E8449;padding-bottom:8px;margin:20px 0 16px}
.exam-row-alta{background:#fff0f0;border-left:3px solid #E74C3C;padding:8px 12px;border-radius:6px;margin:4px 0}
.exam-row-baixa{background:#fff8e6;border-left:3px solid #F39C12;padding:8px 12px;border-radius:6px;margin:4px 0}
.exam-row-normal{background:#f0fff4;border-left:3px solid #27AE60;padding:8px 12px;border-radius:6px;margin:4px 0}
.exam-row-info{background:#f0f4ff;border-left:3px solid #3498DB;padding:8px 12px;border-radius:6px;margin:4px 0}
.cat-header{font-size:15px;font-weight:700;color:#1a3a1a;margin:14px 0 6px;background:#e8f5e9;padding:6px 12px;border-radius:6px}
</style>
""", unsafe_allow_html=True)

st.markdown("## 🧪 Exames Laboratoriais")

exams_data = load_exams()
sessions = {s["id"]: s for s in exams_data.get("sessions", [])}
results = exams_data.get("results", [])

if not results:
    st.warning("Nenhum exame registrado.")
    st.stop()

# ── Seleção de sessão ────────────────────────────────────────────────────────
sess_list = sorted(sessions.values(), key=lambda s: s["date"], reverse=True)
sess_options = {s["id"]: f"{datetime.strptime(s['date'],'%Y-%m-%d').strftime('%d/%m/%Y')} — {s['lab']}" for s in sess_list}
selected_id = st.selectbox("Selecionar data dos exames:", list(sess_options.keys()),
                            format_func=lambda x: sess_options[x])
sel_session = sessions[selected_id]

st.caption(f"📅 Data: **{datetime.strptime(sel_session['date'],'%Y-%m-%d').strftime('%d/%m/%Y')}** · "
           f"Laboratório: **{sel_session['lab']}** · Médica: {sel_session.get('doctor','—')}")
if sel_session.get("notes"):
    st.info(sel_session["notes"])

# ── Resumo alertas ────────────────────────────────────────────────────────────
sel_results = [r for r in results if r["session_id"] == selected_id]
n_alta  = sum(1 for r in sel_results if r["status"] == "alta")
n_baixa = sum(1 for r in sel_results if r["status"] == "baixa")
n_norm  = sum(1 for r in sel_results if r["status"] == "normal")
n_info  = sum(1 for r in sel_results if r["status"] == "info")

ca, cb, cc, cd = st.columns(4)
with ca:
    st.markdown(f"<div style='text-align:center;background:#fff0f0;border-radius:10px;padding:12px'>"
                f"<div style='font-size:28px;font-weight:700;color:#E74C3C'>{n_alta}</div>"
                f"<div style='color:#E74C3C;font-weight:600'>⬆️ Acima</div></div>", unsafe_allow_html=True)
with cb:
    st.markdown(f"<div style='text-align:center;background:#fff8e6;border-radius:10px;padding:12px'>"
                f"<div style='font-size:28px;font-weight:700;color:#F39C12'>{n_baixa}</div>"
                f"<div style='color:#F39C12;font-weight:600'>⬇️ Abaixo</div></div>", unsafe_allow_html=True)
with cc:
    st.markdown(f"<div style='text-align:center;background:#f0fff4;border-radius:10px;padding:12px'>"
                f"<div style='font-size:28px;font-weight:700;color:#27AE60'>{n_norm}</div>"
                f"<div style='color:#27AE60;font-weight:600'>✅ Normal</div></div>", unsafe_allow_html=True)
with cd:
    st.markdown(f"<div style='text-align:center;background:#f0f4ff;border-radius:10px;padding:12px'>"
                f"<div style='font-size:28px;font-weight:700;color:#3498DB'>{n_info}</div>"
                f"<div style='color:#3498DB;font-weight:600'>ℹ️ Info</div></div>", unsafe_allow_html=True)

# ── Resultados por categoria ──────────────────────────────────────────────────
st.markdown("<div class='section-header'>📋 Resultados por Categoria</div>", unsafe_allow_html=True)

# Filtro de categorias
categories = sorted(set(r["category"] for r in sel_results))
cat_filter = st.multiselect("Filtrar categorias:", categories, default=categories)

for cat in cat_filter:
    cat_results = [r for r in sel_results if r["category"] == cat]
    if not cat_results:
        continue

    n_issues = sum(1 for r in cat_results if r["status"] in ("alta","baixa"))
    icon = "⚠️" if n_issues > 0 else "✅"
    st.markdown(f"<div class='cat-header'>{icon} {cat}</div>", unsafe_allow_html=True)

    for r in cat_results:
        status = r["status"]
        css_class = f"exam-row-{status}"
        emoji = status_emoji(status)
        val_str = f"{r['value']} {r['unit']}" if r["value"] is not None else ""
        ref_str = r.get("ref_text","—")
        note = r.get("notes","")

        col1, col2, col3 = st.columns([3, 2, 5])
        with col1:
            st.markdown(f"<div class='{css_class}'>{emoji} <b>{r['exam']}</b></div>", unsafe_allow_html=True)
        with col2:
            color = status_color(status)
            st.markdown(f"<div class='{css_class}'><span style='color:{color};font-weight:700'>{val_str}</span><br>"
                        f"<span style='font-size:11px;color:#888'>Ref: {ref_str}</span></div>", unsafe_allow_html=True)
        with col3:
            if note:
                st.markdown(f"<div class='{css_class}'><span style='font-size:12px'>{note}</span></div>",
                            unsafe_allow_html=True)

# ── Gráficos de tendência ─────────────────────────────────────────────────────
st.markdown("<div class='section-header'>📈 Tendências nos Exames</div>", unsafe_allow_html=True)
st.caption("Evolução dos principais marcadores ao longo das três coletas")

# Marcadores de interesse para trending
TRENDING_EXAMS = [
    ("TSH", "µUI/mL", 0.40, 4.30, "#8E44AD"),
    ("TGO (AST)", "U/L", None, 34, "#E74C3C"),
    ("TGP (ALT)", "U/L", 10, 49, "#C0392B"),
    ("HDL", "mg/dL", 40, None, "#27AE60"),
    ("LDL", "mg/dL", None, 130, "#E67E22"),
    ("Colesterol Total", "mg/dL", None, 190, "#F39C12"),
    ("Triglicérides", "mg/dL", None, 150, "#E74C3C"),
    ("Glicose", "mg/dL", 70, 99, "#2980B9"),
    ("HbA1c", "%", None, 5.7, "#8E44AD"),
    ("Creatinina", "mg/dL", 0.70, 1.30, "#16A085"),
    ("TFG estimada (eGFR)", "mL/min/1,73m²", 90, None, "#1ABC9C"),
]

session_dates = {sid: sessions[sid]["date"] for sid in sessions}

def get_trend_data(exam_name):
    points = []
    for r in results:
        if r["exam"] == exam_name and r["value"] is not None:
            sid = r["session_id"]
            points.append({"date": session_dates.get(sid,""), "value": r["value"], "status": r["status"]})
    return sorted(points, key=lambda x: x["date"])

tab_names = ["🔴 Prioridade Alta", "💊 Tireoide", "❤️ Lipídios", "🍬 Glicemia", "🫁 Fígado", "🫀 Rim"]
tabs = st.tabs(tab_names)

def trend_chart(exam_name, unit, ref_min, ref_max, color, height=280):
    data = get_trend_data(exam_name)
    if len(data) < 2:
        if data:
            st.caption(f"{exam_name}: apenas 1 ponto disponível ({data[0]['value']} {unit})")
        else:
            st.caption(f"Sem dados para {exam_name}")
        return
    dates = [datetime.strptime(d["date"], "%Y-%m-%d") for d in data]
    values = [d["value"] for d in data]
    colors = [status_color(d["status"]) for d in data]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=values, mode="lines+markers+text",
        text=[f"{v}" for v in values], textposition="top center",
        line=dict(color=color, width=2.5), marker=dict(size=10, color=colors)))
    if ref_max is not None:
        fig.add_hline(y=ref_max, line_dash="dash", line_color="#E74C3C",
                      annotation_text=f"Limite sup: {ref_max} {unit}", annotation_position="right")
    if ref_min is not None:
        fig.add_hline(y=ref_min, line_dash="dash", line_color="#27AE60",
                      annotation_text=f"Limite inf: {ref_min} {unit}", annotation_position="right")
    fig.update_layout(height=height, title=f"{exam_name} ({unit})", plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(showgrid=False, automargin=True),
        yaxis=dict(showgrid=True, gridcolor="#eee", automargin=True),
        showlegend=False, margin=dict(l=50, r=175, t=50, b=50))
    st.plotly_chart(fig, use_container_width=True)

with tabs[0]:
    st.caption("Exames que apresentam alteração nas últimas coletas")
    c1, c2 = st.columns(2)
    with c1:
        trend_chart("TSH", "µUI/mL", 0.40, 4.30, "#8E44AD")
        trend_chart("TGO (AST)", "U/L", None, 34, "#E74C3C")
    with c2:
        trend_chart("HDL", "mg/dL", 40, None, "#27AE60")
        trend_chart("TGP (ALT)", "U/L", 10, 49, "#C0392B")

with tabs[1]:
    c1, c2 = st.columns(2)
    with c1:
        trend_chart("TSH", "µUI/mL", 0.40, 4.30, "#8E44AD")
        trend_chart("T4 Livre", "ng/dL", 0.89, 1.76, "#9B59B6")
    with c2:
        trend_chart("Anti-tireoglobulina (anti-TG)", "UI/mL", None, 4.5, "#6C3483")
        trend_chart("Anti-TPO (Antiperoxidase)", "U/mL", None, 13.8, "#A569BD")

with tabs[2]:
    c1, c2 = st.columns(2)
    with c1:
        trend_chart("Colesterol Total", "mg/dL", None, 190, "#F39C12")
        trend_chart("LDL", "mg/dL", None, 130, "#E67E22")
    with c2:
        trend_chart("HDL", "mg/dL", 40, None, "#27AE60")
        trend_chart("Triglicérides", "mg/dL", None, 150, "#E74C3C")

with tabs[3]:
    c1, c2 = st.columns(2)
    with c1:
        trend_chart("Glicose", "mg/dL", 70, 99, "#2980B9")
    with c2:
        trend_chart("HbA1c", "%", None, 5.7, "#8E44AD")

with tabs[4]:
    c1, c2 = st.columns(2)
    with c1:
        trend_chart("TGO (AST)", "U/L", None, 34, "#E74C3C")
    with c2:
        trend_chart("TGP (ALT)", "U/L", 10, 49, "#C0392B")

with tabs[5]:
    c1, c2 = st.columns(2)
    with c1:
        trend_chart("Creatinina", "mg/dL", 0.70, 1.30, "#16A085")
    with c2:
        trend_chart("TFG estimada (eGFR)", "mL/min/1,73m²", 90, None, "#1ABC9C")
