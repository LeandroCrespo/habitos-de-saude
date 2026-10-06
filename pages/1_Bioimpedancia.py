import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime
import sys, re, base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_manager import load_bioimpedance, save_bioimpedance, load_profile, get_bmi_category, get_fat_category
from utils.ailink_ocr import parse_ailink

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
def _vision_ocr(img_bytes: bytes, api_key: str) -> dict:
    """Envia imagem ao Google Cloud Vision API e retorna a resposta (texto + posições)."""
    if not _REQ_OK:
        return {}
    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
    payload = {"requests": [{"image": {"content": base64.b64encode(img_bytes).decode()},
                              "features": [{"type": "TEXT_DETECTION", "maxResults": 1}]}]}
    try:
        r = _req.post(url, json=payload, timeout=15)
        r.raise_for_status()
        resp = r.json().get("responses", [{}])[0]
        return resp if resp.get("textAnnotations") else {}
    except Exception:
        return {}


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
df_show = df_show.iloc[::-1]  # df_full já está em ordem cronológica → mais recente primeiro
st.dataframe(df_show, use_container_width=True, hide_index=True)

if st.session_state.get("bio_del_msg"):
    st.success(f"✅ Medição de {st.session_state.pop('bio_del_msg')} excluída.")

with st.expander("🗑️ Excluir medição"):
    _opts = list(range(len(bio_sorted)))[::-1]
    _sel = st.selectbox(
        "Medição a excluir:", _opts,
        format_func=lambda i: f"{datetime.strptime(bio_sorted[i]['date'], '%Y-%m-%d').strftime('%d/%m/%Y')} — "
                              f"{bio_sorted[i].get('peso_kg','—')} kg · {bio_sorted[i].get('percentual_gordura','—')}% gordura",
        key="bio_del_sel",
    )
    _conf = st.checkbox("Confirmo que quero excluir esta medição (não pode ser desfeito)", key="bio_del_conf")

    def _excluir_medicao(idx):
        _removed = bio_sorted[idx]
        _restante = [b for i, b in enumerate(bio_sorted) if i != idx]
        for _i, _b in enumerate(_restante, start=1):  # IDs em ordem cronológica
            _b["id"] = _i
        save_bioimpedance(_restante)
        st.session_state["bio_del_conf"] = False
        st.session_state["bio_del_msg"] = datetime.strptime(_removed["date"], "%Y-%m-%d").strftime("%d/%m/%Y")

    st.button("Excluir", type="primary", disabled=not _conf, key="bio_del_btn",
              on_click=_excluir_medicao, args=(_sel,))

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

_altura_m = (load_profile() or {}).get("altura_m", 1.82)
if "bio_form_n" not in st.session_state:
    st.session_state["bio_form_n"] = 0

# Campos do formulário: chave → (rótulo, mín, máx, passo, tipo, obrigatório)
_CAMPOS_FORM = {
    "peso_kg":                ("Peso (kg)",                       40.0, 200.0, 0.1, float, True),
    "imc":                    ("BMI",                             15.0,  50.0, 0.1, float, False),
    "percentual_gordura":     ("BFR — % Gordura",                  1.0,  60.0, 0.1, float, True),
    "massa_gordura_kg":       ("Massa Gorda (kg)",                 1.0, 100.0, 0.1, float, False),
    "musculo_esqueletico_kg": ("Massa Muscular Esquelética (kg)", 10.0,  80.0, 0.1, float, True),
    "massa_muscular_kg":      ("Massa Muscular (kg)",             10.0, 120.0, 0.1, float, False),
    "percentual_musculo":     ("Velocidade Muscular (%)",         10.0,  90.0, 0.1, float, True),
    "percentual_agua":        ("Taxa de Umidade (%)",             20.0,  80.0, 0.1, float, True),
    "massa_ossea_kg":         ("Massa Óssea (kg)",                 1.0,   6.0, 0.1, float, True),
    "tmb_kcal":               ("BMR / TMB (kcal)",                1000,  4000, 1,   int,   True),
    "gordura_visceral":       ("Índice de Gordura Visceral",         1,    30, 1,   int,   True),
    "idade_corporal":         ("Idade do Corpo",                    18,    99, 1,   int,   True),
    "percentual_proteina":    ("Taxa de Proteína (%)",             5.0,  30.0, 0.1, float, True),
}
_COL1 = ["peso_kg", "imc", "percentual_gordura", "massa_gordura_kg", "musculo_esqueletico_kg", "massa_muscular_kg"]
_COL2 = ["percentual_musculo", "percentual_agua", "massa_ossea_kg", "tmb_kcal", "gordura_visceral",
         "idade_corporal", "percentual_proteina"]

img_col, form_col = st.columns([1, 1])

