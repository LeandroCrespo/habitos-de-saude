import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils.data_manager import (
    load_profile, load_bioimpedance, load_exams,
    calc_age, get_bmi_category, get_fat_category, status_color, status_emoji
)

st.set_page_config(
    page_title="Saúde de Leandro",
    page_icon="💚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS global ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"] { background: linear-gradient(180deg,#1a5c2a 0%,#0d3318 100%); }
[data-testid="stSidebar"] * { color: #e8f5e9 !important; }
[data-testid="stSidebar"] .stSelectbox label { color:#b2dfdb !important; }
.metric-card {
    background: linear-gradient(135deg,#f0fff4,#e8f5e9);
    border-left: 4px solid #1E8449;
    border-radius: 12px;
    padding: 16px 20px;
    margin: 6px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
}
.metric-card.alert { border-left-color:#E74C3C; background:linear-gradient(135deg,#fff5f5,#ffe0e0); }
.metric-card.warn  { border-left-color:#F39C12; background:linear-gradient(135deg,#fffbf0,#fef3cd); }
.metric-title { font-size:12px; color:#666; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; }
.metric-value { font-size:28px; font-weight:700; color:#1a3a1a; line-height:1.2; }
.metric-sub   { font-size:13px; color:#555; margin-top:2px; }
.section-header {
    font-size:22px; font-weight:700; color:#1E8449;
    border-bottom:3px solid #1E8449; padding-bottom:8px; margin:20px 0 16px 0;
}
.alert-box {
    background:#fff5f5; border:1px solid #E74C3C; border-radius:10px;
    padding:12px 16px; margin:6px 0;
}
.alert-box.warn { background:#fffbf0; border-color:#F39C12; }
.alert-box.good { background:#f0fff4; border-color:#27AE60; }
.hero-banner {
    background: linear-gradient(135deg,#1E8449,#0d5c29);
    border-radius:16px; padding:28px 36px; color:white; margin-bottom:24px;
    box-shadow: 0 4px 20px rgba(30,132,73,0.3);
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
profile = load_profile()
nome = profile.get("nome", "Leandro")
altura = profile.get("altura_m", 1.82)
dob = profile.get("data_nascimento", "1981-06-30")
idade = calc_age(dob)

with st.sidebar:
    st.markdown(f"""
    <div style='text-align:center;padding:16px 0 8px'>
        <div style='font-size:52px'>🧑‍⚕️</div>
        <div style='font-size:17px;font-weight:700'>{nome}</div>
        <div style='font-size:13px;opacity:0.8'>{idade} anos · {altura} m · Masc.</div>
        <hr style='border-color:rgba(255,255,255,0.2);margin:10px 0'>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Objetivo: Emagrecimento + massa muscular")
    st.caption(f"Médica: {profile.get('medico','—')}")

# ── Dashboard principal ──────────────────────────────────────────────────────
st.markdown("""
<div class='hero-banner'>
    <div style='font-size:32px;font-weight:800;margin-bottom:6px'>💚 Painel de Saúde</div>
    <div style='font-size:16px;opacity:0.9'>Acompanhamento completo de evolução — bioimpedância, exames, dieta e exercício</div>
</div>
""", unsafe_allow_html=True)

# ── Bioimpedância mais recente ────────────────────────────────────────────────
bio_list = load_bioimpedance()
if bio_list:
    bio_list_sorted = sorted(bio_list, key=lambda x: x["date"])
    latest = bio_list_sorted[-1]
    prev = bio_list_sorted[-2] if len(bio_list_sorted) > 1 else latest
    first_2026 = next((b for b in bio_list_sorted if b["date"] >= "2026-01-01"), latest)

    st.markdown("<div class='section-header'>📊 Bioimpedância — Última Medição</div>", unsafe_allow_html=True)
    st.caption(f"Data: **{datetime.strptime(latest['date'],'%Y-%m-%d').strftime('%d/%m/%Y')}** | Dispositivo: {latest.get('device','—')}")

    c1, c2, c3, c4 = st.columns(4)

    def delta_str(val, prev_val, unit="", reverse=False):
        d = round(val - prev_val, 1)
        if d == 0:
            return f"= {unit}"
        sym = "▲" if d > 0 else "▼"
        good = (d < 0 and not reverse) or (d > 0 and reverse)
        col = "#27AE60" if good else "#E74C3C"
        return f"<span style='color:{col}'>{sym} {abs(d)}{unit}</span>"

    with c1:
        bmi_cat, bmi_col = get_bmi_category(latest["imc"])
        d = delta_str(latest["peso_kg"], prev["peso_kg"], " kg")
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-title'>Peso Corporal</div>
            <div class='metric-value'>{latest['peso_kg']:.1f} <span style='font-size:16px'>kg</span></div>
            <div class='metric-sub'>IMC {latest['imc']:.1f} · {bmi_cat}</div>
            <div class='metric-sub'>{d}</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        fat_cat, fat_col = get_fat_category(latest["percentual_gordura"])
        d = delta_str(latest["percentual_gordura"], prev["percentual_gordura"], "%")
        st.markdown(f"""<div class='metric-card {"alert" if latest["percentual_gordura"] > 25 else "warn" if latest["percentual_gordura"] > 20 else ""}'>
            <div class='metric-title'>Gordura Corporal</div>
            <div class='metric-value'>{latest['percentual_gordura']:.1f}<span style='font-size:16px'>%</span></div>
            <div class='metric-sub'>{latest['massa_gordura_kg']:.1f} kg · {fat_cat}</div>
            <div class='metric-sub'>{d}</div>
        </div>""", unsafe_allow_html=True)

    with c3:
        d = delta_str(latest["musculo_esqueletico_kg"], prev["musculo_esqueletico_kg"], " kg", reverse=True)
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-title'>Músculo Esquelético</div>
            <div class='metric-value'>{latest['musculo_esqueletico_kg']:.1f} <span style='font-size:16px'>kg</span></div>
            <div class='metric-sub'>{latest.get('percentual_musculo', 0):.1f}% · Água {latest.get('percentual_agua',0):.1f}%</div>
            <div class='metric-sub'>{d}</div>
        </div>""", unsafe_allow_html=True)

    with c4:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-title'>TMB (Metabolismo Basal)</div>
            <div class='metric-value'>{latest.get('tmb_kcal',0):,} <span style='font-size:16px'>kcal</span></div>
            <div class='metric-sub'>Gordura Visceral: {latest.get('gordura_visceral','—')}</div>
            <div class='metric-sub'>Idade Corporal: {latest.get('idade_corporal','—')} anos</div>
        </div>""", unsafe_allow_html=True)

    # Mini gráfico de peso
    df = pd.DataFrame(bio_list_sorted)
    df["date"] = pd.to_datetime(df["date"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["peso_kg"],
        mode="lines+markers", name="Peso",
        line=dict(color="#1E8449", width=3),
        marker=dict(size=6, color="#1E8449"),
        fill="tozeroy", fillcolor="rgba(30,132,73,0.08)"
    ))
    fig.update_layout(
        height=200, margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=True, gridcolor="#eee", title="kg"),
        plot_bgcolor="white", paper_bgcolor="white",
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

    # Evolução desde o início
    primeiro = bio_list_sorted[0]
    st.markdown("<div class='section-header'>📈 Progresso Total</div>", unsafe_allow_html=True)
    cp1, cp2, cp3, cp4 = st.columns(4)
    with cp1:
        delta = round(latest["peso_kg"] - primeiro["peso_kg"], 1)
        st.metric("Peso perdido (total)", f"{abs(delta):.1f} kg", f"{delta:+.1f} kg", delta_color="inverse")
    with cp2:
        delta = round(latest["percentual_gordura"] - primeiro["percentual_gordura"], 1)
        st.metric("Gordura (% total)", f"{latest['percentual_gordura']:.1f}%", f"{delta:+.1f}%", delta_color="inverse")
    with cp3:
        delta = round(latest["musculo_esqueletico_kg"] - primeiro["musculo_esqueletico_kg"], 1)
        st.metric("Músculo ganho", f"{latest['musculo_esqueletico_kg']:.1f} kg", f"{delta:+.1f} kg")
    with cp4:
        delta = round(latest["massa_gordura_kg"] - primeiro["massa_gordura_kg"], 1)
        st.metric("Gordura perdida (kg)", f"{abs(delta):.1f} kg", f"{delta:+.1f} kg", delta_color="inverse")

# ── Alertas de Exames ─────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>🚨 Alertas de Exames Laboratoriais</div>", unsafe_allow_html=True)
exams_data = load_exams()
results = exams_data.get("results", [])
sessions = {s["id"]: s for s in exams_data.get("sessions", [])}

# Pegar resultados da sessão mais recente
latest_session_id = "s003"
alerts = [r for r in results if r["session_id"] == latest_session_id and r["status"] in ("alta", "baixa")]
alerts_all = sorted(
    [r for r in results if r["status"] in ("alta", "baixa")],
    key=lambda x: x["session_id"], reverse=True
)

# Deduplica por exame mostrando mais recente
seen = {}
for r in alerts_all:
    if r["exam"] not in seen:
        seen[r["exam"]] = r

ca, cb = st.columns(2)
items = list(seen.values())
half = (len(items) + 1) // 2
with ca:
    for r in items[:half]:
        sess_date = sessions.get(r["session_id"], {}).get("date", "")
        sess_dt = datetime.strptime(sess_date, "%Y-%m-%d").strftime("%d/%m/%Y") if sess_date else ""
        icon = "🔴" if r["status"] == "alta" else "🟠"
        val = f"{r['value']} {r['unit']}" if r["value"] is not None else r["notes"]
        st.markdown(f"""<div class='alert-box {"warn" if r["status"]=="baixa" else ""}'>
            {icon} <b>{r['exam']}</b> — {val} <span style='color:#888;font-size:12px'>({r['category']} · {sess_dt})</span><br>
            <span style='font-size:12px'>{r.get('notes','')}</span>
        </div>""", unsafe_allow_html=True)
with cb:
    for r in items[half:]:
        sess_date = sessions.get(r["session_id"], {}).get("date", "")
        sess_dt = datetime.strptime(sess_date, "%Y-%m-%d").strftime("%d/%m/%Y") if sess_date else ""
        icon = "🔴" if r["status"] == "alta" else "🟠"
        val = f"{r['value']} {r['unit']}" if r["value"] is not None else r["notes"]
        st.markdown(f"""<div class='alert-box {"warn" if r["status"]=="baixa" else ""}'>
            {icon} <b>{r['exam']}</b> — {val} <span style='color:#888;font-size:12px'>({r['category']} · {sess_dt})</span><br>
            <span style='font-size:12px'>{r.get('notes','')}</span>
        </div>""", unsafe_allow_html=True)

# ── Próximas metas ────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>🎯 Próximas Metas</div>", unsafe_allow_html=True)
if bio_list:
    lat = bio_list_sorted[-1]
    peso_meta = 82.0
    gordura_meta = 20.0
    m1, m2, m3 = st.columns(3)
    with m1:
        falta = round(lat["peso_kg"] - peso_meta, 1)
        st.progress(max(0.0, min(1.0, 1 - (falta / (bio_list_sorted[0]["peso_kg"] - peso_meta)))))
        st.caption(f"**Peso:** {lat['peso_kg']:.1f} kg → meta {peso_meta:.0f} kg (faltam {falta:.1f} kg)")
    with m2:
        falta_g = round(lat["percentual_gordura"] - gordura_meta, 1)
        prog = max(0.0, min(1.0, 1 - (falta_g / (bio_list_sorted[0]["percentual_gordura"] - gordura_meta))))
        st.progress(prog)
        st.caption(f"**Gordura:** {lat['percentual_gordura']:.1f}% → meta {gordura_meta:.0f}% (faltam {falta_g:.1f}pp)")
    with m3:
        musculo_meta = 40.0
        atual_m = lat["musculo_esqueletico_kg"]
        prog_m = min(1.0, atual_m / musculo_meta)
        st.progress(prog_m)
        st.caption(f"**Músculo:** {atual_m:.1f} kg → meta {musculo_meta:.0f} kg")

st.markdown("---")
st.caption("💡 Navegue pelo menu lateral para ver análises detalhadas, registrar alimentos e exercícios.")
