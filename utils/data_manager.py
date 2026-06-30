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
