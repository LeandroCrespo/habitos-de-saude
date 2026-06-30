import streamlit as st
import pandas as pd
from datetime import date, datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_manager import (load_profile, load_bioimpedance, load_exams,
                                 load_exercises, load_food_log, calc_age)

st.set_page_config(page_title="Relatórios", page_icon="📋", layout="wide")

st.markdown("""
<style>
.section-header{font-size:22px;font-weight:700;color:#1E8449;border-bottom:3px solid #1E8449;padding-bottom:8px;margin:20px 0 16px}
.report-area{background:#f8f9fa;border:1px solid #ddd;border-radius:10px;padding:20px;font-family:monospace;font-size:13px}
</style>
""", unsafe_allow_html=True)

st.markdown("## 📋 Gerador de Relatórios")

profile = load_profile()
bio_list = sorted(load_bioimpedance(), key=lambda x: x["date"])
exams_data = load_exams()
results = exams_data.get("results", [])
sessions = {s["id"]: s for s in exams_data.get("sessions", [])}
exercises = load_exercises()
food_logs = load_food_log()

idade = calc_age(profile.get("data_nascimento","1981-06-30"))
hoje = date.today().strftime("%d/%m/%Y")

report_type = st.selectbox("Tipo de Relatório:", [
    "Resumo Geral de Saúde",
    "Relatório de Bioimpedância",
    "Relatório de Exames Laboratoriais",
    "Lista para a Médica (O que pedir)",
    "Relatório de Progresso Mensal",
])

def gerar_resumo_geral():
    lat = bio_list[-1] if bio_list else {}
    fi  = bio_list[0]  if bio_list else {}
    n_alerta = sum(1 for r in results if r["status"] in ("alta","baixa") and r["session_id"] == "s003")

    txt = f"""╔══════════════════════════════════════════════════════════════╗
║         RELATÓRIO DE SAÚDE — LEANDRO LEME CRESPO             ║
║                  Gerado em: {hoje}                     ║
╚══════════════════════════════════════════════════════════════╝

DADOS PESSOAIS
──────────────
Nome: {profile.get('nome','Leandro Leme Crespo')}
Data de Nascimento: 30/06/1981 | Idade: {idade} anos
Sexo: Masculino | Altura: {profile.get('altura_m',1.82)} m
Médica: {profile.get('medico','Dra. Celina Prado de Lima Souza')}
Nutricionista: {profile.get('nutricionista','Maria Eduarda Tardin')}
Medicamentos: {', '.join(m['nome'] for m in profile.get('medicamentos',[]))}

BIOIMPEDÂNCIA — ÚLTIMA MEDIÇÃO
───────────────────────────────
Data: {datetime.strptime(lat.get('date','2026-06-24'),'%Y-%m-%d').strftime('%d/%m/%Y')}
Peso: {lat.get('peso_kg','—')} kg | IMC: {lat.get('imc','—')}
Gordura: {lat.get('percentual_gordura','—')}% ({lat.get('massa_gordura_kg','—')} kg)
Músculo Esq.: {lat.get('musculo_esqueletico_kg','—')} kg ({lat.get('percentual_musculo','—')}%)
Água: {lat.get('percentual_agua','—')}% | Massa Óssea: {lat.get('massa_ossea_kg','—')} kg
TMB: {lat.get('tmb_kcal','—')} kcal | Gordura Visceral: {lat.get('gordura_visceral','—')}

PROGRESSO TOTAL (desde início)
────────────────────────────────
Peso: {fi.get('peso_kg','—')} → {lat.get('peso_kg','—')} kg (Δ {round(lat.get('peso_kg',0)-fi.get('peso_kg',0),1)} kg)
Gordura: {fi.get('percentual_gordura','—')}% → {lat.get('percentual_gordura','—')}% (Δ {round(lat.get('percentual_gordura',0)-fi.get('percentual_gordura',0),1)} pp)
Músculo: {fi.get('musculo_esqueletico_kg','—')} → {lat.get('musculo_esqueletico_kg','—')} kg (Δ +{round(lat.get('musculo_esqueletico_kg',0)-fi.get('musculo_esqueletico_kg',0),1)} kg)

EXAMES LABORATORIAIS — ALERTAS (última coleta 13/05/2026)
──────────────────────────────────────────────────────────
{n_alerta} parâmetros com valores fora da referência:

⬆️ TSH: 7,48 µUI/mL (ref 0,40–4,30) — HIPOTIREOIDISMO
⬆️ TGO: 60 U/L (ref < 34) — ELEVADO
⬆️ TGP: 61 U/L (ref 10–49) — ELEVADO
⬆️ Anti-tireoglobulina: 8,2 UI/mL (ref < 4,5) — HASHIMOTO?
⬇️ HDL: 33 mg/dL (ref > 40) — BAIXO
⬆️ LDL: 143 mg/dL (ref < 130) — ELEVADO
⬆️ Colesterol Total: 199 mg/dL (ref < 190) — LEVEMENTE ELEVADO
⬆️ HbA1c: 5,9% (ref < 5,7%) — PRÉ-DIABETES
⬇️ Anti-HBs: < 2,0 mUI/mL (ref > 10) — SEM IMUNIDADE HEP B

CONDIÇÕES IDENTIFICADAS
────────────────────────
• Hipotireoidismo subclínico (TSH progressivo 4,31→4,50→7,48)
• Possível Tireoidite de Hashimoto (anti-TG positivo)
• Dislipidemia (HDL baixo, LDL elevado)
• Pré-diabetes (HbA1c 5,8–5,9%)
• Transaminases elevadas (investigar com ultrassom)
• Homocisteína elevada (19 µmol/L — out/2025)
• Sem imunidade para Hepatite B
• Sobrepeso (IMC {lat.get('imc','—')})
• Coluna lombo-sacra — RM realizada

PONTOS POSITIVOS
─────────────────
✅ Perda consistente de peso e gordura
✅ Ganho de massa muscular
✅ Glicose normalizada (103→96 mg/dL)
✅ Colesterol total e LDL melhorando
✅ Hemograma normal
✅ PSA normal
✅ Função renal estável

══════════════════════════════════════════════════════════════
AVISO: Este relatório é de acompanhamento pessoal e não
substitui orientação médica profissional.
══════════════════════════════════════════════════════════════"""
    return txt


