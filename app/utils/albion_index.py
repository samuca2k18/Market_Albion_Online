# app/utils/albion_index.py
import json
import unicodedata
from typing import Dict, List, Literal

Lang = Literal["pt_br", "en_us"]


def normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
    return texto.strip()


# Índices separados por idioma
NAME_INDEX_EXACT: Dict[Lang, Dict[str, List[dict]]] = {"pt_br": {}, "en_us": {}}
ITEM_BY_UNIQUE: Dict[str, dict] = {}


def _registrar_itens(caminho: str, lang: Lang):
    nome_campo = "PT-BR" if lang == "pt_br" else "EN-US"
    with open(caminho, "r", encoding="utf-8") as f:
        dados = json.load(f)

    for item in dados:
        unique = item.get("UniqueName")
        nome = item.get(nome_campo)
        if not unique or not nome:
            continue

        # Garante que sempre teremos um dicionario único com ambos os idiomas
        registro = ITEM_BY_UNIQUE.setdefault(unique, {"UniqueName": unique})
        registro[nome_campo] = nome

        chave = normalizar(nome)
        NAME_INDEX_EXACT[lang].setdefault(chave, []).append(registro)


_registrar_itens("nomes_pt_br.json", "pt_br")
_registrar_itens("nomes_en_us.json", "en_us")

# Lista combinada com os campos PT e EN preenchidos
ALBION_ITEMS = list(ITEM_BY_UNIQUE.values())

print(
    f"[Albion] Índices carregados: {len(NAME_INDEX_EXACT['pt_br'])} chaves PT "
    f"e {len(NAME_INDEX_EXACT['en_us'])} chaves EN"
)


def buscar_item_por_nome(query: str, lang: Lang = "pt_br") -> List[dict]:
    """
    Busca itens por idioma específico.
    lang: 'pt_br' ou 'en_us'
    """
    if not query:
        return []

    lang = "pt_br" if lang not in ("pt_br", "en_us") else lang
    chave = normalizar(query)

    # Busca exata primeiro
    resultados = [
        {**r, "__matched": r.get("PT-BR") if lang == "pt_br" else r.get("EN-US")}
        for r in NAME_INDEX_EXACT[lang].get(chave, [])
    ]
    if resultados:
        # Remove duplicados mantendo a ordem
        vistos = set()
        unicos = []
        for r in resultados:
            if r["UniqueName"] not in vistos:
                vistos.add(r["UniqueName"])
                unicos.append(r)
        return unicos

    # Fallback aproximado
    palavras = [p for p in chave.split() if len(p) >= 2]
    candidatos = []
    for item in ALBION_ITEMS:
        nome = normalizar(item.get("PT-BR" if lang == "pt_br" else "EN-US", ""))
        score = 0

        if chave in nome:
            score += 25
        for p in palavras:
            if p in nome:
                score += 6

        if score > 0:
            c = item.copy()
            c["__score"] = score
            c["__matched"] = item.get("PT-BR" if lang == "pt_br" else "EN-US")
            candidatos.append(c)

    candidatos.sort(key=lambda x: x["__score"], reverse=True)
    return candidatos[:10]


def buscar_item_por_nome_pt(query: str) -> List[dict]:
    return buscar_item_por_nome(query, "pt_br")


def buscar_item_por_nome_en(query: str) -> List[dict]:
    return buscar_item_por_nome(query, "en_us")