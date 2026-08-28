import json
import base64
import threading
import os
from pathlib import Path
from datetime import datetime, date

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"


def _load(filename):
    fp = DATA_DIR / filename
    if not fp.exists():
        return {}
    with open(fp, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(filename, data):
    DATA_DIR.mkdir(exist_ok=True)
    fp = DATA_DIR / filename
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── GitHub sync ───────────────────────────────────────────────────────────────
def _github_push(filename, data):
    """
    Persiste um arquivo JSON no repositório GitHub via API.
    Necessário para sobreviver reinicializações do Streamlit Cloud,
    que tem sistema de arquivos efêmero.
    Falha silenciosamente se o token não estiver configurado.
    """
    try:
        import requests
        import streamlit as st

        token = st.secrets.get("GITHUB_TOKEN", "")
        owner = st.secrets.get("GITHUB_OWNER", "LeandroCrespo")
        repo  = st.secrets.get("GITHUB_REPO",  "habitos-de-saude")

        if not token:
            return  # secrets não configurados — funciona apenas localmente

        path    = f"data/{filename}"
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        headers = {
            "Authorization": f"token {token}",
            "Accept":        "application/vnd.github.v3+json",
        }

        # Busca o SHA atual (obrigatório para atualizar sem conflito)
        r = requests.get(api_url, headers=headers, timeout=10)
        if r.status_code != 200:
            return
        sha = r.json().get("sha", "")

        content_str = json.dumps(data, ensure_ascii=False, indent=2)
        content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")

        requests.put(
            api_url,
            headers=headers,
            timeout=15,
            json={
                "message": f"auto: salvar {filename}",
                "content": content_b64,
                "sha":     sha,
                "branch":  "master",
            },
        )
    except Exception:
        pass  # falha silenciosa — dado já está salvo localmente


def _github_push_async(filename, data):
    """Dispara o push para o GitHub em background para não bloquear a UI."""
    t = threading.Thread(target=_github_push, args=(filename, data), daemon=True)
    t.start()


# ── Loaders ───────────────────────────────────────────────────────────────────
def load_profile():
    return _load("profile.json")


def load_bioimpedance():
    data = _load("bioimpedance.json")
    return data.get("measurements", [])


def save_bioimpedance(measurements):
    data = {"measurements": measurements}
    _save("bioimpedance.json", data)
    _github_push_async("bioimpedance.json", data)


def load_exams():
    return _load("exams.json")


def save_exams(data):
    _save("exams.json", data)
    _github_push_async("exams.json", data)


def load_diet():
    return _load("diet.json")


def load_food_log():
    data = _load("food_log.json")
    return data.get("logs", [])


def save_food_log(logs):
    data = {"logs": logs}
    _save("food_log.json", data)
    _github_push_async("food_log.json", data)


def load_exercises():
    data = _load("exercises.json")
    return data.get("logs", [])


def save_exercises(logs):
    data = {"logs": logs}
    _save("exercises.json", data)
    _github_push_async("exercises.json", data)


# ── Helpers ───────────────────────────────────────────────────────────────────
def calc_age(dob_str):
    dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def status_color(status):
    return {"normal": "#27AE60", "alta": "#E74C3C", "baixa": "#E67E22", "info": "#3498DB"}.get(status, "#95A5A6")


def status_emoji(status):
    return {"normal": "✅", "alta": "⬆️", "baixa": "⬇️", "info": "ℹ️"}.get(status, "❓")


# Alinhado ao plano da nutricionista Maria Eduarda Tardin de 28/08/2026 (docs/dieta/)
_DEFAULT_MEALS = [
    {
        "meal_id": "cafe", "meal_name": "Café da Manhã", "time": "07:00:00",
        "foods": ["Banana", "Chia", "Psyllium", "Pão Francês", "Ovo cozido / mexido", "Café sem açúcar"],
        "kcal_total": 438, "prot_g": 19.9, "carb_g": 59.5, "fat_g": 15.0,
    },
    {
        "meal_id": "almoco", "meal_name": "Almoço", "time": "12:00:00",
        "foods": ["Salada / legumes variados", "Peito de frango grelhado sem pele",
                  "Arroz branco cozido", "Feijão carioca cozido"],
        "kcal_total": 408, "prot_g": 46.2, "carb_g": 41.4, "fat_g": 5.18,
    },
    {
        "meal_id": "lanche", "meal_name": "Lanche da Tarde", "time": "15:30:00",
        "foods": ["Banana", "Chia", "Pão de forma integral", "Frango desfiado",
                  "Creme de ricota light", "Café sem açúcar"],
        "kcal_total": 375, "prot_g": 24.7, "carb_g": 52.5, "fat_g": 8.8,
    },
    {
        "meal_id": "jantar", "meal_name": "Jantar", "time": "19:00:00",
        "foods": ["Salada / legumes variados", "Peito de frango grelhado sem pele",
                  "Arroz branco cozido", "Feijão carioca cozido"],
        "kcal_total": 408, "prot_g": 46.2, "carb_g": 41.4, "fat_g": 5.18,
    },
    {
        "meal_id": "cha", "meal_name": "Hora do Chá", "time": "21:00:00",
        "foods": ["Chá de manjericão com casca de limão"],
        "kcal_total": 5, "prot_g": 0.0, "carb_g": 1.0, "fat_g": 0.0,
    },
]


def ensure_today_defaults(food_logs, today_str, backfill_days=14):
    """Garante que as refeições base do dia estejam em food_logs.

    Também recupera dias recentes em que o app não foi aberto. Isto é uma
    camada extra de segurança apenas — a recuperação principal e realmente
    automática (independente de o app ser aberto) roda via GitHub Actions
    (`.github/workflows/daily-food-log.yml` + `scripts/backfill_food_log.py`).
    Verifica os últimos `backfill_days` dias anteriores a hoje e completa
    qualquer um que esteja totalmente vazio, sem sobrescrever dias já
    preenchidos (mesmo que parcialmente). Salva e retorna logs atualizados.
    """
    from datetime import datetime as _dt, timedelta as _td

    existing_dates = {l.get("date") for l in food_logs}
    next_id = max((l["id"] for l in food_logs), default=0) + 1
    added = []

    today_dt = _dt.strptime(today_str, "%Y-%m-%d")
    dias_a_checar = [today_str] + [
        (today_dt - _td(days=i)).strftime("%Y-%m-%d") for i in range(1, backfill_days + 1)
    ]

    for d in dias_a_checar:
        if d in existing_dates:
            continue  # dia já tem pelo menos um registro — não mexe
        for meal in _DEFAULT_MEALS:
            added.append({
                "id": next_id, "date": d, "time": meal["time"],
                "meal_id": meal["meal_id"], "meal_name": meal["meal_name"],
                "foods": meal["foods"],
                "kcal_total": meal["kcal_total"], "prot_g": meal["prot_g"],
                "carb_g": meal["carb_g"], "fat_g": meal["fat_g"],
                "extra_desc": "", "extra_kcal": 0,
                "obs": "Padrão automático" if d == today_str else "Padrão automático (dia recuperado retroativamente)",
            })
            next_id += 1

    if added:
        food_logs = food_logs + added
        save_food_log(food_logs)
    return food_logs


def calc_tdee(tmb_kcal, steps, exercise_min=0):
    """Calcula TDEE (gasto total) com base no TMB, passos e exercício."""
    if steps < 3000:
        activity_factor = 1.20
    elif steps < 7000:
        activity_factor = 1.375
    elif steps < 10000:
        activity_factor = 1.55
    else:
        activity_factor = 1.725
    base_tdee = tmb_kcal * activity_factor
    exercise_extra = exercise_min * 5
    return round(base_tdee + exercise_extra)


def get_bmi_category(imc):
    if imc < 18.5:
        return "Abaixo do peso", "#3498DB"
    elif imc < 25:
        return "Peso normal", "#27AE60"
    elif imc < 30:
        return "Sobrepeso", "#F39C12"
    elif imc < 35:
        return "Obesidade Grau I", "#E74C3C"
    else:
        return "Obesidade Grau II+", "#8E44AD"


def get_fat_category(pct, sex="M"):
    if sex == "M":
        if pct < 6:
            return "Essencial", "#3498DB"
        elif pct < 14:
            return "Atlético", "#27AE60"
        elif pct < 18:
            return "Fitness", "#2ECC71"
        elif pct < 25:
            return "Aceitável", "#F39C12"
        else:
            return "Obesidade", "#E74C3C"
    return "—", "#95A5A6"
