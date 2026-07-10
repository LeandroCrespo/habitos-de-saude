import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime
import zipfile
import json as _json
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_manager import load_exercises, save_exercises, load_bioimpedance, calc_tdee

# ── Mapeamento Samsung Health exercise_type ────────────────────────────────────
_SAMSUNG_TYPES = {
    1001: "Caminhada",
    1002: "Corrida",
    1003: "Ciclismo",
    1004: "Ciclismo Indoor",
    1008: "Bicicleta",
    1009: "Ciclismo Indoor",
    2001: "Natação",
    10001: "Musculação",
    10002: "Musculação",
    11007: "Yoga/Pilates",
    11008: "Pilates",
    11009: "Yoga/Pilates",
    40001: "HIIT",
    40002: "HIIT",
    50001: "Futebol",
    50002: "Basquete",
    50003: "Tênis",
    13001: "Fisioterapia",
    13002: "Fisioterapia",
}


def _samsung_type_name(code):
    try:
        return _SAMSUNG_TYPES.get(int(code), f"Outro ({code})")
    except Exception:
        return "Outro"


def _parse_samsung_dt(s):
    s = str(s).strip().replace("Z", "+0000")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _parse_samsung_zip(file_bytes):
    """Lê ZIP do Samsung Health; retorna (steps_rows, exercise_rows)."""
    steps_map = {}
    exercise_rows = []

    with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
        for name in zf.namelist():
            base = name.split("/")[-1]

            # ── Passos diários ──────────────────────────────────────────
            if "step_daily_trend" in base and base.endswith(".json"):
                with zf.open(name) as f:
                    try:
                        records = _json.load(f)
                    except Exception:
                        continue
                if isinstance(records, dict):
                    records = records.get("data", [])
                for r in records:
                    day_key   = next((k for k in r if "day_time" in k or "create_time" in k), None)
                    count_key = next((k for k in r if k.endswith(".count")), None)
                    cal_key   = next((k for k in r if k.endswith(".calorie")), None)
                    if not day_key or not count_key:
                        continue
                    dt = _parse_samsung_dt(r[day_key])
                    if not dt:
                        continue
                    d = dt.date().isoformat()
                    steps = int(r.get(count_key, 0))
                    cals  = round(float(r.get(cal_key, 0)))
                    if d in steps_map:
                        steps_map[d]["steps"] += steps
                        steps_map[d]["calories"] += cals
                    else:
                        steps_map[d] = {"date": d, "steps": steps, "calories": cals}

            # ── Sessões de exercício ────────────────────────────────────
            elif "shealth.exercise" in base and base.endswith(".json"):
                with zf.open(name) as f:
                    try:
                        records = _json.load(f)
                    except Exception:
                        continue
                if isinstance(records, dict):
                    records = records.get("data", [])
                for r in records:
                    type_key  = next((k for k in r if k.endswith(".exercise_type")), None)
                    start_key = next((k for k in r if k.endswith(".start_time")), None)
                    dur_key   = next((k for k in r if k.endswith(".duration")), None)
                    cal_key   = next((k for k in r if k.endswith(".calorie")), None)
                    step_key  = next((k for k in r if k.endswith(".count")), None)
                    hr_key    = next((k for k in r if "mean_heart_rate" in k), None)
                    if not start_key or not dur_key:
                        continue
                    dt = _parse_samsung_dt(r[start_key])
                    if not dt:
                        continue
                    dur_min = max(1, round(int(r.get(dur_key, 60000)) / 60000))
                    exercise_rows.append({
                        "date":            dt.date().isoformat(),
                        "type":            _samsung_type_name(r.get(type_key, 0)),
                        "duration_min":    dur_min,
                        "calories_burned": round(float(r.get(cal_key, 0))),
                        "steps":           int(r.get(step_key, 0)),
                        "heart_rate":      int(r.get(hr_key, 0)) if hr_key and r.get(hr_key) else 0,
                    })

    return list(steps_map.values()), exercise_rows


# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Exercício & Smartwatch", page_icon="💪", layout="wide")

