import streamlit as st
import pandas as pd
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

st.markdown("## 🩺 Médico do Esporte")
st.markdown("""
<div style='background:linear-gradient(135deg,#1a3a5c,#0d2a4a);border-radius:14px;padding:20px 24px;color:white;margin-bottom:20px'>
    <div style='font-size:15px;opacity:0.8;margin-bottom:4px'>ANÁLISE CLÍNICA PERSONALIZADA</div>
    <div style='font-size:22px;font-weight:700'>Dr. IA Esportiva — Leandro Leme Crespo</div>
    <div style='font-size:13px;opacity:0.8;margin-top:6px'>Análise baseada em: 18 medições de bioimpedância · 3 coletas laboratoriais · Histórico clínico completo</div>
    <div style='font-size:11px;opacity:0.6;margin-top:4px'>⚠️ Esta análise é informativa e complementar. Não substitui a consulta médica.</div>
</div>
""", unsafe_allow_html=True)

profile = load_profile()
idade = calc_age(profile.get("data_nascimento","1981-06-30"))
bio_list = sorted(load_bioimpedance(), key=lambda x: x["date"])
exams = load_exams()
results = exams.get("results", [])
sessions = {s["id"]: s for s in exams.get("sessions", [])}

latest_bio = bio_list[-1] if bio_list else {}
first_bio  = bio_list[0]  if bio_list else {}

tabs = st.tabs(["🔬 Análise Geral","🫀 Cardiovascular","🦋 Tireoide","🍺 Fígado","🍬 Glicemia","💪 Composição Corporal","📋 O que pedir à médica","💊 Suplementos"])

# Helper: get latest value for an exam
def latest_val(exam_name):
    found = None
    for sid in ["s003","s002","s001"]:
        for r in results:
            if r["session_id"] == sid and r["exam"] == exam_name and r["value"] is not None:
                return r["value"], sessions.get(sid,{}).get("date","")
    return None, None

