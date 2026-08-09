import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_manager import load_bioimpedance, load_exams, load_profile, calc_age

st.set_page_config(page_title="Médico do Esporte", page_icon="🩺", layout="wide")

st.markdown("""
<style>
.section-header{font-size:22px;font-weight:700;color:#1E8449;border-bottom:3px solid #1E8449;padding-bottom:8px;margin:20px 0 16px}
.doc-card{background:linear-gradient(135deg,#e8f4fd,#d6eaf8);border-left:5px solid #2980B9;border-radius:12px;padding:18px;margin:10px 0}
.alert-card{background:#fff5f5;border-left:5px solid #E74C3C;border-radius:12px;padding:16px;margin:8px 0}
.warn-card{background:#fffbf0;border-left:5px solid #F39C12;border-radius:12px;padding:16px;margin:8px 0}
.good-card{background:#f0fff4;border-left:5px solid #27AE60;border-radius:12px;padding:16px;margin:8px 0}
.rec-card{background:linear-gradient(135deg,#f3e5f5,#e8d5f0);border-left:5px solid #8E44AD;border-radius:12px;padding:16px;margin:8px 0}
.priority-tag{display:inline-block;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700;margin-bottom:6px}
.p-critica{background:#E74C3C;color:white}
.p-alta{background:#F39C12;color:white}
.p-media{background:#3498DB;color:white}
.p-positiva{background:#27AE60;color:white}
</style>
""", unsafe_allow_html=True)

# ── Carregar dados ─────────────────────────────────────────────────────────────
profile   = load_profile()
idade     = calc_age(profile.get("data_nascimento", "1981-06-30"))
bio_list  = sorted(load_bioimpedance(), key=lambda x: x["date"])
exams     = load_exams()
results   = exams.get("results", [])
sessions  = {s["id"]: s for s in exams.get("sessions", [])}

latest_bio = bio_list[-1] if bio_list else {}
first_bio  = bio_list[0]  if bio_list else {}
n_bio      = len(bio_list)
n_sessions = len(sessions)

# ── Helpers dinâmicos — sempre lêem a sessão mais recente ─────────────────────
def latest_val(exam_name):
    """Retorna (valor, data_str) da medição mais recente do exame."""
    best_date, best_val = "", None
    for r in results:
        if r["exam"] == exam_name and r["value"] is not None:
            d = sessions.get(r["session_id"], {}).get("date", "")
            if d > best_date:
                best_date, best_val = d, r["value"]
    return best_val, best_date

def all_vals(exam_name):
    """Retorna lista ordenada de (data_str, valor) para todas as medições."""
    pts = []
    for r in results:
        if r["exam"] == exam_name and r["value"] is not None:
            d = sessions.get(r["session_id"], {}).get("date", "")
            if d:
                pts.append((d, r["value"]))
    return sorted(pts)

def _trend(vals):
    return " → ".join(str(v) for _, v in vals) if vals else "—"

