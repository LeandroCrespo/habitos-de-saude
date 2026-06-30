import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_manager import load_bioimpedance, save_bioimpedance, get_bmi_category, get_fat_category

st.set_page_config(page_title="Bioimpedância", page_icon="📊", layout="wide")

st.markdown("""
<style>
.section-header{font-size:22px;font-weight:700;color:#1E8449;border-bottom:3px solid #1E8449;padding-bottom:8px;margin:20px 0 16px}
.metric-card{background:linear-gradient(135deg,#f0fff4,#e8f5e9);border-left:4px solid #1E8449;border-radius:12px;padding:16px 20px;margin:6px 0;box-shadow:0 2px 8px rgba(0,0,0,0.07)}
.metric-card.alert{border-left-color:#E74C3C;background:linear-gradient(135deg,#fff5f5,#ffe0e0)}
.metric-card.warn{border-left-color:#F39C12;background:linear-gradient(135deg,#fffbf0,#fef3cd)}
.metric-title{font-size:12px;color:#666;font-weight:600;text-transform:uppercase;letter-spacing:0.5px}
.metric-value{font-size:26px;font-weight:700;color:#1a3a1a;line-height:1.2}
.metric-sub{font-size:12px;color:#555;margin-top:2px}
</style>
""", unsafe_allow_html=True)

st.markdown("## 📊 Bioimpedância Semanal")
st.caption("Medição realizada toda terça-feira · Dispositivo: Smartwatch Ultra")

bio_list = load_bioimpedance()
if not bio_list:
    st.warning("Nenhuma medição registrada ainda.")
    st.stop()

bio_sorted = sorted(bio_list, key=lambda x: x["date"])
df = pd.DataFrame(bio_sorted)
df["date"] = pd.to_datetime(df["date"])
df["date_str"] = df["date"].dt.strftime("%d/%m/%Y")

latest = bio_sorted[-1]
prev = bio_sorted[-2] if len(bio_sorted) > 1 else latest

# ── Última medição ─────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>📌 Última Medição</div>", unsafe_allow_html=True)
st.caption(f"**{datetime.strptime(latest['date'], '%Y-%m-%d').strftime('%d/%m/%Y')}** · {latest.get('device','—')}")