def gerar_relatorio_bio():
    txt = f"""RELATÓRIO DE BIOIMPEDÂNCIA — LEANDRO LEME CRESPO
Gerado em: {hoje}
══════════════════════════════════════════════════

HISTÓRICO COMPLETO DE MEDIÇÕES
"""
    for b in bio_list:
        d = datetime.strptime(b["date"],"%Y-%m-%d").strftime("%d/%m/%Y")
        txt += f"""
──────── {d} ────────
Peso: {b['peso_kg']} kg | IMC: {b['imc']}
Gordura: {b['percentual_gordura']}% ({b['massa_gordura_kg']} kg)
Músculo Esq.: {b['musculo_esqueletico_kg']} kg ({b.get('percentual_musculo','—')}%)
Água: {b.get('percentual_agua','—')}% | Óssea: {b.get('massa_ossea_kg','—')} kg
TMB: {b.get('tmb_kcal','—')} kcal | Gord. Visceral: {b.get('gordura_visceral','—')}
Dispositivo: {b.get('device','—')}
{f"Obs: {b['notes']}" if b.get('notes') else ''}"""

    if bio_list:
        fi = bio_list[0]
        la = bio_list[-1]
        txt += f"""

══════════════════════════════════════════════════
RESUMO DO PROGRESSO
══════════════════════════════════════════════════
Período: {datetime.strptime(fi['date'],'%Y-%m-%d').strftime('%d/%m/%Y')} a {datetime.strptime(la['date'],'%Y-%m-%d').strftime('%d/%m/%Y')}
Peso perdido: {round(fi['peso_kg']-la['peso_kg'],1)} kg
Gordura perdida: {round(fi['percentual_gordura']-la['percentual_gordura'],1)} pontos percentuais
Gordura perdida (kg): {round(fi['massa_gordura_kg']-la['massa_gordura_kg'],1)} kg
Músculo ganho: {round(la['musculo_esqueletico_kg']-fi['musculo_esqueletico_kg'],1)} kg
IMC: {fi['imc']} → {la['imc']}
"""
    return txt


def gerar_lista_medica():
    txt = f"""LISTA PARA CONSULTA MÉDICA — LEANDRO LEME CRESPO
Gerado em: {hoje}
Data de nascimento: 30/06/1981 | {idade} anos
Médica: Dra. Celina Prado de Lima Souza
══════════════════════════════════════════════════

RESUMO DO CONTEXTO
──────────────────
Paciente em acompanhamento por sobrepeso, pré-diabetes e dislipidemia.
Em uso de Puran T4 (levotiroxina, iniciado jun/2026) e Psyllium. Última bioimpedância: {bio_list[-1]['peso_kg'] if bio_list else '—'} kg,
{bio_list[-1]['percentual_gordura'] if bio_list else '—'}% gordura. Pratica musculação regularmente.
Exames laboratoriais de 06/05/2026 e 13/05/2026 (Lavoisier + Delboni).

🔴 SITUAÇÕES URGENTES A DISCUTIR
──────────────────────────────────

1. HIPOTIREOIDISMO / HASHIMOTO — EM TRATAMENTO
   TSH: 4,31 (out/25) → 4,50 (mai/06) → 7,48 µUI/mL (mai/13)
   Anti-tireoglobulina: 8,2 UI/mL (ref < 4,5) | Anti-TPO: normal
   T4 Livre: 1,22 ng/dL (normal)
   Iniciou Puran T4 em jun/2026. Aguardar controle do TSH em 8–12 semanas.

2. TRANSAMINASES ELEVADAS E PIORAS
   TGO: 22 → 53 → 60 U/L | TGP: 34 → 35 → 61 U/L
   Ultrassonografia abdominal foi solicitada em 12/05/2026 — aguardo resultado.
   Pergunta: Resultados da ultrassonografia? Qual conduta com as transaminases?

3. VACINA HEPATITE B
   Anti-HBs < 2,0 mUI/mL | Anti-HBc negativo (nunca vacinou)
   Preciso iniciar esquema de vacinação (0–1–6 meses).

🟡 EXAMES A SOLICITAR NA PRÓXIMA COLETA
──────────────────────────────────────────

□ Testosterona Total e Livre
□ SHBG (globulina ligadora de hormônios sexuais)
□ LH e FSH
□ Homocisteína (repetir — estava 19 µmol/L em out/2025)
□ Vitamina B12 e Ácido Fólico
□ Vitamina D 25-OH (repetir — estava borderline)
□ Insulina de Jejum + HOMA-IR (resistência insulínica)
□ Ferritina + Ferro Sérico + TIBC
□ PCR Ultrassensível
□ Ultrassonografia de Tireoide

🟢 SUPLEMENTOS A DISCUTIR
──────────────────────────
□ Vitamina D3 (4.000 UI/dia)
□ Ômega-3 EPA+DHA (2–3 g/dia)
□ Vitamina B12 + Ácido Fólico + B6 (homocisteína elevada)
□ Magnésio (quelato) — função muscular e sono
□ Creatina monohidratada — musculação
□ Probióticos (Hashimoto)

OUTROS PONTOS
─────────────
• RM lombo-sacra realizada — encaminhamento para fisioterapia?
• Avaliação de encaminhamento para endocrinologista
• Avaliação de risco cardiovascular formal (escore de risco)

══════════════════════════════════════════════════
Este documento é um auxiliar pessoal de acompanhamento.
"""
    return txt