st.markdown("""
<style>
.section-header{font-size:22px;font-weight:700;color:#1E8449;border-bottom:3px solid #1E8449;padding-bottom:8px;margin:20px 0 16px}
.metric-card{background:linear-gradient(135deg,#f0fff4,#e8f5e9);border-left:4px solid #1E8449;border-radius:12px;padding:14px 18px;margin:6px 0;box-shadow:0 2px 8px rgba(0,0,0,0.07)}
.metric-title{font-size:11px;color:#666;font-weight:700;text-transform:uppercase;letter-spacing:0.5px}
.metric-value{font-size:26px;font-weight:700;color:#1a3a1a;line-height:1.2}
.metric-sub{font-size:12px;color:#555;margin-top:2px}
.watch-card{background:linear-gradient(135deg,#1a3a1a,#0d5c29);border-radius:16px;padding:20px;color:white;margin:10px 0}
.import-step{background:#f8fff8;border:1px solid #b2dfdb;border-radius:10px;padding:12px 16px;margin:6px 0;font-size:14px}
</style>
""", unsafe_allow_html=True)

st.markdown("## 💪 Exercício & Smartwatch Ultra")

exercises = load_exercises()
bio_list = load_bioimpedance()

if "edit_ex_id" not in st.session_state:
    st.session_state.edit_ex_id = None

tmb = 1783
if bio_list:
    tmb = sorted(bio_list, key=lambda x: x["date"])[-1].get("tmb_kcal", 1783)

# ── Importar Samsung Health ────────────────────────────────────────────────────
st.markdown("<div class='section-header'>📲 Importar dados do Samsung Health</div>", unsafe_allow_html=True)

with st.expander("📋 Como exportar seus dados do Samsung Health", expanded=False):
    st.markdown("""
**Passo a passo para exportar no app Samsung Health:**

1. Abra o app **Samsung Health** no celular
2. Toque no ícone do seu **perfil** (canto inferior direito ou superior)
3. Role até o final e toque em **Configurações** (ícone de engrenagem ⚙️)
4. Role até a seção **Dados** e toque em **Baixar dados pessoais**
   - _(Em alguns aparelhos o caminho é: perfil → três pontinhos ⋮ → Configurações → Baixar dados pessoais)_
5. Selecione o período desejado e toque em **Solicitar dados**
6. O Samsung irá preparar o arquivo (pode levar alguns minutos)
7. Quando pronto, você receberá uma notificação — toque nela para **baixar o arquivo ZIP**
8. Transfira o ZIP para o computador e faça o upload abaixo

> **Dica:** O arquivo exportado tem nome como `com.samsung.shealth.YYYYMMDD.zip`
""")

uploaded_zip = st.file_uploader(
    "Selecione o arquivo ZIP exportado do Samsung Health:",
    type=["zip"],
    key="samsung_zip_upload",
)

