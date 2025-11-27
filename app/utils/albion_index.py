# app/utils/albion_index.py
import json
import unicodedata
from typing import List, Dict

with open("nomes_simplificados.json", "r", encoding="utf-8") as f:
    ALBION_ITEMS = json.load(f)

def normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
    return texto.strip()

NAME_INDEX_EXACT: Dict[str, List[dict]] = {}
ITEM_BY_UNIQUE: Dict[str, dict] = {}

for item in ALBION_ITEMS:
    unique = item.get("UniqueName")
    if unique:
        ITEM_BY_UNIQUE[unique] = item
    for nome in (item.get("EN-US"), item.get("PT-BR")):
        if nome:
            chave = normalizar(nome)
            NAME_INDEX_EXACT.setdefault(chave, []).append(item)

print(f"[Albion] Índice carregado: {len(ALBION_ITEMS)} itens")

def buscar_item_por_nome(query: str):
    if not query:
        return []
    chave = normalizar(query)
    resultados = NAME_INDEX_EXACT.get(chave, [])
    if resultados:
        return resultados

    palavras = [p for p in chave.split() if len(p) >= 2]
    candidatos = []
    for item in ALBION_ITEMS:
        en = normalizar(item.get("EN-US", ""))
        pt = normalizar(item.get("PT-BR", ""))
        score = 0
        if chave in en: score += 10
        if chave in pt: score += 25
        for p in palavras:
            if p in en: score += 3
            if p in pt: score += 6
        if score > 0:
            c = item.copy()
            c["__score"] = score
            c["__matched"] = item.get("PT-BR") if any(p in pt for p in palavras) else item.get("EN-US")
            candidatos.append(c)
    candidatos.sort(key=lambda x: x["__score"], reverse=True)
    return candidatos[:10]