import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime
import sys, re, base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_manager import load_bioimpedance, save_bioimpedance, get_bmi_category, get_fat_category

try:
    import requests as _req
    _REQ_OK = True
except ImportError:
    _REQ_OK = False

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


# ── Google Vision API helpers ─────────────────────────────────────────────────
def _vision_ocr(img_bytes: bytes, api_key: str) -> str:
    """Envia imagem ao Google Cloud Vision API e retorna texto detectado."""
    if not _REQ_OK:
        return ""
    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
    payload = {"requests": [{"image": {"content": base64.b64encode(img_bytes).decode()},
                              "features": [{"type": "TEXT_DETECTION", "maxResults": 1}]}]}
    try:
        r = _req.post(url, json=payload, timeout=15)
        r.raise_for_status()
        anns = r.json().get("responses", [{}])[0].get("textAnnotations", [])
        return anns[0].get("description", "") if anns else ""
    except Exception:
        return ""


def _parse_ailink(text: str) -> dict:
    """Extrai campos de bioimpedância do texto OCR do app AiLink."""
    result = {}

    def _f(pattern, cast=float):
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                return cast(m.group(1).replace(",", "."))
            except Exception:
                pass
        return None

    # Data: "2026-06-30 09:05"
    m = re.search(r"(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}", text)
    if m:
        result["date"] = m.group(1)

    # Peso corporal: ignora valores fora de 60–200 kg (ex: "Peso da água 46.7 kg")
    for _m in re.finditer(r"\b(\d{2,3}[.,]\d)\s*kg", text, re.IGNORECASE):
        try:
            _v = float(_m.group(1).replace(",", "."))
            if 60.0 <= _v <= 200.0:
                result["peso_kg"] = _v
                break
        except Exception:
            pass

    for key, pat in [
        ("imc",                   r"BMI\s*[\(]?\s*(\d{2}[.,]\d)"),
        ("percentual_gordura",    r"BFR\s*[\(]?\s*(\d{2}[.,]\d)\s*%"),
        ("percentual_musculo",    r"Velocidade\s+muscular\s*[\(]?\s*(\d{2}[.,]\d)\s*%"),
        ("musculo_esqueletico_kg",r"Massa\s+muscular\s+esquel[eé]tica\s*[\(]?\s*(\d{2}[.,]\d)\s*kg"),
        ("percentual_agua",       r"Taxa\s+de\s+umidade\s*[\(]?\s*(\d{2}[.,]\d)\s*%"),
        ("massa_ossea_kg",        r"Massa\s+[oó]ssea\s*[\(]?\s*(\d[.,]\d)\s*kg"),
        ("percentual_proteina",   r"Taxa\s+de\s+prote[ií]na\s*[\(]?\s*(\d{2}[.,]\d)\s*%"),
        ("gordura_subcutanea_pct",r"gordura\s+subcut[aâ]nea\s*[\(]?\s*(\d{2}[.,]\d)\s*%"),
        ("massa_gordura_kg",      r"Massa\s+gorda\s+(\d{2}[.,]\d)\s*kg"),
    ]:
        v = _f(pat)
        if v is not None:
            result[key] = v

    for key, pat in [
        ("tmb_kcal",        r"BMR\s*[\(]?\s*(\d{3,4})\s*kcal"),
        ("gordura_visceral", r"gordura\s+visceral\s*[\(]?\s*(\d{1,2})\s*[\)]?"),
        ("idade_corporal",   r"Idade\s+do\s+corpo\s*[\(]?\s*(\d{2})\s*[\)]?"),
    ]:
        v = _f(pat, int)
        if v is not None:
            result[key] = v

    return result


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
        textfont=dict(size=11),
        cliponaxis=False,
        line=dict(color=color, width=3),
        marker=dict(size=8, color=color),
        fill="tozeroy" if fill else "none",
        fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.07)" if fill else None,
        hovertemplate="%{text}<extra></extra>"
    ))
    if ref_line is not None:
        fig.add_hline(y=ref_line, line_dash="dash", line_color="#F39C12",
                      annotation_text=ref_label, annotation_position="right")
    y_pad = max((max(y) - min(y)) * 0.35, 1.5) if len(y) > 1 else 2
    fig.update_layout(
        height=height, title=title, plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=40, r=100, t=45, b=75),
        xaxis=dict(showgrid=False, tickvals=x_dates, ticktext=tick_labels,
                   tickangle=-40, tickfont=dict(size=11), automargin=True),
        yaxis=dict(showgrid=True, gridcolor="#eee",
                   range=[min(y)-y_pad*0.3, max(y)+y_pad*1.5] if y else [0,100]),
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
        textfont=dict(size=11), cliponaxis=False,
        line=dict(color="#8E44AD", width=3), marker=dict(size=8)
    ))
    fig2.add_hline(y=25, line_dash="dash", line_color="#27AE60", annotation_text="IMC Normal < 25", annotation_position="right")
    y_pad2 = max((max(y_imc) - min(y_imc)) * 0.35, 0.5) if len(y_imc) > 1 else 1
    fig2.update_layout(
        height=300, title="Índice de Massa Corporal (IMC)", plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=40, r=130, t=45, b=75), showlegend=False,
        xaxis=dict(showgrid=False, tickvals=x_dates, ticktext=tick_labels, tickangle=-40, tickfont=dict(size=11), automargin=True),
        yaxis=dict(showgrid=True, gridcolor="#eee", range=[min(y_imc)-y_pad2*0.3, max(y_imc)+y_pad2*1.5])
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
        plot_bgcolor="white", paper_bgcolor="white", margin=dict(l=40, r=20, t=40, b=75),
        xaxis=dict(showgrid=False, tickvals=x_dates, ticktext=tick_labels, tickangle=-40, tickfont=dict(size=11), automargin=True),
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
                               text=[str(v) for v in y_visc], textposition="outside",
                               cliponaxis=False, textfont=dict(size=11)))
        fig2.add_hline(y=9, line_dash="dash", line_color="#27AE60", annotation_text="Meta: ≤ 9", annotation_position="right")
        _vmax = max(y_visc) if y_visc else 15
        fig2.update_layout(
            height=290, title="Gordura Visceral (escala 1–20)", plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=40, r=105, t=45, b=75), showlegend=False,
            xaxis=dict(showgrid=False, tickvals=x_dates, ticktext=tick_labels, tickangle=-40, tickfont=dict(size=11), automargin=True),
            yaxis=dict(showgrid=True, gridcolor="#eee", range=[0, _vmax * 1.35])
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