with img_col:
    uploaded = st.file_uploader(
        "Imagem do app AiLink:", type=["jpg", "jpeg", "png"], key="bio_img",
        help="Melhor tela: a de detalhes (toque em 'Expanda para ver detalhes'), que mostra todos os campos."
    )

    if uploaded:
        img_bytes = uploaded.read()
        img_key   = f"{uploaded.name}_{len(img_bytes)}"
        st.image(img_bytes, use_container_width=True)

        if _gv_key and _REQ_OK:
            if img_key != st.session_state["bio_img_key"]:
                with st.spinner("🔍 Lendo dados com Google Vision..."):
                    resp = _vision_ocr(img_bytes, _gv_key)
                    st.session_state["bio_img_key"] = img_key
                    if resp:
                        st.session_state["bio_ext"] = parse_ailink(resp, _altura_m)
                        st.session_state["bio_ocr_status"] = "ok"
                    else:
                        st.session_state["bio_ext"] = {}
                        st.session_state["bio_ocr_status"] = "error"

            if st.session_state["bio_ocr_status"] == "error":
                st.error("❌ Erro na leitura da imagem — preencha o formulário manualmente")
            elif st.session_state["bio_ocr_status"] == "saved":
                st.info("Medição desta imagem já salva. Envie outra imagem para registrar uma nova medição.")
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
                Melhor tela: a de <b>detalhes</b> (toque em "Expanda para ver detalhes")<br>
                Também funcionam <b>Compartilhamento</b> e <b>Antevisão</b><br>
                Sem a chave Google Vision: preencha o formulário ao lado
            </div>
        </div>""", unsafe_allow_html=True)

# ── Formulário: só vem preenchido o que foi lido da imagem ────────────────────
# Campos não lidos ficam VAZIOS (nunca copiam a medição anterior) e os obrigatórios
# precisam ser digitados antes de salvar.
ext = st.session_state.get("bio_ext", {})

def _val(key):
    """Valor lido da imagem (dentro da faixa do campo) ou None."""
    _, lo, hi, _, cast, _ = _CAMPOS_FORM[key]
    v = ext.get(key)
    try:
        return cast(v) if v is not None and lo <= cast(v) <= hi else None
    except (TypeError, ValueError):
        return None

def _input(key):
    label, lo, hi, step, _, obrig = _CAMPOS_FORM[key]
    ultimo = latest.get(key)
    return st.number_input(
        label + ("" if obrig else " — opcional"), min_value=lo, max_value=hi, value=_val(key), step=step,
        help=(f"Última medição: {ultimo}" if ultimo is not None else None),
    )

with form_col:
    _lidos    = [k for k in _CAMPOS_FORM if _val(k) is not None]
    _faltando = [c[0] for k, c in _CAMPOS_FORM.items() if c[5] and _val(k) is None]
    if ext:
        st.success(f"✅ {len(_lidos)} campos lidos da imagem — confira e salve")
        if _faltando:
            st.warning("⚠️ Não encontrados na imagem — digite manualmente: **" + "**, **".join(_faltando) + "**")
    else:
        st.caption("Preencha os campos com os valores do app AiLink (a dica ⓘ de cada campo mostra a última medição).")

    with st.form(f"nova_bio_{st.session_state['bio_form_n']}_{st.session_state['bio_img_key']}"):
        data_med = st.date_input(
            "📅 Data",
            value=date.fromisoformat(ext["date"]) if "date" in ext else date.today()
        )
        valores = {}
        c1, c2 = st.columns(2)
        with c1:
            for k in _COL1:
                valores[k] = _input(k)
        with c2:
            for k in _COL2:
                valores[k] = _input(k)
        notas = st.text_input("Observações (opcional)")
        submitted = st.form_submit_button("💾 Salvar Medição", type="primary", use_container_width=True)

if submitted:
    _vazios = [c[0] for k, c in _CAMPOS_FORM.items() if c[5] and valores[k] is None]
    if _vazios:
        st.error("Preencha antes de salvar: **" + "**, **".join(_vazios) + "**")
        st.stop()
    if any(b["date"] == str(data_med) for b in bio_list):
        st.error(f"Já existe uma medição em {data_med.strftime('%d/%m/%Y')}. Confira a data ou exclua a "
                 "medição anterior em **🗑️ Excluir medição** antes de salvar.")
        st.stop()
    peso = valores["peso_kg"]
    mg = valores["massa_gordura_kg"]
    if mg is None:   # telas sem "Massa gorda": calcula pelo % de gordura
        mg = peso * valores["percentual_gordura"] / 100
    mg = round(mg, 1)
    new_entry = {
        "id": 0, "date": str(data_med),
        "peso_kg": peso,
        "imc": valores["imc"] if valores["imc"] is not None else round(peso / _altura_m ** 2, 1),
        "percentual_gordura": valores["percentual_gordura"], "massa_gordura_kg": mg,
        "massa_magra_kg": round(peso - mg, 1),
        "musculo_esqueletico_kg": valores["musculo_esqueletico_kg"],
        "percentual_musculo": valores["percentual_musculo"],
        "percentual_agua": valores["percentual_agua"], "massa_ossea_kg": valores["massa_ossea_kg"],
        "tmb_kcal": valores["tmb_kcal"], "gordura_visceral": valores["gordura_visceral"],
        "idade_corporal": valores["idade_corporal"], "percentual_proteina": valores["percentual_proteina"],
        "device": "Smartwatch AiLink", "notes": notas
    }
    if valores["massa_muscular_kg"] is not None:
        new_entry["massa_muscular_kg"] = valores["massa_muscular_kg"]
    bio_list.append(new_entry)
    bio_list.sort(key=lambda x: x["date"])
    for _i, _b in enumerate(bio_list, start=1):  # IDs em ordem cronológica
        _b["id"] = _i
    save_bioimpedance(bio_list)
    st.session_state["bio_ext"]        = {}
    st.session_state["bio_ocr_status"] = "saved"   # mantém bio_img_key: a mesma imagem não é relida
    st.session_state["bio_form_n"]    += 1          # formulário novo, vazio
    st.success(f"✅ Medição de {data_med.strftime('%d/%m/%Y')} salva — {peso} kg")
    st.rerun()
