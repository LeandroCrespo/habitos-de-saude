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

    # ── Sessão mais recente ──────────────────────────────────────────────────────
    all_sess = sorted(sessions.values(), key=lambda s: s["date"])
    if all_sess:
        last_sess      = all_sess[-1]
        latest_sid     = last_sess["id"]
        latest_date_fmt = datetime.strptime(last_sess["date"], "%Y-%m-%d").strftime("%d/%m/%Y")
        latest_lab     = last_sess.get("lab", "—")
    else:
        latest_sid, latest_date_fmt, latest_lab = "", "—", "—"

    n_alerta = sum(1 for r in results if r["status"] in ("alta", "baixa") and r["session_id"] == latest_sid)

    # ── Helper: último valor registrado de um exame ──────────────────────────────
    def lv(exam_name):
        best_d, best_v, best_u = "", None, ""
        for r in results:
            if r["exam"] == exam_name and r["value"] is not None:
                d = sessions.get(r["session_id"], {}).get("date", "")
                if d > best_d:
                    best_d, best_v, best_u = d, r["value"], r.get("unit", "")
        return best_v, best_u

    # ── Alertas dinâmicos da última coleta ──────────────────────────────────────
    alert_lines = []
    for r in sorted(results, key=lambda x: x["exam"]):
        if r["session_id"] != latest_sid or r["status"] not in ("alta", "baixa"):
            continue
        sym  = "⬆️" if r["status"] == "alta" else "⬇️"
        val  = f"{r['value']} {r.get('unit','')}" if r["value"] is not None else (r.get("notes") or "—")
        ref  = f" (ref: {r['ref_text']})" if r.get("ref_text") else ""
        alert_lines.append(f"{sym} {r['exam']}: {val.strip()}{ref}")
    alertas_txt = "\n".join(alert_lines) if alert_lines else "Nenhum parâmetro alterado nesta coleta."

    # ── Condições identificadas (dinâmico por limiares atuais) ──────────────────
    tsh_v, _    = lv("TSH")
    hdl_v, _    = lv("HDL")
    ldl_v, _    = lv("LDL")
    hba1c_v, _  = lv("HbA1c")
    homa_v, _   = lv("HOMA-IR")
    tgo_v, _    = lv("TGO (AST)")
    tgp_v, _    = lv("TGP (ALT)")
    homo_v, _   = lv("Homocisteína")
    antihbs_v,_ = lv("Anti-HBs")
    glicose_v,_ = lv("Glicose")
    ct_v, _     = lv("Colesterol Total")

    condicoes = []
    if tsh_v is not None:
        if tsh_v > 4.3:
            condicoes.append(f"• Hipotireoidismo (TSH {tsh_v} — em tratamento com Puran T4)")
        else:
            condicoes.append(f"• Hipotireoidismo tratado e controlado ✓ (TSH {tsh_v} — normal)")
    condicoes.append("• Possível Tireoidite de Hashimoto (anti-TG positivo — histórico mai/2026)")
    _hdl_baixo = hdl_v is not None and hdl_v < 40
    _ldl_alto  = ldl_v is not None and ldl_v >= 130
    if _hdl_baixo and _ldl_alto:
        condicoes.append(f"• Dislipidemia: HDL baixo ({hdl_v} mg/dL) e LDL elevado ({ldl_v} mg/dL)")
    elif _hdl_baixo:
        condicoes.append(f"• Dislipidemia: HDL baixo ({hdl_v} mg/dL)")
    elif _ldl_alto:
        condicoes.append(f"• Dislipidemia: LDL elevado ({ldl_v} mg/dL)")
    if ct_v is not None and ct_v >= 190:
        condicoes.append(f"• Colesterol Total elevado ({ct_v} mg/dL)")
    if hba1c_v is not None and hba1c_v >= 5.7:
        label = "Pré-diabetes" if hba1c_v < 6.5 else "Diabetes"
        condicoes.append(f"• {label} (HbA1c {hba1c_v}%)")
    if homa_v is not None and homa_v > 2.7:
        condicoes.append(f"• Resistência à insulina (HOMA-IR {homa_v} — ref < 2,70)")
    if (tgo_v is not None and tgo_v > 34) or (tgp_v is not None and tgp_v > 49):
        condicoes.append(f"• Transaminases elevadas (TGO: {tgo_v}, TGP: {tgp_v} — investigar com US)")
    if homo_v is not None and homo_v > 15:
        condicoes.append(f"• Homocisteína elevada ({homo_v} µmol/L)")
    if antihbs_v is not None and antihbs_v < 10:
        condicoes.append("• Sem imunidade para Hepatite B (Anti-HBs baixo)")
    if lat.get("imc"):
        condicoes.append(f"• Sobrepeso (IMC {lat.get('imc','—')})")
    condicoes.append("• Coluna lombo-sacra — RM realizada")
    condicoes_txt = "\n".join(condicoes)

    # ── Pontos positivos (dinâmico) ─────────────────────────────────────────────
    positivos = []
    if bio_list and fi and lat:
        if lat.get("peso_kg",0) < fi.get("peso_kg",0):
            positivos.append("✅ Perda consistente de peso e gordura")
        if lat.get("musculo_esqueletico_kg",0) > fi.get("musculo_esqueletico_kg",0):
            positivos.append("✅ Ganho de massa muscular")
    if tsh_v is not None and tsh_v <= 4.3:
        positivos.append(f"✅ TSH normalizado ({tsh_v} µUI/mL) — hipotireoidismo controlado")
    if hdl_v is not None and hdl_v >= 40:
        positivos.append(f"✅ HDL dentro da referência ({hdl_v} mg/dL ≥ 40)")
    if ldl_v is not None and ldl_v < 130:
        positivos.append(f"✅ LDL normalizado ({ldl_v} mg/dL)")
    if glicose_v is not None and glicose_v < 100:
        positivos.append(f"✅ Glicose normalizada ({glicose_v} mg/dL)")
    positivos.append("✅ Hemograma normal")
    positivos.append("✅ PSA normal")
    positivos.append("✅ Função renal estável")
    positivos_txt = "\n".join(positivos)

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
Data: {datetime.strptime(lat.get('date','2026-06-24'),'%Y-%m-%d').strftime('%d/%m/%Y') if lat.get('date') else '—'}
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

