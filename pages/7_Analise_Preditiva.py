import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import date, datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_manager import load_bioimpedance, load_exams, load_exercises

st.set_page_config(page_title="Análise Preditiva", page_icon="🔮", layout="wide")

st.markdown("""
<style>
.section-header{font-size:22px;font-weight:700;color:#7B2FBE;border-bottom:3px solid #7B2FBE;padding-bottom:8px;margin:20px 0 16px}
.kpi-box{background:linear-gradient(135deg,#f5f0ff,#ede0ff);border:1px solid #9B59B6;border-radius:12px;padding:14px;text-align:center;margin:4px}
.kpi-box-adj{background:linear-gradient(135deg,#f0fff4,#dcfce7);border:1px solid #27AE60;border-radius:12px;padding:14px;text-align:center;margin:4px}
.proj-good{background:#f0fff4;border-left:4px solid #27AE60;padding:10px 14px;border-radius:0 8px 8px 0;margin:6px 0;font-size:13px}
.proj-warn{background:#fffbf0;border-left:4px solid #F39C12;padding:10px 14px;border-radius:0 8px 8px 0;margin:6px 0;font-size:13px}
.proj-alert{background:#fff5f5;border-left:4px solid #E74C3C;padding:10px 14px;border-radius:0 8px 8px 0;margin:6px 0;font-size:13px}
.proj-scenario{background:#f0f8ff;border-left:4px solid #2980B9;padding:10px 14px;border-radius:0 8px 8px 0;margin:6px 0;font-size:13px}
.timeline-item{padding:8px 14px;border-left:3px solid #9B59B6;margin:6px 0;background:#faf5ff;border-radius:0 8px 8px 0;font-size:13px}
.scenario-box{background:linear-gradient(135deg,#e8f5e9,#f0fff4);border:2px solid #27AE60;border-radius:12px;padding:14px;margin:10px 0}
</style>
""", unsafe_allow_html=True)

st.markdown("## 🔮 Análise Preditiva")
st.caption("Projeções baseadas nos seus dados históricos e evidências médicas. As datas são estimativas — não substituem avaliação médica.")

# ── Carregar dados ──────────────────────────────────────────────────────────────
bio_list   = sorted(load_bioimpedance(), key=lambda x: x["date"])
exams_data = load_exams()
ex_list    = load_exercises()

if len(bio_list) < 3:
    st.warning("Dados insuficientes para projeções. Adicione mais medições de bioimpedância.")
    st.stop()

REF_DATE = datetime(2026, 1, 1)
TODAY    = datetime.now()
TODAY_X  = (TODAY - REF_DATE).days

# Marco do Puran T4 (levotiroxina) — usado apenas como anotação nos gráficos
PURAN_T4_DATE = "2026-06-01"

# Regressão desde o início do acompanhamento semanal sistemático (mar/2026)
# Inclui toda a perda de peso real (dieta + exercício + Puran T4)
TRACKING_START = "2026-03-25"
bio_recente = [b for b in bio_list if b["date"] >= TRACKING_START]
if len(bio_recente) < 3:
    bio_recente = bio_list  # fallback

# Medições antigas (antes do acompanhamento semanal) — apenas contexto nos gráficos
bio_historico = [b for b in bio_list if b["date"] < TRACKING_START]

# ── Frequência e gasto calórico reais (últimos 60 dias) ───────────────────────
_cutoff60 = (TODAY - timedelta(days=60)).strftime("%Y-%m-%d")
_ex60     = [e for e in ex_list if e.get("date", "") >= _cutoff60]
_dias_treino = len({e["date"] for e in _ex60})
freq_real  = round(_dias_treino / (60 / 7), 1)          # sessões/semana (float)
freq_real_slider = max(3, min(7, round(freq_real)))      # valor para o slider
_kcal_vals = [e["calories_burned"] for e in _ex60 if e.get("calories_burned", 0) > 50]
kcal_real  = max(200, min(700, int(sum(_kcal_vals) / len(_kcal_vals)))) if _kcal_vals else 420

x_dias   = [(datetime.strptime(b["date"], "%Y-%m-%d") - REF_DATE).days for b in bio_recente]
pesos    = [b["peso_kg"] for b in bio_recente]
gorduras = [b.get("percentual_gordura", 0) for b in bio_recente]
musculos = [b.get("musculo_esqueletico_kg", 0) for b in bio_recente]

# Regressão linear atual (todos os dados = projeção recalibrada)
coef_peso = np.polyfit(x_dias, pesos, 1)
coef_gord = np.polyfit(x_dias, gorduras, 1)
coef_musc = np.polyfit(x_dias, musculos, 1)

