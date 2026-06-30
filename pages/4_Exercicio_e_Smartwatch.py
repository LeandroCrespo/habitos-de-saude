import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_manager import load_exercises, save_exercises, load_bioimpedance, calc_tdee

st.set_page_config(page_title="Exercício & Smartwatch", page_icon="💪", layout="wide")

st.markdown("""
<style>
.section-header{font-size:22px;font-weight:700;color:#1E8449;border-bottom:3px solid #1E8449;padding-bottom:8px;margin:20px 0 16px}
.metric-card{background:linear-gradient(135deg,#f0fff4,#e8f5e9);border-left:4px solid #1E8449;border-radius:12px;padding:14px 18px;margin:6px 0;box-shadow:0 2px 8px rgba(0,0,0,0.07)}
.metric-title{font-size:11px;color:#666;font-weight:700;text-transform:uppercase;letter-spacing:0.5px}
.metric-value{font-size:26px;font-weight:700;color:#1a3a1a;line-height:1.2}
.metric-sub{font-size:12px;color:#555;margin-top:2px}
.watch-card{background:linear-gradient(135deg,#1a3a1a,#0d5c29);border-radius:16px;padding:20px;color:white;margin:10px 0}
</style>
""", unsafe_allow_html=True)

st.markdown("## 💪 Exercício & Smartwatch Ultra")

exercises = load_exercises()
bio_list = load_bioimpedance()

tmb = 1783
if bio_list:
    tmb = sorted(bio_list, key=lambda x: x["date"])[-1].get("tmb_kcal", 1783)

# ── Painel do Smartwatch ───────────────────────────────────────────────────────
st.markdown("<div class='section-header'>⌚ Dados do Smartwatch Ultra — Hoje</div>", unsafe_allow_html=True)

col_w1, col_w2 = st.columns([1, 2])
with col_w1:
    st.markdown("""
    <div class='watch-card'>
        <div style='font-size:13px;opacity:0.7;margin-bottom:4px'>SMARTWATCH ULTRA</div>
        <div style='font-size:40px;text-align:center'>⌚</div>
        <div style='text-align:center;font-size:12px;opacity:0.8;margin-top:8px'>Sincronize os dados abaixo</div>
    </div>
    """, unsafe_allow_html=True)

with col_w2:
    with st.form("smartwatch_hoje"):
        sc1, sc2 = st.columns(2)
        with sc1:
            sw_steps = st.number_input("Passos (hoje):", 0, 50000, 4000, step=100)
            sw_sleep = st.number_input("Pontuação do sono (0-100):", 0, 100, 78, step=1)
            sw_heart = st.number_input("FC média (bpm):", 40, 200, 68, step=1)
        with sc2:
            sw_calories_watch = st.number_input("Calorias pelo watch (kcal):", 0, 5000, 0, step=10)
            sw_active_min = st.number_input("Minutos ativos:", 0, 300, 30, step=5)
            sw_date = st.date_input("Data:", value=date.today())
        sw_submit = st.form_submit_button("📊 Calcular meu gasto calórico", type="primary")

