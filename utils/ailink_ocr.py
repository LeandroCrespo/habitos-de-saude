"""Leitura das telas do app AiLink a partir da resposta do Google Cloud Vision.

O AiLink tem telas com layouts diferentes:
  • "Compartilhamento": rótulo e valor na mesma linha — "Massa muscular esquelética (36.3kg)"
  • "Antevisão": tabela — rótulo numa célula e valor na célula à direita
  • Detalhes (grade de cartões): rótulo cortado ("Massa muscu...") com o valor na linha de baixo

Por isso o valor de cada campo é procurado pela posição na imagem: na própria linha do
rótulo, à direita dele na mesma altura ou logo abaixo na mesma coluna.
"""
import re

_BREAKS_ESPACO = ("SPACE", "SURE_SPACE")
_BREAKS_LINHA  = ("EOL_SURE_SPACE", "LINE_BREAK", "HYPHEN")

_NUM_RE = re.compile(r"(?<![\d.,])(\d{1,4}(?:[.,]\d{1,2})?)\s*(kg|kcal|%)?", re.IGNORECASE)

# campo: (regex do rótulo, unidade esperada, faixa válida, tipo)
CAMPOS = {
    "imc":                    (r"\bBMI\b",                                   None,   (15.0, 50.0),   float),
    "percentual_gordura":     (r"\bB[FE]R\b",                                "%",    (3.0, 60.0),    float),
    "percentual_musculo":     (r"Velocidade\s+m",                            "%",    (10.0, 90.0),   float),
    "percentual_agua":        (r"Taxa\s+de\s+umi",                           "%",    (20.0, 80.0),   float),
    "massa_ossea_kg":         (r"Massa\s+[oó]ssea",                          "kg",   (1.0, 6.0),     float),
    "percentual_proteina":    (r"Taxa\s+de\s+prot",                          "%",    (5.0, 30.0),    float),
    "massa_gordura_kg":       (r"Massa\s+gorda",                             "kg",   (3.0, 100.0),   float),
    "gordura_visceral":       (r"[IÍ]ndice\s+de\s+gor|gordura\s+visceral",   None,   (1, 30),        int),
    "idade_corporal":         (r"Idade\s+d[oe]\s+corpo",                     None,   (18, 99),       int),
    "gordura_subcutanea_pct": (r"Porcentagem",                               "%",    (3.0, 60.0),    float),
}
# "Massa muscular esquelética" e "Massa muscular" (total) aparecem cortadas igualmente
# ("Massa muscu..."); são separadas depois pelo valor.
_MUSC_RE      = re.compile(r"Massa\s+muscu", re.IGNORECASE)
_MUSC_ESQ_RE  = re.compile(r"esquel", re.IGNORECASE)


def _linhas(resp: dict) -> list:
    """Linhas de texto com caixa delimitadora (x0, y0, x1, y1), a partir do fullTextAnnotation."""
    linhas = []
    for page in resp.get("fullTextAnnotation", {}).get("pages", []):
        for bloco in page.get("blocks", []):
            for par in bloco.get("paragraphs", []):
                txt, pts = "", []
                for w in par.get("words", []):
                    for s in w.get("symbols", []):
                        txt += s.get("text", "")
                        pts += [(v.get("x", 0), v.get("y", 0)) for v in s.get("boundingBox", {}).get("vertices", [])]
                        br = s.get("property", {}).get("detectedBreak", {}).get("type")
                        if br in _BREAKS_ESPACO:
                            txt += " "
                        elif br in _BREAKS_LINHA:
                            if txt.strip() and pts:
                                xs, ys = zip(*pts)
                                linhas.append({"txt": txt.strip(), "box": (min(xs), min(ys), max(xs), max(ys))})
                            txt, pts = "", []
                if txt.strip() and pts:
                    xs, ys = zip(*pts)
                    linhas.append({"txt": txt.strip(), "box": (min(xs), min(ys), max(xs), max(ys))})
    return linhas


def _numeros(txt: str) -> list:
    """[(valor, unidade)] encontrados no texto."""
    out = []
    for m in _NUM_RE.finditer(txt):
        try:
            out.append((float(m.group(1).replace(",", ".")), (m.group(2) or "").lower() or None))
        except ValueError:
            pass
    return out