def _fmt_date(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%b/%Y")
    except Exception:
        return d

# ── Buscar valores atuais (todos dinâmicos) ───────────────────────────────────
tsh_val,      tsh_date      = latest_val("TSH")
t4l_val,      t4l_date      = latest_val("T4 Livre")
hdl_val,      hdl_date      = latest_val("HDL")
ldl_val,      ldl_date      = latest_val("LDL")
ct_val,       ct_date       = latest_val("Colesterol Total")
tg_val,       tg_date       = latest_val("Triglicérides")
vldl_val,     _             = latest_val("VLDL")
tgo_val,      tgo_date      = latest_val("TGO (AST)")
tgp_val,      tgp_date      = latest_val("TGP (ALT)")
hba1c_val,    hba1c_date    = latest_val("HbA1c")
glicose_val,  glicose_date  = latest_val("Glicose")
homa_val,     homa_date     = latest_val("HOMA-IR")
insulina_val, _             = latest_val("Insulina")
homo_val,     homo_date     = latest_val("Homocisteína")
antihbs_val,  _             = latest_val("Anti-HBs (Imunidade Hep B)")
vitd_val,     vitd_date     = latest_val("Vitamina D (25-OH)")

tsh_hist     = all_vals("TSH")
hdl_hist     = all_vals("HDL")
ldl_hist     = all_vals("LDL")
ct_hist      = all_vals("Colesterol Total")
tg_hist      = all_vals("Triglicérides")
glicose_hist = all_vals("Glicose")
hba1c_hist   = all_vals("HbA1c")
tgo_hist     = all_vals("TGO (AST)")
tgp_hist     = all_vals("TGP (ALT)")

# ── Geração dinâmica de problemas e pontos positivos ─────────────────────────
dyn_issues    = []   # (prio, cor, css, titulo, desc)
dyn_positives = []   # string

# TSH / Tireoide
if tsh_val is not None:
    if tsh_val > 4.30:
        dyn_issues.append(("CRÍTICO", "#E74C3C", "p-critica", "🦋 Hipotireoidismo ativo",
            f"TSH atual: <b>{tsh_val} µUI/mL</b> ({_fmt_date(tsh_date)}) — acima do limite (4,30). "
            f"Progressão: {_trend(tsh_hist)} µUI/mL. "
            "Tratamento com Puran T4 em andamento — avaliar ajuste de dose com a Dra. Celina."))
    else:
        dyn_positives.append(
            f"TSH normalizado: <b>{tsh_val} µUI/mL</b> ({_fmt_date(tsh_date)}) — Puran T4 na dose correta. "
            f"Progressão: {_trend(tsh_hist)} µUI/mL ✅")

# HDL
if hdl_val is not None:
    if hdl_val < 40:
        dyn_issues.append(("ALTA", "#F39C12", "p-alta", "❤️ HDL baixo",
            f"HDL atual: <b>{hdl_val} mg/dL</b> ({_fmt_date(hdl_date)}) — abaixo do mínimo (> 40). "
            f"Progressão: {_trend(hdl_hist)} mg/dL. "
            "Exercício aeróbico e normalização tireoidiana são os principais tratamentos."))
    else:
        dyn_positives.append(
            f"HDL recuperado: <b>{hdl_val} mg/dL</b> ({_fmt_date(hdl_date)}) — dentro do intervalo (> 40). "
            f"Progressão: {_trend(hdl_hist)} mg/dL ✅")

# HOMA-IR / Resistência Insulínica
if homa_val is not None:
    if homa_val > 2.70:
        sev = "CRÍTICO" if homa_val > 5.0 else "ALTA"
        cor = "#E74C3C" if homa_val > 5.0 else "#F39C12"
        css = "p-critica" if homa_val > 5.0 else "p-alta"
        ins_txt = f"Insulina jejum: {insulina_val} µUI/mL (ref 2,5–13,1). " if insulina_val else ""
        dyn_issues.append((sev, cor, css, "🍬 Resistência Insulínica — HOMA-IR elevado",
            f"HOMA-IR: <b>{homa_val}</b> ({_fmt_date(homa_date)}) — ref < 2,70. {ins_txt}"
            "O pâncreas produz insulina em excesso para manter a glicose controlada. "
            "Associado ao hipotireoidismo (TSH já normalizado — melhora esperada) e excesso de peso. "
            "Discutir uso de metformina com a Dra. Celina."))
    else:
        dyn_positives.append(f"Resistência insulínica normalizada: HOMA-IR {homa_val} ✅")

# Glicose
if glicose_val is not None:
    if glicose_val >= 126:
        dyn_issues.append(("CRÍTICO", "#E74C3C", "p-critica", "🍬 Glicose — critério de diabetes",
            f"Glicose jejum: <b>{glicose_val} mg/dL</b> ({_fmt_date(glicose_date)}) — ≥ 126 = critério diagnóstico para DM2. "
            "Avaliação médica urgente."))
    elif glicose_val > 99:
        dyn_issues.append(("MÉDIA", "#3498DB", "p-media", "🍬 Glicose acima do normal",
            f"Glicose jejum: <b>{glicose_val} mg/dL</b> ({_fmt_date(glicose_date)}) — zona pré-diabetes (100–125). "
            f"Progressão: {_trend(glicose_hist)} mg/dL. "
            "Combinada com HOMA-IR elevado, confirma resistência insulínica ativa."))
    else:
        dyn_positives.append(f"Glicose normal: <b>{glicose_val} mg/dL</b> ({_fmt_date(glicose_date)}) ✅")

# HbA1c
if hba1c_val is not None:
    if hba1c_val >= 6.5:
        dyn_issues.append(("CRÍTICO", "#E74C3C", "p-critica", "🍬 Diabetes Mellitus (HbA1c ≥ 6,5%)",
            f"HbA1c: <b>{hba1c_val}%</b> ({_fmt_date(hba1c_date)}) — critério diagnóstico para DM2. Avaliação urgente."))
    elif hba1c_val >= 5.7:
        dyn_issues.append(("MÉDIA", "#3498DB", "p-media", "🍬 Pré-diabetes (HbA1c em zona de risco)",
            f"HbA1c: <b>{hba1c_val}%</b> ({_fmt_date(hba1c_date)}) — zona de risco aumentado (5,7–6,4%). "
            f"Progressão: {_trend(hba1c_hist)}%. Meta: < 5,7%. "
            "Com TSH normalizado + dieta + exercício, melhora esperada no próximo exame."))
    else:
        dyn_positives.append(f"HbA1c normal: <b>{hba1c_val}%</b> ✅")

# TGO / TGP
tgo_high = tgo_val is not None and tgo_val > 34
tgp_high = tgp_val is not None and tgp_val > 49
if tgo_high or tgp_high:
    max_trans = max(tgo_val or 0, tgp_val or 0)
    sev = "CRÍTICO" if max_trans > 60 else "ALTA"
    cor = "#E74C3C" if max_trans > 60 else "#F39C12"
    css = "p-critica" if max_trans > 60 else "p-alta"
    dyn_issues.append((sev, cor, css, "🍺 Transaminases elevadas",
        f"TGO: {_trend(tgo_hist)} U/L (ref < 34) · TGP: {_trend(tgp_hist)} U/L (ref < 49). "
        f"Última medição: {_fmt_date(tgo_date)}. "
        "Com TSH normalizado, melhora espontânea é esperada. Repetir na próxima coleta."))
elif tgo_val is not None and tgp_val is not None:
    dyn_positives.append(f"Transaminases normalizadas: TGO {tgo_val} · TGP {tgp_val} U/L ✅")

# Homocisteína
if homo_val is not None and homo_val > 15:
    dyn_issues.append(("ALTA", "#F39C12", "p-alta", "🧬 Homocisteína elevada",
        f"<b>{homo_val} µmol/L</b> ({_fmt_date(homo_date)}) — ref ≤ 15. "
        "Marcador de risco cardiovascular e cerebrovascular. "
        "Tratamento: B12, B9 (folato) e B6. Não reavaliada desde a última coleta."))

# Hepatite B
if antihbs_val is not None and antihbs_val < 10:
    dyn_issues.append(("ALTA", "#F39C12", "p-alta", "💉 Sem imunidade para Hepatite B",
        f"Anti-HBs: {antihbs_val} mUI/mL — sem proteção. "
        "Vacinação completa (3 doses: 0, 1, 6 meses) indicada o quanto antes."))

# Colesterol Total
if ct_val is not None and ct_val >= 190:
    dyn_issues.append(("MÉDIA", "#3498DB", "p-media", "❤️ Colesterol Total acima do desejável",
        f"Colesterol Total: <b>{ct_val} mg/dL</b> ({_fmt_date(ct_date)}) — ref < 190. "
        f"Progressão: {_trend(ct_hist)} mg/dL. Tendência de melhora progressiva."))
elif ct_val is not None:
    dyn_positives.append(
        f"Colesterol Total dentro do alvo: <b>{ct_val} mg/dL</b> ({_fmt_date(ct_date)}) ✅")

# Triglicérides
if tg_val is not None:
    if tg_val >= 150:
        dyn_issues.append(("ALTA", "#F39C12", "p-alta", "❤️ Triglicérides elevados",
            f"Triglicérides: <b>{tg_val} mg/dL</b> ({_fmt_date(tg_date)}) — ref < 150. "
            f"Progressão: {_trend(tg_hist)} mg/dL."))
    else:
        dyn_positives.append(
            f"Triglicérides normalizados: <b>{tg_val} mg/dL</b> ({_fmt_date(tg_date)}) — "
            f"progressão: {_trend(tg_hist)} mg/dL ✅")

# LDL (tendência positiva)
if ldl_val is not None:
    dyn_positives.append(
        f"LDL em queda consistente: <b>{ldl_val} mg/dL</b> ({_fmt_date(ldl_date)}) — "
        f"progressão: {_trend(ldl_hist)} mg/dL ✅")

# Bioimpedância
if bio_list:
    lat, fi = bio_list[-1], bio_list[0]
    peso_perdido = fi["peso_kg"] - lat["peso_kg"]
    if peso_perdido > 0:
        dyn_positives.append(
            f"Peso reduzindo: {fi['peso_kg']} → <b>{lat['peso_kg']} kg</b> (−{peso_perdido:.1f} kg desde o início) ✅")
    gord_diff = fi["percentual_gordura"] - lat["percentual_gordura"]
    if gord_diff > 0:
        dyn_positives.append(
            f"Gordura corporal caindo: {fi['percentual_gordura']}% → <b>{lat['percentual_gordura']}%</b> "
            f"(−{gord_diff:.1f} pp) ✅")
    musc_diff = lat["musculo_esqueletico_kg"] - fi["musculo_esqueletico_kg"]
    if musc_diff > 0:
        dyn_positives.append(
            f"Massa muscular crescendo: {fi['musculo_esqueletico_kg']} → "
            f"<b>{lat['musculo_esqueletico_kg']} kg</b> (+{musc_diff:.1f} kg) ✅")

dyn_positives += [
    "Hemograma completamente normal nas coletas realizadas ✅",
    "HIV, Hepatite C, Sífilis — todos negativos ✅",
    "PSA normal (próstata) — 0,96 ng/mL ✅",
]

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
st.markdown("## 🩺 Médico do Esporte")
st.markdown(f"""
<div style='background:linear-gradient(135deg,#1a3a5c,#0d2a4a);border-radius:14px;padding:20px 24px;color:white;margin-bottom:20px'>
    <div style='font-size:15px;opacity:0.8;margin-bottom:4px'>ANÁLISE CLÍNICA PERSONALIZADA</div>
    <div style='font-size:22px;font-weight:700'>Dr. IA Esportiva — {profile.get('nome','Leandro Leme Crespo')}</div>
    <div style='font-size:13px;opacity:0.8;margin-top:6px'>
        Análise baseada em: {n_bio} medições de bioimpedância · {n_sessions} coletas laboratoriais · Histórico clínico completo
    </div>
    <div style='font-size:11px;opacity:0.6;margin-top:4px'>⚠️ Esta análise é informativa e complementar. Não substitui a consulta médica.</div>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["🔬 Análise Geral", "🫀 Cardiovascular", "🦋 Tireoide",
                "🍺 Fígado", "🍬 Glicemia", "💪 Composição Corporal",
                "📋 O que pedir à médica", "💊 Suplementos"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 0 — ANÁLISE GERAL
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown("<div class='section-header'>🔬 Resumo Clínico Geral</div>", unsafe_allow_html=True)
    meds = ', '.join(m['nome'] for m in profile.get('medicamentos', []))
    st.markdown(f"""
    <div class='doc-card'>
    <b>Paciente:</b> {profile.get('nome','Leandro Leme Crespo')} · {idade} anos · Masculino · {profile.get('altura_m',1.82)} m<br>
    <b>Medicamentos:</b> {meds or '—'}<br>
    <b>Médica responsável:</b> {profile.get('medico','—')}<br>
    <b>Última bioimpedância:</b> {latest_bio.get('date','—')} · Peso {latest_bio.get('peso_kg','—')} kg · {latest_bio.get('percentual_gordura','—')}% gordura
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🚨 Pontos que requerem atenção")
    if dyn_issues:
        for prio, col, css, title, desc in dyn_issues:
            card_class = "alert-card" if prio == "CRÍTICO" else "warn-card" if prio == "ALTA" else "doc-card"
            st.markdown(f"""<div class='{card_class}'>
                <span class='priority-tag {css}'>{prio}</span> <b>{title}</b><br>
                <span style='font-size:13px'>{desc}</span>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("<div class='good-card'>✅ Nenhum ponto crítico identificado nos dados atuais.</div>",
                    unsafe_allow_html=True)

    st.markdown("### ✅ Pontos Positivos")
    for p in dyn_positives:
        st.markdown(f"<div class='good-card'>{p}</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — CARDIOVASCULAR
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown("<div class='section-header'>❤️ Análise Cardiovascular</div>", unsafe_allow_html=True)

    # HDL — dinâmico
    if hdl_val is not None:
        if hdl_val < 40:
            hdl_card, hdl_icon = "alert-card", "⬇️"
            hdl_status = f"MUITO BAIXO — abaixo do mínimo (> 40 mg/dL)"
        elif hdl_val < 50:
            hdl_card, hdl_icon = "warn-card", "⚠️"
            hdl_status = "dentro do mínimo, mas ainda abaixo do ideal (> 50 mg/dL)"
        else:
            hdl_card, hdl_icon = "good-card", "✅"
            hdl_status = "dentro do intervalo saudável"

        st.markdown(f"""<div class='{hdl_card}'>
        <b>{hdl_icon} HDL: {hdl_val} mg/dL ({_fmt_date(hdl_date)}) — {hdl_status}</b><br>
        Progressão: {_trend(hdl_hist)} mg/dL<br><br>
        {"O HDL (<b>colesterol bom</b>) é protetor cardiovascular. Valores < 40 representam fator de risco independente." if hdl_val < 40 else "O HDL está recuperado após a queda causada pelo hipotireoidismo não tratado."}<br><br>
        <b>Para manter e aumentar o HDL:</b><br>
        • ✅ Exercício aeróbico 150+ min/semana (caminhada, bicicleta, natação)<br>
        • ✅ Ômega-3 EPA+DHA 2–3g/dia<br>
        • ✅ Controle do hipotireoidismo (principal fator — já normalizado)<br>
        • ✅ Redução da gordura visceral (em progresso)
        </div>""", unsafe_allow_html=True)

    # Homocisteína
    if homo_val is not None:
        homo_card = "warn-card" if homo_val > 15 else "good-card"
        homo_icon = "🧬⚠️" if homo_val > 15 else "🧬✅"
        st.markdown(f"""<div class='{homo_card}'>
        <b>{homo_icon} Homocisteína: {homo_val} µmol/L ({_fmt_date(homo_date)}) — ref ≤ 15</b><br>
        {"Marcador de risco para infarto, AVC e doença coronariana. Valores 15–30 = risco moderado." if homo_val > 15 else "Dentro do intervalo normal."}<br><br>
        {"<b>Tratamento:</b><br>• Suplementação de ácido fólico (B9), B12 e B6 — discutir com médica<br>• Deve ser reavaliada na próxima coleta" if homo_val > 15 else ""}
        </div>""", unsafe_allow_html=True)

    # Gráfico lipídios — totalmente dinâmico (lê todos os results)
    lipid_exams = ["Colesterol Total", "HDL", "LDL", "Triglicérides"]
    fig = go.Figure()
    colors = {"Colesterol Total": "#F39C12", "HDL": "#27AE60", "LDL": "#E74C3C", "Triglicérides": "#9B59B6"}
    for exam_name in lipid_exams:
        pts = all_vals(exam_name)
        if pts:
            fig.add_trace(go.Scatter(
                x=[datetime.strptime(d, "%Y-%m-%d") for d, _ in pts],
                y=[v for _, v in pts],
                mode="lines+markers+text",
                text=[str(v) for _, v in pts], textposition="top center",
                textfont=dict(size=11), cliponaxis=False,
                name=exam_name, line=dict(width=2.5, color=colors.get(exam_name, "#333")),
                marker=dict(size=8)
            ))
    for exam_name, ref_val in {"Colesterol Total": 190, "HDL": 40, "LDL": 130, "Triglicérides": 150}.items():
        fig.add_hline(y=ref_val, line_dash="dot", line_color=colors.get(exam_name, "#ccc"), opacity=0.5)
    fig.update_layout(height=400, title="Evolução do Perfil Lipídico", plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(showgrid=False, automargin=True, tickangle=-15),
        yaxis=dict(showgrid=True, gridcolor="#eee", title="mg/dL", automargin=True),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22),
        margin=dict(l=60, r=40, t=60, b=90))
    st.plotly_chart(fig, use_container_width=True)

    # Tabela de risco — valores dinâmicos
    def _risk_icon(val, low=None, high=None, invert=False):
        """Retorna ícone de status. invert=True: maior é melhor (ex: HDL)."""
        if val is None:
            return "—"
        if invert:
            return "✅" if val >= (low or 0) else ("⚠️" if val >= (low or 0) * 0.8 else "🔴")
        return "✅" if (high and val < high) else ("⚠️" if (high and val < high * 1.1) else "🔴")

    st.markdown(f"""
**Risco cardiovascular atual (principais marcadores):**

| Fator | Valor | Status |
|---|---|---|
| Colesterol Total | {ct_val or '—'} mg/dL | {_risk_icon(ct_val, high=190)} |
| HDL | {hdl_val or '—'} mg/dL | {_risk_icon(hdl_val, low=40, invert=True)} |
| LDL | {ldl_val or '—'} mg/dL | {_risk_icon(ldl_val, high=130)} |
| Triglicérides | {tg_val or '—'} mg/dL | {_risk_icon(tg_val, high=150)} |
| Homocisteína | {homo_val or '—'} µmol/L | {'⚠️ Elevada' if homo_val and homo_val > 15 else '✅ Normal' if homo_val else '—'} |
""")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TIREOIDE
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown("<div class='section-header'>🦋 Análise da Tireoide</div>", unsafe_allow_html=True)

    antitg_val, _  = latest_val("Anti-tireoglobulina (anti-TG)")
    antitpo_val, _ = latest_val("Anti-TPO (Antiperoxidase)")

    if tsh_val is not None:
        if tsh_val > 4.30:
            card_class = "alert-card"
            tsh_titulo = "🚨 HIPOTIREOIDISMO ATIVO"
            tsh_cor_txt = "Puran T4 em andamento — ajuste de dose pode ser necessário."
        else:
            card_class = "good-card"
            tsh_titulo = "✅ TIREOIDE NORMALIZADA COM PURAN T4"
            tsh_cor_txt = "O tratamento com levotiroxina está funcionando. Manter acompanhamento semestral."

        st.markdown(f"""<div class='{card_class}'>
        <b>{tsh_titulo}</b><br><br>
        <b>TSH atual:</b> {tsh_val} µUI/mL ({_fmt_date(tsh_date)}) — ref 0,40–4,30<br>
        <b>Progressão do TSH:</b> {_trend(tsh_hist)} µUI/mL<br>
        {f"<b>T4 Livre:</b> {t4l_val} ng/dL ({_fmt_date(t4l_date)}) — ref 0,89–1,76<br>" if t4l_val else ""}
        {f"<b>Anti-TG:</b> {antitg_val} UI/mL — {'POSITIVO (sugestivo de Hashimoto)' if antitg_val and antitg_val > 4.5 else 'normal'}<br>" if antitg_val else ""}
        <br>{tsh_cor_txt}<br><br>
        <b>Impacto do hipotireoidismo no metabolismo:</b><br>
        • Retarda o metabolismo → dificulta emagrecimento<br>
        • Eleva LDL e reduz HDL<br>
        • Aumenta a resistência insulínica (HOMA-IR)<br>
        • Eleva transaminases (TGO/TGP)<br>
        • Com TSH normalizado, todos esses efeitos tendem a reverter gradualmente
        </div>""", unsafe_allow_html=True)

    # Gráfico TSH — dinâmico
    if tsh_hist:
        fig = go.Figure()
        _tsh_y = [v for _, v in tsh_hist]
        fig.add_trace(go.Scatter(
            x=[datetime.strptime(d, "%Y-%m-%d") for d, _ in tsh_hist],
            y=_tsh_y,
            mode="lines+markers+text",
            text=[str(v) for _, v in tsh_hist], textposition="top center",
            textfont=dict(size=11), cliponaxis=False,
            line=dict(color="#8E44AD", width=3), marker=dict(size=12, color="#8E44AD")
        ))
        fig.add_hrect(y0=0.40, y1=4.30, fillcolor="rgba(39,174,96,0.1)",
                      line_width=0, annotation_text="Zona normal")
        fig.add_hrect(y0=4.30, y1=max(_tsh_y) * 1.2 + 1, fillcolor="rgba(231,76,60,0.1)",
                      line_width=0, annotation_text="Hipotireoidismo")
        fig.add_hline(y=4.30, line_dash="dash", line_color="#E74C3C",
                      annotation_text="Limite sup. 4,30")
        fig.update_layout(
            height=340,
            title=f"Evolução do TSH (µUI/mL) — atual: {tsh_val}",
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=False, automargin=True, tickangle=-15),
            yaxis=dict(showgrid=True, gridcolor="#eee", title="TSH µUI/mL",
                       automargin=True, range=[0, max(_tsh_y) * 1.3 + 1]),
            showlegend=False, margin=dict(l=60, r=170, t=60, b=55))
        st.plotly_chart(fig, use_container_width=True)

    tsh_ok = tsh_val is not None and tsh_val <= 4.30
    st.markdown(f"""
**Próximos passos para a tireoide:**
1. {"✅ TSH normalizado — manter dose atual do Puran T4" if tsh_ok else "⚠️ Ajustar dose do Puran T4 com a Dra. Celina"}
2. 🔄 Repetir TSH + T4 Livre em 3–6 meses para confirmar estabilidade
3. 📋 Solicitar ultrassonografia de tireoide (avalia estrutura — Hashimoto causa ecotextura heterogênea)
4. 💊 Meta de TSH: 1,0–2,5 µUI/mL (faixa ideal para tratamento de hipotireoidismo)
5. 📊 Monitorar impacto nos lipídios, HOMA-IR e transaminases nas próximas coletas
""")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — FÍGADO
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown("<div class='section-header'>🍺 Análise Hepática</div>", unsafe_allow_html=True)

    if tgo_val is not None or tgp_val is not None:
        tgo_high2 = tgo_val and tgo_val > 34
        tgp_high2 = tgp_val and tgp_val > 49
        if tgo_high2 or tgp_high2:
            card_class = "alert-card"
            titulo = "⬆️ Transaminases elevadas"
        else:
            card_class = "good-card"
            titulo = "✅ Transaminases dentro do normal"

        st.markdown(f"""<div class='{card_class}'>
        <b>{titulo}</b><br><br>
        TGO (AST): {_trend(tgo_hist)} U/L | Ref: &lt; 34 | Atual: <b>{tgo_val}</b> ({_fmt_date(tgo_date)})<br>
        TGP (ALT): {_trend(tgp_hist)} U/L | Ref: &lt; 49 | Atual: <b>{tgp_val}</b> ({_fmt_date(tgp_date)})<br><br>
        {"<b>Causas mais prováveis:</b><br>1. Hipotireoidismo — causa direta de elevação de transaminases (TSH agora normalizado!)<br>2. Esteatose hepática (fígado gorduroso) — comum em sobrepeso com resistência insulínica<br>3. Exercício muscular intenso — eleva TGO, menos TGP<br><br><b>Com o TSH normalizado, a tendência é de melhora nas próximas coletas.</b>" if (tgo_high2 or tgp_high2) else "Transaminases dentro dos limites normais. Manter monitoramento semestral."}
        </div>""", unsafe_allow_html=True)

    # Gráfico TGO/TGP — dinâmico
    fig = go.Figure()
    for exam_name, color, ref in [("TGO (AST)", "#E74C3C", 34), ("TGP (ALT)", "#C0392B", 49)]:
        pts = all_vals(exam_name)
        if pts:
            fig.add_trace(go.Scatter(
                x=[datetime.strptime(d, "%Y-%m-%d") for d, _ in pts],
                y=[v for _, v in pts],
                mode="lines+markers+text",
                text=[str(v) for _, v in pts], textposition="top center",
                textfont=dict(size=11), cliponaxis=False,
                name=exam_name, line=dict(width=2.5, color=color), marker=dict(size=10)
            ))
            fig.add_hline(y=ref, line_dash="dot", line_color=color, opacity=0.5,
                          annotation_text=f"Ref {exam_name}: {ref}")
    fig.update_layout(height=360, title="Evolução das Transaminases", plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(showgrid=False, automargin=True, tickangle=-15),
        yaxis=dict(showgrid=True, gridcolor="#eee", title="U/L", automargin=True),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22),
        margin=dict(l=60, r=170, t=60, b=90))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
**Ações:**
- 🔍 Com o hipotireoidismo tratado, repetir TGO/TGP na próxima coleta para confirmar normalização
- 🚫 Evitar álcool enquanto houver elevação
- 🥗 Reduzir gorduras saturadas, frituras e açúcar simples (especialmente frutose)
- 💊 Resistência insulínica elevada (HOMA-IR) favorece esteatose — controle glicêmico melhora o fígado
""")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — GLICEMIA
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.markdown("<div class='section-header'>🍬 Análise Glicêmica</div>", unsafe_allow_html=True)

    # HOMA-IR card — dinâmico
    if homa_val is not None:
        if homa_val > 5.0:
            homa_card, homa_icon = "alert-card", "🔴"
        elif homa_val > 2.70:
            homa_card, homa_icon = "warn-card", "⚠️"
        else:
            homa_card, homa_icon = "good-card", "✅"

        st.markdown(f"""<div class='{homa_card}'>
        <b>{homa_icon} Resistência Insulínica — HOMA-IR: {homa_val} ({_fmt_date(homa_date)}) | Ref: &lt; 2,70</b><br>
        {f"Insulina de jejum: <b>{insulina_val} µUI/mL</b> — ref 2,5–13,1<br>" if insulina_val else ""}
        Glicose de jejum: <b>{glicose_val or '—'} mg/dL</b> — ref 70–99<br><br>
        {"O pâncreas está produzindo insulina muito acima do necessário para manter a glicose. Isso é um sinal direto de resistência insulínica significativa, fortemente associada ao hipotireoidismo (TSH estava em 7,48). Com o TSH normalizado, melhora progressiva é esperada.<br><br><b>Discutir com a Dra. Celina o uso de metformina para acelerar a normalização.</b>" if homa_val > 2.70 else "Resistência insulínica dentro dos parâmetros normais."}
        </div>""", unsafe_allow_html=True)

    # HbA1c e Glicose card
    glicose_txt = (f"Glicose: {_trend(glicose_hist)} mg/dL — "
                   f"atual <b>{glicose_val} mg/dL</b> ({_fmt_date(glicose_date)})<br>")
    hba1c_txt = (f"HbA1c: {_trend(hba1c_hist)}% — "
                 f"atual <b>{hba1c_val}%</b> ({_fmt_date(hba1c_date)})<br>") if hba1c_val else ""

    glicose_ok = glicose_val is not None and glicose_val <= 99
    hba1c_ok   = hba1c_val is not None and hba1c_val < 5.7
    glic_card  = "good-card" if (glicose_ok and hba1c_ok) else "warn-card"

    st.markdown(f"""<div class='{glic_card}'>
    <b>{'✅' if glicose_ok and hba1c_ok else '⚠️'} Marcadores glicêmicos</b><br><br>
    {glicose_txt}{hba1c_txt}<br>
    Glicose Média Estimada (GME): <b>{latest_val('Glicose Média Estimada (GME)')[0] or '—'} mg/dL</b><br><br>
    {"HbA1c reflete a média glicêmica dos últimos 3 meses. Ainda na zona de risco (5,7–6,4%) — o próximo exame, com o TSH controlado, deve mostrar melhora real." if hba1c_val and hba1c_val >= 5.7 else ""}
    </div>""", unsafe_allow_html=True)

    # Gráfico — dinâmico
    fig = go.Figure()
    pts_glic = all_vals("Glicose")
    pts_hba1c = all_vals("HbA1c")
    if pts_glic:
        fig.add_trace(go.Scatter(
            x=[datetime.strptime(d, "%Y-%m-%d") for d, _ in pts_glic],
            y=[v for _, v in pts_glic],
            mode="lines+markers+text",
            text=[str(v) for _, v in pts_glic], textposition="top center",
            textfont=dict(size=11), cliponaxis=False,
            name="Glicose (mg/dL)", line=dict(width=2.5, color="#2980B9"),
            marker=dict(size=10)
        ))
    if pts_hba1c:
        fig.add_trace(go.Scatter(
            x=[datetime.strptime(d, "%Y-%m-%d") for d, _ in pts_hba1c],
            y=[v for _, v in pts_hba1c],
            mode="lines+markers+text",
            text=[str(v) for _, v in pts_hba1c], textposition="top center",
            textfont=dict(size=11), cliponaxis=False,
            name="HbA1c (%)", line=dict(width=2.5, color="#8E44AD"),
            marker=dict(size=10), yaxis="y2"
        ))
    fig.update_layout(height=360, title="Glicose e HbA1c ao longo do tempo",
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=False, automargin=True, tickangle=-15),
        yaxis=dict(title="Glicose (mg/dL)", showgrid=True, gridcolor="#eee", automargin=True),
        yaxis2=dict(title="HbA1c (%)", overlaying="y", side="right", automargin=True),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22),
        margin=dict(l=60, r=90, t=60, b=90))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
