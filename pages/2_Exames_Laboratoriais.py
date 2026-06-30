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

# Descrições curtas de cada exame
EXAM_DESC = {
    "Eritrócitos": "Glóbulos vermelhos — transportam oxigênio",
    "Hemoglobina": "Proteína que carrega oxigênio no sangue",
    "Hematócrito": "Proporção de glóbulos vermelhos no sangue",
    "VCM": "Tamanho médio dos glóbulos vermelhos",
    "HCM": "Quantidade de hemoglobina por glóbulo vermelho",
    "CHCM": "Concentração de hemoglobina nos glóbulos",
    "RDW": "Variação no tamanho dos glóbulos vermelhos",
    "Leucócitos": "Glóbulos brancos — defesa imunológica",
    "Neutrófilos": "Células de defesa contra bactérias",
    "Linfócitos": "Células de defesa — imunidade adaptativa",
    "Monócitos": "Células de defesa — fagocitam patógenos",
    "Eosinófilos": "Células ligadas a alergias e parasitas",
    "Basófilos": "Células envolvidas em reações alérgicas",
    "Plaquetas": "Coagulação do sangue",
    "Creatinina": "Resíduo muscular filtrado pelos rins — avalia função renal",
    "TFG estimada (eGFR)": "Taxa de filtração glomerular — eficiência dos rins",
    "Albumina Urinária": "Proteína na urina — sinal precoce de lesão renal",
    "Ureia": "Resíduo do metabolismo de proteínas — filtrado pelos rins",
    "Potássio": "Eletrólito essencial para coração e músculos",
    "Sódio": "Eletrólito que controla líquidos do corpo",
    "Homocisteína": "Aminoácido — elevado indica risco cardiovascular e falta de B12/B9",
    "PCR": "Proteína C Reativa — marcador de inflamação",
    "Glicose": "Açúcar no sangue em jejum — rastreia diabetes",
    "HbA1c": "Hemoglobina glicada — média do açúcar dos últimos 3 meses",
    "Insulina": "Hormônio que controla o açúcar no sangue",
    "Colesterol Total": "Soma de todo colesterol no sangue",
    "HDL": "Colesterol bom — remove excesso das artérias",
    "LDL": "Colesterol ruim — deposita nas artérias",
    "VLDL": "Colesterol muito ruim — ligado a triglicérides",
    "Triglicérides": "Gordura no sangue — relacionada a dieta e álcool",
    "TGO (AST)": "Enzima hepática e muscular — elevada indica lesão no fígado ou músculo",
    "TGP (ALT)": "Enzima hepática — mais específica para o fígado que o TGO",
    "GGT": "Enzima hepática — sensível a álcool e medicamentos",
    "Bilirrubina Total": "Pigmento da destruição de glóbulos vermelhos — avalia fígado",
    "Fosfatase Alcalina": "Enzima de fígado e ossos",
    "TSH": "Hormônio que estimula a tireoide — avalia hipotireoidismo",
    "T4 Livre": "Hormônio ativo da tireoide — controla metabolismo",
    "Anti-tireoglobulina (anti-TG)": "Anticorpo contra a tireoide — indica Hashimoto",
    "Anti-TPO (Antiperoxidase)": "Anticorpo contra enzima da tireoide — indica Hashimoto",
    "Ferritina": "Reserva de ferro no organismo",
    "Ferro": "Ferro circulante no sangue",
    "Vitamina D": "Vitamina essencial para ossos, imunidade e humor",
    "Vitamina B12": "Vitamina para nervos, DNA e produção de glóbulos vermelhos",
    "Ácido Fólico": "Vitamina B9 — essencial para DNA e produção sanguínea",
    "Ácido Úrico": "Resíduo do metabolismo — elevado causa gota",
    "Albumina": "Principal proteína do sangue — avalia nutrição e fígado",
    "Proteínas Totais": "Total de proteínas no sangue",
    "Anti-HIV": "Teste para o vírus HIV",
    "HBsAg (Hepatite B)": "Antígeno de superfície — detecta infecção ativa por Hepatite B",
    "Anti-HBs (Imunidade Hep B)": "Anticorpo protetor contra Hepatite B — avalia imunidade",
    "Anti-HBc Total": "Contato prévio com Hepatite B",
    "Anti-HCV (Hepatite C)": "Anticorpo contra o vírus da Hepatite C",
    "Hemácias (sedimento)": "Glóbulos vermelhos na urina — pode indicar inflamação ou cálculo",
    "Leucócitos (sedimento)": "Glóbulos brancos na urina — pode indicar infecção urinária",
}

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

        desc = EXAM_DESC.get(r["exam"], "")
        col1, col2, col3 = st.columns([3, 2, 5])
        with col1:
            st.markdown(
                f"<div class='{css_class}'>{emoji} <b>{r['exam']}</b>"
                + (f"<br><span style='font-size:11px;color:#666'>{desc}</span>" if desc else "")
                + "</div>", unsafe_allow_html=True)
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

