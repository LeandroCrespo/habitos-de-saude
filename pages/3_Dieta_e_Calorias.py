import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime, time as dt_time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_manager import load_diet, load_food_log, save_food_log, load_bioimpedance, load_exercises, calc_tdee

st.set_page_config(page_title="Dieta & Calorias", page_icon="🥗", layout="wide")

st.markdown("""
<style>
.section-header{font-size:22px;font-weight:700;color:#1E8449;border-bottom:3px solid #1E8449;padding-bottom:8px;margin:20px 0 16px}
.kcal-badge{background:#1E8449;color:white;border-radius:20px;padding:2px 10px;font-size:12px;font-weight:700}
</style>
""", unsafe_allow_html=True)

st.markdown("## 🥗 Dieta & Calorias")

diet      = load_diet()
food_logs = load_food_log()
bio_list  = load_bioimpedance()
exercises = load_exercises()

today_str = str(date.today())

# ── Session state ──────────────────────────────────────────────────────────────
if "diet_form_key"   not in st.session_state: st.session_state.diet_form_key   = 0
if "editing_log_id"  not in st.session_state: st.session_state.editing_log_id  = None

# ── Balanço calórico hoje ──────────────────────────────────────────────────────
st.markdown("<div class='section-header'>⚖️ Balanço Calórico de Hoje</div>", unsafe_allow_html=True)

tmb = 1783
if bio_list:
    tmb = sorted(bio_list, key=lambda x: x["date"])[-1].get("tmb_kcal", 1783)

today_exercise = next(
    (e for e in sorted(exercises, key=lambda x: x["date"], reverse=True) if e["date"] == today_str), None
)
steps_hoje = st.number_input("Passos hoje (Smartwatch Ultra):", min_value=0, max_value=50000,
                              value=today_exercise["steps"] if today_exercise else 3000, step=100,
                              key="steps_hoje")
exercise_min_hoje = st.number_input("Minutos de exercício hoje:", min_value=0, max_value=300,
                                     value=today_exercise["duration_min"] if today_exercise else 0, step=5,
                                     key="ex_min_hoje")

