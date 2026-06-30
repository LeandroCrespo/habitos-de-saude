import json
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


def load_profile():
    return _load("profile.json")


def load_bioimpedance():
    data = _load("bioimpedance.json")
    return data.get("measurements", [])


def save_bioimpedance(measurements):
    _save("bioimpedance.json", {"measurements": measurements})


def load_exams():
    return _load("exams.json")


def save_exams(data):
    _save("exams.json", data)


def load_diet():
    return _load("diet.json")


def load_food_log():
    data = _load("food_log.json")
    return data.get("logs", [])


def save_food_log(logs):
    _save("food_log.json", {"logs": logs})


def load_exercises():
    data = _load("exercises.json")
    return data.get("logs", [])


def save_exercises(logs):
    _save("exercises.json", {"logs": logs})


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