def trend_chart(exam_name, unit, ref_min, ref_max, color, height=280, tab_key=""):
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
        textfont=dict(size=11), cliponaxis=False,
        line=dict(color=color, width=2.5), marker=dict(size=10, color=colors)))
    if ref_max is not None:
        fig.add_hline(y=ref_max, line_dash="dash", line_color="#E74C3C",
                      annotation_text=f"Limite sup: {ref_max} {unit}", annotation_position="right")
    if ref_min is not None:
        fig.add_hline(y=ref_min, line_dash="dash", line_color="#27AE60",
                      annotation_text=f"Limite inf: {ref_min} {unit}", annotation_position="right")
    _ypad = max((max(values) - min(values)) * 0.4, abs(max(values)) * 0.08 + 0.5) if values else 1
    fig.update_layout(height=height, title=f"{exam_name} ({unit})", plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(showgrid=False, automargin=True, tickangle=-20),
        yaxis=dict(showgrid=True, gridcolor="#eee", automargin=True,
                   range=[min(values) - _ypad * 0.3, max(values) + _ypad * 1.8] if values else None),
        showlegend=False, margin=dict(l=50, r=185, t=55, b=55))
    safe_key = exam_name.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
    st.plotly_chart(fig, use_container_width=True, key=f"tc_{tab_key}_{safe_key}")

with tabs[0]:
    st.caption("Exames que apresentam alteração nas últimas coletas")
    c1, c2 = st.columns(2)
    with c1:
        trend_chart("TSH", "µUI/mL", 0.40, 4.30, "#8E44AD", tab_key="prio")
        trend_chart("TGO (AST)", "U/L", None, 34, "#E74C3C", tab_key="prio")
    with c2:
        trend_chart("HDL", "mg/dL", 40, None, "#27AE60", tab_key="prio")
        trend_chart("TGP (ALT)", "U/L", 10, 49, "#C0392B", tab_key="prio")

with tabs[1]:
    c1, c2 = st.columns(2)
    with c1:
        trend_chart("TSH", "µUI/mL", 0.40, 4.30, "#8E44AD", tab_key="tir")
        trend_chart("T4 Livre", "ng/dL", 0.89, 1.76, "#9B59B6", tab_key="tir")
    with c2:
        trend_chart("Anti-tireoglobulina (anti-TG)", "UI/mL", None, 4.5, "#6C3483", tab_key="tir")
        trend_chart("Anti-TPO (Antiperoxidase)", "U/mL", None, 13.8, "#A569BD", tab_key="tir")

with tabs[2]:
    c1, c2 = st.columns(2)
    with c1:
        trend_chart("Colesterol Total", "mg/dL", None, 190, "#F39C12", tab_key="lip")
        trend_chart("LDL", "mg/dL", None, 130, "#E67E22", tab_key="lip")
    with c2:
        trend_chart("HDL", "mg/dL", 40, None, "#27AE60", tab_key="lip")
        trend_chart("Triglicérides", "mg/dL", None, 150, "#E74C3C", tab_key="lip")

with tabs[3]:
    c1, c2 = st.columns(2)
    with c1:
        trend_chart("Glicose", "mg/dL", 70, 99, "#2980B9", tab_key="glic")
    with c2:
        trend_chart("HbA1c", "%", None, 5.7, "#8E44AD", tab_key="glic")

with tabs[4]:
    c1, c2 = st.columns(2)
    with c1:
        trend_chart("TGO (AST)", "U/L", None, 34, "#E74C3C", tab_key="hep")
    with c2:
        trend_chart("TGP (ALT)", "U/L", 10, 49, "#C0392B", tab_key="hep")

with tabs[5]:
    c1, c2 = st.columns(2)
    with c1:
        trend_chart("Creatinina", "mg/dL", 0.70, 1.30, "#16A085", tab_key="rim")
    with c2:
        trend_chart("TFG estimada (eGFR)", "mL/min/1,73m²", 90, None, "#1ABC9C", tab_key="rim")
