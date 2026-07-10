import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
import sys, re, base64, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_manager import load_exams, save_exams, status_color, status_emoji

try:
    import requests as _req
    _REQ_OK = True
except ImportError:
    _REQ_OK = False

# ── OCR de PDF via Google Vision API ─────────────────────────────────────────
def _vision_pdf_ocr(pdf_bytes: bytes, api_key: str) -> str:
    if not _REQ_OK:
        return ""
    url = f"https://vision.googleapis.com/v1/files:annotate?key={api_key}"
    payload = {"requests": [{"inputConfig": {
        "content": base64.b64encode(pdf_bytes).decode(),
        "mimeType": "application/pdf"},
        "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
        "pages": list(range(1, 6))}]}
    try:
        r = _req.post(url, json=payload, timeout=30)
        r.raise_for_status()
        texts = []
        for resp in r.json().get("responses", [{}]):
            for page in resp.get("responses", []):
                t = page.get("fullTextAnnotation", {}).get("text", "")
                if t:
                    texts.append(t)
        return "\n".join(texts)
    except Exception:
        return ""

# ── Parser de laudos laboratoriais ───────────────────────────────────────────
# Mapeamento: alias (minúsculas) → nome canônico
_ALIAS = {
    "eritrócitos": "Eritrócitos", "eritrocitos": "Eritrócitos",
    "hemoglobina": "Hemoglobina",
    "hematócrito": "Hematócrito", "hematocrito": "Hematócrito",
    "vcm": "VCM", "hcm": "HCM", "chcm": "CHCM", "rdw": "RDW",
    "leucócitos": "Leucócitos", "leucocitos": "Leucócitos",
    "neutrófilos": "Neutrófilos", "neutrofilos": "Neutrófilos",
    "linfócitos": "Linfócitos", "linfocitos": "Linfócitos",
    "monócitos": "Monócitos", "monocitos": "Monócitos",
    "eosinófilos": "Eosinófilos", "eosinofilos": "Eosinófilos",
    "basófilos": "Basófilos", "basofilos": "Basófilos",
    "plaquetas": "Plaquetas",
    "creatinina": "Creatinina",
    "tfg estimada": "TFG estimada (eGFR)", "egfr": "TFG estimada (eGFR)",
    "tfg": "TFG estimada (eGFR)", "taxa de filtração glomerular": "TFG estimada (eGFR)",
    "ureia": "Ureia",
    "albumina urinária": "Albumina Urinária", "albumina urinaria": "Albumina Urinária",
    "potássio": "Potássio", "potassio": "Potássio",
    "sódio": "Sódio", "sodio": "Sódio",
    "homocisteína": "Homocisteína", "homocisteina": "Homocisteína",
    "pcr": "PCR", "proteína c reativa": "PCR", "proteina c reativa": "PCR",
    "glicose": "Glicose",
    "hba1c": "HbA1c", "hemoglobina glicada": "HbA1c", "glicohemoglobina": "HbA1c",
    "colesterol total": "Colesterol Total",
    "hdl colesterol": "HDL", "hdl-colesterol": "HDL", "hdl": "HDL",
    "ldl colesterol": "LDL", "ldl-colesterol": "LDL", "ldl": "LDL",
    "vldl": "VLDL",
    "triglicérides": "Triglicérides", "triglicerides": "Triglicérides",
    "triglicerídeos": "Triglicérides", "triacilgliceróis": "Triglicérides",
    "tgo (ast)": "TGO (AST)", "tgo": "TGO (AST)", "ast": "TGO (AST)",
    "aspartato aminotransferase": "TGO (AST)",
    "tgp (alt)": "TGP (ALT)", "tgp": "TGP (ALT)", "alt": "TGP (ALT)",
    "alanina aminotransferase": "TGP (ALT)",
    "ggt": "GGT", "gamaglutamiltransferase": "GGT",
    "bilirrubina total": "Bilirrubina Total",
    "fosfatase alcalina": "Fosfatase Alcalina",
    "tsh": "TSH",
    "t4 livre": "T4 Livre",
    "anti-tireoglobulina (anti-tg)": "Anti-tireoglobulina (anti-TG)",
    "anti-tireoglobulina": "Anti-tireoglobulina (anti-TG)",
    "anti-tg": "Anti-tireoglobulina (anti-TG)",
    "anti-tpo (antiperoxidase)": "Anti-TPO (Antiperoxidase)",
    "anti-tpo": "Anti-TPO (Antiperoxidase)", "antiperoxidase": "Anti-TPO (Antiperoxidase)",
    "ferritina": "Ferritina",
    "ferro sérico": "Ferro", "ferro serico": "Ferro", "ferro": "Ferro",
    "vitamina d": "Vitamina D", "25-oh vitamina d": "Vitamina D",
    "vitamina b12": "Vitamina B12", "cobalamina": "Vitamina B12",
    "ácido fólico": "Ácido Fólico", "acido folico": "Ácido Fólico",
    "ácido úrico": "Ácido Úrico", "acido urico": "Ácido Úrico",
    "albumina": "Albumina",
    "proteínas totais": "Proteínas Totais", "proteinas totais": "Proteínas Totais",
    "anti-hiv": "Anti-HIV",
    "hbsag": "HBsAg (Hepatite B)", "hbsag (hepatite b)": "HBsAg (Hepatite B)",
    "anti-hbs": "Anti-HBs (Imunidade Hep B)",
    "anti-hbc total": "Anti-HBc Total", "anti-hbc": "Anti-HBc Total",
    "anti-hcv": "Anti-HCV (Hepatite C)", "anti-hcv (hepatite c)": "Anti-HCV (Hepatite C)",
    "hemácias (sedimento)": "Hemácias (sedimento)", "hemacias": "Hemácias (sedimento)",
    "leucócitos (sedimento)": "Leucócitos (sedimento)",
}