if uploaded_zip is not None:
    with st.spinner("Lendo o arquivo ZIP..."):
        try:
            steps_rows, exercise_rows = _parse_samsung_zip(uploaded_zip.read())
        except Exception as e:
            st.error(f"Erro ao ler o arquivo: {e}")
            steps_rows, exercise_rows = [], []

    if not steps_rows and not exercise_rows:
        st.warning(
            "Nenhum dado de passos ou exercícios encontrado no arquivo. "
            "Verifique se o ZIP é uma exportação válida do Samsung Health."
        )
    else:
        # Tabela de exercícios encontrados
        existing_keys = {(e["date"], e["type"]) for e in exercises}

        tab_ex, tab_steps = st.tabs([
            f"🏋️ Exercícios ({len(exercise_rows)} encontrados)",
            f"👣 Passos diários ({len(steps_rows)} dias)",
        ])

        with tab_ex:
            if exercise_rows:
                df_ex_imp = pd.DataFrame(exercise_rows)
                df_ex_imp["ja_existe"] = df_ex_imp.apply(
                    lambda r: (r["date"], r["type"]) in existing_keys, axis=1
                )
                df_ex_imp["data_br"] = pd.to_datetime(df_ex_imp["date"]).dt.strftime("%d/%m/%Y")

                novos = df_ex_imp[~df_ex_imp["ja_existe"]]
                duplicados = df_ex_imp[df_ex_imp["ja_existe"]]

                if not novos.empty:
                    st.success(f"**{len(novos)} sessão(ões) nova(s)** prontas para importar:")
                    df_show = novos[["data_br", "type", "duration_min", "calories_burned", "steps", "heart_rate"]].copy()
                    df_show.columns = ["Data", "Tipo", "Duração (min)", "Calorias", "Passos", "FC média (bpm)"]
                    st.dataframe(df_show, width='stretch', hide_index=True)

                    if st.button("💾 Importar sessões de exercício", type="primary", key="btn_import_ex"):
                        next_id = max([e.get("id", 0) for e in exercises], default=0)
                        for _, row in novos.iterrows():
                            next_id += 1
                            exercises.append({
                                "id":             next_id,
                                "date":           row["date"],
                                "type":           row["type"],
                                "duration_min":   int(row["duration_min"]),
                                "calories_burned": int(row["calories_burned"]),
                                "steps":          int(row["steps"]),
                                "sleep_score":    0,
                                "notes":          f"Importado Samsung Health (FC: {int(row['heart_rate'])} bpm)" if row["heart_rate"] else "Importado Samsung Health",
                            })
                        save_exercises(exercises)
                        st.success(f"✅ {len(novos)} sessão(ões) importada(s) com sucesso!")
                        st.rerun()
                else:
                    st.info("Todos os exercícios encontrados já estão registrados.")

                if not duplicados.empty:
                    with st.expander(f"⚠️ {len(duplicados)} registro(s) já existente(s) — clique para ver"):
                        df_dup = duplicados[["data_br", "type", "duration_min", "calories_burned"]].copy()
                        df_dup.columns = ["Data", "Tipo", "Duração (min)", "Calorias"]
                        st.dataframe(df_dup, width='stretch', hide_index=True)
            else:
                st.info("Nenhuma sessão de exercício encontrada no arquivo.")

        with tab_steps:
            if steps_rows:
                df_st_imp = pd.DataFrame(sorted(steps_rows, key=lambda x: x["date"], reverse=True))
                df_st_imp["data_br"] = pd.to_datetime(df_st_imp["date"]).dt.strftime("%d/%m/%Y")
                st.info(
                    "Os dados de passos diários são informativos. "
                    "Para registrar passos de um dia específico, use a seção **Registrar Treino** abaixo "
                    "ou o painel do Smartwatch acima."
                )
                df_st_show = df_st_imp[["data_br", "steps", "calories"]].copy()
                df_st_show.columns = ["Data", "Passos", "Calorias estimadas"]
                st.dataframe(df_st_show, width='stretch', hide_index=True)
            else:
                st.info("Nenhum dado de passos encontrado no arquivo.")

# ── Painel do Smartwatch ───────────────────────────────────────────────────────
st.markdown("<div class='section-header'>⌚ Dados do Smartwatch Ultra — Hoje</div>", unsafe_allow_html=True)

col_w1, col_w2 = st.columns([1, 2])
with col_w1:
    st.markdown(
        "<div class='watch-card'>"
        "<div style='font-size:13px;opacity:0.7;margin-bottom:4px'>SMARTWATCH ULTRA</div>"
        "<div style='font-size:40px;text-align:center'>⌚</div>"
        "<div style='text-align:center;font-size:12px;opacity:0.8;margin-top:8px'>Sincronize os dados abaixo</div>"
        "</div>",
        unsafe_allow_html=True,
    )

with col_w2:
    with st.form("smartwatch_hoje"):
        sc1, sc2 = st.columns(2)
        with sc1:
            sw_steps = st.number_input("Passos (hoje):", 0, 50000, 4000, step=100)
            sw_sleep = st.number_input("Pontuação do sono (0-100):", 0, 100, 78, step=1)
            sw_heart = st.number_input("FC média (bpm):", 40, 200, 68, step=1)
        with sc2:
            sw_calories_watch = st.number_input("Calorias pelo watch (kcal):", 0, 5000, 0, step=10)
            sw_active_min = st.number_input("Minutos ativos:", 0, 300, 30, step=5)
            sw_date = st.date_input("Data:", value=date.today())
        sw_submit = st.form_submit_button("📊 Calcular meu gasto calórico", type="primary")

