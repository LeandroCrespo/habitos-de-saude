import streamlit as st
import pandas as pd
import plotly.graph_objects as go
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

MESES_PT = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
            7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
MESES_PT_FULL = {1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",5:"Maio",6:"Junho",
                 7:"Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro"}

DATA_INICIO_2026 = pd.Timestamp("2026-03-25")


def x_labels_semanal(dates):
    return [f"{d.day:02d}/{MESES_PT[d.month]}" for d in dates]


def x_labels_mensal(dates):
    return [f"{MESES_PT[d.month]}/{d.year}" for d in dates]


def filtrar_df(df, periodo, visao, col="peso_kg"):
    if "2026" in periodo:
        df = df[df["date"] >= DATA_INICIO_2026].copy()
    else:
        df = df.copy()
    if visao == "Mensal":
        df["ym"] = df["date"].dt.to_period("M")
        df = df.groupby("ym").agg({c: "last" for c in df.columns if c not in ["ym","date"]}
                                   | {"date": "last"}).reset_index(drop=True)
    return df


st.markdown("## 📊 Bioimpedância Semanal")
st.caption("Medição realizada toda terça-feira · Dispositivo: Smartwatch Ultra")

bio_list = load_bioimpedance()
if not bio_list:
    st.warning("Nenhuma medição registrada ainda.")
    st.stop()

bio_sorted = sorted(bio_list, key=lambda x: x["date"])
df_full = pd.DataFrame(bio_sorted)
df_full["date"] = pd.to_datetime(df_full["date"])
df_full["date_str"] = df_full["date"].dt.strftime("%d/%m/%Y")

latest = bio_sorted[-1]
prev   = bio_sorted[-2] if len(bio_sorted) > 1 else latest

# ── Última medição ─────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>📌 Última Medição</div>", unsafe_allow_html=True)
st.caption(f"**{datetime.strptime(latest['date'], '%Y-%m-%d').strftime('%d/%m/%Y')}** · {latest.get('device','—')}")

c1, c2, c3, c4, c5 = st.columns(5)
metrics = [
    ("Peso", f"{latest['peso_kg']:.1f} kg", f"IMC {latest['imc']:.1f}", latest["peso_kg"] - prev["peso_kg"], "", False),
    ("% Gordura", f"{latest['percentual_gordura']:.1f}%", f"{latest['massa_gordura_kg']:.1f} kg", latest["percentual_gordura"] - prev["percentual_gordura"], "%", False),
    ("Músculo Esq.", f"{latest['musculo_esqueletico_kg']:.1f} kg", f"{latest.get('percentual_musculo',0):.1f}%", latest["musculo_esqueletico_kg"] - prev["musculo_esqueletico_kg"], " kg", True),
    ("% Água", f"{latest.get('percentual_agua',0):.1f}%", "Hidratação", latest.get("percentual_agua",0) - prev.get("percentual_agua",0), "%", True),
    ("TMB", f"{latest.get('tmb_kcal',0):,} kcal", f"G. Visceral: {latest.get('gordura_visceral','—')}", latest.get("tmb_kcal",0) - prev.get("tmb_kcal",0), " kcal", True),
]
for col_w, (title, val, sub, delta, unit, hib) in zip([c1,c2,c3,c4,c5], metrics):
    with col_w:
        if delta != 0:
            sym = "▲" if delta > 0 else "▼"
            good = (delta > 0) == hib
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

# ── Controles de período e visualização ─────────────────────────────────────
st.markdown("<div class='section-header'>📈 Evolução Temporal</div>", unsafe_allow_html=True)

ctrl1, ctrl2 = st.columns(2)
with ctrl1:
    periodo = st.radio("Período:", ["2026 — acompanhamento atual", "Todo o histórico"],
                       horizontal=True, key="periodo_bio")
with ctrl2:
    visao = st.radio("Visualização:", ["Semanal", "Mensal"],
                     horizontal=True, key="visao_bio")

# Filtrar dataframe
if "2026" in periodo:
    df = df_full[df_full["date"] >= DATA_INICIO_2026].copy()
