import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_manager import load_diet, load_food_log, save_food_log, load_bioimpedance, load_exercises, calc_tdee

st.set_page_config(page_title="Dieta & Calorias", page_icon="🥗", layout="wide")

st.markdown("""
<style>
.section-header{font-size:22px;font-weight:700;color:#1E8449;border-bottom:3px solid #1E8449;padding-bottom:8px;margin:20px 0 16px}
.meal-card{background:#f8fff9;border:1px solid #c8e6c9;border-radius:12px;padding:16px;margin:8px 0}
.meal-title{font-size:17px;font-weight:700;color:#1a5c2a;margin-bottom:8px}
.food-item{font-size:13px;color:#333;padding:3px 0;border-bottom:1px solid #eee}
.kcal-badge{background:#1E8449;color:white;border-radius:20px;padding:2px 10px;font-size:12px;font-weight:700}
.deficit-good{background:linear-gradient(135deg,#f0fff4,#e8f5e9);border:1px solid #27AE60;border-radius:12px;padding:16px}
.deficit-bad{background:linear-gradient(135deg,#fff5f5,#ffe0e0);border:1px solid #E74C3C;border-radius:12px;padding:16px}
</style>
""", unsafe_allow_html=True)

st.markdown("## 🥗 Dieta & Calorias")

diet = load_diet()
food_logs = load_food_log()
bio_list = load_bioimpedance()
exercises = load_exercises()

today_str = str(date.today())

# ── Balanço calórico hoje ──────────────────────────────────────────────────────
st.markdown("<div class='section-header'>⚖️ Balanço Calórico de Hoje</div>", unsafe_allow_html=True)

# TMB da última bioimpedância
tmb = 1783
if bio_list:
    latest_bio = sorted(bio_list, key=lambda x: x["date"])[-1]
    tmb = latest_bio.get("tmb_kcal", 1783)

# Passos e exercício de hoje (pode ser do Smartwatch ou último log)
today_exercise = next((e for e in sorted(exercises, key=lambda x: x["date"], reverse=True)
                        if e["date"] == today_str), None)
steps_hoje = st.number_input("Passos hoje (Smartwatch Ultra):", min_value=0, max_value=50000,
                              value=today_exercise["steps"] if today_exercise else 3000, step=100,
                              key="steps_hoje")
exercise_min_hoje = st.number_input("Minutos de exercício hoje:", min_value=0, max_value=300,
                                     value=today_exercise["duration_min"] if today_exercise else 0, step=5,
                                     key="ex_min_hoje")

tdee_hoje = calc_tdee(tmb, steps_hoje, exercise_min_hoje)
kcal_plano = diet.get("total_kcal_plan", 1740)

# Logs alimentares de hoje
today_logs = [log for log in food_logs if log.get("date") == today_str]
kcal_consumidas = sum(log.get("kcal_total", 0) for log in today_logs)

