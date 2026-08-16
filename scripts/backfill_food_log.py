#!/usr/bin/env python3
"""
Backfill automático de data/food_log.json.

Roda via GitHub Actions (cron), de forma totalmente independente de o app
Streamlit ser aberto — o Streamlit Cloud só executa código quando alguém
acessa a página, então sem este script dias sem visita ficam sem registro
de alimentação.

Preenche com as refeições-padrão qualquer dia (dos últimos BACKFILL_DAYS
dias) que esteja completamente sem registro. Nunca sobrescreve um dia que
já tenha pelo menos um registro (preserva qualquer edição manual/real).
"""
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

BASE_DIR = Path(__file__).parent.parent
FOOD_LOG_PATH = BASE_DIR / "data" / "food_log.json"
BRASILIA = timezone(timedelta(hours=-3))
BACKFILL_DAYS = 14  # janela de recuperação em caso de falha de execuções anteriores

# Mantido em sincronia manual com _DEFAULT_MEALS em utils/data_manager.py
_DEFAULT_MEALS = [
    {
        "meal_id": "cafe", "meal_name": "Café da Manhã", "time": "07:00:00",
        "foods": ["Banana", "Psyllium", "Pão Francês", "Ovo cozido / mexido", "Café sem açúcar"],
        "kcal_total": 380, "prot_g": 17.9, "carb_g": 55.5, "fat_g": 11.3,
    },
    {
        "meal_id": "almoco", "meal_name": "Almoço", "time": "12:00:00",
        "foods": ["Salada / legumes variados", "Peito de frango grelhado",
                  "Arroz branco cozido", "Feijão carioca cozido"],
        "kcal_total": 485, "prot_g": 49.0, "carb_g": 56.0, "fat_g": 6.0,
    },
    {
        "meal_id": "lanche", "meal_name": "Lanche da Tarde", "time": "15:30:00",
        "foods": ["Banana", "Pão Francês", "Ovo cozido", "Café sem açúcar"],
        "kcal_total": 365, "prot_g": 17.4, "carb_g": 51.5, "fat_g": 11.3,
    },
    {
        "meal_id": "jantar", "meal_name": "Jantar", "time": "19:00:00",
        "foods": ["Salada / legumes variados", "Peito de frango grelhado",
                  "Arroz branco cozido", "Feijão carioca cozido"],
        "kcal_total": 485, "prot_g": 49.0, "carb_g": 56.0, "fat_g": 6.0,
    },
    {
        "meal_id": "cha", "meal_name": "Hora do Chá", "time": "21:00:00",
        "foods": ["Chá de manjericão com limão"],
        "kcal_total": 5, "prot_g": 0.0, "carb_g": 1.0, "fat_g": 0.0,
    },
]


def main():
    if not FOOD_LOG_PATH.exists():
        print("food_log.json não encontrado — nada a fazer.")
        return

    with open(FOOD_LOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    logs = data.get("logs", [])
    existing_dates = {l.get("date") for l in logs}
    next_id = max((l["id"] for l in logs), default=0) + 1

    today = datetime.now(BRASILIA).date()
    dias_a_checar = [(today - timedelta(days=i)).isoformat() for i in range(0, BACKFILL_DAYS + 1)]

    added = []
    for d in dias_a_checar:
        if d in existing_dates:
            continue  # dia já tem registro (mesmo que parcial) — não mexe
        is_today = (d == today.isoformat())
        for meal in _DEFAULT_MEALS:
            added.append({
                "id": next_id, "date": d, "time": meal["time"],
                "meal_id": meal["meal_id"], "meal_name": meal["meal_name"],
                "foods": meal["foods"],
                "kcal_total": meal["kcal_total"], "prot_g": meal["prot_g"],
                "carb_g": meal["carb_g"], "fat_g": meal["fat_g"],
                "extra_desc": "", "extra_kcal": 0,
                "obs": "Padrão automático" if is_today else "Padrão automático (dia recuperado via GitHub Actions)",
            })
            next_id += 1

    if not added:
        print(f"Nenhum dia faltando nos últimos {BACKFILL_DAYS} dias. Nada a fazer.")
        return

    data["logs"] = logs + added
    with open(FOOD_LOG_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    dias_preenchidos = sorted({a["date"] for a in added})
    print(f"Preenchidos {len(dias_preenchidos)} dia(s): {', '.join(dias_preenchidos)}")


if __name__ == "__main__":
    main()