tdee_hoje   = calc_tdee(tmb, steps_hoje, exercise_min_hoje)
kcal_plano  = diet.get("total_kcal_plan", 1740)
today_logs  = [log for log in food_logs if log.get("date") == today_str]
kcal_consumidas = sum(log.get("kcal_total", 0) for log in today_logs)
deficit  = tdee_hoje - kcal_consumidas
restante = kcal_plano - kcal_consumidas

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""<div style='text-align:center;background:#f0f4ff;border-radius:10px;padding:14px'>
        <div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>TMB</div>
        <div style='font-size:26px;font-weight:700;color:#2980B9'>{tmb:,}</div>
        <div style='font-size:12px;color:#888'>kcal/dia</div></div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""<div style='text-align:center;background:#fffbf0;border-radius:10px;padding:14px'>
        <div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>TDEE</div>
        <div style='font-size:26px;font-weight:700;color:#E67E22'>{tdee_hoje:,}</div>
        <div style='font-size:12px;color:#888'>{steps_hoje:,} passos + {exercise_min_hoje} min</div></div>""", unsafe_allow_html=True)
with col3:
    c3 = "#27AE60" if kcal_consumidas <= kcal_plano else "#E74C3C"
    st.markdown(f"""<div style='text-align:center;background:#f8fff9;border-radius:10px;padding:14px'>
        <div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>Consumido</div>
        <div style='font-size:26px;font-weight:700;color:{c3}'>{kcal_consumidas:,}</div>
        <div style='font-size:12px;color:#888'>Plano: {kcal_plano:,} kcal</div></div>""", unsafe_allow_html=True)
with col4:
    dc = "#27AE60" if deficit > 0 else "#E74C3C"
    dl = "Déficit" if deficit > 0 else "Superávit"
    bg = "#f0fff4" if deficit > 0 else "#fff5f5"
    st.markdown(f"""<div style='text-align:center;background:{bg};border-radius:10px;padding:14px'>
        <div style='font-size:11px;color:#666;font-weight:700;text-transform:uppercase'>{dl}</div>
        <div style='font-size:26px;font-weight:700;color:{dc}'>{abs(deficit):,}</div>
        <div style='font-size:12px;color:#888'>kcal</div></div>""", unsafe_allow_html=True)

prog = min(1.0, kcal_consumidas / kcal_plano) if kcal_plano > 0 else 0
st.progress(prog)
st.caption(f"{kcal_consumidas} / {kcal_plano} kcal — Restam {max(0, restante):.0f} kcal")
if deficit >= 300:   st.success(f"✅ Déficit de **{deficit} kcal** — ótimo!")
elif deficit >= 0:   st.info(f"ℹ️ Déficit leve de {deficit} kcal.")
else:                st.error(f"⚠️ Superávit de {abs(deficit)} kcal — acima do gasto.")

# ── Helpers ────────────────────────────────────────────────────────────────────
meals_options = {m["id"]: f"{m['name']} (~{m['kcal_estimated']} kcal)" for m in diet.get("meals", [])}
meals_by_id   = {m["id"]: m for m in diet.get("meals", [])}

def _food_lbl(f):
    return (f"{f['item']} — {f['qty']} "
            f"({f['kcal']} kcal · P:{f.get('prot_g',0)}g · C:{f.get('carb_g',0)}g · G:{f.get('fat_g',0)}g)")

def _lbl_to_food(items, label):
    for f in items:
        if _food_lbl(f) == label:
            return f
    return None

_empty_custom = pd.DataFrame({
    "Alimento": pd.Series(dtype="str"),
    "Kcal":     pd.Series(dtype="float"),
    "Prot (g)": pd.Series(dtype="float"),
    "Carb (g)": pd.Series(dtype="float"),
    "Gord (g)": pd.Series(dtype="float"),
})

_col_cfg = {
    "Alimento": st.column_config.TextColumn("Alimento", width="large"),
    "Kcal":     st.column_config.NumberColumn("Kcal",     min_value=0, max_value=2000, step=5),
    "Prot (g)": st.column_config.NumberColumn("Prot (g)", min_value=0, max_value=200,  step=0.5),
    "Carb (g)": st.column_config.NumberColumn("Carb (g)", min_value=0, max_value=300,  step=0.5),
    "Gord (g)": st.column_config.NumberColumn("Gord (g)", min_value=0, max_value=200,  step=0.5),
}

def _parse_time(t_str):
    try:
        parts = str(t_str).split(":")
        return dt_time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
    except Exception:
        return dt_time(12, 0)

# ── Refeições de Hoje ──────────────────────────────────────────────────────────
if today_logs:
    st.markdown("<div class='section-header'>📋 Refeições de Hoje</div>", unsafe_allow_html=True)
    for log in sorted(today_logs, key=lambda x: x.get("time", "")):
        hora_raw = str(log.get("time", ""))
        hora_fmt = hora_raw[:-3] if hora_raw.endswith(":00") and len(hora_raw) > 5 else hora_raw
        obs_html = f"<br><span style='font-size:12px;color:#999'>{log['obs']}</span>" if log.get("obs") else ""
        html_card = (
            "<div style='background:#f0fff4;border:1px solid #c8e6c9;border-radius:10px;padding:12px;margin:2px 0'>"
            f"<b>🍽️ {log['meal_name']}</b> · {hora_fmt}<br>"
            f"<span style='color:#E74C3C;font-weight:700'>{log['kcal_total']:.0f} kcal</span> · "
            f"P:{log.get('prot_g',0)}g · C:{log.get('carb_g',0)}g · G:{log.get('fat_g',0)}g<br>"
            f"<span style='font-size:12px;color:#555'>{', '.join(log.get('foods', []))}</span>"
            + obs_html + "</div>"
        )
        c_card, c_edit, c_del = st.columns([10, 1, 1])
        with c_card:
            st.markdown(html_card, unsafe_allow_html=True)
        with c_edit:
            if st.button("✏️", key=f"edit_btn_{log['id']}", help="Editar refeição"):
                st.session_state.editing_log_id = log["id"]
                st.session_state.diet_form_key += 1
                st.rerun()
        with c_del:
            if st.button("🗑️", key=f"del_btn_{log['id']}", help="Excluir refeição"):
                food_logs[:] = [l for l in food_logs if l.get("id") != log["id"]]
                save_food_log(food_logs)
                if st.session_state.editing_log_id == log["id"]:
                    st.session_state.editing_log_id = None
                st.rerun()

    # Macros do dia
    tp = sum(l.get("prot_g", 0) for l in today_logs)
    tc = sum(l.get("carb_g", 0) for l in today_logs)
    tf = sum(l.get("fat_g",  0) for l in today_logs)
    if tp + tc + tf > 0:
        fig_pie = go.Figure(data=[go.Pie(
            labels=["Proteínas", "Carboidratos", "Gorduras"], values=[tp, tc, tf],
            marker_colors=["#2980B9", "#F39C12", "#E74C3C"], hole=0.4,
        )])
        fig_pie.update_layout(height=260, margin=dict(l=20, r=20, t=20, b=70),
                               legend=dict(orientation="h", yanchor="bottom", y=-0.3))
        st.plotly_chart(fig_pie, use_container_width=True)

# ── Formulário de edição ───────────────────────────────────────────────────────
editing_id  = st.session_state.editing_log_id
editing_log = next((l for l in food_logs if l.get("id") == editing_id), None) if editing_id else None

if editing_log:
    st.markdown("<div class='section-header'>✏️ Editar Refeição</div>", unsafe_allow_html=True)
    st.info(
        f"Editando **{editing_log['meal_name']}** de {editing_log['date']} às {editing_log.get('time', '')}  \n"
        "Ajuste os itens abaixo e clique em **Salvar Alterações**."
    )

    edit_meal   = meals_by_id.get(editing_log["meal_id"], {})
    edit_groups = edit_meal.get("groups", [])
    edit_preps  = edit_meal.get("preparations", [])
    edit_foods_in_log = set(editing_log.get("foods", []))

    # Identifica se a refeição original usou uma preparação
    prep_used = next((p for p in edit_preps if p["item"] in edit_foods_in_log), None)

    # Seletor de preparação fora do form
    edit_prep_selected = None
    if edit_preps:
        edit_prep_labels = ["— Refeição base (grupos abaixo) —"] + [
            f"{p['item']} ({p['kcal']} kcal)" for p in edit_preps
        ]
        edit_prep_default_idx = 0
        if prep_used:
            try:
                edit_prep_default_idx = [p["item"] for p in edit_preps].index(prep_used["item"]) + 1
            except ValueError:
                pass
        edit_prep_choice = st.selectbox(
            "🍳 Preparação alternativa:",
            edit_prep_labels,
            index=edit_prep_default_idx,
            key=f"edit_prep_sel_{editing_id}"
        )
        if edit_prep_choice != edit_prep_labels[0]:
            prep_name = edit_prep_choice.split(" (")[0]
            edit_prep_selected = next((p for p in edit_preps if p["item"] == prep_name), None)

    # Alimentos não reconhecidos em nenhum grupo (extras)
    all_group_names = {f["item"] for g in edit_groups for f in g.get("items", [])}
    prep_names      = {p["item"] for p in edit_preps}
    unmatched       = [n for n in editing_log.get("foods", [])
                       if n not in all_group_names and n not in prep_names]
    unmatched_df    = pd.DataFrame(
        [{"Alimento": n, "Kcal": 0.0, "Prot (g)": 0.0, "Carb (g)": 0.0, "Gord (g)": 0.0} for n in unmatched]
    ) if unmatched else _empty_custom.copy()

    efk = f"ef_{editing_id}"
    with st.form(f"edit_form_{efk}"):
        col_a, col_b = st.columns([2, 1])
        with col_a:
            edit_selected_foods = []

            if edit_prep_selected:
                st.markdown(f"**Preparação:** {edit_prep_selected['item']}")
                st.caption("Grupos desabilitados enquanto uma preparação está selecionada.")

            for group in edit_groups:
                group_items = group.get("items", [])
                if not group_items:
                    continue
                grp_label = f"{group.get('emoji', '')} **{group['name']}**"
                if group.get("instruction"):
                    grp_label += f" — _{group['instruction']}_"

                # Pré-seleciona os itens que estavam no log original
                default_labels = [_food_lbl(f) for f in group_items if f["item"] in edit_foods_in_log]
                all_labels     = [_food_lbl(f) for f in group_items]

                sel = st.multiselect(
                    grp_label,
                    options=all_labels,
                    default=default_labels,
                    key=f"edit_grp_{efk}_{group['id']}",
                    disabled=bool(edit_prep_selected),
                )
                if not edit_prep_selected:
                    for lbl in sel:
                        f = _lbl_to_food(group_items, lbl)
                        if f:
                            edit_selected_foods.append(f)

            st.caption("**Alimentos fora do plano:**")
            edit_custom_df = st.data_editor(
                unmatched_df,
                num_rows="dynamic",
                use_container_width=True,
                column_config=_col_cfg,
                key=f"edit_custom_{efk}",
            )

        with col_b:
            edit_date_val = datetime.strptime(editing_log["date"], "%Y-%m-%d").date()
            edit_time_val = _parse_time(editing_log.get("time", "12:00:00"))

            edit_date = st.date_input("Data:", value=edit_date_val)
            edit_time = st.time_input("Hora:", value=edit_time_val)
            edit_obs  = st.text_input("Observações:", value=editing_log.get("obs", ""))

            if edit_prep_selected:
                ek = edit_prep_selected["kcal"]
                ep = edit_prep_selected.get("prot_g", 0)
                ec = edit_prep_selected.get("carb_g", 0)
                ef = edit_prep_selected.get("fat_g",  0)
            else:
                ek = sum(f["kcal"]          for f in edit_selected_foods)
                ep = sum(f.get("prot_g", 0) for f in edit_selected_foods)
                ec = sum(f.get("carb_g", 0) for f in edit_selected_foods)
                ef = sum(f.get("fat_g",  0) for f in edit_selected_foods)

            st.markdown(f"""