with tabs[0]:
    st.markdown("<div class='section-header'>🔬 Resumo Clínico Geral</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='doc-card'>
    <b>Paciente:</b> {profile.get('nome','Leandro Leme Crespo')} · {idade} anos · Masculino · {profile.get('altura_m',1.82)} m<br>
    <b>Medicamentos:</b> {', '.join(m['nome'] for m in profile.get('medicamentos',[]))}<br>
    <b>Médica responsável:</b> {profile.get('medico','—')}<br>
    <b>Última bioimpedância:</b> {latest_bio.get('date','—')} · Peso {latest_bio.get('peso_kg','—')} kg · {latest_bio.get('percentual_gordura','—')}% gordura
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🚨 Pontos Críticos Identificados")
    issues = [
        ("CRÍTICO","#E74C3C","p-critica","🦋 Hipotireoidismo / Hashimoto",
         "TSH: 4,31 → 4,50 → 7,48 µUI/mL (triplicou!). Anti-TG elevado (8,2 UI/mL). "
         "Sugere Tireoidite de Hashimoto. O hipotireoidismo dificulta o emagrecimento, reduz energia, prejudica o controle glicêmico e afeta a recuperação muscular."),
        ("CRÍTICO","#E74C3C","p-critica","🍺 Transaminases elevadas e em alta",
         "TGO: 22 → 53 → 60 U/L. TGP: 34 → 35 → 61 U/L. "
         "Ultrassonografia abdominal foi pedida (aguardar resultado). Causas prováveis: esteatose hepática (fígado gorduroso), hipotireoidismo, ou exercício intenso (TGO). "
         "TGP elevando junto com TGO sugere envolvimento hepático real — não apenas muscular."),
        ("ALTA","#F39C12","p-alta","❤️ HDL baixo e piorando",
         "HDL: 41 → 33 mg/dL. Muito abaixo do mínimo (>40). "
         "HDL baixo é fator de risco cardiovascular independente. "
         "Combinado com LDL 143 e histórico de Colesterol Total 222, o risco aumenta. "
         "Causa provável: sedentarismo + hipotireoidismo."),
        ("ALTA","#F39C12","p-alta","🧬 Homocisteína elevada",
         "19 µmol/L (ref ≤15). Marcador de risco cardiovascular e cerebrovascular. "
         "Geralmente causada por deficiência de B12, B9 (ácido fólico) e B6. "
         "Importante: não foi reavaliada desde outubro/2025."),
        ("MÉDIA","#3498DB","p-media","🍬 Pré-diabetes (HbA1c 5,8–5,9%)",
         "Glicose melhorou (103→96), mas HbA1c subiu levemente (5,8→5,9%). "
         "Com o Puran T4 controlando a tireoide + dieta da nutricionista, a HbA1c deve normalizar. "
         "Meta: HbA1c < 5,7%."),
        ("MÉDIA","#3498DB","p-media","💉 Sem imunidade para Hepatite B",
         "Anti-HBs < 2,0 mUI/mL. Nunca teve contato com o vírus (Anti-HBc negativo). "
         "Deve fazer a vacinação completa (3 doses) o mais rápido possível."),
    ]
    for prio, col, css, title, desc in issues:
        st.markdown(f"""<div class='{"alert-card" if prio=="CRÍTICO" else "warn-card" if prio=="ALTA" else "doc-card"}'>
            <span class='priority-tag {css}'>{prio}</span> <b>{title}</b><br>
            <span style='font-size:13px'>{desc}</span>
        </div>""", unsafe_allow_html=True)

    st.markdown("### ✅ Pontos Positivos")
    positives = [
        "Peso reduzindo consistentemente: -6,2 kg desde o início (99,2 → 93,0 kg)",
        "Gordura corporal caindo: 36% → 29,9% (queda de mais de 6 pontos percentuais)",
        "Massa muscular mantida e crescendo: 35,0 → 36,4 kg (+1,4 kg)",
        "Glicose melhorou: 103 → 96 mg/dL (dentro da normalidade)",
        "Colesterol Total melhorou: 222 → 199 mg/dL",
        "LDL melhorou: 162 → 143 mg/dL",
        "Hemograma completamente normal nas 3 coletas",
        "HIV, Hepatite C, Sífilis — todos negativos",
        "PSA normal (próstata) — 0,96 ng/mL",
        "Musculação regular está preservando e ganhando massa muscular",
    ]
    for p in positives:
        st.markdown(f"<div class='good-card'>✅ {p}</div>", unsafe_allow_html=True)

with tabs[1]:
    st.markdown("<div class='section-header'>❤️ Análise Cardiovascular</div>", unsafe_allow_html=True)
    st.markdown("""
    <div class='alert-card'>
    <b>⬇️ HDL: 33 mg/dL — MUITO BAIXO (referência > 40 mg/dL)</b><br>
    O HDL ("colesterol bom") é protetor cardiovascular. Valores < 40 representam fator de risco independente. O seu caiu de 41 para 33 mg/dL em 7 meses — tendência preocupante.<br><br>
    <b>Causas prováveis:</b><br>
    • Sedentarismo (2.900–5.000 passos/dia — insuficiente)<br>
    • Hipotireoidismo (hormônio T3 baixo eleva LDL e reduz HDL)<br>
    • Excesso de gordura visceral<br><br>
    <b>Como aumentar o HDL naturalmente:</b><br>
    • ✅ Exercício aeróbico 150+ min/semana (caminhada, bicicleta, natação)<br>
    • ✅ Ômega-3 EPA+DHA 2–3g/dia<br>
    • ✅ Tratar o hipotireoidismo (principal causa aqui)<br>
    • ✅ Perda de gordura visceral (já está acontecendo)
    </div>
    """, unsafe_allow_html=True)

    val_homo, d_homo = latest_val("Homocisteína")
    st.markdown(f"""
    <div class='warn-card'>
    <b>🧬 Homocisteína: {val_homo or '19'} µmol/L — ELEVADA (ref ≤ 15)</b><br>
    Marcador de risco para infarto, AVC e doença coronariana. Valores entre 15–30 indicam risco moderado.<br><br>
    <b>Tratamento:</b><br>
    • Suplementação de ácido fólico (B9), B12 e B6 — discutir com médica<br>
    • Redução no consumo de carnes vermelhas processadas<br>
    • Deve ser reavaliada na próxima coleta (não foi medida em 2026)
    </div>
    """, unsafe_allow_html=True)

    # Gráfico lipídios
    lipid_exams = ["Colesterol Total","HDL","LDL","Triglicérides"]
    fig = go.Figure()
    colors = {"Colesterol Total":"#F39C12","HDL":"#27AE60","LDL":"#E74C3C","Triglicérides":"#9B59B6"}
    for exam_name in lipid_exams:
        points = []
        for r in results:
            if r["exam"] == exam_name and r["value"] is not None:
                sid = r["session_id"]
                points.append((sessions.get(sid,{}).get("date",""), r["value"]))
        if points:
            points.sort()
            fig.add_trace(go.Scatter(
                x=[datetime.strptime(p[0],"%Y-%m-%d") for p in points],
                y=[p[1] for p in points],
                mode="lines+markers+text",
                text=[str(p[1]) for p in points], textposition="top center",
                textfont=dict(size=11), cliponaxis=False,
                name=exam_name, line=dict(width=2.5, color=colors.get(exam_name,"#333")),
                marker=dict(size=8)
            ))
    refs = {"Colesterol Total":190,"HDL":40,"LDL":130,"Triglicérides":150}
    for exam_name, ref_val in refs.items():
        fig.add_hline(y=ref_val, line_dash="dot", line_color=colors.get(exam_name,"#ccc"), opacity=0.5)
    fig.update_layout(height=400, title="Evolução do Perfil Lipídico", plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=False, automargin=True, tickangle=-15),
        yaxis=dict(showgrid=True, gridcolor="#eee", title="mg/dL", automargin=True),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22),
        margin=dict(l=60, r=40, t=60, b=90))
    st.plotly_chart(fig, width='stretch')

    st.markdown("""
    **Risco cardiovascular atual (Framingham simplificado):**
    | Fator | Valor | Status |
    |---|---|---|
    | Colesterol Total | 199 mg/dL | ⚠️ Acima do desejável |
    | HDL | 33 mg/dL | 🔴 Muito baixo |
    | LDL | 143 mg/dL | ⚠️ Acima |
    | Triglicérides | 117 mg/dL | ✅ Normal |
    | Pressão arterial | Não informada | — |
    | Tabagismo | Não informado | — |
    | Homocisteína | 19 µmol/L | ⚠️ Elevada |
    | Atividade física | Baixa–moderada | ⚠️ Insuficiente |
    """)