else:
    df = df_full.copy()

if visao == "Mensal":
    df["ym"] = df["date"].dt.to_period("M")
    num_cols = [c for c in df.columns if df[c].dtype in ["float64","int64"] and c not in ["id"]]
    agg_dict = {c: "last" for c in num_cols}
    agg_dict["date"] = "last"
    df = df.groupby("ym").agg(agg_dict).reset_index(drop=True)

x_dates = df["date"].tolist()
if visao == "Mensal":
    tick_labels = x_labels_mensal(x_dates)
else:
    tick_labels = x_labels_semanal(x_dates)

def make_chart(y_col, title, color, ref_line=None, ref_label="", height=300, fill=True):
    y = df[y_col].tolist()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_dates, y=y,
        mode="lines+markers+text",
        text=[f"{v:.1f}" for v in y],
        textposition="top center",
        line=dict(color=color, width=3),
        marker=dict(size=8, color=color),
        fill="tozeroy" if fill else "none",
        fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.07)" if fill else None,
        hovertemplate="%{text}<extra></extra>"
    ))
    if ref_line is not None:
        fig.add_hline(y=ref_line, line_dash="dash", line_color="#F39C12",
                      annotation_text=ref_label, annotation_position="right")
    y_pad = (max(y) - min(y)) * 0.3 if len(y) > 1 else 2
    fig.update_layout(
        height=height, title=title, plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=0, r=80, t=40, b=50),
        xaxis=dict(showgrid=False, tickvals=x_dates, ticktext=tick_labels,
                   tickangle=-35, tickfont=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor="#eee",
                   range=[min(y)-y_pad, max(y)+y_pad+1] if y else [0,100]),
        showlegend=False
    )
    return fig

# ── Tabs de gráficos ─────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["⚖️ Peso & IMC", "🔥 Composição Corporal", "💪 Músculo & Água", "🫀 TMB & Visceral"])

with tab1:
    st.plotly_chart(make_chart("peso_kg", "Peso Corporal (kg)", "#1E8449", 82, "Meta: 82 kg"), use_container_width=True)

    # IMC com zonas coloridas
    y_imc = df["imc"].tolist()
    fig2 = go.Figure()
    fig2.add_hrect(y0=18.5, y1=25, fillcolor="rgba(39,174,96,0.1)", line_width=0)
    fig2.add_hrect(y0=25,   y1=30, fillcolor="rgba(243,156,18,0.1)", line_width=0)
    fig2.add_hrect(y0=30,   y1=40, fillcolor="rgba(231,76,60,0.1)",  line_width=0)
    fig2.add_trace(go.Scatter(
        x=x_dates, y=y_imc, mode="lines+markers+text",
        text=[f"{v:.1f}" for v in y_imc], textposition="top center",
        line=dict(color="#8E44AD", width=3), marker=dict(size=8)
    ))
    fig2.add_hline(y=25, line_dash="dash", line_color="#27AE60", annotation_text="IMC Normal < 25", annotation_position="right")
    y_pad2 = (max(y_imc) - min(y_imc)) * 0.3 if len(y_imc) > 1 else 1
    fig2.update_layout(
        height=280, title="Índice de Massa Corporal (IMC)", plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=0, r=100, t=40, b=50), showlegend=False,
        xaxis=dict(showgrid=False, tickvals=x_dates, ticktext=tick_labels, tickangle=-35, tickfont=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor="#eee", range=[min(y_imc)-y_pad2, max(y_imc)+y_pad2+0.5])
    )
    st.plotly_chart(fig2, use_container_width=True)