_EXAM_CAT = {
    "Eritrócitos": "Hemograma", "Hemoglobina": "Hemograma", "Hematócrito": "Hemograma",
    "VCM": "Hemograma", "HCM": "Hemograma", "CHCM": "Hemograma", "RDW": "Hemograma",
    "Leucócitos": "Hemograma", "Neutrófilos": "Hemograma", "Linfócitos": "Hemograma",
    "Monócitos": "Hemograma", "Eosinófilos": "Hemograma", "Basófilos": "Hemograma",
    "Plaquetas": "Hemograma",
    "Creatinina": "Função Renal", "TFG estimada (eGFR)": "Função Renal",
    "Ureia": "Função Renal", "Albumina Urinária": "Urina Tipo I",
    "Hemácias (sedimento)": "Urina Tipo I", "Leucócitos (sedimento)": "Urina Tipo I",
    "Potássio": "Eletrólitos", "Sódio": "Eletrólitos",
    "Homocisteína": "Metabolismo Cardiovascular", "PCR": "Inflamação",
    "Glicose": "Metabolismo Glicídico", "HbA1c": "Metabolismo Glicídico",
    "Colesterol Total": "Perfil Lipídico", "HDL": "Perfil Lipídico",
    "LDL": "Perfil Lipídico", "VLDL": "Perfil Lipídico", "Triglicérides": "Perfil Lipídico",
    "TGO (AST)": "Função Hepática", "TGP (ALT)": "Função Hepática",
    "GGT": "Função Hepática", "Bilirrubina Total": "Função Hepática",
    "Fosfatase Alcalina": "Função Hepática",
    "TSH": "Tireoide", "T4 Livre": "Tireoide",
    "Anti-tireoglobulina (anti-TG)": "Tireoide", "Anti-TPO (Antiperoxidase)": "Tireoide",
    "Ferritina": "Metabolismo do Ferro", "Ferro": "Metabolismo do Ferro",
    "Vitamina D": "Vitaminas", "Vitamina B12": "Vitaminas", "Ácido Fólico": "Vitaminas",
    "Ácido Úrico": "Outros", "Albumina": "Outros", "Proteínas Totais": "Outros",
    "Anti-HIV": "Sorologias", "HBsAg (Hepatite B)": "Sorologias",
    "Anti-HBs (Imunidade Hep B)": "Sorologias",
    "Anti-HBc Total": "Sorologias", "Anti-HCV (Hepatite C)": "Sorologias",
}