with tabs[2]:
    st.markdown("<div class='section-header'>🦋 Análise da Tireoide</div>", unsafe_allow_html=True)

    tsh_val, tsh_date = latest_val("TSH")
    t4l_val, _ = latest_val("T4 Livre")
    antitg_val, _ = latest_val("Anti-tireoglobulina (anti-TG)")

    st.markdown(f"""
    <div class='alert-card'>
    <b>🚨 HIPOTIREOIDISMO SUBCLÍNICO EVOLUINDO — Possível Tireoidite de Hashimoto</b><br><br>
    <b>Progressão do TSH:</b> 4,31 (out/2025) → 4,50 (mai/06/2026) → 7,48 µUI/mL (mai/13/2026)<br>
    TSH > 4,30 = hipotireoidismo. TSH 7,48 = hipotireoidismo claro, mesmo com T4 Livre normal (1,22 ng/dL).<br><br>
    <b>Anti-tireoglobulina: 8,2 UI/mL</b> (ref < 4,5) → POSITIVO<br>
    Anti-TPO: normal. Anti-TG positivo com TSH elevado é muito sugestivo de <b>Tireoidite de Hashimoto</b> (doença autoimune da tireoide).<br><br>
    <b>O que isso significa para você?</b><br>
    • Hipotireoidismo retarda o metabolismo → dificulta emagrecimento<br>
    • Aumenta o colesterol (especialmente LDL e reduz HDL)<br>
    • Causa fadiga, queda de cabelo, constipação, sensação de frio<br>
    • Pode prejudicar a força muscular e a recuperação pós-treino<br>
    • Hipotireoidismo dificulta o controle glicêmico e prejudica o metabolismo<br><br>
    <b>Em tratamento:</b> Puran T4 (levotiroxina) iniciado em jun/2026. Normalização do TSH esperada em 8–12 semanas. Monitorar dose e repetir TSH + T4 Livre em 3 meses.
    </div>
    """, unsafe_allow_html=True)

    # Gráfico TSH
    tsh_points = [(r["session_id"], r["value"]) for r in results if r["exam"] == "TSH" and r["value"] is not None]
    tsh_data = [(sessions.get(sid,{}).get("date",""), val) for sid, val in tsh_points]
    tsh_data.sort()

    fig = go.Figure()
    _tsh_vals = [v for d,v in tsh_data]
    _tsh_pad = max((_tsh_vals[-1] - _tsh_vals[0]) * 0.4, 1.0) if len(_tsh_vals) > 1 else 1.5
    fig.add_trace(go.Scatter(
        x=[datetime.strptime(d,"%Y-%m-%d") for d,v in tsh_data],
        y=[v for d,v in tsh_data],
        mode="lines+markers+text",
        text=[str(v) for d,v in tsh_data], textposition="top center",
        textfont=dict(size=11), cliponaxis=False,
        line=dict(color="#8E44AD", width=3), marker=dict(size=12, color="#8E44AD")
    ))
    fig.add_hrect(y0=0.40, y1=4.30, fillcolor="rgba(39,174,96,0.1)", line_width=0, annotation_text="Zona normal")
    fig.add_hrect(y0=4.30, y1=10, fillcolor="rgba(231,76,60,0.1)", line_width=0, annotation_text="Hipotireoidismo")
    fig.add_hline(y=4.30, line_dash="dash", line_color="#E74C3C", annotation_text="Limite sup. 4,30")
    fig.update_layout(height=340, title="Evolução do TSH (µUI/mL) — Tendência Preocupante",
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=False, automargin=True, tickangle=-15),
        yaxis=dict(showgrid=True, gridcolor="#eee", title="TSH µUI/mL", automargin=True,
                   range=[0, max(_tsh_vals) + _tsh_pad * 1.5] if _tsh_vals else None),
        showlegend=False, margin=dict(l=60, r=170, t=60, b=55))
    st.plotly_chart(fig, width='stretch')

    st.markdown("""
    **Próximos passos para a tireoide:**
    1. ✅ **Puran T4 (levotiroxina) já iniciado** — manter conforme prescrição da Dra. Celina
    2. 📋 Solicitar ultrassonografia de tireoide (para avaliar estrutura — Hashimoto causa ecotextura heterogênea)
    3. 🔄 Repetir TSH, T4 Livre em 8–12 semanas para avaliar resposta à dose
    4. 💊 Ajuste de dose se TSH não normalizar (meta: 1,0–2,5 µUI/mL)
    5. 📊 Esperar impacto positivo nos lipídios — tratamento da tireoide tende a melhorar HDL e LDL
    """)

