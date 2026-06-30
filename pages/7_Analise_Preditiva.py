import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import date, datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_manager import load_bioimpedance, load_exams

st.set_page_config(page_title="Análise Preditiva", page_icon="🔮", layout="wide")

st.markdown("""
<style>
.section-header{font-size:22px;font-weight:700;color:#7B2FBE;border-bottom:3px solid #7B2FBE;padding-bottom:8px;margin:20px 0 16px}
.kpi-box{background:linear-gradient(135deg,#f5f0ff,#ede0ff);border:1px solid #9B59B6;border-radius:12px;padding:14px;text-align:center;margin:4px}
.proj-good{background:#f0fff4;border-left:4px solid #27AE60;padding:10px 14px;border-radius:0 8px 8px 0;margin:6px 0;font-size:13px}
.proj-warn{background:#fffbf0;border-left:4px solid #F39C12;padding:10px 14px;border-radius:0 8px 8px 0;margin:6px 0;font-size:13px}
.proj-alert{background:#fff5f5;border-left:4px solid #E74C3C;padding:10px 14px;border-radius:0 8px 8px 0;margin:6px 0;font-size:13px}
.timeline-item{padding:8px 14px;border-left:3px solid #9B59B6;margin:6px 0;background:#faf5ff;border-radius:0 8px 8px 0;font-size:13px}
</style>
""", unsafe_allow_html=True)

st.markdown("## 🔮 Análise Preditiva")
st.caption("Projeções baseadas nos seus dados históricos e evidências médicas. As datas são estimativas — não substituem avaliação médica.")

# ── Carregar dados ──────────────────────────────────────────────────────────────
bio_list = sorted(load_bioimpedance(), key=lambda x: x["date"])
exams_data = load_exams()

if len(bio_list) < 3:
    st.warning("Dados insuficientes para projeções. Adicione mais medições de bioimpedância.")
    st.stop()

# Usar dados de 2026 (fase atual de acompanhamento)
REF_DATE = datetime(2026, 1, 1)
TODAY    = datetime.now()
TODAY_X  = (TODAY - REF_DATE).days

bio_recente = [b for b in bio_list if b["date"] >= "2026-01-01"]
if len(bio_recente) < 3:
    bio_recente = bio_list

x_dias   = [(datetime.strptime(b["date"], "%Y-%m-%d") - REF_DATE).days for b in bio_recente]
pesos    = [b["peso_kg"] for b in bio_recente]
gorduras = [b.get("percentual_gordura", 0) for b in bio_recente]
musculos = [b.get("musculo_esqueletico_kg", 0) for b in bio_recente]

# Regressão linear
coef_peso = np.polyfit(x_dias, pesos, 1)
coef_gord = np.polyfit(x_dias, gorduras, 1)
coef_musc = np.polyfit(x_dias, musculos, 1)

peso_atual = bio_recente[-1]["peso_kg"]
gord_atual = bio_recente[-1].get("percentual_gordura", 0)
musc_atual = bio_recente[-1].get("musculo_esqueletico_kg", 0)

taxa_peso_sem = coef_peso[0] * 7  # kg/semana
taxa_gord_sem = coef_gord[0] * 7  # %/semana
taxa_musc_sem = coef_musc[0] * 7  # kg/semana

PESO_META = 82.0
GORD_META = 22.0
MUSC_META = 40.0

def _dias_para_meta(valor, meta, coef):
    if coef == 0:
        return None, None
    dias = (meta - coef[1] - valor) / coef[0] if False else (meta - np.polyval(coef, TODAY_X)) / coef[0]
    if days_raw := (meta - np.polyval(coef, TODAY_X)) / coef[0]:
        if days_raw <= 0:
            return None, None
        d = int(days_raw)
        return d, (TODAY + timedelta(days=d)).date()
    return None, None

# Calcular datas de meta
if coef_peso[0] < 0:
    dias_peso_falta = (PESO_META - np.polyval(coef_peso, TODAY_X)) / coef_peso[0]
    dt_peso = (TODAY + timedelta(days=int(dias_peso_falta))).date() if dias_peso_falta > 0 else None
else:
    dias_peso_falta, dt_peso = None, None

if coef_gord[0] < 0:
    dias_gord_falta = (GORD_META - np.polyval(coef_gord, TODAY_X)) / coef_gord[0]
    dt_gord = (TODAY + timedelta(days=int(dias_gord_falta))).date() if dias_gord_falta > 0 else None
else:
    dias_gord_falta, dt_gord = None, None