**Estratégias para controle glicêmico:**
- ✅ Tratamento do hipotireoidismo com Puran T4 — melhora direta a sensibilidade insulínica
- 🚶 Caminhada de 15–20 min após o almoço — reduz o pico de glicose pós-prandial (maior impacto comprovado)
- 🌿 Continuar psyllium antes das refeições (reduz pico glicêmico)
- 🍽️ Reduzir carboidratos refinados (açúcar, farinha branca, sucos) — atacam o HOMA-IR diretamente
- 💊 Discutir metformina com a Dra. Celina (HOMA-IR 6,16 é indicação considerável)
- 📊 Meta próxima coleta: HbA1c < 5,7% · Glicose < 99 mg/dL · HOMA-IR < 2,70
""")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — COMPOSIÇÃO CORPORAL
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[5]:
    st.markdown("<div class='section-header'>💪 Análise da Composição Corporal</div>", unsafe_allow_html=True)

    if bio_list:
        lat = bio_list[-1]
        fi  = bio_list[0]

        st.markdown(f"""
        <div class='doc-card'>
        <b>Altura:</b> {profile.get('altura_m',1.82)} m · <b>Peso meta:</b> 82 kg<br>
        <b>Gordura corporal meta:</b> 15–20% (hoje: {lat['percentual_gordura']:.1f}%)<br>
        <b>Músculo esquelético meta:</b> 40+ kg (hoje: {lat['musculo_esqueletico_kg']:.1f} kg)<br><br>
        <b>Progresso desde o início ({fi['date']} → {lat['date']}):</b><br>
        • Peso: {fi['peso_kg']:.1f} → {lat['peso_kg']:.1f} kg (perdeu {fi['peso_kg']-lat['peso_kg']:.1f} kg) ✅<br>
        • Gordura: {fi['percentual_gordura']:.1f}% → {lat['percentual_gordura']:.1f}% (reduziu {fi['percentual_gordura']-lat['percentual_gordura']:.1f} pp) ✅<br>
        • Músculo: {fi['musculo_esqueletico_kg']:.1f} → {lat['musculo_esqueletico_kg']:.1f} kg
          ({'ganhou' if lat['musculo_esqueletico_kg'] > fi['musculo_esqueletico_kg'] else 'variou'} {abs(lat['musculo_esqueletico_kg']-fi['musculo_esqueletico_kg']):.1f} kg) ✅<br>
        • Gordura visceral: {fi.get('gordura_visceral','—')} → {lat.get('gordura_visceral','—')} (meta: ≤ 9) ✅
        </div>
        """, unsafe_allow_html=True)

        PESO_META = 82.0
        GORD_META = 20.0
        MUSC_META = 40.0

        fig = go.Figure()
        categories = ["Peso↓", "Gordura%↓", "Músculo↑", "Água↑", "TMB↑", "Fat Visc↓"]
        peso_score = min(100, max(0, int((fi["peso_kg"] - lat["peso_kg"]) / max(fi["peso_kg"] - PESO_META, 0.01) * 100)))
        gord_score = min(100, max(0, int((fi["percentual_gordura"] - lat["percentual_gordura"]) / max(fi["percentual_gordura"] - GORD_META, 0.01) * 100)))
        musc_score = min(100, max(0, int((lat["musculo_esqueletico_kg"] - fi["musculo_esqueletico_kg"]) / max(MUSC_META - fi["musculo_esqueletico_kg"], 0.01) * 100)))
        agua_score = min(100, max(0, int((lat.get("percentual_agua", 48) - fi.get("percentual_agua", 47)) / (55 - 47) * 100)))
        tmb_score  = min(100, max(0, int((lat.get("tmb_kcal", 1780) - fi.get("tmb_kcal", 1780)) / 200 * 100)))
        visc_score = min(100, max(0, int((fi.get("gordura_visceral", 13) - lat.get("gordura_visceral", 9)) / max(fi.get("gordura_visceral", 13) - 9, 1) * 100)))

        fig.add_trace(go.Scatterpolar(
            r=[peso_score, gord_score, musc_score, agua_score, tmb_score, visc_score],
            theta=categories, fill="toself",
            name="Progresso (%)", line_color="#1E8449", fillcolor="rgba(30,132,73,0.2)"
        ))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            height=350, title="Progresso em direção às metas (100% = meta atingida)",
            paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    tsh_ok2 = tsh_val is not None and tsh_val <= 4.30
    st.markdown(f"""