**Resumo (plano):**
- 🔥 {ek:.0f} kcal
- 💪 {ep:.1f}g prot
- 🍞 {ec:.1f}g carb
- 🧈 {ef:.1f}g gord
""")

        cs, cc = st.columns(2)
        with cs:
            submitted_edit = st.form_submit_button("💾 Salvar Alterações", type="primary")
        with cc:
            cancel_edit = st.form_submit_button("✖ Cancelar")

    if cancel_edit:
        st.session_state.editing_log_id = None
        st.rerun()

    if submitted_edit:
        extra_kcal_t = extra_prot_t = extra_carb_t = extra_fat_t = 0.0
        extra_items_e = []
        for _, row in edit_custom_df.iterrows():
            name = str(row.get("Alimento") or "").strip()
            if not name:
                continue
            extra_items_e.append(name)
            extra_kcal_t += float(row["Kcal"])     if pd.notna(row.get("Kcal"))     else 0.0
            extra_prot_t += float(row["Prot (g)"]) if pd.notna(row.get("Prot (g)")) else 0.0
            extra_carb_t += float(row["Carb (g)"]) if pd.notna(row.get("Carb (g)")) else 0.0
            extra_fat_t  += float(row["Gord (g)"]) if pd.notna(row.get("Gord (g)")) else 0.0

        if edit_prep_selected:
            foods_e = [edit_prep_selected["item"]] + extra_items_e
        else:
            foods_e = [f["item"] for f in edit_selected_foods] + extra_items_e

        for i, l in enumerate(food_logs):
            if l.get("id") == editing_id:
                food_logs[i] = {
                    **l,
                    "date":       str(edit_date),
                    "time":       str(edit_time),
                    "foods":      foods_e,
                    "kcal_total": round(ek + extra_kcal_t, 0),
                    "prot_g":     round(ep + extra_prot_t, 1),
                    "carb_g":     round(ec + extra_carb_t, 1),
                    "fat_g":      round(ef + extra_fat_t,  1),
                    "extra_desc": ", ".join(extra_items_e),
                    "extra_kcal": round(extra_kcal_t, 0),
                    "obs":        edit_obs,
                }
                break

        save_food_log(food_logs)
        st.session_state.editing_log_id = None
        st.session_state.diet_form_key += 1
        st.success("✅ Refeição atualizada!")
        st.rerun()

# ── Registrar nova refeição ────────────────────────────────────────────────────
st.markdown("<div class='section-header'>🍽️ Registrar o que comi</div>", unsafe_allow_html=True)

meal_id  = st.selectbox("Refeição:", list(meals_options.keys()), format_func=lambda x: meals_options[x])
sel_meal = meals_by_id.get(meal_id, {})
groups   = sel_meal.get("groups", [])
preps    = sel_meal.get("preparations", [])

prep_selected = None
if preps:
    prep_labels = ["— Refeição base (grupos abaixo) —"] + [
        f"{p['item']} ({p['kcal']} kcal)" for p in preps
    ]
    prep_choice = st.selectbox(
        "🍳 Preparação alternativa _(substitui os grupos)_:",
        prep_labels,
        key=f"prep_sel_{meal_id}"
    )
    if prep_choice != prep_labels[0]:
        prep_name = prep_choice.split(" (")[0]
        prep_selected = next((p for p in preps if p["item"] == prep_name), None)
        if prep_selected:
            st.info(
                f"**{prep_selected['item']}** — {prep_selected.get('desc', '')}  \n"
                f"🔥 {prep_selected['kcal']} kcal · "
                f"P:{prep_selected.get('prot_g',0)}g · "
                f"C:{prep_selected.get('carb_g',0)}g · "
                f"G:{prep_selected.get('fat_g',0)}g"
            )

fk = st.session_state.diet_form_key
with st.form(f"log_{fk}", clear_on_submit=True):
    col_a, col_b = st.columns([2, 1])
    with col_a:
        all_selected_foods = []

        if prep_selected:
            st.markdown(f"**Preparação selecionada:** {prep_selected['item']}")
            st.caption("Grupos desabilitados enquanto uma preparação está selecionada.")

        for group in groups:
            group_items = group.get("items", [])
            if not group_items:
                continue
            default_labels = [_food_lbl(f) for f in group_items if f.get("default", False)]
            all_labels     = [_food_lbl(f) for f in group_items]
            grp_label = f"{group.get('emoji', '')} **{group['name']}**"
            if group.get("instruction"):
                grp_label += f" — _{group['instruction']}_"

            sel = st.multiselect(
                grp_label,
                options=all_labels,
                default=default_labels,
                key=f"grp_{fk}_{meal_id}_{group['id']}",
                disabled=bool(prep_selected),
            )
            if not prep_selected:
                for lbl in sel:
                    f = _lbl_to_food(group_items, lbl)
                    if f:
                        all_selected_foods.append(f)

        st.caption("**Alimentos fora do plano** — clique em ＋ para adicionar linhas:")
        custom_df = st.data_editor(
            _empty_custom,
            num_rows="dynamic",
            use_container_width=True,
            column_config=_col_cfg,
            key=f"custom_ed_{fk}",
        )

    with col_b:
        data_ref = st.date_input("Data:", value=date.today())
        hora_ref = st.time_input("Hora:")
        obs_ref  = st.text_input("Observações:")

        if prep_selected:
            kcal_plan = prep_selected["kcal"]
            prot_plan = prep_selected.get("prot_g", 0)
            carb_plan = prep_selected.get("carb_g", 0)
            fat_plan  = prep_selected.get("fat_g",  0)
        else:
            kcal_plan = sum(f["kcal"]          for f in all_selected_foods)
            prot_plan = sum(f.get("prot_g", 0) for f in all_selected_foods)
            carb_plan = sum(f.get("carb_g", 0) for f in all_selected_foods)
            fat_plan  = sum(f.get("fat_g",  0) for f in all_selected_foods)

        st.markdown(f"""