EXAMES LABORATORIAIS — ALERTAS (última coleta: {latest_date_fmt} — {latest_lab})
──────────────────────────────────────────────────────────────────────
{n_alerta} parâmetro(s) com valores fora da referência:

{alertas_txt}

CONDIÇÕES IDENTIFICADAS
────────────────────────
{condicoes_txt}

PONTOS POSITIVOS
─────────────────
{positivos_txt}

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
    # ── Helpers para lista médica ─────────────────────────────────────────────────
    def lv_med(exam_name):
        best_d, best_v, best_u = "", None, ""
        for r in results:
            if r["exam"] == exam_name and r["value"] is not None:
                d = sessions.get(r["session_id"], {}).get("date", "")
                if d > best_d:
                    best_d, best_v, best_u = d, r["value"], r.get("unit", "")
        return best_v, best_u

    def trend_med(exam_name):
        """Histórico do exame em forma de progressão 'v (data) → v (data)'."""
        pts = []
        for r in results:
            if r["exam"] == exam_name and r["value"] is not None:
                d = sessions.get(r["session_id"], {}).get("date", "")
                lab = sessions.get(r["session_id"], {}).get("lab", "")
                if d:
                    pts.append((d, r["value"], r.get("unit",""), lab))
        pts.sort()
        if not pts:
            return "—"
        meses_pt = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
        parts = []
        for d, v, u, lab in pts:
            dt = datetime.strptime(d, "%Y-%m-%d")
            parts.append(f"{v} {u} ({meses_pt[dt.month-1]}/{str(dt.year)[2:]})")
        return " → ".join(parts)

    # Coletas registradas
    datas_coletas = " | ".join(
        f"{datetime.strptime(s['date'],'%Y-%m-%d').strftime('%d/%m/%Y')} ({s.get('lab','—')})"
        for s in sorted(sessions.values(), key=lambda x: x["date"])
    ) or "—"

    # TSH status
    tsh_v_med, tsh_u_med = lv_med("TSH")
    _tsh_ctrl = tsh_v_med is not None and tsh_v_med <= 4.3
    _tsh_histo = trend_med("TSH")
    tsh_bloco = (
        f"   TSH: {_tsh_histo}\n"
        f"   ✅ TSH CONTROLADO em {tsh_v_med} µUI/mL — dentro da referência (0,40–4,30)\n"
        f"   Puran T4 (levotiroxina) iniciado jun/2026 — efeito confirmado."
        if _tsh_ctrl else
        f"   TSH: {_tsh_histo}\n"
        f"   Anti-tireoglobulina: 8,2 UI/mL (ref < 4,5) | Anti-TPO: normal\n"
        f"   T4 Livre: 1,22 ng/dL (normal)\n"
        f"   Iniciou Puran T4 em jun/2026. Aguardar controle do TSH em 8–12 semanas."
    )

    # TGO/TGP
    tgo_v_med, _ = lv_med("TGO (AST)")
    tgp_v_med, _ = lv_med("TGP (ALT)")
    _trans_ok_med = (tgo_v_med is None or tgo_v_med <= 34) and (tgp_v_med is None or tgp_v_med <= 49)
    tgo_hist = trend_med("TGO (AST)")
    tgp_hist = trend_med("TGP (ALT)")

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
Exames laboratoriais registrados: {datas_coletas}

🔴 SITUAÇÕES A DISCUTIR
──────────────────────────────────

1. HIPOTIREOIDISMO / HASHIMOTO
{tsh_bloco}
   Anti-tireoglobulina: 8,2 UI/mL (ref < 4,5) | Possível Tireoidite de Hashimoto

2. TRANSAMINASES{" — NORMALIZADAS ✅" if _trans_ok_med else " — ELEVADAS"}
   TGO: {tgo_hist}
   TGP: {tgp_hist}
   {"Transaminases dentro dos limites de referência." if _trans_ok_med else "Ultrassonografia abdominal solicitada em mai/2026 — aguardo resultado."}
   {"" if _trans_ok_med else "Pergunta: Resultados da ultrassonografia? Qual conduta?"}

3. RESISTÊNCIA À INSULINA / PRÉ-DIABETES
   HOMA-IR: {trend_med("HOMA-IR")} (ref < 2,70)
   HbA1c: {trend_med("HbA1c")} (ref < 5,7%)
   Glicose: {trend_med("Glicose")} mg/dL | Insulina: {trend_med("Insulina")} µUI/mL
   Pergunta: Indicação de metformina? Ajuste na dieta/exercício para IR?

4. VACINA HEPATITE B
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