with tabs[3]:
    st.markdown("<div class='section-header'>🍺 Análise Hepática</div>", unsafe_allow_html=True)
    st.markdown("""
    <div class='alert-card'>
    <b>⬆️ TGO e TGP elevados e piores na última coleta</b><br><br>
    TGO (AST): 22 (out/25) → 53 (mai/06) → 60 U/L (mai/13) | Ref: < 34<br>
    TGP (ALT): 34 (out/25) → 35 (mai/06) → 61 U/L (mai/13) | Ref: 10–49<br><br>
    <b>Interpretação:</b><br>
    • TGO isoladamente elevado → pode ser muscular (musculação intensa libera TGO/CK)<br>
    • TGP elevando junto com TGO → sinal de envolvimento hepático real<br>
    • Padrão: TGP > TGO sugere lesão hepática (NAFLD, hepatite medicamentosa)<br>
    • Ultrassonografia abdominal foi solicitada (aguardar resultado!)<br><br>
    <b>Causas mais prováveis:</b><br>
    1. Doença hepática gordurosa não alcoólica (NAFLD/esteatose) — comum em sobrepeso<br>
    2. Hipotireoidismo — pode causar elevação de transaminases (mais comum do que se pensa)<br>
    3. Exercício muscular intenso — afeta TGO mas menos TGP<br>
    4. Outros medicamentos ou suplementos<br><br>
    <b>⚠️ Se a ultrassonografia confirmar esteatose hepática: ajuste alimentar mais restrito em gordura saturada e frutose.</b>
    </div>
    """, unsafe_allow_html=True)

    # Gráfico TGO/TGP
    fig = go.Figure()
    for exam_name, color, ref in [("TGO (AST)","#E74C3C",34),("TGP (ALT)","#C0392B",49)]:
        pts = [(sessions.get(r["session_id"],{}).get("date",""), r["value"])
               for r in results if r["exam"] == exam_name and r["value"] is not None]
        pts.sort()
        if pts:
            fig.add_trace(go.Scatter(
                x=[datetime.strptime(d,"%Y-%m-%d") for d,v in pts],
                y=[v for d,v in pts],
                mode="lines+markers+text",
                text=[str(v) for d,v in pts], textposition="top center",
                textfont=dict(size=11), cliponaxis=False,
                name=exam_name, line=dict(width=2.5, color=color), marker=dict(size=10)
            ))
            fig.add_hline(y=ref, line_dash="dot", line_color=color, opacity=0.5,
                          annotation_text=f"Ref sup {exam_name}: {ref}")
    fig.update_layout(height=360, title="Evolução das Transaminases", plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=False, automargin=True, tickangle=-15),
        yaxis=dict(showgrid=True, gridcolor="#eee", title="U/L", automargin=True),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22),
        margin=dict(l=60, r=170, t=60, b=90))
    st.plotly_chart(fig, width='stretch')

    st.markdown("""
    **Ações imediatas:**
    - 🔍 Aguardar resultado da ultrassonografia abdominal (já solicitada)
    - 🚫 Evitar álcool completamente enquanto transaminases estiverem elevadas
    - 🥗 Reduzir gorduras saturadas, frituras e açúcar simples
    - 💊 Com o tratamento do hipotireoidismo (Puran T4), as transaminases tendem a normalizar
    - 📋 Repetir TGO e TGP em 30–60 dias para avaliar tendência
    """)