**Resumo (plano):**
- 🔥 {kcal_plan:.0f} kcal
- 💪 {prot_plan:.1f}g prot
- 🍞 {carb_plan:.1f}g carb
- 🧈 {fat_plan:.1f}g gord
""")
        st.caption("*(+ extras ao salvar)*")

    submitted_log = st.form_submit_button("💾 Registrar Refeição", type="primary")

if submitted_log:
    extra_kcal_tot = extra_prot_tot = extra_carb_tot = extra_fat_tot = 0.0
    extra_items = []
    for _, row in custom_df.iterrows():
        name = str(row.get("Alimento") or "").strip()
        if not name:
            continue
        extra_items.append(name)
        extra_kcal_tot += float(row["Kcal"])     if pd.notna(row.get("Kcal"))     else 0.0
        extra_prot_tot += float(row["Prot (g)"]) if pd.notna(row.get("Prot (g)")) else 0.0
        extra_carb_tot += float(row["Carb (g)"]) if pd.notna(row.get("Carb (g)")) else 0.0
        extra_fat_tot  += float(row["Gord (g)"]) if pd.notna(row.get("Gord (g)")) else 0.0

    foods_list = ([prep_selected["item"]] if prep_selected else [f["item"] for f in all_selected_foods]) + extra_items
    total_kcal = kcal_plan + extra_kcal_tot
    total_prot = prot_plan + extra_prot_tot
    total_carb = carb_plan + extra_carb_tot
    total_fat  = fat_plan  + extra_fat_tot

    new_log = {
        "id":         max([l.get("id", 0) for l in food_logs], default=0) + 1,
        "date":       str(data_ref),
        "time":       str(hora_ref),
        "meal_id":    meal_id,
        "meal_name":  sel_meal.get("name", ""),
        "foods":      foods_list,
        "kcal_total": round(total_kcal, 0),
        "prot_g":     round(total_prot, 1),
        "carb_g":     round(total_carb, 1),
        "fat_g":      round(total_fat,  1),
        "extra_desc": ", ".join(extra_items),
        "extra_kcal": round(extra_kcal_tot, 0),
        "obs":        obs_ref,
    }
    food_logs.append(new_log)
    save_food_log(food_logs)
    st.session_state.diet_form_key += 1
    st.success(f"✅ {sel_meal.get('name', '')} registrado: {total_kcal:.0f} kcal")
    st.rerun()

# ── Plano nutricional ──────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>📄 Plano Nutricional Atual</div>", unsafe_allow_html=True)
st.caption(
    f"Nutricionista: **{diet.get('nutritionist', '—')}** (CRN {diet.get('nutritionist_crn', '—')}) · "
    f"Desde: {datetime.strptime(diet.get('plan_date', '2026-06-02'), '%Y-%m-%d').strftime('%d/%m/%Y')}"
)
st.caption(f"Objetivo: **{diet.get('goal', '—')}** · Total planejado: **{diet.get('total_kcal_plan', 0)} kcal**")
if diet.get("notes"):
    st.info(f"📝 {diet['notes']}")

ICONS = {"cafe": "☕", "almoco": "🍽️", "lanche": "🥤", "jantar": "🌙", "cha": "🍵"}
for meal in diet.get("meals", []):
    with st.expander(f"{ICONS.get(meal['id'],'🍴')} {meal['name']} — ~{meal['kcal_estimated']} kcal | {meal.get('time_suggested','')}"):
        for group in meal.get("groups", []):
            items = group.get("items", [])
            if not items:
                continue
            st.markdown(f"**{group.get('emoji','')} {group['name']}** — _{group.get('instruction','')}_")
            rows = [{"Alimento": ("✅ " if f.get("default") else "    ") + f["item"],
                     "Quantidade": f["qty"], "Kcal": f["kcal"],
                     "Prot(g)": f.get("prot_g", 0), "Carb(g)": f.get("carb_g", 0), "Gord(g)": f.get("fat_g", 0)}
                    for f in items]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        if meal.get("preparations"):
            st.markdown("---")
            st.markdown("**🍳 Preparações alternativas**")
            for p in meal["preparations"]:
                st.markdown(f"- **{p['item']}** — {p.get('desc','—')} · {p['kcal']} kcal · P:{p.get('prot_g',0)}g C:{p.get('carb_g',0)}g G:{p.get('fat_g',0)}g")

# ── Histórico das últimas 4 semanas ───────────────────────────────────────────
if food_logs:
    st.markdown("<div class='section-header'>📅 Histórico Calórico (últimas 4 semanas)</div>", unsafe_allow_html=True)
    df_logs = pd.DataFrame(food_logs)
    df_logs["date"] = pd.to_datetime(df_logs["date"])
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=28)
    df_rec = df_logs[df_logs["date"] >= cutoff]
    if df_rec.empty:
        df_rec = df_logs

    df_daily = (
        df_rec.groupby("date")
        .agg(kcal=("kcal_total", "sum"), prot=("prot_g", "sum"),
             carb=("carb_g", "sum"), fat=("fat_g", "sum"))
        .reset_index().sort_values("date")
    )

    bar_colors = ["#27AE60" if k <= kcal_plano * 1.05 else "#E74C3C" for k in df_daily["kcal"]]
    tdee_fixo  = int(tmb * 1.45)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_daily["date"], y=df_daily["kcal"], name="Kcal consumidas",
        marker_color=bar_colors,
        text=[f"{int(k)}" for k in df_daily["kcal"]],
        textposition="outside", textfont=dict(size=11), cliponaxis=False,
    ))
    fig.add_hline(y=kcal_plano, line_dash="dot", line_color="#F39C12", line_width=2,
                  annotation_text=f"Plano: {kcal_plano} kcal", annotation_position="right")
    fig.add_hline(y=tdee_fixo, line_dash="dash", line_color="#3498DB", line_width=1.5,
                  annotation_text=f"Gasto estimado: {tdee_fixo} kcal", annotation_position="right")
    fig.update_layout(
        height=340, title="Calorias por dia — verde = dentro do plano | vermelho = acima",
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=False, automargin=True, tickangle=-30, tickformat="%d/%m"),
        yaxis=dict(showgrid=True, gridcolor="#eee", title="kcal", automargin=True,
                   range=[0, max(df_daily["kcal"].max(), kcal_plano) * 1.25]),
        showlegend=False, margin=dict(l=50, r=200, t=60, b=70),
    )
    st.plotly_chart(fig, use_container_width=True)

    dias_ok    = sum(1 for k in df_daily["kcal"] if k <= kcal_plano * 1.05)
    media_kcal = int(df_daily["kcal"].mean())
    deficit_m  = tdee_fixo - media_kcal
    cr = st.columns(3)
    with cr[0]:
        st.metric("Dias dentro do plano", f"{dias_ok}/{len(df_daily)}")
    with cr[1]:
        st.metric("Média diária", f"{media_kcal} kcal",
                  delta=f"Plano: {kcal_plano} kcal",
                  delta_color="inverse" if media_kcal > kcal_plano else "normal")
    with cr[2]:
        st.metric("Déficit médio estimado", f"{abs(deficit_m)} kcal",
                  delta="déficit" if deficit_m > 0 else "superávit",
                  delta_color="normal" if deficit_m > 0 else "inverse")