**Análise como Médico do Esporte:**

✅ **O que está funcionando:** A combinação de musculação + dieta da nutricionista + Puran T4 está preservando a massa muscular enquanto perde gordura. Este é o cenário ideal para recomposição corporal.

{"✅ **Hipotireoidismo controlado:** Com TSH normalizado (" + str(tsh_val) + " µUI/mL), o metabolismo está responsivo. A perda de gordura deve acelerar progressivamente." if tsh_ok2 else "⚠️ **Hipotireoidismo ainda ativo:** TSH elevado reduz o metabolismo basal e dificulta a perda de gordura. Ajuste de dose com a médica é prioritário."}

⚠️ **Resistência insulínica (HOMA-IR {homa_val or '—'}):** Favorece acúmulo de gordura, especialmente visceral. Melhora com a normalização do TSH + exercício + dieta.

💡 **Para acelerar os resultados:**
- Aumentar cardio para 150 min/semana
- Caminhada de 15 min após as refeições principais
- Manter déficit calórico de 300–500 kcal/dia
- Atingir 7.000+ passos/dia
""")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6 — O QUE PEDIR À MÉDICA
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[6]:
    st.markdown("<div class='section-header'>📋 O que Pedir à Médica</div>", unsafe_allow_html=True)
    st.markdown("""
    > 💡 **Como usar esta seção:** Leve esta lista para a próxima consulta com a Dra. Celina.
    > Itens ✅ já foram realizados — verifique os resultados no sistema.
    """)

    # Gera lista dinamicamente baseada no que já foi feito e no que está pendente
    recs = []

    # TSH normalizado — não é urgente mas precisa de follow-up
    if tsh_val is not None and tsh_val <= 4.30:
        recs.append(("✅ FEITO", "Monitorar dose do Puran T4",
            f"TSH normalizado: {tsh_val} µUI/mL ({_fmt_date(tsh_date)}). "
            "Continuar Puran T4 na dose atual. Repetir TSH + T4 Livre em 6 meses para confirmar estabilidade."))
    else:
        recs.append(("🔴 URGENTE", "Ajustar dose do Puran T4",
            f"TSH atual: {tsh_val} µUI/mL — acima do normal. Requer avaliação e ajuste de dose. "
            "Meta: TSH 1,0–2,5 µUI/mL."))

    # HOMA-IR / Metformina — novo e importante
    if homa_val is not None and homa_val > 2.70:
        recs.append(("🟡 IMPORTANTE", "Avaliar uso de metformina (HOMA-IR elevado)",
            f"HOMA-IR: {homa_val} (ref < 2,70) · Insulina: {insulina_val} µUI/mL. "
            "Resistência insulínica significativa confirmada. Discutir se metformina é indicada "
            "ou se aguarda mais 3 meses para avaliar resposta com TSH normalizado."))

    # Hepatite B — ainda não vacinado
    if antihbs_val is not None and antihbs_val < 10:
        recs.append(("🔴 URGENTE", "Iniciar vacinação contra Hepatite B",
            f"Anti-HBs: {antihbs_val} mUI/mL — sem imunidade. "
            "Esquema de 3 doses (0, 1, 6 meses). Custo baixo, proteção essencial."))

    # TGO/TGP — ainda elevados, mas com TSH controlado
    if tgo_high or tgp_high:
        recs.append(("🟡 IMPORTANTE", "Repetir TGO e TGP (transaminases)",
            f"TGO: {tgo_val} U/L · TGP: {tgp_val} U/L. "
            "Com TSH agora normalizado, espera-se queda espontânea. "
            "Repetir na próxima coleta para confirmar. Se persistirem, solicitar ultrassom abdominal."))

    # Homocisteína — não reavaliada
    if homo_val is not None and homo_val > 15:
        recs.append(("🟡 IMPORTANTE", "Repetir Homocisteína",
            f"Última medição: {homo_val} µmol/L ({_fmt_date(homo_date)}) — não reavaliada. "
            "Solicitar B12 e Ácido Fólico junto. Se ainda elevada: suplementar B12 + B9 + B6."))

    # Exames nunca realizados
    recs.append(("🟡 IMPORTANTE", "Solicitar Testosterona Total e Livre + SHBG",
        "Homem, 45 anos, sobrepeso, resistência insulínica e hipotireoidismo → risco elevado de "
        "hipogonadismo. Testosterona baixa impacta composição corporal, libido e energia. Nunca foi medida."))

    recs.append(("🟡 IMPORTANTE", "Solicitar Vitamina D (25-OH) — nova dosagem",
        f"{'Última medição: ' + str(vitd_val) + ' ng/mL (' + _fmt_date(vitd_date) + ').' if vitd_val else 'Não reavaliada recentemente.'} "
        "Ideal: 40–60 ng/mL. Deficiência é comum em hipotireoidismo e impacta resistência insulínica."))

    recs.append(("🟡 IMPORTANTE", "Solicitar Vitamina B12 e Ácido Fólico",
        "Para investigar causa da homocisteína elevada. Deficiência de B12 é comum em "
        "hipotireoidismo e impacta energia, memória e função neurológica."))

    recs.append(("🟡 IMPORTANTE", "Solicitar Ultrassonografia de Tireoide",
        "Para avaliar estrutura glandular (Hashimoto causa ecotextura heterogênea). "
        "Complementa o diagnóstico de Tireoidite de Hashimoto (Anti-TG positivo)."))

    recs.append(("🟢 CONSIDERAR", "Ferritina + Ferro Sérico + TIBC",
        "Homem ativo com dieta em déficit calórico → risco de deficiência de ferro. "
        "Afeta energia, performance e recuperação muscular. Nunca foi medido."))

    recs.append(("🟢 CONSIDERAR", "PCR Ultrassensível (PCR-us)",
        "Marcador inflamatório de baixo grau. Hashimoto + sobrepeso + resistência insulínica "
        "→ inflamação crônica provável. Útil para avaliar resposta ao tratamento."))

    recs.append(("🟢 CONSIDERAR", "Encaminhamento para Endocrinologista",
        "Manejo especializado de Hashimoto + pré-diabetes + resistência insulínica + sobrepeso. "
        "Complementa o acompanhamento com a Dra. Celina."))

    for prio, title, desc in recs:
        if "✅" in prio:
            color, border = "#f0fff4", "#27AE60"
        elif "URGENTE" in prio:
            color, border = "#fff0f0", "#E74C3C"
        elif "IMPORTANTE" in prio:
            color, border = "#fffbf0", "#F39C12"
        else:
            color, border = "#f0fff4", "#27AE60"
        st.markdown(f"""<div style='background:{color};border-left:4px solid {border};
