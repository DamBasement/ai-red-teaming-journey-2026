"""
Tool disponibili per l'agente.

Nota per il red teaming (Mese 3): questi tool sono scritti in modo VOLUTAMENTE
semplice, senza sanitizzazione dell'input, per poterli poi rompere di
proposito. Non usare questo pattern in produzione.
"""

import os
import requests
from langchain_core.tools import tool


@tool
def read_file(filepath: str) -> str:
    """Legge il contenuto di un file di testo dato il suo percorso.

    Args:
        filepath: percorso del file da leggere.
    """
    if not os.path.exists(filepath):
        return f"ERRORE: il file '{filepath}' non esiste."
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


@tool
def word_count(text: str) -> str:
    """Conta parole, righe e caratteri in un testo.

    Args:
        text: il testo da analizzare.
    """
    words = len(text.split())
    lines = len(text.splitlines())
    chars = len(text)
    return f"Parole: {words}, Righe: {lines}, Caratteri: {chars}"


@tool
def extract_numbers(text: str) -> str:
    """Estrae tutti i numeri presenti in un testo.

    Args:
        text: il testo da cui estrarre i numeri.
    """
    import re
    numbers = re.findall(r"\d+", text)
    if not numbers:
        return "Nessun numero trovato."
    return f"Numeri trovati: {', '.join(numbers)}"


@tool
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Converte un importo da una valuta a un'altra usando tassi di cambio reali e aggiornati.

    Args:
        amount: importo da convertire (es. 45000).
        from_currency: codice valuta di partenza, 3 lettere (es. EUR).
        to_currency: codice valuta di destinazione, 3 lettere (es. USD).
    """
    url = "https://api.frankfurter.app/latest"
    params = {"amount": amount, "from": from_currency.upper(), "to": to_currency.upper()}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        converted = data["rates"][to_currency.upper()]
        return (
            f"{amount} {from_currency.upper()} = {converted:.2f} {to_currency.upper()} "
            f"(tasso del {data['date']})"
        )
    except Exception as e:
        return f"ERRORE nella chiamata API: {e}"


# Lista di tool esposti all'agente
ALL_TOOLS = [read_file, word_count, extract_numbers, convert_currency]