# ── Predição original (primeiro terço dos dados — escala com o histórico) ──────
# Mínimo de 6 medições (~6 semanas) para superar a fase inicial de adaptação
# hídrica e capturar a tendência metabólica real.
N_BASE = max(6, len(bio_recente) // 3)
x_base   = x_dias[:N_BASE]
coef_peso_orig = np.polyfit(x_base, pesos[:N_BASE], 1)
coef_gord_orig = np.polyfit(x_base, gorduras[:N_BASE], 1)
coef_musc_orig = np.polyfit(x_base, musculos[:N_BASE], 1)

# Calcula desvio de cada medição em relação à predição original
desvios_peso = []
desvios_gord = []
desvios_musc = []
hist_datas_dev = []
for i, (b, xd) in enumerate(zip(bio_recente, x_dias)):
    if i < N_BASE:
        continue
    pred_p = float(np.polyval(coef_peso_orig, xd))
    pred_g = float(np.polyval(coef_gord_orig, xd))
    pred_m = float(np.polyval(coef_musc_orig, xd))
    desvios_peso.append(b["peso_kg"] - pred_p)
    desvios_gord.append(b.get("percentual_gordura", 0) - pred_g)
    desvios_musc.append(b.get("musculo_esqueletico_kg", 0) - pred_m)
    hist_datas_dev.append(datetime.strptime(b["date"], "%Y-%m-%d"))

peso_atual = bio_recente[-1]["peso_kg"]
gord_atual = bio_recente[-1].get("percentual_gordura", 0)
musc_atual = bio_recente[-1].get("musculo_esqueletico_kg", 0)

# Taxas semanais da linha de base (3x/semana)
taxa_peso_sem = coef_peso[0] * 7
taxa_gord_sem = coef_gord[0] * 7
taxa_musc_sem = coef_musc[0] * 7

PESO_META = 82.0
GORD_META = 22.0
MUSC_META = 40.0

# Ponto projetado hoje (pelo modelo recalibrado)
val_hoje_peso = float(np.polyval(coef_peso, TODAY_X))
val_hoje_gord = float(np.polyval(coef_gord, TODAY_X))
val_hoje_musc = float(np.polyval(coef_musc, TODAY_X))

# Ponto previsto hoje (pela predição original)
pred_hoje_peso = float(np.polyval(coef_peso_orig, TODAY_X))
pred_hoje_gord = float(np.polyval(coef_gord_orig, TODAY_X))
pred_hoje_musc = float(np.polyval(coef_musc_orig, TODAY_X))

# Status vs predição original
def _status_desvio(desvio, metrica):
    """Retorna (emoji, texto, cor) para o desvio em relação à predição."""
    if metrica == "peso" or metrica == "gord":
        # Para peso e gordura: negativo é melhor (perdendo mais)
        if desvio < -0.5:
            return "🚀", "Superando a predição", "#27AE60"
        elif desvio < 0.2:
            return "✅", "No ritmo previsto", "#2980B9"
        elif desvio < 1.0:
            return "⚠️", "Levemente atrás", "#F39C12"
        else:
            return "🔴", "Abaixo do esperado", "#E74C3C"
    else:
        # Para músculo: positivo é melhor (ganhando mais)
        if desvio > 0.3:
            return "🚀", "Superando a predição", "#27AE60"
        elif desvio > -0.1:
            return "✅", "No ritmo previsto", "#2980B9"
        elif desvio > -0.5:
            return "⚠️", "Levemente atrás", "#F39C12"
        else:
            return "🔴", "Abaixo do esperado", "#E74C3C"

# ── Painel de Alertas vs Predição ─────────────────────────────────────────────
if desvios_peso:
    dev_peso_atual = peso_atual - pred_hoje_peso
    dev_gord_atual = gord_atual - pred_hoje_gord
    dev_musc_atual = musc_atual - pred_hoje_musc

    emoji_p, txt_p, cor_p = _status_desvio(dev_peso_atual, "peso")
    emoji_g, txt_g, cor_g = _status_desvio(dev_gord_atual, "gord")
    emoji_m, txt_m, cor_m = _status_desvio(dev_musc_atual, "musc")

    st.markdown("<div class='section-header'>📡 Acompanhamento vs Predição Original</div>", unsafe_allow_html=True)
    a1, a2, a3 = st.columns(3)
    with a1:
        sinal = "+" if dev_peso_atual > 0 else ""
        st.markdown(f"""<div style='background:#f8f8f8;border-left:5px solid {cor_p};border-radius:8px;padding:14px;'>
<div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>Peso — vs Predição</div>
<div style='font-size:28px;font-weight:700;color:{cor_p}'>{emoji_p} {sinal}{dev_peso_atual:+.1f} kg</div>
<div style='font-size:13px;color:{cor_p};font-weight:600'>{txt_p}</div>
<div style='font-size:12px;color:#888;margin-top:4px'>Previsto hoje: {pred_hoje_peso:.1f} kg · Real: {peso_atual:.1f} kg</div>
</div>""", unsafe_allow_html=True)
    with a2:
        sinal = "+" if dev_gord_atual > 0 else ""
        st.markdown(f"""<div style='background:#f8f8f8;border-left:5px solid {cor_g};border-radius:8px;padding:14px;'>
<div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>Gordura — vs Predição</div>
<div style='font-size:28px;font-weight:700;color:{cor_g}'>{emoji_g} {dev_gord_atual:+.1f}%</div>
<div style='font-size:13px;color:{cor_g};font-weight:600'>{txt_g}</div>
<div style='font-size:12px;color:#888;margin-top:4px'>Previsto hoje: {pred_hoje_gord:.1f}% · Real: {gord_atual:.1f}%</div>
</div>""", unsafe_allow_html=True)
    with a3:
        st.markdown(f"""<div style='background:#f8f8f8;border-left:5px solid {cor_m};border-radius:8px;padding:14px;'>
<div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>Músculo — vs Predição</div>
<div style='font-size:28px;font-weight:700;color:{cor_m}'>{emoji_m} {dev_musc_atual:+.1f} kg</div>
<div style='font-size:13px;color:{cor_m};font-weight:600'>{txt_m}</div>
<div style='font-size:12px;color:#888;margin-top:4px'>Previsto hoje: {pred_hoje_musc:.1f} kg · Real: {musc_atual:.1f} kg</div>
</div>""", unsafe_allow_html=True)
    st.caption(f"Predição original calculada com os {N_BASE} primeiros registros do acompanhamento semanal (mar/2026). A projeção é recalibrada com todos os dados desde então, incluindo o período pós-Puran T4.")
    st.markdown("")

# ── Configurador de Cenário de Treino ─────────────────────────────────────────
st.markdown("<div class='section-header'>⚙️ Simular Frequência de Treino</div>", unsafe_allow_html=True)

c_s1, c_s2, c_s3 = st.columns([3, 2, 3])
with c_s1:
    freq_treino = st.select_slider(
        "Treinos por semana:",
        options=[3, 4, 5, 6, 7],
        value=freq_real_slider,
        format_func=lambda x: f"{x}x/semana",
        key="freq_treino_slider",
        help=f"Frequência calculada do seu histórico (60 dias): {freq_real:.1f}x/sem. Ajuste para simular cenários."
    )
with c_s2:
    kcal_por_sessao = st.number_input(
        "Kcal por treino:",
        min_value=200, max_value=700, value=kcal_real, step=10,
        key="kcal_sessao_input",
        help=f"Média real dos seus treinos recentes: {kcal_real} kcal/sessão"
    )

# Cálculo do ajuste de cenário
KCAL_POR_KG_GORDURA = 7700  # kcal necessárias para perder 1 kg de gordura
extra_sessoes = freq_treino - freq_real  # delta em relação à frequência real

# Impacto extra semanal (adicional ao baseline de 3x/sem)
extra_kcal_sem   = extra_sessoes * kcal_por_sessao
extra_peso_sem   = extra_kcal_sem / KCAL_POR_KG_GORDURA          # kg/semana a mais
extra_gord_sem   = extra_sessoes * 0.04                            # pp/semana a mais (gordura %)
extra_musc_sem   = min(extra_sessoes * 0.012, 0.048)              # kg/semana a mais (limite fisiológico)

# Taxas ajustadas para o cenário
taxa_peso_aj = taxa_peso_sem - extra_peso_sem   # mais negativo = mais perda
taxa_gord_aj = taxa_gord_sem - extra_gord_sem
taxa_musc_aj = taxa_musc_sem + extra_musc_sem

# Slopes ajustados por dia (para projeção)
adj_slope_peso = -extra_peso_sem / 7
adj_slope_gord = -extra_gord_sem / 7
adj_slope_musc = +extra_musc_sem / 7

with c_s3:
    if extra_sessoes == 0:
        st.info(f"📊 **Cenário atual** — frequência real calculada: {freq_real:.1f}x/semana (últimos 60 dias).")
    else:
        extra_kg_mes = extra_peso_sem * 4.3
        st.markdown(f"""<div class='scenario-box'>
<b>✅ Cenário: {freq_treino}x/semana</b><br>
{extra_sessoes:+.1f} treino(s)/sem = <b>{extra_kcal_sem:+.0f} kcal/sem</b> gastas<br>
→ <b>~{extra_kg_mes:+.2f} kg</b> de perda por mês em relação ao ritmo atual
</div>""", unsafe_allow_html=True)

# Dados para gráficos
proj_x      = list(range(TODAY_X, TODAY_X + 40 * 7, 7))
proj_datas  = [REF_DATE + timedelta(days=d) for d in proj_x]

# Projeções baseline (3x/sem)
proj_pesos    = [float(np.polyval(coef_peso, d)) for d in proj_x]
proj_gorduras = [float(np.polyval(coef_gord, d)) for d in proj_x]
proj_musculos = [float(np.polyval(coef_musc, d)) for d in proj_x]

# Projeções ajustadas (cenário Xx/sem) — partem do valor de hoje projetado pelo modelo
proj_pesos_aj    = [val_hoje_peso + (coef_peso[0] + adj_slope_peso) * (d - TODAY_X) for d in proj_x]
proj_gorduras_aj = [val_hoje_gord + (coef_gord[0] + adj_slope_gord) * (d - TODAY_X) for d in proj_x]
proj_musculos_aj = [val_hoje_musc + (coef_musc[0] + adj_slope_musc) * (d - TODAY_X) for d in proj_x]

# Linha de tendência sobre histórico
trend_x     = list(range(x_dias[0], TODAY_X + 1))
trend_datas = [REF_DATE + timedelta(days=d) for d in trend_x]
hist_datas  = [datetime.strptime(b["date"], "%Y-%m-%d") for b in bio_recente]

# Datas de meta — baseline
if coef_peso[0] < 0:
    d_falta = (PESO_META - val_hoje_peso) / coef_peso[0]
    dt_peso = (TODAY + timedelta(days=int(d_falta))).date() if d_falta > 0 else None
    dias_peso_falta = d_falta
else:
    dt_peso, dias_peso_falta = None, None

if coef_gord[0] < 0:
    d_falta = (GORD_META - val_hoje_gord) / coef_gord[0]
    dt_gord = (TODAY + timedelta(days=int(d_falta))).date() if d_falta > 0 else None
else:
    dt_gord = None

if coef_musc[0] > 0:
    d_falta = (MUSC_META - val_hoje_musc) / coef_musc[0]
    dt_musc = (TODAY + timedelta(days=int(d_falta))).date() if d_falta > 0 else None
    dias_musc_falta = d_falta
else:
    dt_musc, dias_musc_falta = None, None

# Datas de meta — cenário ajustado
slope_peso_aj_dia = coef_peso[0] + adj_slope_peso
slope_gord_aj_dia = coef_gord[0] + adj_slope_gord
slope_musc_aj_dia = coef_musc[0] + adj_slope_musc

if slope_peso_aj_dia < 0:
    d_aj = (PESO_META - val_hoje_peso) / slope_peso_aj_dia
    dt_peso_aj = (TODAY + timedelta(days=int(d_aj))).date() if d_aj > 0 else None
    dias_peso_aj = d_aj
else:
    dt_peso_aj, dias_peso_aj = None, None

if slope_gord_aj_dia < 0:
    d_aj = (GORD_META - val_hoje_gord) / slope_gord_aj_dia
    dt_gord_aj = (TODAY + timedelta(days=int(d_aj))).date() if d_aj > 0 else None
else:
    dt_gord_aj = None

if slope_musc_aj_dia > 0:
    d_aj = (MUSC_META - val_hoje_musc) / slope_musc_aj_dia
    dt_musc_aj = (TODAY + timedelta(days=int(d_aj))).date() if d_aj > 0 else None
    dias_musc_aj = d_aj
else:
    dt_musc_aj, dias_musc_aj = None, None

# Escolhe quais valores mostrar nos KPIs (ajustado quando freq > 3)
usar_aj = extra_sessoes > 0
taxa_peso_kpi = taxa_peso_aj if usar_aj else taxa_peso_sem
taxa_gord_kpi = taxa_gord_aj if usar_aj else taxa_gord_sem
taxa_musc_kpi = taxa_musc_aj if usar_aj else taxa_musc_sem
dt_peso_kpi   = dt_peso_aj   if usar_aj else dt_peso
dias_peso_kpi = dias_peso_aj if usar_aj else dias_peso_falta

# ── KPIs ──────────────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>📊 Ritmo Projetado</div>", unsafe_allow_html=True)
kpi_class = "kpi-box-adj" if usar_aj else "kpi-box"
if usar_aj:
    st.caption(f"Valores para o cenário de **{freq_treino}x/semana** (linha verde nos gráficos)")

c1, c2, c3, c4 = st.columns(4)

with c1:
    cor = "#27AE60" if taxa_peso_kpi < 0 else "#E74C3C"
    seta = "↓" if taxa_peso_kpi < 0 else "↑"
    st.markdown(f"""<div class='{kpi_class}'>
<div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>Perda de Peso</div>
<div style='font-size:32px;font-weight:700;color:{cor}'>{seta} {abs(taxa_peso_kpi):.2f}</div>
<div style='font-size:12px;color:#888'>kg/semana</div>
<div style='font-size:12px;color:{cor};font-weight:600'>{abs(taxa_peso_kpi*4.3):.1f} kg/mês</div>
</div>""", unsafe_allow_html=True)

with c2:
    cor2 = "#27AE60" if taxa_gord_kpi < 0 else "#E74C3C"
    seta2 = "↓" if taxa_gord_kpi < 0 else "↑"
    st.markdown(f"""<div class='{kpi_class}'>
<div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>Gordura Corporal</div>
<div style='font-size:32px;font-weight:700;color:{cor2}'>{seta2} {abs(taxa_gord_kpi):.2f}</div>
<div style='font-size:12px;color:#888'>%/semana</div>
<div style='font-size:12px;color:{cor2};font-weight:600'>Atual: {gord_atual:.1f}%</div>
</div>""", unsafe_allow_html=True)

with c3:
    cor3 = "#27AE60" if taxa_musc_kpi > 0 else "#F39C12"
    seta3 = "↑" if taxa_musc_kpi > 0 else "→"
    st.markdown(f"""<div class='{kpi_class}'>
<div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>Ganho Muscular</div>
<div style='font-size:32px;font-weight:700;color:{cor3}'>{seta3} {abs(taxa_musc_kpi):.3f}</div>
<div style='font-size:12px;color:#888'>kg/semana</div>
<div style='font-size:12px;color:{cor3};font-weight:600'>+{taxa_musc_kpi*4.3:.2f} kg/mês</div>
</div>""", unsafe_allow_html=True)

with c4:
    if dt_peso_kpi:
        meses = int(dias_peso_kpi / 30)
        st.markdown(f"""<div class='{kpi_class}'>
<div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>Meta 82 kg</div>
<div style='font-size:24px;font-weight:700;color:#7B2FBE'>{dt_peso_kpi.strftime('%b/%Y')}</div>
<div style='font-size:12px;color:#888'>em ~{meses} meses</div>
<div style='font-size:12px;color:#7B2FBE;font-weight:600'>Faltam {peso_atual - PESO_META:.1f} kg</div>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class='{kpi_class}'>
<div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>Meta 82 kg</div>
<div style='font-size:22px;font-weight:700;color:#E74C3C'>Sem tendência</div>
<div style='font-size:12px;color:#888'>Ajustar dieta/treino</div>
</div>""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["⚖️ Peso & Gordura", "💪 Músculo", "🧪 Exames Laboratoriais"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: PESO & GORDURA
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    col_g, col_r = st.columns([3, 1])
    with col_g:
        # Gráfico de peso
        fig_peso = go.Figure()
        if bio_historico:
            _h_datas = [datetime.strptime(b["date"], "%Y-%m-%d") for b in bio_historico]
            _h_pesos = [b["peso_kg"] for b in bio_historico]
            fig_peso.add_trace(go.Scatter(
                x=_h_datas, y=_h_pesos, name="Histórico pré-Puran T4",
                mode="lines+markers", opacity=0.35,
                line=dict(color="#95A5A6", width=1.5, dash="dot"),
                marker=dict(size=5, color="#95A5A6"),
            ))
        fig_peso.add_trace(go.Scatter(
            x=hist_datas, y=pesos, name="Peso real (pós-Puran T4)",
            mode="lines+markers",
            line=dict(color="#2980B9", width=2.5),
            marker=dict(size=7, color="#2980B9"),
        ))
        fig_peso.add_trace(go.Scatter(
            x=trend_datas,
            y=[float(np.polyval(coef_peso, d)) for d in trend_x],
            name="Tendência recalibrada",
            mode="lines",
            line=dict(color="#27AE60", width=1.5, dash="dot"),
        ))
        fig_peso.add_trace(go.Scatter(
            x=trend_datas,
            y=[float(np.polyval(coef_peso_orig, d)) for d in trend_x],
            name="Predição original",
            mode="lines",
            line=dict(color="#E67E22", width=1.5, dash="dashdot"),
        ))
        fig_peso.add_trace(go.Scatter(
            x=proj_datas, y=proj_pesos, name=f"Projeção {freq_real_slider}x/sem (atual)",
            mode="lines",
            line=dict(color="#9B59B6", width=2, dash="dash"),
        ))
        if usar_aj:
            fig_peso.add_trace(go.Scatter(
                x=proj_datas, y=proj_pesos_aj,
                name=f"Projeção {freq_treino}x/sem",
                mode="lines",
                line=dict(color="#27AE60", width=2.5, dash="longdash"),
            ))
        fig_peso.add_hline(y=PESO_META, line_dash="dot", line_color="#E74C3C", line_width=1.5,
                           annotation_text="Meta: 82 kg", annotation_position="right")
        if dt_peso:
            fig_peso.add_vline(
                x=pd.Timestamp(dt_peso).value // 10**6,
                line_dash="dot", line_color="#9B59B6", line_width=1,
                annotation_text=f"3x: {dt_peso.strftime('%m/%Y')}", annotation_position="top right",
            )
        if usar_aj and dt_peso_aj:
            fig_peso.add_vline(
                x=pd.Timestamp(dt_peso_aj).value // 10**6,
                line_dash="dot", line_color="#27AE60", line_width=1.5,
                annotation_text=f"{freq_treino}x: {dt_peso_aj.strftime('%m/%Y')}", annotation_position="top left",
            )
        fig_peso.add_vline(
            x=pd.Timestamp(PURAN_T4_DATE).value // 10**6,
            line_dash="dashdot", line_color="#8E44AD", line_width=1.2,
            annotation_text="Puran T4", annotation_position="bottom right",
        )
        fig_peso.update_layout(
            title=f"Projeção de Peso" + (f" — Comparativo {freq_real_slider}x vs {freq_treino}x/semana" if usar_aj else ""),
            height=360, plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=False, automargin=True, tickangle=-15, tickformat="%b/%y"),
            yaxis=dict(showgrid=True, gridcolor="#eee", title="kg", automargin=True,
                       range=[79, max(pesos) + 2]),
            legend=dict(orientation="h", yanchor="bottom", y=-0.32),
            margin=dict(l=50, r=150, t=60, b=80),
        )
        st.plotly_chart(fig_peso, use_container_width=True, key="pred_peso")

        # Gráfico de gordura
        fig_gord = go.Figure()
        if bio_historico:
            _h_gords = [b.get("percentual_gordura", 0) for b in bio_historico]
            fig_gord.add_trace(go.Scatter(
                x=_h_datas, y=_h_gords, name="Histórico pré-Puran T4",
                mode="lines+markers", opacity=0.35,
                line=dict(color="#95A5A6", width=1.5, dash="dot"),
                marker=dict(size=5, color="#95A5A6"),
            ))
        fig_gord.add_trace(go.Scatter(
            x=hist_datas, y=gorduras, name="Gordura real (pós-Puran T4)",
            mode="lines+markers",
            line=dict(color="#E74C3C", width=2.5), marker=dict(size=7),
        ))
        fig_gord.add_trace(go.Scatter(
            x=trend_datas,
            y=[float(np.polyval(coef_gord_orig, d)) for d in trend_x],
            name="Predição original",
            mode="lines",
            line=dict(color="#E67E22", width=1.5, dash="dashdot"),
        ))
        fig_gord.add_trace(go.Scatter(
            x=proj_datas, y=proj_gorduras, name=f"Projeção {freq_real_slider}x/sem (atual)",
            mode="lines",
            line=dict(color="#9B59B6", width=2, dash="dash"),
        ))
        if usar_aj:
            fig_gord.add_trace(go.Scatter(
                x=proj_datas, y=proj_gorduras_aj,
                name=f"Projeção {freq_treino}x/sem",
                mode="lines",
                line=dict(color="#27AE60", width=2.5, dash="longdash"),
            ))
        fig_gord.add_hline(y=GORD_META, line_dash="dot", line_color="#27AE60", line_width=1.5,
                           annotation_text=f"Meta: {GORD_META}%", annotation_position="right")
        if dt_gord:
            fig_gord.add_vline(
                x=pd.Timestamp(dt_gord).value // 10**6,
                line_dash="dot", line_color="#9B59B6", line_width=1,
                annotation_text=f"3x: {dt_gord.strftime('%m/%Y')}", annotation_position="top right",
            )
        if usar_aj and dt_gord_aj:
            fig_gord.add_vline(
                x=pd.Timestamp(dt_gord_aj).value // 10**6,
                line_dash="dot", line_color="#27AE60", line_width=1.5,
                annotation_text=f"{freq_treino}x: {dt_gord_aj.strftime('%m/%Y')}", annotation_position="top left",
            )
        fig_gord.update_layout(
            title="Projeção de Gordura Corporal (%)",
            height=300, plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=False, automargin=True, tickangle=-15, tickformat="%b/%y"),
            yaxis=dict(showgrid=True, gridcolor="#eee", title="%", automargin=True),
            legend=dict(orientation="h", yanchor="bottom", y=-0.36),
            margin=dict(l=50, r=150, t=50, b=80),
        )
        st.plotly_chart(fig_gord, use_container_width=True, key="pred_gord")

    with col_r:
        st.markdown("**📋 Projeções**")
        falta_peso = peso_atual - PESO_META
        falta_gord = gord_atual - GORD_META

        # Cenário baseline
        if dt_peso:
            meses_b = int(dias_peso_falta / 30)
            st.markdown(
                f"<div class='proj-warn'><b>⚖️ {freq_real_slider}x/sem (atual) — Meta 82 kg</b><br>"
                f"Chegará em <b>{dt_peso.strftime('%d/%m/%Y')}</b><br>"
                f"~{meses_b} meses · {taxa_peso_sem:.2f} kg/sem</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='proj-alert'><b>⚖️ Meta 82 kg</b><br>"
                f"Faltam {falta_peso:.1f} kg<br>"
                f"Tendência não alcança a meta</div>",
                unsafe_allow_html=True,
            )

        # Cenário ajustado
        if usar_aj:
            if dt_peso_aj:
                meses_aj = int(dias_peso_aj / 30)
                acelerou = (int(dias_peso_falta) - int(dias_peso_aj)) if dt_peso and dt_peso_aj else 0
                st.markdown(
                    f"<div class='proj-scenario'><b>✅ {freq_treino}x/sem — Meta 82 kg</b><br>"
                    f"Chegará em <b>{dt_peso_aj.strftime('%d/%m/%Y')}</b><br>"
                    f"~{meses_aj} meses · {taxa_peso_aj:.2f} kg/sem<br>"
                    + (f"<span style='color:#27AE60;font-weight:700'>⚡ {acelerou} dias mais rápido!</span>" if acelerou > 0 else "")
                    + "</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div class='proj-alert'><b>{freq_treino}x/sem — Meta 82 kg</b><br>"
                    f"Tendência não alcança a meta</div>",
                    unsafe_allow_html=True,
                )

        # Gordura
        if dt_gord:
            st.markdown(
                f"<div class='proj-good'><b>🔴 Meta &lt;{GORD_META}% gordura</b><br>"
                f"Chegará em <b>{dt_gord.strftime('%d/%m/%Y')}</b><br>"
                f"ao ritmo {taxa_gord_sem:.2f}%/sem</div>",
                unsafe_allow_html=True,
            )

        # vs melhor 2025
        bio_2025 = [b for b in bio_list if "2025" in b["date"]]
        if bio_2025:
            melhor_2025 = min(b["peso_kg"] for b in bio_2025)
            variacao = peso_atual - melhor_2025
            cor_var = "#27AE60" if variacao < 0 else "#E74C3C"
            st.markdown(
                f"<div style='background:#f0f4ff;border-radius:8px;padding:10px;margin-top:8px;font-size:13px'>"
                f"<b>📅 vs. melhor peso 2025:</b><br>"
                f"{melhor_2025:.1f} kg → {peso_atual:.1f} kg<br>"
                f"<span style='color:{cor_var};font-weight:700'>{variacao:+.1f} kg</span></div>",
                unsafe_allow_html=True,
            )

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: MÚSCULO
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    col_mg, col_mr = st.columns([3, 1])
    with col_mg:
        fig_musc = go.Figure()
        if bio_historico:
            _h_muscs = [b.get("musculo_esqueletico_kg", 0) for b in bio_historico]
            fig_musc.add_trace(go.Scatter(
                x=_h_datas, y=_h_muscs, name="Histórico pré-Puran T4",
                mode="lines+markers", opacity=0.35,
                line=dict(color="#95A5A6", width=1.5, dash="dot"),
                marker=dict(size=5, color="#95A5A6"),
            ))
        fig_musc.add_trace(go.Scatter(
            x=hist_datas, y=musculos, name="Músculo real (pós-Puran T4)",
            mode="lines+markers",
            line=dict(color="#27AE60", width=2.5), marker=dict(size=7),
        ))
        fig_musc.add_trace(go.Scatter(
            x=trend_datas,
            y=[float(np.polyval(coef_musc, d)) for d in trend_x],
            name="Tendência recalibrada",
            mode="lines",
            line=dict(color="#1ABC9C", width=1.5, dash="dot"),
        ))
        fig_musc.add_trace(go.Scatter(
            x=trend_datas,
            y=[float(np.polyval(coef_musc_orig, d)) for d in trend_x],
            name="Predição original",
            mode="lines",
            line=dict(color="#E67E22", width=1.5, dash="dashdot"),
        ))
        fig_musc.add_trace(go.Scatter(
            x=proj_datas, y=proj_musculos, name=f"Projeção {freq_real_slider}x/sem (atual)",
            mode="lines",
            line=dict(color="#9B59B6", width=2, dash="dash"),
        ))
        if usar_aj:
            fig_musc.add_trace(go.Scatter(
                x=proj_datas, y=proj_musculos_aj,
                name=f"Projeção {freq_treino}x/sem",
                mode="lines",
                line=dict(color="#F39C12", width=2.5, dash="longdash"),
            ))
        fig_musc.add_hline(y=MUSC_META, line_dash="dot", line_color="#F39C12", line_width=1.5,
                           annotation_text=f"Meta: {MUSC_META} kg", annotation_position="right")
        if dt_musc:
            fig_musc.add_vline(
                x=pd.Timestamp(dt_musc).value // 10**6,
                line_dash="dot", line_color="#9B59B6", line_width=1,
                annotation_text=f"3x: {dt_musc.strftime('%m/%Y')}", annotation_position="top right",
            )
        if usar_aj and dt_musc_aj:
            fig_musc.add_vline(
                x=pd.Timestamp(dt_musc_aj).value // 10**6,
                line_dash="dot", line_color="#F39C12", line_width=1.5,
                annotation_text=f"{freq_treino}x: {dt_musc_aj.strftime('%m/%Y')}", annotation_position="top left",
            )
        fig_musc.update_layout(
            title="Projeção de Massa Muscular Esquelética",
            height=380, plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=False, automargin=True, tickangle=-15, tickformat="%b/%y"),
            yaxis=dict(showgrid=True, gridcolor="#eee", title="kg", automargin=True,
                       range=[min(musculos) - 1, max(max(musculos), MUSC_META) + 1]),
            legend=dict(orientation="h", yanchor="bottom", y=-0.32),
            margin=dict(l=50, r=150, t=60, b=80),
        )
        st.plotly_chart(fig_musc, use_container_width=True, key="pred_musc")

        musc_pct   = (musc_atual / peso_atual * 100) if peso_atual > 0 else 0
        ganho_total = musc_atual - bio_recente[0].get("musculo_esqueletico_kg", musc_atual)
        periodo_dias = (datetime.strptime(bio_recente[-1]["date"], "%Y-%m-%d") -
                        datetime.strptime(bio_recente[0]["date"], "%Y-%m-%d")).days
        ganho_mes = ganho_total / (periodo_dias / 30) if periodo_dias > 0 else 0

        c_m1, c_m2, c_m3 = st.columns(3)
        with c_m1:
            st.metric("Músculo atual", f"{musc_atual:.1f} kg", f"{ganho_total:+.1f} kg total")
        with c_m2:
            st.metric("% do peso corporal", f"{musc_pct:.1f}%")
        with c_m3:
            taxa_kpi = taxa_musc_aj if usar_aj else taxa_musc_sem
            st.metric("Ritmo projetado", f"+{taxa_kpi * 4.3:.2f} kg/mês",
                      delta=f"{freq_treino}x/sem" if usar_aj else f"{freq_real_slider}x/sem")

    with col_mr:
        st.markdown("**📋 Projeção Muscular**")
        falta_musc = MUSC_META - musc_atual

        if dt_musc and taxa_musc_sem > 0:
            meses_musc = int(dias_musc_falta / 30)
            st.markdown(
                f"<div class='proj-warn'><b>💪 {freq_real_slider}x/sem (atual) — Meta {MUSC_META} kg</b><br>"
                f"Chegará em <b>{dt_musc.strftime('%d/%m/%Y')}</b><br>"
                f"~{meses_musc} meses</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='proj-warn'><b>💪 Meta {MUSC_META} kg</b><br>"
                f"Faltam <b>{falta_musc:.1f} kg</b><br>"
                f"Ritmo: {taxa_musc_sem:+.3f} kg/sem</div>",
                unsafe_allow_html=True,
            )

        if usar_aj and dt_musc_aj:
            meses_aj = int(dias_musc_aj / 30)
            acelerou = (int(dias_musc_falta) - int(dias_musc_aj)) if dt_musc and dt_musc_aj else 0
            st.markdown(
                f"<div class='proj-scenario'><b>✅ {freq_treino}x/sem</b><br>"
                f"Chegará em <b>{dt_musc_aj.strftime('%d/%m/%Y')}</b><br>"
                f"~{meses_aj} meses<br>"
                + (f"<span style='color:#27AE60;font-weight:700'>⚡ {acelerou} dias antes!</span>" if acelerou > 0 else "")
                + "</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            "<div style='background:#f5f5f5;border-radius:8px;padding:10px;margin-top:8px;font-size:12px'>"
            "<b>ℹ️ Ganho natural de músculo:</b><br>"
            "Iniciantes: 0,5–1 kg/mês<br>"
            "Intermediários: 0,2–0,5 kg/mês<br>"
            "Com déficit calórico: 0,1–0,2 kg/mês<br>"
            "Com Puran T4 controlado: tende a melhorar</div>",
            unsafe_allow_html=True,
        )

# ═══════════════════════════════════════════════════════════════════════════════
# GORDURA VISCERAL — painel contextual (fora das tabs, largura total)
# ═══════════════════════════════════════════════════════════════════════════════
_gv_vals  = [(datetime.strptime(b["date"], "%Y-%m-%d"), b.get("gordura_visceral", 0))
             for b in bio_list if b.get("gordura_visceral")]
if _gv_vals:
    _gv_datas, _gv_nums = zip(*_gv_vals)
    _gv_atual = _gv_nums[-1]
    # Classificação clínica (escala Tanita/similares: 1-59)
    if _gv_atual <= 9:
        _gv_cor, _gv_label = "#27AE60", "Zona segura (≤ 9)"
    elif _gv_atual <= 14:
        _gv_cor, _gv_label = "#F39C12", "Risco moderado (10–14)"
    else:
        _gv_cor, _gv_label = "#E74C3C", "Risco alto (≥ 15)"

    st.markdown("<div class='section-header'>🫀 Gordura Visceral — Monitoramento</div>", unsafe_allow_html=True)
    _gvc1, _gvc2 = st.columns([1, 3])
    with _gvc1:
        st.markdown(f"""<div style='background:#f8f8f8;border-left:5px solid {_gv_cor};
border-radius:8px;padding:16px;text-align:center;'>
<div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>Valor Atual</div>
<div style='font-size:48px;font-weight:700;color:{_gv_cor}'>{_gv_atual}</div>
<div style='font-size:13px;color:{_gv_cor};font-weight:600'>{_gv_label}</div>
<div style='font-size:12px;color:#888;margin-top:6px'>Meta: ≤ 9</div>
</div>""", unsafe_allow_html=True)
        st.markdown(f"""<div style='background:#fffbf0;border-left:4px solid #F39C12;
border-radius:0 8px 8px 0;padding:10px 12px;margin-top:8px;font-size:12px'>
<b>ℹ️ Sobre a projeção</b><br>
A gordura visceral responde mais lentamente do que o peso e a gordura total.
Tende a começar a cair após <b>3–6 meses</b> de déficit calórico sustentado.
Não é projetada por data — acompanhe a tendência nas medições semanais.</div>""",
        unsafe_allow_html=True)
    with _gvc2:
        fig_gv = go.Figure()
        fig_gv.add_trace(go.Scatter(
            x=list(_gv_datas), y=list(_gv_nums),
            name="Gordura visceral", mode="lines+markers",
            line=dict(color=_gv_cor, width=2.5), marker=dict(size=8),
        ))
        fig_gv.add_hline(y=9, line_dash="dot", line_color="#27AE60", line_width=1.5,
                         annotation_text="Meta: 9", annotation_position="right")
        fig_gv.add_hline(y=15, line_dash="dot", line_color="#E74C3C", line_width=1,
                         annotation_text="Risco alto: 15", annotation_position="right")
        fig_gv.update_layout(
            title="Histórico de Gordura Visceral",
            height=250, plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=False, tickangle=-15, tickformat="%b/%y"),
            yaxis=dict(showgrid=True, gridcolor="#eee", title="Índice", range=[0, max(20, _gv_atual + 3)]),
            margin=dict(l=50, r=120, t=40, b=60),
            showlegend=False,
        )
        st.plotly_chart(fig_gv, use_container_width=True, key="pred_gv")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: EXAMES
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("**Projeções baseadas em evidências médicas e no seu histórico de tratamento (Puran T4 + dieta + exercício)**")
    if usar_aj:
        extra_hdl_mes = extra_sessoes * 0.5  # +0.5 mg/dL/mês por sessão extra (cardio)
        st.info(f"Com {freq_treino}x/semana de treino, o HDL sobe ~{extra_hdl_mes:.1f} mg/dL a mais por mês do que a estimativa base.")

    results  = exams_data.get("results", [])
    sessions = {s["id"]: s["date"] for s in exams_data.get("sessions", [])}

    latest_by_exam = {}
    for r in results:
        exam = r["exam"]
        if (exam not in latest_by_exam or
                sessions.get(r["session_id"], "") > sessions.get(latest_by_exam[exam]["session_id"], "")):
            latest_by_exam[exam] = r

    def _val(exam_name):
        r = latest_by_exam.get(exam_name)
        return r["value"] if r and r["value"] is not None else None

    today_date = TODAY.date()

    # Tabela comparativa histórica
    st.markdown("### 📊 Comparativo de Exames ao Longo do Tempo")
    exams_compare = [
        ("TSH",             "µUI/mL", "< 4,3",   None, 4.3),
        ("TGO (AST)",       "U/L",    "< 34",    None, 40),
        ("TGP (ALT)",       "U/L",    "< 49",    10,   49),
        ("HDL",             "mg/dL",  "> 40",    40,   None),
        ("LDL",             "mg/dL",  "< 130",   None, 130),
        ("HbA1c",           "%",      "< 5,7%",  None, 5.7),
        ("Colesterol Total","mg/dL",  "< 190",   None, 190),
    ]

    rows = []
    for exam_name, unit, ref_label, ref_min, ref_max in exams_compare:
        vals_by_session = {}
        for r in results:
            if r["exam"] == exam_name and r["value"] is not None:
                vals_by_session[sessions.get(r["session_id"], "")] = r["value"]

        s1  = vals_by_session.get("2025-10-18", "—")
        s2  = vals_by_session.get("2026-05-06", "—")
        s3  = vals_by_session.get("2026-05-13", "—")
        cur = _val(exam_name)

        if cur is not None and ref_max is not None:
            ok = cur <= ref_max
        elif cur is not None and ref_min is not None:
            ok = cur >= ref_min
        else:
            ok = True

        rows.append({
            "Exame":       exam_name,
            "Out/2025":    s1,
            "Mai 06/26":   s2,
            "Mai 13/26":   s3,
            "Referência":  ref_label,
            "Status":      "✅ Normal" if ok else "🔴 Alterado",
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Projeções individuais
    st.markdown("### 🎯 Projeção de Normalização por Exame")

    # HDL: ajustado pela frequência de treino
    hdl_atual = _val("HDL") or 33
    hdl_melhora_mes_base = 1.5  # mg/dL/mês com exercício aeróbico ≥ 150 min/sem
    hdl_melhora_mes_aj   = hdl_melhora_mes_base + (extra_sessoes * 0.5)
    hdl_meses_para_40    = max(1, int((40 - hdl_atual) / hdl_melhora_mes_aj)) if usar_aj else max(1, int((40 - hdl_atual) / hdl_melhora_mes_base))
    hdl_expected         = today_date + timedelta(weeks=int(hdl_meses_para_40 * 4.3))

    exam_projs = [
        {
            "exam":       "TSH",
            "unit":       "µUI/mL",
            "current":    _val("TSH"),
            "goal_label": "1,0–2,5 µUI/mL (controle com levotiroxina)",
            "up":         False,
            "goal":       2.5,
            "expected":   today_date + timedelta(weeks=10),
            "confidence": "Alta",
            "mechanism":  "✅ Puran T4 iniciado em jun/2026",
            "note":       "Com dose adequada, TSH normaliza em 8–12 semanas. Controle esperado em set/2026.",
        },
        {
            "exam":       "TGO (AST)",
            "unit":       "U/L",
            "current":    _val("TGO (AST)"),
            "goal_label": "< 34 U/L",
            "up":         False,
            "goal":       34,
            "expected":   today_date + timedelta(weeks=18),
            "confidence": "Moderada",
            "mechanism":  "🔧 Tratamento do hipotireoidismo + perda de peso",
            "note":       "Hipotireoidismo é causa direta de TGO elevada. Com TSH controlado e peso reduzindo, TGO deve normalizar em 3–5 meses.",
        },
        {
            "exam":       "TGP (ALT)",
            "unit":       "U/L",
            "current":    _val("TGP (ALT)"),
            "goal_label": "< 49 U/L",
            "up":         False,
            "goal":       49,
            "expected":   today_date + timedelta(weeks=18),
            "confidence": "Moderada",
            "mechanism":  "🔧 Tratamento do hipotireoidismo + resultado da US abdominal",
            "note":       "TGP elevada junto com TGO indica envolvimento hepático. Aguardar resultado da ultrassonografia para conduta definitiva.",
        },
        {
            "exam":       "HDL",
            "unit":       "mg/dL",
            "current":    _val("HDL"),
            "goal_label": "> 40 mg/dL (ideal > 60)",
            "up":         True,
            "goal":       40,
            "expected":   hdl_expected,
            "confidence": "Alta",
            "mechanism":  f"🏃 Exercício aeróbico — {freq_treino}x/sem (+{hdl_melhora_mes_aj:.1f} mg/dL/mês estimado)",
            "note":       (f"Com {freq_treino}x/sem, HDL sobe ~{hdl_melhora_mes_aj:.1f} mg/dL/mês. "
                          f"De {hdl_atual} para 40 mg/dL em ~{hdl_meses_para_40} meses."),
        },
        {
            "exam":       "LDL",
            "unit":       "mg/dL",
            "current":    _val("LDL"),
            "goal_label": "< 130 mg/dL",
            "up":         False,
            "goal":       130,
            "expected":   today_date + timedelta(weeks=14),
            "confidence": "Alta",
            "mechanism":  "🥗 Dieta da nutricionista + perda de peso + Puran T4",
            "note":       "LDL já melhorou (162→143). Com -5 kg a mais, espera-se redução adicional de 8–12%. Normalização em ~3 meses.",
        },
        {
            "exam":       "HbA1c",
            "unit":       "%",
            "current":    _val("HbA1c"),
            "goal_label": "< 5,7% (normal)",
            "up":         False,
            "goal":       5.7,
            "expected":   today_date + timedelta(weeks=12),
            "confidence": "Moderada",
            "mechanism":  "🌿 Dieta + psyllium + perda de peso + Puran T4",
            "note":       "HbA1c reflete média de 3 meses. Com hipotireoidismo tratado + dieta, pode normalizar na próxima coleta (set/2026).",
        },
        {
            "exam":       "Colesterol Total",
            "unit":       "mg/dL",
            "current":    _val("Colesterol Total"),
            "goal_label": "< 190 mg/dL",
            "up":         False,
            "goal":       190,
            "expected":   today_date + timedelta(weeks=10),
            "confidence": "Alta",
            "mechanism":  "🥗 Dieta + perda de peso + Puran T4 (hipotireoidismo eleva colesterol)",
            "note":       "Já melhorou (222→199). Com tratamento da tireoide, colesterol tende a cair mais. Normalização em ~2,5 meses.",
        },
    ]

    for ep in exam_projs:
        if ep["current"] is None:
            continue
        cur   = ep["current"]
        goal  = ep["goal"]
        is_up = ep["up"]
        is_ok = (cur >= goal) if is_up else (cur <= goal)
        diff  = abs(cur - goal)

        if is_ok:
            pct = 100
        elif is_up:
            pct = max(0, min(99, int(cur / goal * 100)))
        else:
            start_ref = cur + diff * 0.5
            pct = max(0, min(99, int((1 - (cur - goal) / (start_ref - goal)) * 100))) if start_ref != goal else 50

        icon = "✅" if is_ok else ("⚠️" if diff < 15 else "🔴")
        with st.expander(
            f"{icon} **{ep['exam']}** — atual: **{cur} {ep['unit']}** · meta: {ep['goal_label']}",
            expanded=not is_ok,
        ):
            col_l, col_r2 = st.columns([2, 1])
            with col_l:
                if is_ok:
                    st.success("✅ Dentro da referência!")
                else:
                    st.progress(min(1.0, pct / 100), text=f"Progresso estimado: {pct}%")
                st.caption(f"🔧 **Como melhora:** {ep['mechanism']}")
                st.caption(f"ℹ️ {ep['note']}")
            with col_r2:
                if is_ok:
                    st.markdown(
                        "<div class='proj-good'>✅ Normalizado<br>Manter o estilo de vida!</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<div class='proj-warn'><b>Estimativa:</b><br>{ep['expected'].strftime('%B/%Y')}<br>"
                        f"<b>Confiança:</b> {ep['confidence']}</div>",
                        unsafe_allow_html=True,
                    )

    # Linha do tempo
    st.markdown("---")
    st.markdown("### 📅 Linha do Tempo de Melhoras Esperadas")

    dt_82kg_str = dt_peso_aj.strftime("%b/%Y") if usar_aj and dt_peso_aj else (dt_peso.strftime("%b/%Y") if dt_peso else "2027")
    dt_musc_str = dt_musc_aj.strftime("%b/%Y") if usar_aj and dt_musc_aj else (dt_musc.strftime("%b/%Y") if dt_musc else "2027+")

    timeline = [
        ("Jul/2026", "🟣", "Início do efeito do Puran T4 — primeiros sinais de melhora no metabolismo"),
        ("Ago/2026", "🟢", "TSH normaliza com levotiroxina (8–12 semanas após início)"),
        ("Set/2026", "🟢", "HbA1c volta ao normal (< 5,7%) — sai da zona pré-diabetes"),
        ("Set/2026", "🟢", "Colesterol Total < 190 mg/dL com dieta + tratamento da tireoide"),
        ("Out/2026", "🟢", "LDL < 130 mg/dL com dieta + perda de peso"),
        ("Nov/2026", "🟡", "TGO e TGP normalizam após TSH controlado + resultado da US"),
        (f"~{hdl_meses_para_40} meses", "🟡", f"HDL atinge 40 mg/dL — com {freq_treino}x/sem de exercício"),
        (dt_82kg_str, "⚖️", f"Meta 82 kg — {peso_atual - PESO_META:.1f} kg abaixo do peso atual" + (f" (cenário {freq_treino}x/sem)" if usar_aj else "")),
        (dt_musc_str, "💪", "Meta 40 kg de músculo esquelético"),
    ]

    for mes, icon, desc in timeline:
        st.markdown(
            f"<div class='timeline-item'><b>{mes}</b> {icon} {desc}</div>",
            unsafe_allow_html=True,
        )

    st.info(
        "💊 **Nota importante:** As projeções assumem uso contínuo do Puran T4, "
        "adesão ao plano alimentar da nutricionista, prática regular de musculação e "
        "início de exercício aeróbico. Consultas regulares com a Dra. Celina são "
        "fundamentais para ajuste de doses e acompanhamento dos exames."
    )