if coef_musc[0] > 0:
    dias_musc_falta = (MUSC_META - np.polyval(coef_musc, TODAY_X)) / coef_musc[0]
    dt_musc = (TODAY + timedelta(days=int(dias_musc_falta))).date() if dias_musc_falta > 0 else None
else:
    dias_musc_falta, dt_musc = None, None

# Dados projetados (40 semanas à frente)
proj_x       = list(range(TODAY_X, TODAY_X + 40 * 7, 7))
proj_datas   = [REF_DATE + timedelta(days=d) for d in proj_x]
proj_pesos   = [float(np.polyval(coef_peso, d)) for d in proj_x]
proj_gorduras = [float(np.polyval(coef_gord, d)) for d in proj_x]
proj_musculos = [float(np.polyval(coef_musc, d)) for d in proj_x]

# Linha de tendência sobre histórico
trend_x     = list(range(x_dias[0], TODAY_X + 1))
trend_datas = [REF_DATE + timedelta(days=d) for d in trend_x]
hist_datas  = [datetime.strptime(b["date"], "%Y-%m-%d") for b in bio_recente]

# ── KPIs ──────────────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>📊 Ritmo Atual</div>", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)

with c1:
    cor = "#27AE60" if taxa_peso_sem < 0 else "#E74C3C"
    seta = "↓" if taxa_peso_sem < 0 else "↑"
    st.markdown(f"""<div class='kpi-box'>
<div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>Perda de Peso</div>
<div style='font-size:32px;font-weight:700;color:{cor}'>{seta} {abs(taxa_peso_sem):.2f}</div>
<div style='font-size:12px;color:#888'>kg/semana</div>
<div style='font-size:12px;color:{cor};font-weight:600'>{abs(taxa_peso_sem*4.3):.1f} kg/mês</div>
</div>""", unsafe_allow_html=True)

with c2:
    cor2 = "#27AE60" if taxa_gord_sem < 0 else "#E74C3C"
    seta2 = "↓" if taxa_gord_sem < 0 else "↑"
    st.markdown(f"""<div class='kpi-box'>
<div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>Gordura Corporal</div>
<div style='font-size:32px;font-weight:700;color:{cor2}'>{seta2} {abs(taxa_gord_sem):.2f}</div>
<div style='font-size:12px;color:#888'>%/semana</div>
<div style='font-size:12px;color:{cor2};font-weight:600'>Atual: {gord_atual:.1f}%</div>
</div>""", unsafe_allow_html=True)

with c3:
    cor3 = "#27AE60" if taxa_musc_sem > 0 else "#F39C12"
    seta3 = "↑" if taxa_musc_sem > 0 else "→"
    st.markdown(f"""<div class='kpi-box'>
<div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>Ganho Muscular</div>
<div style='font-size:32px;font-weight:700;color:{cor3}'>{seta3} {abs(taxa_musc_sem):.3f}</div>
<div style='font-size:12px;color:#888'>kg/semana</div>
<div style='font-size:12px;color:{cor3};font-weight:600'>+{taxa_musc_sem*4.3:.2f} kg/mês</div>
</div>""", unsafe_allow_html=True)