with tab2:
    st.plotly_chart(make_chart("percentual_gordura", "Percentual de Gordura Corporal (%)", "#E74C3C", 20, "Meta: 20%"), use_container_width=True)

    # Barras gordura vs músculo
    y_gord = df["massa_gordura_kg"].tolist()
    y_musc = df["musculo_esqueletico_kg"].tolist()
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=x_dates, y=y_gord, name="Gordura (kg)", marker_color="#E74C3C", opacity=0.8))
    fig2.add_trace(go.Bar(x=x_dates, y=y_musc, name="Músculo (kg)", marker_color="#2980B9", opacity=0.8))
    fig2.update_layout(
        height=280, title="Gordura vs. Músculo (kg)", barmode="group",
        plot_bgcolor="white", paper_bgcolor="white", margin=dict(l=0, r=10, t=40, b=50),
        xaxis=dict(showgrid=False, tickvals=x_dates, ticktext=tick_labels, tickangle=-35, tickfont=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor="#eee", title="kg"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.35)
    )
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.plotly_chart(make_chart("musculo_esqueletico_kg", "Massa Muscular Esquelética (kg)", "#2980B9", 40, "Meta: 40 kg"), use_container_width=True)
    st.plotly_chart(make_chart("percentual_agua", "Percentual de Água Corporal (%)", "#16A085", 55, "Ref mín.: 55%"), use_container_width=True)

with tab4:
    st.plotly_chart(make_chart("tmb_kcal", "Taxa Metabólica Basal — TMB (kcal)", "#E67E22"), use_container_width=True)

    if "gordura_visceral" in df.columns:
        y_visc = df["gordura_visceral"].tolist()
        colors_visc = ["#E74C3C" if v >= 13 else "#F39C12" if v >= 10 else "#27AE60" for v in y_visc]
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=x_dates, y=y_visc, marker_color=colors_visc,
                               text=[str(v) for v in y_visc], textposition="outside"))
        fig2.add_hline(y=9, line_dash="dash", line_color="#27AE60", annotation_text="Meta: ≤ 9", annotation_position="right")
        fig2.update_layout(
            height=260, title="Gordura Visceral (escala 1–20)", plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=0, r=80, t=40, b=50), showlegend=False,
            xaxis=dict(showgrid=False, tickvals=x_dates, ticktext=tick_labels, tickangle=-35, tickfont=dict(size=11)),
            yaxis=dict(showgrid=True, gridcolor="#eee")
        )
        st.plotly_chart(fig2, use_container_width=True)

# ── Tabela histórica ─────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>📋 Histórico Completo</div>", unsafe_allow_html=True)
df_show = df_full[["date_str","peso_kg","imc","percentual_gordura","massa_gordura_kg",
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
        data_med    = st.date_input("Data", value=date.today())
        peso        = st.number_input("Peso (kg)", 50.0, 200.0, float(latest["peso_kg"]), 0.1)
        imc         = st.number_input("IMC", 15.0, 50.0, float(latest["imc"]), 0.1)
        pct_gordura = st.number_input("% Gordura", 1.0, 60.0, float(latest["percentual_gordura"]), 0.1)
    with col2:
        massa_gordura = st.number_input("Gordura (kg)", 1.0, 100.0, float(latest["massa_gordura_kg"]), 0.1)
        musculo       = st.number_input("Músculo Esq. (kg)", 10.0, 80.0, float(latest["musculo_esqueletico_kg"]), 0.1)
        pct_agua      = st.number_input("% Água", 20.0, 80.0, float(latest.get("percentual_agua", 48)), 0.1)
        pct_musculo   = st.number_input("% Músculo", 10.0, 80.0, float(latest.get("percentual_musculo", 65)), 0.1)
    with col3:
        tmb          = st.number_input("TMB (kcal)", 1000, 4000, int(latest.get("tmb_kcal", 1780)), 1)
        gordura_visc = st.number_input("Gordura Visceral", 1, 30, int(latest.get("gordura_visceral", 10)), 1)
        massa_ossea  = st.number_input("Massa Óssea (kg)", 1.0, 6.0, float(latest.get("massa_ossea_kg", 3.3)), 0.1)
        device       = st.selectbox("Dispositivo", ["Smartwatch Ultra","Balança Bioimpedância","InBody","Heath Pro","Outro"])
    notas = st.text_input("Observações (opcional)")
    submitted = st.form_submit_button("💾 Salvar Medição", type="primary")

if submitted:
    new_id = max([b.get("id", 0) for b in bio_list], default=0) + 1
    new_entry = {
        "id": new_id, "date": str(data_med),
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