# ── Upload + Nova Medição (Google Vision API) ─────────────────────────────────
st.markdown("<div class='section-header'>📷 Registrar Nova Medição — App AiLink</div>", unsafe_allow_html=True)

# Session state para guardar extração entre reruns
for _k, _d in [("bio_ext", {}), ("bio_img_key", ""), ("bio_ocr_status", "idle")]:
    if _k not in st.session_state:
        st.session_state[_k] = _d

# Chave da Google Vision API (secrets do Streamlit)
_gv_key = ""
try:
    _gv_key = st.secrets.get("GOOGLE_VISION_API_KEY", "")
except Exception:
    pass

img_col, form_col = st.columns([1, 1])

with img_col:
    uploaded = st.file_uploader(
        "Imagem do app AiLink:", type=["jpg", "jpeg", "png"], key="bio_img",
        help="Use a tela 'Compartilhamento d...' ou 'Antevisão' do AiLink"
    )

    if uploaded:
        img_bytes = uploaded.read()
        img_key   = f"{uploaded.name}_{len(img_bytes)}"
        st.image(img_bytes, use_container_width=True)

        if _gv_key and _REQ_OK:
            if img_key != st.session_state["bio_img_key"]:
                with st.spinner("🔍 Lendo dados com Google Vision..."):
                    ocr = _vision_ocr(img_bytes, _gv_key)
                    if ocr:
                        ext = _parse_ailink(ocr)
                        st.session_state["bio_ext"]      = ext
                        st.session_state["bio_img_key"]  = img_key
                        st.session_state["bio_ocr_status"] = "ok" if len(ext) >= 5 else "partial"
                    else:
                        st.session_state["bio_ocr_status"] = "error"
                        st.session_state["bio_img_key"]  = img_key

            _status = st.session_state["bio_ocr_status"]
            if _status == "ok":
                st.success(f"✅ {len(st.session_state['bio_ext'])} campos extraídos — confirme ao lado →")
            elif _status == "partial":
                st.warning("⚠️ Extração parcial — verifique e corrija os campos ao lado")
            elif _status == "error":
                st.error("❌ Erro na API — preencha o formulário manualmente")
        elif not _gv_key:
            st.info("💡 Adicione `GOOGLE_VISION_API_KEY` nos secrets para extração automática.\n\n"
                    "Sem a chave: preencha o formulário ao lado lendo os valores da imagem.")
    else:
        st.markdown("""
        <div style='background:#f0f9ff;border:2px dashed #90caf9;border-radius:12px;
                    padding:32px;text-align:center;color:#1565C0;margin-top:8px'>
            <div style='font-size:44px;margin-bottom:10px'>📷</div>
            <div style='font-weight:700;font-size:15px'>Envie a imagem do app AiLink</div>
            <div style='font-size:13px;margin-top:8px;opacity:0.85;line-height:1.6'>
                Use a tela <b>Compartilhamento</b> ou <b>Antevisão</b><br>
                Com a chave Google Vision: extração automática<br>
                Sem a chave: preencha o formulário ao lado
            </div>
        </div>""", unsafe_allow_html=True)