deficit = tdee_hoje - kcal_consumidas
restante = kcal_plano - kcal_consumidas

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""<div style='text-align:center;background:#f0f4ff;border-radius:10px;padding:14px'>
        <div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>TMB (Metabolismo Basal)</div>
        <div style='font-size:26px;font-weight:700;color:#2980B9'>{tmb:,}</div>
        <div style='font-size:12px;color:#888'>kcal/dia</div>
    </div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""<div style='text-align:center;background:#fffbf0;border-radius:10px;padding:14px'>
        <div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>TDEE (Gasto Total)</div>
        <div style='font-size:26px;font-weight:700;color:#E67E22'>{tdee_hoje:,}</div>
        <div style='font-size:12px;color:#888'>{steps_hoje:,} passos + {exercise_min_hoje} min</div>
    </div>""", unsafe_allow_html=True)
with col3:
    color3 = "#27AE60" if kcal_consumidas <= kcal_plano else "#E74C3C"
    st.markdown(f"""<div style='text-align:center;background:#f8fff9;border-radius:10px;padding:14px'>
        <div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>Consumido Hoje</div>
        <div style='font-size:26px;font-weight:700;color:{color3}'>{kcal_consumidas:,}</div>
        <div style='font-size:12px;color:#888'>Plano: {kcal_plano:,} kcal</div>
    </div>""", unsafe_allow_html=True)
with col4:
    deficit_color = "#27AE60" if deficit > 0 else "#E74C3C"
    deficit_label = "Déficit" if deficit > 0 else "Superávit"
    st.markdown(f"""<div style='text-align:center;background:{"#f0fff4" if deficit > 0 else "#fff5f5"};border-radius:10px;padding:14px'>
        <div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>{deficit_label} Calórico</div>
        <div style='font-size:26px;font-weight:700;color:{deficit_color}'>{abs(deficit):,}</div>
        <div style='font-size:12px;color:#888'>kcal ({deficit_label.lower()})</div>
    </div>""", unsafe_allow_html=True)

# Barra de progresso calórico
st.markdown("**Calorias consumidas vs. plano:**")
prog = min(1.0, kcal_consumidas / kcal_plano) if kcal_plano > 0 else 0
st.progress(prog)
st.caption(f"{kcal_consumidas} / {kcal_plano} kcal — Restam {max(0, restante):.0f} kcal para o plano")

if deficit >= 300:
    st.success(f"✅ Déficit calórico de **{deficit} kcal** — ótimo para emagrecimento!")
elif deficit >= 0:
    st.info(f"ℹ️ Déficit calórico leve de {deficit} kcal. Bom, mas pode aumentar a atividade.")
else:
    st.error(f"⚠️ Superávit de {abs(deficit)} kcal — acima do gasto. Ajuste as refeições.")

# ── Registrar refeição ─────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>🍽️ Registrar o que comi</div>", unsafe_allow_html=True)

meals_options = {m["id"]: f"{m['name']} (~{m['kcal_estimated']} kcal)" for m in diet.get("meals",[])}
meals_by_id = {m["id"]: m for m in diet.get("meals",[])}

with st.form("log_refeicao", clear_on_submit=True):
    col_a, col_b = st.columns([2, 1])
    with col_a:
        meal_id = st.selectbox("Refeição:", list(meals_options.keys()), format_func=lambda x: meals_options[x])
        sel_meal = meals_by_id.get(meal_id, {})
        foods_in_meal = sel_meal.get("foods", [])

        # Checkboxes para alimentos consumidos (simplificado — marcar o que comeu)
        st.caption(f"Alimentos do plano para esta refeição ({sel_meal.get('name','')}):")
        selected_foods = []
        for food in foods_in_meal:
            checked = st.checkbox(
                f"{food['item']} — {food['qty']} ({food['kcal']} kcal, {food['prot_g']}g prot)",
                value=True, key=f"food_{meal_id}_{food['item']}"
            )
            if checked:
                selected_foods.append(food)

        extra_desc = st.text_input("Outros alimentos não previstos no plano (descreva):")
        extra_kcal = st.number_input("Calorias extras estimadas (kcal):", 0, 2000, 0, step=10)
    with col_b:
        data_ref = st.date_input("Data:", value=date.today())
        hora_ref = st.time_input("Hora:")
        obs_ref = st.text_input("Observações:")

        kcal_sel = sum(f["kcal"] for f in selected_foods)
        prot_sel = sum(f.get("prot_g",0) for f in selected_foods)
        carb_sel = sum(f.get("carb_g",0) for f in selected_foods)
        fat_sel  = sum(f.get("fat_g",0) for f in selected_foods)

        st.markdown(f"""
        **Resumo desta refeição:**
        - 🔥 Calorias: **{kcal_sel + extra_kcal} kcal**
        - 💪 Proteínas: {prot_sel:.0f}g
        - 🍞 Carboidratos: {carb_sel:.0f}g
        - 🧈 Gorduras: {fat_sel:.0f}g
        """)

    submitted_log = st.form_submit_button("💾 Registrar Refeição", type="primary")

if submitted_log:
    new_log = {
        "id": max([l.get("id",0) for l in food_logs], default=0) + 1,
        "date": str(data_ref),
        "time": str(hora_ref),
        "meal_id": meal_id,
        "meal_name": sel_meal.get("name",""),
        "foods": [f["item"] for f in selected_foods],
        "kcal_total": kcal_sel + extra_kcal,
        "prot_g": round(prot_sel, 1),
        "carb_g": round(carb_sel, 1),
        "fat_g": round(fat_sel, 1),
        "extra_desc": extra_desc,
        "extra_kcal": extra_kcal,
        "obs": obs_ref
    }
    food_logs.append(new_log)
    save_food_log(food_logs)
    st.success(f"✅ {sel_meal.get('name','')} registrado: {kcal_sel + extra_kcal} kcal")
    st.rerun()

# ── Histórico alimentar do dia ─────────────────────────────────────────────────
if today_logs:
    st.markdown("<div class='section-header'>📋 Refeições de Hoje</div>", unsafe_allow_html=True)
    for log in sorted(today_logs, key=lambda x: x.get("time","")):
        color_bg = "#f0fff4"
        st.markdown(f"""<div style='background:{color_bg};border:1px solid #c8e6c9;border-radius:10px;padding:12px;margin:6px 0'>
            <b>🍽️ {log['meal_name']}</b> · {log.get('time','')}<br>
            <span style='color:#E74C3C;font-weight:700'>{log['kcal_total']} kcal</span> ·
            Prot: {log.get('prot_g',0)}g · Carb: {log.get('carb_g',0)}g · Gord: {log.get('fat_g',0)}g<br>
            <span style='font-size:12px;color:#666'>{', '.join(log.get('foods',[]))}</span>
            {f"<br><span style='font-size:12px;color:#999'>{log['obs']}</span>" if log.get('obs') else ''}
        </div>""", unsafe_allow_html=True)

    # Gráfico de macros do dia
    st.markdown("**Macronutrientes do dia:**")
    total_prot = sum(l.get("prot_g",0) for l in today_logs)
    total_carb = sum(l.get("carb_g",0) for l in today_logs)
    total_fat  = sum(l.get("fat_g",0) for l in today_logs)
    if total_prot + total_carb + total_fat > 0:
        fig_pie = go.Figure(data=[go.Pie(
            labels=["Proteínas","Carboidratos","Gorduras"],
            values=[total_prot, total_carb, total_fat],
            marker_colors=["#2980B9","#F39C12","#E74C3C"],
            hole=0.4
        )])
        fig_pie.update_layout(height=300, margin=dict(l=20,r=20,t=30,b=80),
            legend=dict(orientation="h", yanchor="bottom", y=-0.25))
        st.plotly_chart(fig_pie, use_container_width=True)

# ── Plano nutricional ──────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>📄 Plano Nutricional Atual</div>", unsafe_allow_html=True)
st.caption(f"Nutricionista: **{diet.get('nutricionista','—')}** (CRN {diet.get('nutritionist_crn','—')}) · "
           f"Desde: {datetime.strptime(diet.get('plan_date','2026-06-02'),'%Y-%m-%d').strftime('%d/%m/%Y')}")
st.caption(f"Objetivo: **{diet.get('goal','—')}** · Total planejado: **{diet.get('total_kcal_plan',0)} kcal**")
if diet.get("notes"):
    st.info(f"📝 {diet['notes']}")

ICONS = {"cafe":"☕","almoco":"🍽️","lanche":"🥤","jantar":"🌙","cha":"🍵"}

for meal in diet.get("meals",[]):
    mid = meal["id"]
    icon = ICONS.get(mid, "🍴")
    with st.expander(f"{icon} {meal['name']} — ~{meal['kcal_estimated']} kcal | {meal.get('time_suggested','')}"):
        foods = meal.get("foods",[])
        df_foods = pd.DataFrame(foods)[["item","qty","kcal","prot_g","carb_g","fat_g"]]
        df_foods.columns = ["Alimento","Quantidade","Kcal","Prot (g)","Carb (g)","Gord (g)"]
        st.dataframe(df_foods, use_container_width=True, hide_index=True)
        total_k = sum(f["kcal"] for f in foods)
        total_p = sum(f.get("prot_g",0) for f in foods)
        total_c = sum(f.get("carb_g",0) for f in foods)
        total_f = sum(f.get("fat_g",0) for f in foods)
        st.markdown(f"**Total:** {total_k} kcal · Prot {total_p:.0f}g · Carb {total_c:.0f}g · Gord {total_f:.0f}g")
        if meal.get("substitutions"):
            st.markdown("**Substituições:**")
            for sub in meal["substitutions"]:
                st.markdown(f"- {sub}")

# ── Histórico semanal ─────────────────────────────────────────────────────────
if food_logs:
    st.markdown("<div class='section-header'>📅 Histórico Semanal</div>", unsafe_allow_html=True)
    df_logs = pd.DataFrame(food_logs)
    df_logs["date"] = pd.to_datetime(df_logs["date"])
    df_daily = df_logs.groupby("date").agg({"kcal_total":"sum","prot_g":"sum"}).reset_index()
    df_daily = df_daily.sort_values("date")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_daily["date"], y=df_daily["kcal_total"], name="Kcal consumidas",
        marker_color="#1E8449", opacity=0.8))
    fig.add_hline(y=tdee_hoje, line_dash="dash", line_color="#E74C3C",
                  annotation_text=f"TDEE estimado: {tdee_hoje} kcal")
    fig.add_hline(y=kcal_plano, line_dash="dot", line_color="#F39C12",
                  annotation_text=f"Plano: {kcal_plano} kcal")
    fig.update_layout(height=300, title="Calorias Diárias", plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=False, automargin=True, tickangle=-30),
        yaxis=dict(showgrid=True, gridcolor="#eee", title="kcal", automargin=True),
        showlegend=False, margin=dict(l=50, r=180, t=50, b=60))
    st.plotly_chart(fig, use_container_width=True)