with c4:
    if dt_peso:
        meses = int(dias_peso_falta / 30)
        st.markdown(f"""<div class='kpi-box'>
<div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>Meta 82 kg</div>
<div style='font-size:24px;font-weight:700;color:#7B2FBE'>{dt_peso.strftime('%b/%Y')}</div>
<div style='font-size:12px;color:#888'>em ~{meses} meses</div>
<div style='font-size:12px;color:#7B2FBE;font-weight:600'>Faltam {peso_atual - PESO_META:.1f} kg</div>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class='kpi-box'>
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
        fig_peso.add_trace(go.Scatter(
            x=hist_datas, y=pesos, name="Peso real",
            mode="lines+markers",
            line=dict(color="#2980B9", width=2.5),
            marker=dict(size=7, color="#2980B9"),
        ))
        fig_peso.add_trace(go.Scatter(
            x=trend_datas,
            y=[float(np.polyval(coef_peso, d)) for d in trend_x],
            name="Tendência",
            mode="lines",
            line=dict(color="#27AE60", width=1.5, dash="dot"),
        ))
        fig_peso.add_trace(go.Scatter(
            x=proj_datas, y=proj_pesos, name="Projeção",
            mode="lines",
            line=dict(color="#9B59B6", width=2, dash="dash"),
        ))
        fig_peso.add_hline(y=PESO_META, line_dash="dot", line_color="#E74C3C", line_width=1.5,
                           annotation_text="Meta: 82 kg", annotation_position="right")
        if dt_peso:
            fig_peso.add_vline(
                x=datetime.combine(dt_peso, datetime.min.time()),
                line_dash="dot", line_color="#E74C3C", line_width=1,
                annotation_text=dt_peso.strftime("%d/%m/%Y"), annotation_position="top right",
            )
        fig_peso.update_layout(
            title="Projeção de Peso",
            height=360, plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=False, automargin=True, tickangle=-15, tickformat="%b/%y"),
            yaxis=dict(showgrid=True, gridcolor="#eee", title="kg", automargin=True,
                       range=[80, max(pesos) + 2]),
            legend=dict(orientation="h", yanchor="bottom", y=-0.28),
            margin=dict(l=50, r=150, t=50, b=80),
        )
        st.plotly_chart(fig_peso, use_container_width=True, key="pred_peso")

        # Gráfico de gordura
        fig_gord = go.Figure()
        fig_gord.add_trace(go.Scatter(
            x=hist_datas, y=gorduras, name="Gordura real (%)",
            mode="lines+markers",
            line=dict(color="#E74C3C", width=2.5), marker=dict(size=7),
        ))
        fig_gord.add_trace(go.Scatter(
            x=proj_datas, y=proj_gorduras, name="Projeção",
            mode="lines",
            line=dict(color="#9B59B6", width=2, dash="dash"),
        ))
        fig_gord.add_hline(y=GORD_META, line_dash="dot", line_color="#27AE60", line_width=1.5,
                           annotation_text=f"Meta: {GORD_META}%", annotation_position="right")
        if dt_gord:
            fig_gord.add_vline(
                x=datetime.combine(dt_gord, datetime.min.time()),
                line_dash="dot", line_color="#27AE60", line_width=1,
                annotation_text=dt_gord.strftime("%d/%m/%Y"), annotation_position="top right",
            )
        fig_gord.update_layout(
            title="Projeção de Gordura Corporal (%)",
            height=300, plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=False, automargin=True, tickangle=-15, tickformat="%b/%y"),
            yaxis=dict(showgrid=True, gridcolor="#eee", title="%", automargin=True),
            legend=dict(orientation="h", yanchor="bottom", y=-0.32),
            margin=dict(l=50, r=150, t=50, b=80),
        )
        st.plotly_chart(fig_gord, use_container_width=True, key="pred_gord")

    with col_r:
        st.markdown("**📋 Projeções**")

        # Peso
        falta_peso = peso_atual - PESO_META
        if dt_peso:
            st.markdown(f"<div class='proj-good'><b>⚖️ Meta 82 kg</b><br>"
                        f"Faltam <b>{falta_peso:.1f} kg</b><br>"
                        f"Chegará em <b>{dt_peso.strftime('%d/%m/%Y')}</b><br>"
                        f"<span style='color:#888'>ao ritmo de {taxa_peso_sem:.2f} kg/sem</span></div>",
                        unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='proj-alert'><b>⚖️ Meta 82 kg</b><br>"
                        f"Faltam <b>{falta_peso:.1f} kg</b><br>"
                        f"Tendência atual não alcança a meta</div>", unsafe_allow_html=True)

        # Gordura
        falta_gord = gord_atual - GORD_META
        if dt_gord:
            st.markdown(f"<div class='proj-good'><b>🔴 Meta &lt;{GORD_META}% gordura</b><br>"
                        f"Faltam <b>{falta_gord:.1f}%</b><br>"
                        f"Chegará em <b>{dt_gord.strftime('%d/%m/%Y')}</b><br>"
                        f"<span style='color:#888'>ao ritmo de {taxa_gord_sem:.2f}%/sem</span></div>",
                        unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='proj-alert'><b>🔴 Meta &lt;{GORD_META}%</b><br>"
                        f"Faltam <b>{falta_gord:.1f}%</b><br>"
                        f"Ritmo insuficiente — ajustar déficit</div>", unsafe_allow_html=True)

        # Comparativo vs melhor histórico
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
        fig_musc.add_trace(go.Scatter(
            x=hist_datas, y=musculos, name="Músculo real",
            mode="lines+markers",
            line=dict(color="#27AE60", width=2.5), marker=dict(size=7),
        ))
        fig_musc.add_trace(go.Scatter(
            x=trend_datas,
            y=[float(np.polyval(coef_musc, d)) for d in trend_x],
            name="Tendência",
            mode="lines",
            line=dict(color="#1ABC9C", width=1.5, dash="dot"),
        ))
        fig_musc.add_trace(go.Scatter(
            x=proj_datas, y=proj_musculos, name="Projeção",
            mode="lines",
            line=dict(color="#9B59B6", width=2, dash="dash"),
        ))
        fig_musc.add_hline(y=MUSC_META, line_dash="dot", line_color="#F39C12", line_width=1.5,
                           annotation_text=f"Meta: {MUSC_META} kg", annotation_position="right")
        if dt_musc:
            fig_musc.add_vline(
                x=datetime.combine(dt_musc, datetime.min.time()),
                line_dash="dot", line_color="#F39C12", line_width=1,
                annotation_text=dt_musc.strftime("%d/%m/%Y"), annotation_position="top right",
            )
        fig_musc.update_layout(
            title="Projeção de Massa Muscular Esquelética",
            height=380, plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=False, automargin=True, tickangle=-15, tickformat="%b/%y"),
            yaxis=dict(showgrid=True, gridcolor="#eee", title="kg", automargin=True,
                       range=[min(musculos) - 1, max(max(musculos), MUSC_META) + 1]),
            legend=dict(orientation="h", yanchor="bottom", y=-0.3),
            margin=dict(l=50, r=150, t=50, b=80),
        )
        st.plotly_chart(fig_musc, use_container_width=True, key="pred_musc")

        # KPIs de músculo
        musc_pct = (musc_atual / peso_atual * 100) if peso_atual > 0 else 0
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
            st.metric("Ritmo atual", f"+{ganho_mes:.2f} kg/mês")

    with col_mr:
        st.markdown("**📋 Projeção Muscular**")
        falta_musc = MUSC_META - musc_atual
        if dt_musc and taxa_musc_sem > 0:
            meses_musc = int(dias_musc_falta / 30)
            st.markdown(
                f"<div class='proj-good'><b>💪 Meta {MUSC_META} kg</b><br>"
                f"Faltam <b>{falta_musc:.1f} kg</b><br>"
                f"Chegará em <b>{dt_musc.strftime('%d/%m/%Y')}</b><br>"
                f"<span style='color:#888'>em ~{meses_musc} meses</span></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='proj-warn'><b>💪 Meta {MUSC_META} kg</b><br>"
                f"Faltam <b>{falta_musc:.1f} kg</b><br>"
                f"Ritmo: {taxa_musc_sem:+.3f} kg/sem<br>"
                f"<span style='color:#888'>Intensifique musculação</span></div>",
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
# TAB 3: EXAMES
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("**Projeções baseadas em evidências médicas e no seu histórico de tratamento (Puran T4 + dieta + exercício)**")

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
        ("TSH", "µUI/mL", "< 4,3", None, 4.3),
        ("TGO (AST)", "U/L", "< 34", None, 40),
        ("TGP (ALT)", "U/L", "< 49", 10, 49),
        ("HDL", "mg/dL", "> 40", 40, None),
        ("LDL", "mg/dL", "< 130", None, 130),
        ("HbA1c", "%", "< 5,7%", None, 5.7),
        ("Colesterol Total", "mg/dL", "< 190", None, 190),
    ]

    rows = []
    for exam_name, unit, ref_label, ref_min, ref_max in exams_compare:
        vals_by_session = {}
        for r in results:
            if r["exam"] == exam_name and r["value"] is not None:
                vals_by_session[sessions.get(r["session_id"], "")] = r["value"]

        s1 = vals_by_session.get("2025-10-18", "—")
        s2 = vals_by_session.get("2026-05-06", "—")
        s3 = vals_by_session.get("2026-05-13", "—")
        cur = _val(exam_name)

        if cur is not None and ref_max is not None:
            ok = cur <= ref_max
        elif cur is not None and ref_min is not None:
            ok = cur >= ref_min
        else:
            ok = True

        status = "✅ Normal" if ok else "🔴 Alterado"
        rows.append({
            "Exame": exam_name,
            "Out/2025": s1,
            "Mai 06/2026": s2,
            "Mai 13/2026": s3,
            "Referência": ref_label,
            "Status": status,
        })

    df_comp = pd.DataFrame(rows)
    st.dataframe(df_comp, use_container_width=True, hide_index=True)

    # Projeções individuais
    st.markdown("### 🎯 Projeção de Normalização por Exame")

    exam_projs = [
        {
            "exam": "TSH",
            "unit": "µUI/mL",
            "current": _val("TSH"),
            "goal_label": "1,0–2,5 µUI/mL (controle com levotiroxina)",
            "up": False,
            "goal": 2.5,
            "expected": today_date + timedelta(weeks=10),
            "confidence": "Alta",
            "mechanism": "✅ Puran T4 iniciado em jun/2026",
            "note": "Com dose adequada, TSH normaliza em 8–12 semanas. Controle esperado em set/2026.",
        },
        {
            "exam": "TGO (AST)",
            "unit": "U/L",
            "current": _val("TGO (AST)"),
            "goal_label": "< 34 U/L",
            "up": False,
            "goal": 34,
            "expected": today_date + timedelta(weeks=18),
            "confidence": "Moderada",
            "mechanism": "🔧 Tratamento do hipotireoidismo + perda de peso",
            "note": "Hipotireoidismo é causa direta de TGO elevada. Com TSH controlado e peso reduzindo, TGO deve normalizar em 3–5 meses.",
        },
        {
            "exam": "TGP (ALT)",
            "unit": "U/L",
            "current": _val("TGP (ALT)"),
            "goal_label": "< 49 U/L",
            "up": False,
            "goal": 49,
            "expected": today_date + timedelta(weeks=18),
            "confidence": "Moderada",
            "mechanism": "🔧 Tratamento do hipotireoidismo + resultado da US abdominal",
            "note": "TGP elevada junto com TGO indica envolvimento hepático. Aguardar resultado da ultrassonografia para conduta definitiva.",
        },
        {
            "exam": "HDL",
            "unit": "mg/dL",
            "current": _val("HDL"),
            "goal_label": "> 40 mg/dL (ideal > 60)",
            "up": True,
            "goal": 40,
            "expected": today_date + timedelta(weeks=20),
            "confidence": "Alta",
            "mechanism": "🏃 Exercício aeróbico ≥ 150 min/semana",
            "note": "HDL aumenta +1,5 mg/dL/mês com cardio regular. De 33 para 40 mg/dL levará ~5 meses de exercício consistente.",
        },
        {
            "exam": "LDL",
            "unit": "mg/dL",
            "current": _val("LDL"),
            "goal_label": "< 130 mg/dL",
            "up": False,
            "goal": 130,
            "expected": today_date + timedelta(weeks=14),
            "confidence": "Alta",
            "mechanism": "🥗 Dieta da nutricionista + perda de peso + Puran T4",
            "note": "LDL já melhorou (162→143). Com -5 kg a mais, espera-se redução adicional de 8–12%. Normalização em ~3 meses.",
        },
        {
            "exam": "HbA1c",
            "unit": "%",
            "current": _val("HbA1c"),
            "goal_label": "< 5,7% (normal)",
            "up": False,
            "goal": 5.7,
            "expected": today_date + timedelta(weeks=12),
            "confidence": "Moderada",
            "mechanism": "🌿 Dieta + psyllium + perda de peso + Puran T4",
            "note": "HbA1c reflete média de 3 meses. Com hipotireoidismo tratado + dieta, pode normalizar na próxima coleta (set/2026).",
        },
        {
            "exam": "Colesterol Total",
            "unit": "mg/dL",
            "current": _val("Colesterol Total"),
            "goal_label": "< 190 mg/dL",
            "up": False,
            "goal": 190,
            "expected": today_date + timedelta(weeks=10),
            "confidence": "Alta",
            "mechanism": "🥗 Dieta + perda de peso + Puran T4 (hipotireoidismo eleva colesterol)",
            "note": "Já melhorou (222→199). Com tratamento da tireoide, colesterol tende a cair mais. Normalização em ~2,5 meses.",
        },
    ]

    for ep in exam_projs:
        if ep["current"] is None:
            continue
        cur  = ep["current"]
        goal = ep["goal"]
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

    timeline = [
        ("Jul/2026", "🟣", "Início do efeito do Puran T4 — primeiros sinais de melhora no metabolismo"),
        ("Ago/2026", "🟢", "TSH normaliza com levotiroxina (8–12 semanas após início)"),
        ("Set/2026", "🟢", "HbA1c volta ao normal (< 5,7%) — sai da zona pré-diabetes"),
        ("Set/2026", "🟢", "Colesterol Total < 190 mg/dL com dieta + tratamento da tireoide"),
        ("Out/2026", "🟢", "LDL < 130 mg/dL com dieta + perda de peso"),
        ("Nov/2026", "🟡", "TGO e TGP normalizam após TSH controlado + resultado da US"),
        ("Dez/2026", "🟡", "HDL atinge 40 mg/dL com cardio consistente (150+ min/sem)"),
        (f"{dt_peso.strftime('%b/%Y') if dt_peso else '2027'}", "⚖️", f"Meta 82 kg — {peso_atual - PESO_META:.1f} kg a menos do peso atual"),
        ("2027", "💪", "Meta 40 kg de músculo esquelético"),
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