c1, c2, c3, c4, c5 = st.columns(5)
metrics = [
    ("Peso", f"{latest['peso_kg']:.1f} kg", f"IMC {latest['imc']:.1f}", latest["peso_kg"] - prev["peso_kg"], "", False),
    ("% Gordura", f"{latest['percentual_gordura']:.1f}%", f"{latest['massa_gordura_kg']:.1f} kg de gordura", latest["percentual_gordura"] - prev["percentual_gordura"], "%", False),
    ("Músculo Esq.", f"{latest['musculo_esqueletico_kg']:.1f} kg", f"{latest.get('percentual_musculo',0):.1f}% do corpo", latest["musculo_esqueletico_kg"] - prev["musculo_esqueletico_kg"], " kg", True),
    ("% Água", f"{latest.get('percentual_agua',0):.1f}%", "Hidratação", latest.get("percentual_agua",0) - prev.get("percentual_agua",0), "%", True),
    ("TMB", f"{latest.get('tmb_kcal',0):,} kcal", f"G. Visceral: {latest.get('gordura_visceral','—')}", latest.get("tmb_kcal",0) - prev.get("tmb_kcal",0), " kcal", True),
]
for col, (title, val, sub, delta, unit, higher_is_better) in zip([c1,c2,c3,c4,c5], metrics):
    with col:
        if delta != 0:
            sym = "▲" if delta > 0 else "▼"
            good = (delta > 0) == higher_is_better
            color = "#27AE60" if good else "#E74C3C"
            delta_html = f"<span style='color:{color}'>{sym} {abs(round(delta,1))}{unit}</span>"
        else:
            delta_html = "= sem alteração"
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-title'>{title}</div>
            <div class='metric-value'>{val}</div>
            <div class='metric-sub'>{sub}</div>
            <div class='metric-sub'>{delta_html}</div>
        </div>""", unsafe_allow_html=True)

if latest.get("notes"):
    st.info(f"📝 {latest['notes']}")

# ── Gráficos ────────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>📈 Evolução Temporal</div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["⚖️ Peso & IMC", "🔥 Composição Corporal", "💪 Músculo & Água", "🫀 TMB & Visceral"])

COLOR_MAIN = "#1E8449"
COLOR_FAT  = "#E74C3C"
COLOR_MUS  = "#2980B9"
COLOR_WAT  = "#16A085"

with tab1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["peso_kg"], mode="lines+markers", name="Peso (kg)",
        line=dict(color=COLOR_MAIN, width=3), marker=dict(size=7), fill="tozeroy", fillcolor="rgba(30,132,73,0.07)"))
    fig.add_hline(y=82, line_dash="dash", line_color="#F39C12", annotation_text="Meta: 82 kg", annotation_position="right")
    fig.update_layout(height=320, title="Evolução do Peso Corporal", plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#eee", title="kg"), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df["date"], y=df["imc"], mode="lines+markers", name="IMC",
        line=dict(color="#8E44AD", width=3), marker=dict(size=7)))
    fig2.add_hrect(y0=18.5, y1=25, fillcolor="rgba(39,174,96,0.1)", line_width=0, annotation_text="Normal")
    fig2.add_hrect(y0=25, y1=30, fillcolor="rgba(243,156,18,0.1)", line_width=0, annotation_text="Sobrepeso")
    fig2.add_hrect(y0=30, y1=40, fillcolor="rgba(231,76,60,0.1)", line_width=0, annotation_text="Obesidade")
    fig2.update_layout(height=260, title="Índice de Massa Corporal (IMC)", plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#eee", title="IMC"), showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

with tab2:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["percentual_gordura"], mode="lines+markers", name="% Gordura",
        line=dict(color=COLOR_FAT, width=3), marker=dict(size=7), fill="tozeroy", fillcolor="rgba(231,76,60,0.07)"))
    fig.add_hline(y=20, line_dash="dash", line_color="#F39C12", annotation_text="Meta: 20%")
    fig.add_hline(y=25, line_dash="dot", line_color="#E74C3C", annotation_text="Limite aceitável")
    fig.update_layout(height=300, title="Percentual de Gordura Corporal", plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#eee", title="%"), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=df["date"], y=df["massa_gordura_kg"], name="Gordura (kg)",
        marker_color=COLOR_FAT, opacity=0.8))
    fig2.add_trace(go.Bar(x=df["date"], y=df["musculo_esqueletico_kg"], name="Músculo (kg)",
        marker_color=COLOR_MUS, opacity=0.8))
    fig2.update_layout(height=280, title="Gordura vs. Músculo (kg)", barmode="group",
        plot_bgcolor="white", paper_bgcolor="white", xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#eee", title="kg"), legend=dict(orientation="h"))
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["musculo_esqueletico_kg"], mode="lines+markers",
        name="Músculo Esq. (kg)", line=dict(color=COLOR_MUS, width=3), marker=dict(size=7)))
    fig.add_hline(y=40, line_dash="dash", line_color="#27AE60", annotation_text="Meta: 40 kg")
    fig.update_layout(height=280, title="Massa Muscular Esquelética", plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#eee", title="kg"), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df["date"], y=df["percentual_agua"], mode="lines+markers",
        name="% Água", line=dict(color=COLOR_WAT, width=3), marker=dict(size=7),
        fill="tozeroy", fillcolor="rgba(22,160,133,0.07)"))
    fig2.add_hline(y=55, line_dash="dash", line_color="#16A085", annotation_text="Referência mín. 55%")
    fig2.update_layout(height=260, title="Percentual de Água Corporal", plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#eee", title="%"), showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

with tab4:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["tmb_kcal"], mode="lines+markers",
        name="TMB (kcal)", line=dict(color="#E67E22", width=3), marker=dict(size=7),
        fill="tozeroy", fillcolor="rgba(230,126,34,0.07)"))
    fig.update_layout(height=280, title="Taxa Metabólica Basal (TMB)", plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#eee", title="kcal"), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    if "gordura_visceral" in df.columns:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=df["date"], y=df["gordura_visceral"], name="Gordura Visceral",
            marker_color=["#E74C3C" if v >= 13 else "#F39C12" if v >= 10 else "#27AE60"
                          for v in df["gordura_visceral"]]))
        fig2.add_hline(y=9, line_dash="dash", line_color="#27AE60", annotation_text="Meta: ≤ 9")
        fig2.update_layout(height=260, title="Gordura Visceral (escala 1-20)", plot_bgcolor="white",
            paper_bgcolor="white", xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#eee"),
            showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

# ── Tabela histórica ─────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>📋 Histórico Completo</div>", unsafe_allow_html=True)
df_show = df[["date_str","peso_kg","imc","percentual_gordura","massa_gordura_kg",
              "musculo_esqueletico_kg","percentual_agua","tmb_kcal","gordura_visceral","device"]].copy()
df_show.columns = ["Data","Peso (kg)","IMC","Gordura (%)","Gordura (kg)",
                   "Músculo (kg)","Água (%)","TMB (kcal)","G. Visceral","Dispositivo"]
df_show = df_show.sort_values("Data", ascending=False)
st.dataframe(df_show, use_container_width=True, hide_index=True)

# ── Adicionar nova medição ────────────────────────────────────────────────────
st.markdown("<div class='section-header'>➕ Registrar Nova Medição</div>", unsafe_allow_html=True)
with st.form("nova_bio", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        data_med = st.date_input("Data", value=date.today())
        peso = st.number_input("Peso (kg)", 50.0, 200.0, float(latest["peso_kg"]), 0.1)
        imc = st.number_input("IMC", 15.0, 50.0, float(latest["imc"]), 0.1)
        pct_gordura = st.number_input("% Gordura", 1.0, 60.0, float(latest["percentual_gordura"]), 0.1)
    with col2:
        massa_gordura = st.number_input("Gordura (kg)", 1.0, 100.0, float(latest["massa_gordura_kg"]), 0.1)
        musculo = st.number_input("Músculo Esq. (kg)", 10.0, 80.0, float(latest["musculo_esqueletico_kg"]), 0.1)
        pct_agua = st.number_input("% Água", 20.0, 80.0, float(latest.get("percentual_agua",48)), 0.1)
        pct_musculo = st.number_input("% Músculo", 10.0, 80.0, float(latest.get("percentual_musculo",65)), 0.1)
    with col3:
        tmb = st.number_input("TMB (kcal)", 1000, 4000, int(latest.get("tmb_kcal",1780)), 1)
        gordura_visc = st.number_input("Gordura Visceral", 1, 30, int(latest.get("gordura_visceral",10)), 1)
        massa_ossea = st.number_input("Massa Óssea (kg)", 1.0, 6.0, float(latest.get("massa_ossea_kg",3.3)), 0.1)
        device = st.selectbox("Dispositivo", ["Smartwatch Ultra","Balança Bioimpedância","InBody","Heath Pro","Outro"])
    notas = st.text_input("Observações (opcional)")
    submitted = st.form_submit_button("💾 Salvar Medição", type="primary")

if submitted:
    new_id = max([b.get("id",0) for b in bio_list], default=0) + 1
    new_entry = {
        "id": new_id,
        "date": str(data_med),
        "peso_kg": peso, "imc": imc,
        "percentual_gordura": pct_gordura, "massa_gordura_kg": massa_gordura,
        "massa_magra_kg": round(peso - massa_gordura, 1),
        "musculo_esqueletico_kg": musculo, "percentual_musculo": pct_musculo,
        "percentual_agua": pct_agua, "massa_ossea_kg": massa_ossea,
        "tmb_kcal": tmb, "gordura_visceral": gordura_visc,
        "idade_corporal": 0, "device": device, "notes": notas
    }
    bio_list.append(new_entry)
    save_bioimpedance(bio_list)
    st.success(f"✅ Medição de {data_med.strftime('%d/%m/%Y')} salva com sucesso!")
    st.rerun()