border-radius:10px;padding:14px;margin:8px 0'>
            <b>{prio} — {title}</b><br>
            <span style='font-size:13px'>{desc}</span>
        </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 7 — SUPLEMENTOS
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[7]:
    st.markdown("<div class='section-header'>💊 Suplementação — Análise e Recomendações</div>",
                unsafe_allow_html=True)
    st.markdown("> ⚠️ **Sempre discuta suplementos com seu médico antes de iniciar.** Esta análise é orientativa.")

    supls = [
        ("Whey Protein", "30–40g pós-treino", "🟢 RECOMENDADO",
         "Essencial para preservar e ganhar massa muscular durante o emagrecimento. "
         "Com déficit calórico e resistência insulínica, a proteína é o principal aliado para não perder músculo."),
        ("Vitamina D3", "4.000 UI/dia", "🟡 CONSIDERAR",
         f"{'Última medição: ' + str(vitd_val) + ' ng/mL — abaixo do ideal (40–60 ng/mL). ' if vitd_val and vitd_val < 40 else ''}"
         "Importante para função imune (Hashimoto!), síntese de testosterona e sensibilidade insulínica. Tomar com refeição."),
        ("Ômega-3 EPA+DHA", "2–3g/dia", "🟡 CONSIDERAR",
         f"HDL atual: {hdl_val or '—'} mg/dL. Ômega-3 eleva HDL, reduz triglicérides e tem ação anti-inflamatória. "
         "Preferir produtos com EPA > DHA para efeito lipídico."),
        ("Complexo B (B12, B9, B6)", "Dose terapêutica — definir com médica", "🟡 CONSIDERAR",
         f"Homocisteína de {homo_val or '—'} µmol/L pode ser tratada com B12 (500–1000 mcg), "
         "B9 (400–800 mcg) e B6 (50 mg). Usar metilcobalamina e metilfolato para melhor absorção."),
        ("Magnésio (quelato)", "200–400 mg/dia", "🟢 RECOMENDADO",
         "Atua na função muscular, qualidade do sono e sensibilidade insulínica — especialmente relevante "
         "com HOMA-IR elevado. Deficiência é comum em hipotireoidismo. Tomar à noite."),
        ("Creatina Monohidratada", "3–5g/dia", "🟢 RECOMENDADO",
         "Melhora performance na musculação, favorece hipertrofia e preserva massa magra durante emagrecimento. "
         "Segura e amplamente estudada."),
        ("Psyllium", "10g/dia com água", "🟢 JÁ NO PLANO",
         "Excelente para controle glicêmico (reduz pico pós-prandial), saciedade e saúde intestinal. Manter."),
        ("Berberina", "500 mg 2–3x/dia com refeições", "🟡 CONSIDERAR",
         f"Com HOMA-IR de {homa_val or '—'}, a berberina tem evidência para melhora da resistência insulínica "
         "por mecanismo similar à metformina. Discutir com a médica antes de iniciar."),
    ]

    for name, dose, status, desc in supls:
        sc_map = {"🟢 RECOMENDADO": "#27AE60", "🟡 CONSIDERAR": "#F39C12", "🟢 JÁ NO PLANO": "#1E8449"}
        bg_map = {"🟢 RECOMENDADO": "#f0fff4", "🟡 CONSIDERAR": "#fffbf0", "🟢 JÁ NO PLANO": "#e8f5e9"}
        key = status.split("(")[0].strip()
        sc = sc_map.get(key, "#333")
        bg = bg_map.get(key, "#f5f5f5")
        st.markdown(f"""<div style='background:{bg};border-left:4px solid {sc};
border-radius:10px;padding:14px;margin:8px 0'>
            <div style='font-size:16px;font-weight:700'>{name} <span style='font-size:12px;color:{sc}'>{status}</span></div>
            <div style='font-size:13px;color:#555;margin:2px 0'><b>Dose:</b> {dose}</div>
            <div style='font-size:13px'>{desc}</div>
        </div>""", unsafe_allow_html=True)