def _candidatos(rotulo: dict, linhas: list, fim_rotulo: int) -> list:
    """Valores candidatos para um rótulo, do mais próximo ao mais distante.

    fim_rotulo: posição no texto da linha onde o rótulo termina (valores depois dele
    na mesma linha têm prioridade máxima).
    """
    cands = [(0.0, v, u) for v, u in _numeros(rotulo["txt"][fim_rotulo:])]
    x0, y0, x1, y1 = rotulo["box"]
    h  = max(4, y1 - y0)
    cy = (y0 + y1) / 2
    for ln in linhas:
        if ln is rotulo or not re.match(r"^[\s(]*-?\d", ln["txt"]):
            continue  # só linhas que começam com número
        a0, b0, a1, b1 = ln["box"]
        nums = _numeros(ln["txt"])
        if not nums:
            continue
        v, u = nums[0]
        if abs((b0 + b1) / 2 - cy) < h * 0.8 and a0 >= x1 - h:      # à direita, mesma altura
            cands.append((1 + (a0 - x1) / h, v, u))
        elif abs(a0 - x0) <= h * 2.5 and 0 <= b0 - y1 <= h * 4:      # logo abaixo, mesma coluna
            cands.append((1 + (b0 - y1) / h, v, u))
    return sorted(cands, key=lambda c: c[0])


def _valido(v, unidade_lida, unidade_esperada, faixa) -> bool:
    if unidade_esperada and unidade_lida and unidade_lida != unidade_esperada:
        return False
    return faixa[0] <= v <= faixa[1]


def parse_ailink(resp: dict, altura_m: float = None) -> dict:
    """Extrai os campos de bioimpedância de uma resposta do Google Vision (TEXT_DETECTION)."""
    texto  = (resp.get("textAnnotations") or [{}])[0].get("description", "")
    linhas = _linhas(resp)
    result = {}

    # Data da medição: "2026-06-30 09:05" (ignora a data de comparação "vs 2026/06/23")
    m = re.search(r"(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}", texto)
    if m:
        result["date"] = m.group(1)

    # Campos com rótulo
    for campo, (pat, unid, faixa, cast) in CAMPOS.items():
        melhor = None
        for ln in linhas:
            mr = re.search(pat, ln["txt"], re.IGNORECASE)
            if not mr:
                continue
            for dist, v, u in _candidatos(ln, linhas, mr.end()):
                if _valido(v, u, unid, faixa):
                    if melhor is None or dist < melhor[0]:
                        melhor = (dist, v)
                    break
        if melhor:
            result[campo] = cast(melhor[1])

    # TMB: único valor em kcal (o rótulo "BMR" às vezes é lido como "AMR")
    for v, u in _numeros(texto):
        if u == "kcal" and 1000 <= v <= 4000:
            result["tmb_kcal"] = int(v)
            break

    # Peso: com IMC e altura, o candidato mais coerente com IMC × altura²; senão, o maior texto
    pesos = []
    for ln in linhas:
        for v, u in _numeros(ln["txt"]):
            if 40.0 <= v <= 200.0 and u in (None, "kg") and re.search(r"\d[.,]\d", ln["txt"]):
                pesos.append((v, ln["box"][3] - ln["box"][1]))
    if pesos:
        if result.get("imc") and altura_m:
            alvo = result["imc"] * altura_m ** 2
            v = min(pesos, key=lambda p: abs(p[0] - alvo))[0]
            if abs(v - alvo) <= 2.0:
                result["peso_kg"] = v
        else:
            result["peso_kg"] = max(pesos, key=lambda p: p[1])[0]

    # Massa muscular esquelética × massa muscular total
    musc = []
    for ln in linhas:
        mr = _MUSC_RE.search(ln["txt"])
        if not mr:
            continue
        for dist, v, u in _candidatos(ln, linhas, mr.end()):
            if u in (None, "kg") and 15.0 <= v <= 90.0:
                musc.append((v, bool(_MUSC_ESQ_RE.search(ln["txt"]))))
                break
    peso = result.get("peso_kg")
    for v, explicito_esq in musc:
        if explicito_esq:
            result["musculo_esqueletico_kg"] = v
        elif len({m[0] for m in musc}) >= 2:
            # duas massas musculares na tela: a menor é a esquelética
            chave = "musculo_esqueletico_kg" if v == min(m[0] for m in musc) else "massa_muscular_kg"
            result.setdefault(chave, v)
        elif peso:
            # só uma: esquelética fica em ~35–45% do peso; a massa muscular total, em ~55–75%
            result.setdefault("musculo_esqueletico_kg" if v < peso * 0.5 else "massa_muscular_kg", v)

    # Campos que podem ser calculados a partir dos lidos
    if "massa_gordura_kg" not in result and peso and result.get("percentual_gordura"):
        result["massa_gordura_kg"] = round(peso * result["percentual_gordura"] / 100, 1)
    if "imc" not in result and peso and altura_m:
        result["imc"] = round(peso / altura_m ** 2, 1)

    return result
