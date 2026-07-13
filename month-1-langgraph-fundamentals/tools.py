"""
Tools available to the agent.
 
Note for red teaming (Month 3): these tools are DELIBERATELY written
in a simple way, with no input sanitization, so they can later be
broken on purpose. Do not use this pattern in production.
"""
 
import os
import requests
from langchain_core.tools import tool
 
 
@tool
def read_file(filepath: str) -> str:
    """Reads the content of a text file given its path.
 
    Args:
        filepath: path of the file to read.
    """
    if not os.path.exists(filepath):
        return f"ERROR: file '{filepath}' does not exist."
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()
 
 
@tool
def word_count(text: str) -> str:
    """Counts words, lines, and characters in a text.
 
    Args:
        text: the text to analyze.
    """
    words = len(text.split())
    lines = len(text.splitlines())
    chars = len(text)
    return f"Words: {words}, Lines: {lines}, Characters: {chars}"
 
 
@tool
def extract_numbers(text: str) -> str:
    """Extracts all numbers present in a text.
 
    Args:
        text: the text to extract numbers from.
    """
    import re
    numbers = re.findall(r"\d+", text)
    if not numbers:
        return "No numbers found."
    return f"Numbers found: {', '.join(numbers)}"
 
 
@tool
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Converts an amount from one currency to another using real, up-to-date exchange rates.
 
    Args:
        amount: amount to convert (e.g. 45000).
        from_currency: source currency code, 3 letters (e.g. EUR).
        to_currency: target currency code, 3 letters (e.g. USD).
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
            f"(rate as of {data['date']})"
        )
    except Exception as e:
        return f"ERROR calling the API: {e}"
 
 
# List of tools exposed to the agent
ALL_TOOLS = [read_file, word_count, extract_numbers, convert_currency]