with tabs[4]:
    st.markdown("<div class='section-header'>🍬 Análise Glicêmica</div>", unsafe_allow_html=True)
    st.markdown("""
    <div class='warn-card'>
    <b>Pré-diabetes (HbA1c 5,8–5,9%)</b><br><br>
    HbA1c: 5,8% (out/2025) → 5,9% (mai/2026) · Referência: < 5,7% normal | 5,7–6,4% pré-diabetes<br>
    Glicose jejum: 103 (out/2025) → 96 mg/dL (mai/2026) → normalizou ✅<br><br>
    <b>Análise:</b><br>
    • Glicose melhorou significativamente (dieta + perda de peso + psyllium)<br>
    • HbA1c subiu levemente (reflete média dos últimos 3 meses)<br>
    • Hipotireoidismo pode prejudicar sensibilidade à insulina<br>
    • Com tratamento da tireoide e continuidade do programa, HbA1c deve normalizar<br><br>
    <b>Meta próxima coleta:</b> HbA1c < 5,7% + glicose < 99 mg/dL
    </div>
    """, unsafe_allow_html=True)

    fig = go.Figure()
    for exam_name, color, ref_min, ref_max, title in [
        ("Glicose","#2980B9",70,99,"Glicose (mg/dL)"),
        ("HbA1c","#8E44AD",None,5.7,"HbA1c (%)")
    ]:
        pts = [(sessions.get(r["session_id"],{}).get("date",""), r["value"])
               for r in results if r["exam"] == exam_name and r["value"] is not None]
        pts.sort()
        if pts:
            fig.add_trace(go.Scatter(
                x=[datetime.strptime(d,"%Y-%m-%d") for d,v in pts],
                y=[v for d,v in pts],
                mode="lines+markers+text",
                text=[str(v) for d,v in pts], textposition="top center",
                textfont=dict(size=11), cliponaxis=False,
                name=exam_name, line=dict(width=2.5, color=color), marker=dict(size=10),
                yaxis="y2" if "HbA1c" in exam_name else "y"
            ))
    fig.update_layout(height=360, title="Glicose vs. HbA1c ao longo do tempo", plot_bgcolor="white",
        paper_bgcolor="white", xaxis=dict(showgrid=False, automargin=True, tickangle=-15),
        yaxis=dict(title="Glicose (mg/dL)", showgrid=True, gridcolor="#eee", automargin=True),
        yaxis2=dict(title="HbA1c (%)", overlaying="y", side="right", automargin=True),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22),
        margin=dict(l=60, r=90, t=60, b=90))
    st.plotly_chart(fig, width='stretch')

    st.markdown("""
    **Estratégias para controle glicêmico:**
    - ✅ Tratar hipotireoidismo com Puran T4 — melhora sensibilidade insulínica diretamente
    - 🌿 Continuar psyllium (reduz pico glicêmico pós-prandial quando tomado antes das refeições)
    - 🚶 Caminhada de 10–15 min após almoço e jantar (reduz pico pós-prandial de glicose)
    - 🥗 Plano nutricional da nutricionista está adequado (rico em fibras, proteínas)
    - 📊 Monitorar com smartwatch ou glicosímetro se disponível
    - 🔄 Tratar hipotireoidismo (melhora sensibilidade insulínica)
    """)