if sw_submit:
    tdee_calc = calc_tdee(tmb, sw_steps, sw_active_min)
    st.markdown("<div class='section-header'>📊 Resultado do Balanço</div>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-title'>TMB (Bioimpedância)</div>
            <div class='metric-value'>{tmb:,}<span style='font-size:14px'> kcal</span></div>
            <div class='metric-sub'>Metabolismo de repouso</div>
        </div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-title'>TDEE Estimado</div>
            <div class='metric-value' style='color:#E67E22'>{tdee_calc:,}<span style='font-size:14px'> kcal</span></div>
            <div class='metric-sub'>{sw_steps:,} passos + {sw_active_min} min exerc.</div>
        </div>""", unsafe_allow_html=True)
    with m3:
        sleep_color = "#27AE60" if sw_sleep >= 75 else "#F39C12" if sw_sleep >= 60 else "#E74C3C"
        sleep_label = "Ótimo" if sw_sleep >= 85 else "Bom" if sw_sleep >= 70 else "Regular" if sw_sleep >= 55 else "Ruim"
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-title'>Qualidade do Sono</div>
            <div class='metric-value' style='color:{sleep_color}'>{sw_sleep}<span style='font-size:14px'>/100</span></div>
            <div class='metric-sub'>{sleep_label}</div>
        </div>""", unsafe_allow_html=True)
    with m4:
        step_color = "#27AE60" if sw_steps >= 7000 else "#F39C12" if sw_steps >= 4000 else "#E74C3C"
        step_label = "Ativo" if sw_steps >= 7000 else "Moderado" if sw_steps >= 4000 else "Sedentário"
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-title'>Passos</div>
            <div class='metric-value' style='color:{step_color}'>{sw_steps:,}</div>
            <div class='metric-sub'>{step_label} · Meta: 7.000+</div>
        </div>""", unsafe_allow_html=True)

    # Gauge de passos
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=sw_steps,
        delta={"reference": 7000, "valueformat": ","},
        gauge={
            "axis": {"range": [0, 15000], "tickformat": ","},
            "bar": {"color": step_color},
            "steps": [
                {"range": [0, 3000], "color": "#ffe0e0"},
                {"range": [3000, 7000], "color": "#fff3cd"},
                {"range": [7000, 15000], "color": "#d4edda"},
            ],
            "threshold": {"line": {"color": "green", "width": 3}, "thickness": 0.8, "value": 7000}
        },
        title={"text": "Passos (meta: 7.000)"}
    ))
    fig_gauge.update_layout(height=250, margin=dict(l=10,r=10,t=40,b=10))
    st.plotly_chart(fig_gauge, use_container_width=True)

    if sw_steps < 3000:
        st.error("🚨 Nível de atividade muito baixo! Caminhadas curtas ao longo do dia ajudam muito no HDL e no controle glicêmico.")
    elif sw_steps < 7000:
        st.warning("⚠️ Atividade moderada. Tente chegar a 7.000–10.000 passos para maximizar o emagrecimento e melhorar o HDL.")
    else:
        st.success("✅ Parabéns! Nível de atividade adequado.")

# ── Registrar treino ──────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>🏋️ Registrar Treino</div>", unsafe_allow_html=True)

with st.form("novo_treino", clear_on_submit=True):
    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        data_treino = st.date_input("Data:", value=date.today())
        tipo = st.selectbox("Tipo:", ["Musculação","Caminhada","Corrida","HIIT","Natação",
                                       "Bicicleta","Yoga/Pilates","Fisioterapia","Outro"])
    with tc2:
        duracao = st.number_input("Duração (min):", 5, 300, 60, step=5)
        cal_queimadas = st.number_input("Calorias queimadas (kcal):", 0, 2000, 350, step=10)
    with tc3:
        passos_treino = st.number_input("Passos durante o treino:", 0, 30000, 1000, step=100)
        sleep_score = st.number_input("Pontuação do sono (noite anterior):", 0, 100, 75, step=1)
    notas_treino = st.text_input("Grupos musculares / observações:")
    t_submit = st.form_submit_button("💾 Salvar Treino", type="primary")

if t_submit:
    new_ex = {
        "id": max([e.get("id",0) for e in exercises], default=0) + 1,
        "date": str(data_treino),
        "type": tipo,
        "duration_min": duracao,
        "calories_burned": cal_queimadas,
        "steps": passos_treino,
        "sleep_score": sleep_score,
        "notes": notas_treino
    }
    exercises.append(new_ex)
    save_exercises(exercises)
    st.success(f"✅ Treino de {data_treino.strftime('%d/%m/%Y')} salvo!")
    st.rerun()

# ── Histórico de treinos ──────────────────────────────────────────────────────
if exercises:
    st.markdown("<div class='section-header'>📋 Histórico de Treinos</div>", unsafe_allow_html=True)
    df_ex = pd.DataFrame(sorted(exercises, key=lambda x: x["date"], reverse=True))
    df_ex["date"] = pd.to_datetime(df_ex["date"])
    df_ex["date_str"] = df_ex["date"].dt.strftime("%d/%m/%Y")

    # Gráficos
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_ex["date"].sort_values(), y=df_ex.sort_values("date")["calories_burned"],
            marker_color="#1E8449", name="Calorias queimadas"
        ))
        fig.update_layout(height=240, title="Calorias por Treino", plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#eee", title="kcal"), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_g2:
        fig2 = go.Figure()
        df_sorted = df_ex.sort_values("date")
        colors_sleep = ["#27AE60" if s >= 75 else "#F39C12" if s >= 60 else "#E74C3C"
                        for s in df_sorted["sleep_score"]]
        fig2.add_trace(go.Bar(x=df_sorted["date"], y=df_sorted["sleep_score"],
            marker_color=colors_sleep, name="Sleep Score"))
        fig2.add_hline(y=75, line_dash="dash", line_color="#27AE60", annotation_text="Meta: 75")
        fig2.update_layout(height=240, title="Pontuação do Sono", plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#eee", title="Score 0-100"),
            showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    # Passos
    fig3 = go.Figure()
    df_steps = df_ex.sort_values("date")
    step_colors = ["#27AE60" if s >= 7000 else "#F39C12" if s >= 4000 else "#E74C3C"
                   for s in df_steps["steps"]]
    fig3.add_trace(go.Bar(x=df_steps["date"], y=df_steps["steps"],
        marker_color=step_colors, name="Passos"))
    fig3.add_hline(y=7000, line_dash="dash", line_color="#27AE60", annotation_text="Meta: 7.000 passos")
    fig3.add_hline(y=3000, line_dash="dot", line_color="#E74C3C", annotation_text="Mínimo recomendado")
    fig3.update_layout(height=250, title="Passos Diários", plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#eee", title="passos"), showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)

    # Tabela
    df_show = df_ex[["date_str","type","duration_min","calories_burned","steps","sleep_score","notes"]].copy()
    df_show.columns = ["Data","Tipo","Duração (min)","Calorias (kcal)","Passos","Sono (score)","Notas"]
    st.dataframe(df_show, use_container_width=True, hide_index=True)

# ── Dicas personalizadas ──────────────────────────────────────────────────────
st.markdown("<div class='section-header'>💡 Dicas de Atividade Física (Perfil de Leandro)</div>", unsafe_allow_html=True)
st.markdown("""
> **Atenção:** Você possui laudo de RM da coluna lombo-sacra. Exerça as atividades com supervisão profissional (fisioterapeuta/preparador físico).

| Recomendação | Meta semanal | Status |
|---|---|---|
| 🏋️ Musculação | 3–4x por semana | Em andamento ✅ |
| 🚶 Caminhada / cardio aeróbico | 150 min/semana | Aumentar ⚠️ |
| 📊 Passos diários | 7.000–10.000 | Aumentar ⚠️ |
| 🧘 Alongamento / mobilidade | Após cada treino | Incluir |

**Por que aumentar o cardio?**
- HDL baixo (33 mg/dL) → exercício aeróbico é o principal elevador natural do HDL
- Controle glicêmico → caminhadas de 10 min após refeições reduzem pico de glicose
- Hipotireoidismo → pode causar fadiga; cardio leve ajuda a combater

**Meta de passos progressiva:**
- Semana 1–2: 4.000 passos/dia
- Semana 3–4: 6.000 passos/dia
- A partir do mês 2: 8.000–10.000 passos/dia
""")