if sw_submit:
    tdee_calc = calc_tdee(tmb, sw_steps, sw_active_min)
    st.markdown("<div class='section-header'>📊 Resultado do Balanço</div>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            "<div class='metric-card'>"
            "<div class='metric-title'>TMB (Bioimpedância)</div>"
            f"<div class='metric-value'>{tmb:,}<span style='font-size:14px'> kcal</span></div>"
            "<div class='metric-sub'>Metabolismo de repouso</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            "<div class='metric-card'>"
            "<div class='metric-title'>TDEE Estimado</div>"
            f"<div class='metric-value' style='color:#E67E22'>{tdee_calc:,}<span style='font-size:14px'> kcal</span></div>"
            f"<div class='metric-sub'>{sw_steps:,} passos + {sw_active_min} min exerc.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    with m3:
        sleep_color = "#27AE60" if sw_sleep >= 75 else "#F39C12" if sw_sleep >= 60 else "#E74C3C"
        sleep_label = "Ótimo" if sw_sleep >= 85 else "Bom" if sw_sleep >= 70 else "Regular" if sw_sleep >= 55 else "Ruim"
        st.markdown(
            "<div class='metric-card'>"
            "<div class='metric-title'>Qualidade do Sono</div>"
            f"<div class='metric-value' style='color:{sleep_color}'>{sw_sleep}<span style='font-size:14px'>/100</span></div>"
            f"<div class='metric-sub'>{sleep_label}</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    with m4:
        step_color = "#27AE60" if sw_steps >= 7000 else "#F39C12" if sw_steps >= 4000 else "#E74C3C"
        step_label = "Ativo" if sw_steps >= 7000 else "Moderado" if sw_steps >= 4000 else "Sedentário"
        st.markdown(
            "<div class='metric-card'>"
            "<div class='metric-title'>Passos</div>"
            f"<div class='metric-value' style='color:{step_color}'>{sw_steps:,}</div>"
            f"<div class='metric-sub'>{step_label} · Meta: 7.000+</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=sw_steps,
        delta={"reference": 7000, "valueformat": ","},
        gauge={
            "axis": {"range": [0, 15000], "tickformat": ","},
            "bar": {"color": step_color},
            "steps": [
                {"range": [0, 3000], "color": "#ffe0e0"},
                {"range": [3000, 7000], "color": "#fff3cd"},
                {"range": [7000, 15000], "color": "#d4edda"},
            ],
            "threshold": {"line": {"color": "green", "width": 3}, "thickness": 0.8, "value": 7000},
        },
        title={"text": "Passos (meta: 7.000)"},
    ))
    fig_gauge.update_layout(height=280, margin=dict(l=20, r=20, t=60, b=20))
    st.plotly_chart(fig_gauge, width='stretch')

    if sw_steps < 3000:
        st.error("🚨 Nível de atividade muito baixo! Caminhadas curtas ao longo do dia ajudam muito no HDL e no controle glicêmico.")
    elif sw_steps < 7000:
        st.warning("⚠️ Atividade moderada. Tente chegar a 7.000–10.000 passos para maximizar o emagrecimento e melhorar o HDL.")
    else:
        st.success("✅ Parabéns! Nível de atividade adequado.")

# ── Registrar treino ──────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>🏋️ Registrar Treino</div>", unsafe_allow_html=True)

with st.form("novo_treino", clear_on_submit=True):
    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        data_treino = st.date_input("Data:", value=date.today())
        tipo = st.selectbox("Tipo:", ["Musculação", "Caminhada", "Corrida", "HIIT", "Natação",
                                      "Bicicleta", "Yoga/Pilates", "Fisioterapia", "Outro"])
    with tc2:
        duracao = st.number_input("Duração (min):", 5, 300, 60, step=5)
        cal_queimadas = st.number_input("Calorias queimadas (kcal):", 0, 2000, 350, step=10)
        distancia_km = st.number_input("Distância (km):", 0.0, 100.0, 0.0, step=0.1,
                                       help="Preencha para caminhada, corrida e bicicleta")
    with tc3:
        passos_treino = st.number_input("Passos durante o treino:", 0, 30000, 0, step=100)
        sleep_score = st.number_input("Pontuação do sono (noite anterior):", 0, 100, 75, step=1)
    notas_treino = st.text_input("Grupos musculares / observações:")
    t_submit = st.form_submit_button("💾 Salvar Treino", type="primary")

if t_submit:
    new_ex = {
        "id":             max([e.get("id", 0) for e in exercises], default=0) + 1,
        "date":           str(data_treino),
        "type":           tipo,
        "duration_min":   duracao,
        "calories_burned": cal_queimadas,
        "distance_km":    round(distancia_km, 2),
        "steps":          passos_treino,
        "sleep_score":    sleep_score,
        "notes":          notas_treino,
    }
    exercises.append(new_ex)
    save_exercises(exercises)
    st.success(f"✅ Treino de {data_treino.strftime('%d/%m/%Y')} salvo!")
    st.rerun()

# ── Histórico de treinos ──────────────────────────────────────────────────────
if exercises:
    st.markdown("<div class='section-header'>📋 Histórico de Treinos</div>", unsafe_allow_html=True)
    df_ex = pd.DataFrame(sorted(exercises, key=lambda x: x["date"], reverse=True))
    df_ex["date"] = pd.to_datetime(df_ex["date"])
    df_ex["date_str"] = df_ex["date"].dt.strftime("%d/%m/%Y")

    periodo = st.radio(
        "Período (treinos e sono):", ["Últimos 30 dias", "Últimos 90 dias", "Tudo"],
        horizontal=True, index=0
    )
    if periodo == "Últimos 30 dias":
        cutoff = pd.Timestamp.now() - pd.Timedelta("30D")
    elif periodo == "Últimos 90 dias":
        cutoff = pd.Timestamp.now() - pd.Timedelta("90D")
    else:
        cutoff = pd.Timestamp("2018-01-01")

    df_all = df_ex.copy()
    df_period = df_ex[df_ex["date"] >= cutoff]

    # Gráfico 1: Calorias por treino (filtrado por período, só calorias > 0)
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        df_cal = df_period[df_period["calories_burned"] > 0].sort_values("date")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_cal["date"], y=df_cal["calories_burned"],
            marker_color="#1E8449", name="Calorias queimadas",
        ))
        fig.update_layout(height=280, title="Calorias por Treino", plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=False, automargin=True, tickangle=-30),
            yaxis=dict(showgrid=True, gridcolor="#eee", title="kcal", automargin=True),
            showlegend=False, margin=dict(l=50, r=20, t=50, b=60))
        st.plotly_chart(fig, width='stretch')

    # Gráfico 2: Pontuação do sono (filtrado por período, só sono > 0)
    with col_g2:
        df_sleep = df_period[df_period["sleep_score"] > 0].sort_values("date")
        colors_sleep = ["#27AE60" if s >= 75 else "#F39C12" if s >= 60 else "#E74C3C"
                        for s in df_sleep["sleep_score"]]
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=df_sleep["date"], y=df_sleep["sleep_score"],
            marker_color=colors_sleep, name="Sleep Score"))
        fig2.add_hline(y=75, line_dash="dash", line_color="#27AE60", annotation_text="Meta: 75")
        fig2.update_layout(height=280, title="Pontuação do Sono", plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=False, automargin=True, tickangle=-30),
            yaxis=dict(showgrid=True, gridcolor="#eee", title="Score 0-100", automargin=True),
            showlegend=False, margin=dict(l=50, r=100, t=50, b=60))
        st.plotly_chart(fig2, width='stretch')

    # Gráfico 3: Passos — apenas registros com passos > 0 (dados do HealthSync)
    df_steps_real = df_all[df_all["steps"] > 0].sort_values("date")
    if not df_steps_real.empty:
        step_colors = ["#27AE60" if s >= 7000 else "#F39C12" if s >= 4000 else "#E74C3C"
                       for s in df_steps_real["steps"]]
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=df_steps_real["date"], y=df_steps_real["steps"],
            marker_color=step_colors, name="Passos"))
        fig3.add_hline(y=7000, line_dash="dash", line_color="#27AE60", annotation_text="Meta: 7.000 passos")
        fig3.add_hline(y=3000, line_dash="dot", line_color="#E74C3C", annotation_text="Mínimo recomendado")
        fig3.update_layout(height=300, title="Passos Diários (sincronizados pelo HealthSync)", plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=False, automargin=True, tickangle=-30),
            yaxis=dict(showgrid=True, gridcolor="#eee", title="passos", automargin=True),
            showlegend=False, margin=dict(l=50, r=160, t=50, b=60))
        st.plotly_chart(fig3, width='stretch')
    else:
        st.info("Passos serão exibidos aqui após a primeira sincronização automática às 23h30.")

    _TIPOS = ["Musculação", "Caminhada", "Corrida", "HIIT", "Natação",
              "Bicicleta", "Yoga/Pilates", "Fisioterapia", "Outro"]

    st.markdown("**Registros:**")
    ex_filtered = [e for e in exercises if pd.Timestamp(e["date"]) >= cutoff]
    for ex in sorted(ex_filtered, key=lambda x: x["date"], reverse=True):
        col_info, col_edit, col_del = st.columns([10, 1, 1])
        with col_info:
            dt_fmt = datetime.strptime(ex["date"], "%Y-%m-%d").strftime("%d/%m/%Y")
            dist_str = f" · {ex['distance_km']} km" if ex.get("distance_km", 0) > 0 else ""
            st.markdown(
                f"**{dt_fmt}** · {ex['type']} · {ex['duration_min']} min · "
                f"{ex['calories_burned']} kcal{dist_str} · {ex['steps']} passos · "
                f"sono: {ex['sleep_score']}" +
                (f" · _{ex['notes']}_" if ex.get("notes") else "")
            )
        with col_edit:
            if st.button("✏️", key=f"edit_ex_{ex['id']}", help="Editar treino"):
                st.session_state.edit_ex_id = ex["id"] if st.session_state.edit_ex_id != ex["id"] else None
                st.rerun()
        with col_del:
            if st.button("🗑️", key=f"del_ex_{ex['id']}", help="Excluir treino"):
                exercises[:] = [e for e in exercises if e.get("id") != ex["id"]]
                save_exercises(exercises)
                st.rerun()

        if st.session_state.edit_ex_id == ex["id"]:
            with st.form(f"form_edit_ex_{ex['id']}"):
                ec1, ec2, ec3 = st.columns(3)
                with ec1:
                    e_data = st.date_input("Data:", value=datetime.strptime(ex["date"], "%Y-%m-%d").date())
                    tipo_idx = _TIPOS.index(ex["type"]) if ex["type"] in _TIPOS else len(_TIPOS) - 1
                    e_tipo = st.selectbox("Tipo:", _TIPOS, index=tipo_idx)
                with ec2:
                    e_dur = st.number_input("Duração (min):", 5, 300, int(ex.get("duration_min", 60)), step=5)
                    e_cal = st.number_input("Calorias (kcal):", 0, 2000, int(ex.get("calories_burned", 0)), step=10)
                    e_dist = st.number_input("Distância (km):", 0.0, 100.0, float(ex.get("distance_km", 0.0)), step=0.1)
                with ec3:
                    e_passos = st.number_input("Passos:", 0, 30000, int(ex.get("steps", 0)), step=100)
                    e_sono = st.number_input("Sono (0-100):", 0, 100, int(ex.get("sleep_score", 75)), step=1)
                e_notas = st.text_input("Observações:", value=ex.get("notes", ""))
                col_s, col_c = st.columns(2)
                with col_s:
                    e_submit = st.form_submit_button("💾 Salvar alterações", type="primary")
                with col_c:
                    e_cancel = st.form_submit_button("Cancelar")

            if e_submit:
                for i, e in enumerate(exercises):
                    if e.get("id") == ex["id"]:
                        exercises[i].update({
                            "date": str(e_data),
                            "type": e_tipo,
                            "duration_min": e_dur,
                            "calories_burned": e_cal,
                            "distance_km": round(e_dist, 2),
                            "steps": e_passos,
                            "sleep_score": e_sono,
                            "notes": e_notas,
                        })
                        break
                save_exercises(exercises)
                st.session_state.edit_ex_id = None
                st.rerun()
            elif e_cancel:
                st.session_state.edit_ex_id = None
                st.rerun()