def _parse_lab_text(text: str) -> list[dict]:
    """Extrai exames do texto OCR de um laudo laboratorial."""
    rows = []
    seen = set()
    lines = text.replace("\r", "\n").split("\n")
    # Regex para capturar: valor numérico e possível referência na mesma linha
    num_pat  = re.compile(r"(\d+[,.]?\d*)")
    ref_pat  = re.compile(
        r"(?:VR|Ref\.?|Valor de refer[eê]ncia)?[:\s]*"
        r"(?:(?:(\d+[,.]\d+)\s*[–\-]\s*(\d+[,.]\d+))"   # min – max
        r"|(?:[<≤]\s*(\d+[,.]\d+))"                       # < max
        r"|(?:[>≥]\s*(\d+[,.]\d+)))",                     # > min
        re.IGNORECASE
    )
    for i, line in enumerate(lines):
        line_l = line.strip().lower()
        if not line_l:
            continue
        # Tenta identificar nome do exame no início da linha
        canonical = None
        # Ordena aliases do mais longo para o mais curto (evita match parcial)
        for alias in sorted(_ALIAS.keys(), key=len, reverse=True):
            if line_l.startswith(alias) or f" {alias}" in line_l:
                canonical = _ALIAS[alias]
                break
        if not canonical or canonical in seen:
            continue
        # Extrai valor numérico
        nums = num_pat.findall(line)
        if not nums:
            # Tenta linha seguinte
            next_line = lines[i+1].strip() if i+1 < len(lines) else ""
            nums = num_pat.findall(next_line)
            combined = line + " " + next_line
        else:
            combined = line
        if not nums:
            continue
        try:
            value = float(nums[0].replace(",", "."))
        except ValueError:
            continue
        # Extrai referência
        ref_min = ref_max = None
        ref_text = ""
        m = ref_pat.search(combined)
        if m:
            if m.group(1) and m.group(2):
                ref_min = float(m.group(1).replace(",", "."))
                ref_max = float(m.group(2).replace(",", "."))
                ref_text = f"{m.group(1)} – {m.group(2)}"
            elif m.group(3):
                ref_max = float(m.group(3).replace(",", "."))
                ref_text = f"< {m.group(3)}"
            elif m.group(4):
                ref_min = float(m.group(4).replace(",", "."))
                ref_text = f"> {m.group(4)}"
        # Status
        if ref_min is not None and value < ref_min:
            status = "baixa"
        elif ref_max is not None and value > ref_max:
            status = "alta"
        elif ref_min is not None or ref_max is not None:
            status = "normal"
        else:
            status = "info"
        rows.append({
            "exam": canonical,
            "category": _EXAM_CAT.get(canonical, "Outros"),
            "value": value,
            "unit": "",
            "ref_min": ref_min,
            "ref_max": ref_max,
            "ref_text": ref_text,
            "status": status,
            "notes": "",
        })
        seen.add(canonical)
    return rows

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