with tabs[5]:
    st.markdown("<div class='section-header'>💪 Análise da Composição Corporal</div>", unsafe_allow_html=True)

    if bio_list:
        lat = bio_list[-1]
        fi  = bio_list[0]

        st.markdown(f"""
        <div class='doc-card'>
        <b>Altura:</b> 1,82 m · <b>Peso meta:</b> 82 kg (IMC ~24,8)<br>
        <b>Gordura corporal meta:</b> 15–20% (hoje: {lat['percentual_gordura']:.1f}%)<br>
        <b>Músculo esquelético meta:</b> 40+ kg (hoje: {lat['musculo_esqueletico_kg']:.1f} kg)<br><br>
        <b>Progresso desde o início:</b><br>
        • Peso: {fi['peso_kg']:.1f} → {lat['peso_kg']:.1f} kg (perdeu {fi['peso_kg']-lat['peso_kg']:.1f} kg) ✅<br>
        • Gordura: {fi['percentual_gordura']:.1f}% → {lat['percentual_gordura']:.1f}% (reduziu {fi['percentual_gordura']-lat['percentual_gordura']:.1f} pp) ✅<br>
        • Músculo: {fi['musculo_esqueletico_kg']:.1f} → {lat['musculo_esqueletico_kg']:.1f} kg (ganhou {lat['musculo_esqueletico_kg']-fi['musculo_esqueletico_kg']:.1f} kg) ✅<br>
        • Gordura visceral: {fi.get('gordura_visceral','—')} → {lat.get('gordura_visceral','—')} (meta: ≤ 9) ✅
        </div>
        """, unsafe_allow_html=True)

        # Radar chart composição
        fig = go.Figure()
        categories = ["Peso↓","Gordura%↓","Músculo↑","Água↑","TMB↑","Fat Visc↓"]
        peso_score  = min(100, max(0, int((fi["peso_kg"]-lat["peso_kg"])/(fi["peso_kg"]-82)*100)))
        gord_score  = min(100, max(0, int((fi["percentual_gordura"]-lat["percentual_gordura"])/(fi["percentual_gordura"]-20)*100)))
        musc_score  = min(100, max(0, int((lat["musculo_esqueletico_kg"]-fi["musculo_esqueletico_kg"])/(40-fi["musculo_esqueletico_kg"])*100)))
        agua_score  = min(100, max(0, int((lat.get("percentual_agua",48)-fi.get("percentual_agua",47))/(55-47)*100)))
        tmb_score   = min(100, max(0, int((lat.get("tmb_kcal",1780)-fi.get("tmb_kcal",1780))/200*100)))
        visc_score  = min(100, max(0, int((fi.get("gordura_visceral",13)-lat.get("gordura_visceral",9))/(13-9)*100)))
        values = [peso_score, gord_score, musc_score, agua_score, tmb_score, visc_score]
        fig.add_trace(go.Scatterpolar(r=values, theta=categories, fill="toself",
            name="Progresso (%)", line_color="#1E8449", fillcolor="rgba(30,132,73,0.2)"))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100])),
            height=350, title="Progresso em direção às metas (100% = meta atingida)",
            paper_bgcolor="white")
        st.plotly_chart(fig, width='stretch')

    st.markdown("""
    **Análise como Médico do Esporte:**

    ✅ **O que está funcionando:** A combinação de musculação + dieta da nutricionista + Puran T4 está preservando a massa muscular enquanto perde gordura. Isso é o cenário ideal para recomposição corporal.

    ⚠️ **O hipotireoidismo está dificultando o progresso.** Com TSH de 7,48, o metabolismo está reduzido. O tratamento com levotiroxina provavelmente vai acelerar a perda de gordura e melhorar a retenção muscular.

    🎯 **Projeção:** Mantendo o ritmo atual (aprox. -0,5 a -1 kg/mês), você chegará ao peso meta (~82 kg) em aproximadamente **8–12 meses**, dependendo do tratamento da tireoide.

    💡 **Para aumentar a velocidade segura de perda:**
    - Aumentar cardio para 150 min/semana
    - Atingir 7.000+ passos/dia consistentemente
    - Manter déficit calórico de 300–500 kcal/dia
    """)