# ── Dicas personalizadas ──────────────────────────────────────────────────────
st.markdown("<div class='section-header'>💡 Dicas de Atividade Física (Perfil de Leandro)</div>", unsafe_allow_html=True)
st.markdown("""
> **Atenção:** Você possui laudo de RM da coluna lombo-sacra. Exerça as atividades com supervisão profissional (fisioterapeuta/preparador físico).

| Recomendação | Meta semanal | Status |
|---|---|---|
| 🏋️ Musculação | 3–4x por semana | Em andamento ✅ |
| 🚶 Caminhada / cardio aeróbico | 150 min/semana | Aumentar ⚠️ |
| 📊 Passos diários | 7.000–10.000 | Aumentar ⚠️ |
| 🧘 Alongamento / mobilidade | Após cada treino | Incluir |

**Por que aumentar o cardio?**
- HDL baixo (33 mg/dL) → exercício aeróbico é o principal elevador natural do HDL
- Controle glicêmico → caminhadas de 10 min após refeições reduzem pico de glicose
- Hipotireoidismo → pode causar fadiga; cardio leve ajuda a combater

**Meta de passos progressiva:**
- Semana 1–2: 4.000 passos/dia
- Semana 3–4: 6.000 passos/dia
- A partir do mês 2: 8.000–10.000 passos/dia
""")