# ── Importar novo laudo (PDF) ─────────────────────────────────────────────────
with st.expander("📤 Importar novo laudo (PDF)", expanded=False):
    api_key = st.secrets.get("GOOGLE_VISION_API_KEY", "")

    col_a, col_b = st.columns([2, 1])
    with col_a:
        uploaded_pdf = st.file_uploader("Selecione o PDF do laudo (Lavoisier, Delboni…):",
                                        type=["pdf"], key="pdf_upload")
    with col_b:
        lab_name  = st.text_input("Laboratório:", value="Lavoisier")
        exam_date = st.date_input("Data do exame:", value=date.today())
        doctor    = st.text_input("Médica solicitante:", value="Dra. Celina Prado de Lima Souza")
        exam_notes = st.text_input("Observações da coleta (opcional):")

    if uploaded_pdf:
        pdf_key = f"{uploaded_pdf.name}_{uploaded_pdf.size}"
        if st.session_state.get("_pdf_key") != pdf_key:
            st.session_state["_pdf_key"] = pdf_key
            st.session_state["_pdf_rows"] = None
            st.session_state["_pdf_text"] = None

        if st.session_state.get("_pdf_rows") is None:
            if not api_key:
                st.warning("GOOGLE_VISION_API_KEY não configurada nos secrets.")
            else:
                with st.spinner("Lendo PDF com OCR…"):
                    raw_text = _vision_pdf_ocr(uploaded_pdf.read(), api_key)
                    st.session_state["_pdf_text"] = raw_text
                    st.session_state["_pdf_rows"] = _parse_lab_text(raw_text)

        rows = st.session_state.get("_pdf_rows", [])
        raw_text = st.session_state.get("_pdf_text", "")

        if rows:
            st.success(f"**{len(rows)} exame(s) identificado(s).** Revise abaixo antes de salvar.")
            df_edit = pd.DataFrame(rows)[["exam","category","value","unit","ref_min","ref_max","ref_text","status","notes"]]
            df_edit.columns = ["Exame","Categoria","Valor","Unidade","Ref Mín","Ref Máx","Ref Texto","Status","Notas"]
            edited = st.data_editor(
                df_edit,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "Status": st.column_config.SelectboxColumn(options=["normal","alta","baixa","info"]),
                },
                key="exam_editor"
            )
            if st.button("💾 Salvar laudo", type="primary"):
                new_sid = f"s{len(exams_data.get('sessions',[]))+1:03d}"
                exams_data.setdefault("sessions", []).append({
                    "id": new_sid,
                    "date": str(exam_date),
                    "lab": lab_name,
                    "doctor": doctor,
                    "notes": exam_notes or f"Importado via OCR — {len(rows)} exames"
                })
                for _, row in edited.iterrows():
                    try:
                        v = float(str(row["Valor"]).replace(",", "."))
                    except Exception:
                        v = None
                    try:
                        rmin = float(str(row["Ref Mín"]).replace(",", ".")) if pd.notna(row["Ref Mín"]) else None
                    except Exception:
                        rmin = None
                    try:
                        rmax = float(str(row["Ref Máx"]).replace(",", ".")) if pd.notna(row["Ref Máx"]) else None
                    except Exception:
                        rmax = None
                    exams_data.setdefault("results", []).append({
                        "session_id": new_sid,
                        "category": row["Categoria"],
                        "exam": row["Exame"],
                        "value": v,
                        "unit": row["Unidade"] or "",
                        "ref_min": rmin,
                        "ref_max": rmax,
                        "ref_text": row["Ref Texto"] or "",
                        "status": row["Status"],
                        "notes": row["Notas"] or "",
                    })
                save_exams(exams_data)
                st.session_state["_pdf_key"] = None
                st.session_state["_pdf_rows"] = None
                st.success(f"✅ Laudo de {exam_date.strftime('%d/%m/%Y')} salvo com {len(edited)} exame(s)!")
                st.rerun()
        else:
            st.warning("Nenhum exame reconhecido automaticamente. Verifique o texto abaixo.")

        if raw_text:
            with st.expander("Texto extraído pelo OCR (para conferência)"):
                st.text(raw_text[:3000])

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
    desc = EXAM_DESC.get(exam_name, "")
    if desc:
        st.caption(f"ℹ️ {desc}")

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