with tabs[6]:
    st.markdown("<div class='section-header'>📋 O que Pedir à Médica</div>", unsafe_allow_html=True)
    st.markdown("""
    > 💡 **Como usar esta seção:** Leve esta lista para a próxima consulta com a Dra. Celina. Estas são sugestões baseadas no seu histórico — ela decidirá o que é adequado para o seu caso.
    """)

    recs = [
        ("🟡 IMPORTANTE","Monitorar e ajustar dose de Puran T4","Leandro já iniciou levotiroxina em jun/2026. Repetir TSH + T4 Livre em 8–12 semanas para verificar se a dose está correta. Meta: TSH 1,0–2,5 µUI/mL. Tratamento adequado melhora: energia, HDL, controle glicêmico, composição corporal."),
        ("🔴 URGENTE","Iniciar vacinação contra Hepatite B","Anti-HBs < 2,0 mUI/mL + Anti-HBc negativo = nunca vacinou e sem imunidade. Esquema de 3 doses (0, 1, 6 meses). Reforço necessário."),
        ("🔴 URGENTE","Verificar resultado da ultrassonografia abdominal","Solicitada em 12/05/2026 por TGP/TGO elevados. Se confirmar esteatose hepática: ajustar dieta (reduzir gordura saturada e frutose) e repetir exames em 60 dias."),
        ("🟡 IMPORTANTE","Solicitar Testosterona Total e Livre + SHBG + LH + FSH","Homem, 44 anos, sobrepeso, hipotireoidismo → risco alto de deficiência de testosterona. Nunca foi medida. Testosterona baixa impacta: libido, massa muscular, composição corporal, humor, energia."),
        ("🟡 IMPORTANTE","Solicitar Homocisteína (repetir)","Estava 19 µmol/L em out/2025. Não reavaliada. Importante para risco cardiovascular. Se ainda elevada: suplementar B12 + B9 + B6."),
        ("🟡 IMPORTANTE","Solicitar Vitamina B12 e Ácido Fólico","Para investigar causa da homocisteína elevada e deficiência associada ao hipotireoidismo."),
        ("🟡 IMPORTANTE","Solicitar Vitamina D (25-OH) — nova dosagem","Estava borderline (23,93 ng/mL) em out/2025. Ideal: 40–60 ng/mL. D3 tem papel na função tireoidiana e imunidade."),
        ("🟡 IMPORTANTE","Solicitar Ultrassonografia da Tireoide","Para avaliar estrutura glandular (Hashimoto causa ecotextura heterogênea). Complementa o diagnóstico."),
        ("🟡 IMPORTANTE","Solicitar Insulina de Jejum + HOMA-IR","Avaliar resistência insulínica (HbA1c 5,9% — zona pré-diabetes). Importante para ajuste da dieta e avaliação do impacto do Puran T4 na sensibilidade insulínica."),
        ("🟢 CONSIDERAR","Ferritina + Ferro Sérico + TIBC","Homem ativo com dieta em déficit calórico — risco de deficiência de ferro (afeta energia e performance). Não foi medido."),
        ("🟢 CONSIDERAR","PCR Ultrassensível (PCR-us)","Marcador inflamatório de baixo grau. Hashimoto + sobrepeso + transaminases elevadas → risco de inflamação crônica de baixo grau."),
        ("🟢 CONSIDERAR","Encaminhamento para Fisioterapia","RM lombo-sacra realizada — supervisão para exercícios é importante. Pode prevenir lesão e otimizar treino."),
        ("🟢 CONSIDERAR","Encaminhamento para Endocrinologista","Para manejo especializado de Hashimoto + pré-diabetes + sobrepeso. Pode ser necessário além do acompanhamento clínico."),
        ("🟢 CONSIDERAR","Ômega-3 EPA+DHA 2g/dia","HDL baixo (33 mg/dL). Ômega-3 reduz triglicérides e tem ação anti-inflamatória. Seguro e sem custo alto."),
    ]
    for prio, title, desc in recs:
        color = "#fff0f0" if "URGENTE" in prio else "#fffbf0" if "IMPORTANTE" in prio else "#f0fff4"
        border = "#E74C3C" if "URGENTE" in prio else "#F39C12" if "IMPORTANTE" in prio else "#27AE60"
        st.markdown(f"""<div style='background:{color};border-left:4px solid {border};border-radius:10px;padding:14px;margin:8px 0'>
            <b>{prio} — {title}</b><br>
            <span style='font-size:13px'>{desc}</span>
        </div>""", unsafe_allow_html=True)