# Geração
if report_type == "Resumo Geral de Saúde":
    report = gerar_resumo_geral()
elif report_type == "Relatório de Bioimpedância":
    report = gerar_relatorio_bio()
elif report_type == "Lista para a Médica (O que pedir)":
    report = gerar_lista_medica()
elif report_type == "Relatório de Exames Laboratoriais":
    lines = ["EXAMES LABORATORIAIS — LEANDRO LEME CRESPO", f"Gerado em: {hoje}", "═"*60, ""]
    for s in sorted(sessions.values(), key=lambda x: x["date"]):
        lines.append(f"\n{'─'*50}")
        lines.append(f"Data: {datetime.strptime(s['date'],'%Y-%m-%d').strftime('%d/%m/%Y')} | Lab: {s['lab']}")
        lines.append(f"{'─'*50}")
        cat_results = {}
        for r in results:
            if r["session_id"] == s["id"]:
                cat = r["category"]
                cat_results.setdefault(cat, []).append(r)
        for cat, cat_r in sorted(cat_results.items()):
            lines.append(f"\n{cat}:")
            for r in cat_r:
                status_sym = {"normal":"✅","alta":"⬆️","baixa":"⬇️","info":"ℹ️"}.get(r["status"],"")
                val = f"{r['value']} {r['unit']}" if r["value"] is not None else r["notes"]
                lines.append(f"  {status_sym} {r['exam']}: {val} (ref: {r.get('ref_text','—')})")
    report = "\n".join(lines)
elif report_type == "Relatório de Progresso Mensal":
    report = f"""RELATÓRIO DE PROGRESSO MENSAL
{hoje} — Leandro Leme Crespo
═══════════════════════════════════

Mês de referência: Junho/2026

BIOIMPEDÂNCIA
─────────────"""
    if bio_list:
        jun = [b for b in bio_list if b["date"].startswith("2026-06")]
        if jun:
            fi_j = jun[0]; la_j = jun[-1]
            report += f"""
Início do mês: {fi_j['peso_kg']} kg, {fi_j['percentual_gordura']}% gordura
Final do mês: {la_j['peso_kg']} kg, {la_j['percentual_gordura']}% gordura
Variação de peso: {round(la_j['peso_kg']-fi_j['peso_kg'],1)} kg
Variação de gordura: {round(la_j['percentual_gordura']-fi_j['percentual_gordura'],1)} pp
"""
    report += f"""
EXERCÍCIOS
──────────
Total de treinos: {len(exercises)} sessões registradas
Calorias queimadas (total): {sum(e.get('calories_burned',0) for e in exercises)} kcal

METAS DO PRÓXIMO MÊS
─────────────────────
□ Aumentar passos para 7.000/dia
□ 4 treinos de musculação/semana
□ 150 min de cardio/semana
□ Aguardar resultado da ultrassonografia
□ Consulta com Dra. Celina — discutir levotiroxina
"""
else:
    report = ""

st.markdown("<div class='section-header'>📄 Relatório Gerado</div>", unsafe_allow_html=True)
st.text_area("", report, height=600)

st.download_button(
    label="⬇️ Baixar Relatório (.txt)",
    data=report.encode("utf-8"),
    file_name=f"saude_leandro_{date.today().strftime('%Y%m%d')}_{report_type.replace(' ','_').lower()}.txt",
    mime="text/plain"
)

st.caption("💡 Dica: Clique em 'Baixar Relatório' para salvar o texto. Você pode enviar para a médica por e-mail ou WhatsApp.")