# ── Formulário (pré-preenchido com valores extraídos ou última medição) ────────
ext = st.session_state.get("bio_ext", {})

_RANGES = {
    "peso_kg": (40.0, 200.0), "imc": (15.0, 50.0),
    "percentual_gordura": (1.0, 60.0), "massa_gordura_kg": (1.0, 100.0),
    "musculo_esqueletico_kg": (10.0, 80.0), "percentual_musculo": (10.0, 80.0),
    "percentual_agua": (20.0, 80.0), "massa_ossea_kg": (1.0, 6.0),
    "tmb_kcal": (1000, 4000), "gordura_visceral": (1, 30),
    "idade_corporal": (20, 90), "percentual_proteina": (5.0, 30.0),
}

def _val(key, default, cast=float):
    try:
        v = cast(ext.get(key, default))
        lo, hi = _RANGES.get(key, (None, None))
        if lo is not None and not (lo <= v <= hi):
            return cast(default)
        return v
    except Exception:
        try:
            return cast(default)
        except Exception:
            return cast(0)

with form_col:
    if ext:
        st.success(f"✅ {len(ext)} campos preenchidos automaticamente — revise e salve")
    else:
        st.caption("Campos pré-preenchidos com a **última medição** — atualize com os valores da imagem")

    with st.form("nova_bio", clear_on_submit=True):
        data_med = st.date_input(
            "📅 Data",
            value=date.fromisoformat(ext["date"]) if "date" in ext else date.today()
        )
        c1, c2 = st.columns(2)
        with c1:
            peso         = st.number_input("Peso (kg)",               50.0, 200.0, _val("peso_kg",              latest["peso_kg"]),               0.1)
            imc          = st.number_input("BMI",                      15.0,  50.0, _val("imc",                  latest["imc"]),                    0.1)
            pct_gordura  = st.number_input("BFR — % Gordura",          1.0,   60.0, _val("percentual_gordura",   latest["percentual_gordura"]),      0.1)
            massa_gordura= st.number_input("Massa Gorda (kg)",          1.0,  100.0, _val("massa_gordura_kg",     latest["massa_gordura_kg"]),        0.1)
            musculo      = st.number_input("Massa Musc. Esq. (kg)",    10.0,   80.0, _val("musculo_esqueletico_kg", latest["musculo_esqueletico_kg"]), 0.1)
            pct_musculo  = st.number_input("Velocidade Muscular (%)",  10.0,   80.0, _val("percentual_musculo",   latest.get("percentual_musculo", 66.3)), 0.1)
        with c2:
            pct_agua     = st.number_input("Taxa de Umidade (%)",      20.0,   80.0, _val("percentual_agua",      latest.get("percentual_agua", 49.7)),  0.1)
            massa_ossea  = st.number_input("Massa Óssea (kg)",          1.0,    6.0, _val("massa_ossea_kg",       latest.get("massa_ossea_kg", 3.3)),    0.1)
            tmb          = st.number_input("BMR / TMB (kcal)",        1000,   4000,  _val("tmb_kcal",             latest.get("tmb_kcal", 1743),   int),  1)
            gordura_visc = st.number_input("Gordura Visceral",            1,     30,  _val("gordura_visceral",     latest.get("gordura_visceral", 14), int), 1)
            idade_corp   = st.number_input("Idade do Corpo",             20,     90,  _val("idade_corporal",       latest.get("idade_corporal", 47),  int),  1)
            pct_proteina = st.number_input("Taxa de Proteína (%)",      5.0,   30.0, _val("percentual_proteina",  latest.get("percentual_proteina", 13.5)), 0.1)
        notas = st.text_input("Observações (opcional)")
        submitted = st.form_submit_button("💾 Salvar Medição", type="primary", use_container_width=True)

if submitted:
    new_id = max([b.get("id", 0) for b in bio_list], default=0) + 1
    mg = round(massa_gordura, 1)
    new_entry = {
        "id": new_id, "date": str(data_med),
        "peso_kg": peso, "imc": imc,
        "percentual_gordura": pct_gordura, "massa_gordura_kg": mg,
        "massa_magra_kg": round(peso - mg, 1),
        "musculo_esqueletico_kg": musculo, "percentual_musculo": pct_musculo,
        "percentual_agua": pct_agua, "massa_ossea_kg": massa_ossea,
        "tmb_kcal": tmb, "gordura_visceral": gordura_visc,
        "idade_corporal": int(idade_corp), "percentual_proteina": pct_proteina,
        "device": "Smartwatch AiLink", "notes": notas
    }
    bio_list.append(new_entry)
    save_bioimpedance(bio_list)
    st.session_state["bio_ext"]      = {}
    st.session_state["bio_img_key"]  = ""
    st.session_state["bio_ocr_status"] = "idle"
    st.success(f"✅ Medição de {data_med.strftime('%d/%m/%Y')} salva — {peso} kg")
    st.rerun()