with tabs[7]:
    st.markdown("<div class='section-header'>💊 Suplementação — Análise e Recomendações</div>", unsafe_allow_html=True)
    st.markdown("""
    > ⚠️ **Sempre discuta suplementos com seu médico antes de iniciar.** Esta análise é orientativa.
    """)

    supls = [
        ("Whey Protein","30–40g pós-treino","🟢 RECOMENDADO",
         "Já no plano da nutricionista (2 medidas de 30g). Essencial para preservar e ganhar massa muscular durante o emagrecimento. Com déficit calórico, a proteína é o principal aliado para não perder músculo."),
        ("Vitamina D3","4.000 UI/dia","🟡 CONSIDERAR",
         "Vitamina D estava 23,93 ng/mL (borderline). Ideal: 40–60 ng/mL. Importante para: função imune (Hashimoto!), saúde óssea, síntese de testosterona, músculo. Suplementar com refeição (lipossolúvel)."),
        ("Ômega-3 EPA+DHA","2–3g/dia","🟡 CONSIDERAR",
         "HDL baixo (33 mg/dL). Ômega-3 reduz triglicérides, tem ação anti-inflamatória e suporte cardiovascular. Tomar com refeição. Preferir produtos com EPA > DHA para lipídios."),
        ("Complexo B (B12, B9, B6)","Dose terapêutica — ver com médica","🟡 CONSIDERAR",
         "Homocisteína de 19 µmol/L é tratada com B12 (500–1000mcg), B9/folato (400–800mcg) e B6 (50mg). Usar preferencialmente vitamina B12 na forma metilcobalamina e folato como metilfolato para melhor absorção."),
        ("Magnésio (quelato)","200–400mg/dia","🟢 RECOMENDADO",
         "Atua na função muscular, qualidade do sono, sensibilidade insulínica e síntese hormonal. Deficiência é comum em pessoas com hipotireoidismo e dieta restritiva. Tomar à noite (melhora o sono)."),
        ("Creatina Monohidratada","3–5g/dia","🟢 RECOMENDADO (atletas)",
         "Melhora performance na musculação, favorece hipertrofia e preserva massa magra durante emagrecimento. Segura e bem estudada. Não contraindicada para rim saudável (seu eGFR variou mas está ok)."),
        ("Psyllium","10g/dia com água","🟢 JÁ NO PLANO",
         "Já indicado pela nutricionista. Excelente para controle glicêmico (reduz pico pós-prandial), saciedade e saúde intestinal. Manter."),
        ("Probióticos","Cepa específica — ver com médica","🟡 CONSIDERAR",
         "Estudos sugerem impacto positivo em hipotireoidismo autoimune (Hashimoto). Melhora a microbiota, pode reduzir inflamação e melhorar absorção de levotiroxina."),
    ]

    for name, dose, status, desc in supls:
        status_color_map = {"🟢 RECOMENDADO":"#27AE60","🟡 CONSIDERAR":"#F39C12","🟢 JÁ NO PLANO":"#1E8449"}
        bg_map = {"🟢 RECOMENDADO":"#f0fff4","🟡 CONSIDERAR":"#fffbf0","🟢 JÁ NO PLANO":"#e8f5e9"}
        sc = status_color_map.get(status.split("(")[0].strip(), "#333")
        bg = bg_map.get(status.split("(")[0].strip(), "#f5f5f5")
        st.markdown(f"""<div style='background:{bg};border-left:4px solid {sc};border-radius:10px;padding:14px;margin:8px 0'>
            <div style='font-size:16px;font-weight:700'>{name} <span style='font-size:12px;color:{sc}'>{status}</span></div>
            <div style='font-size:13px;color:#555;margin:2px 0'><b>Dose:</b> {dose}</div>
            <div style='font-size:13px'>{desc}</div>
        </div>""", unsafe_allow_html=True)
