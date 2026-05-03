import json
import os
from typing import Any

from google import genai

from ai_schema import SAFE_DB_SCHEMA


def get_ai_prompt(user_prompt: str) -> str:
    return f"""
Sei un interprete sicuro di richieste dati per un CRM commerciale.

Devi trasformare la richiesta utente in un piano query JSON.
Non devi generare SQL.
Non devi generare codice.
Non devi inventare tabelle o campi.
Puoi usare solo lo schema DB fornito.

Schema DB consentito:
{json.dumps(SAFE_DB_SCHEMA, ensure_ascii=False, indent=2)}

Richiesta utente:
{user_prompt}

Rispondi SOLO con JSON valido in questo formato:

{{
  "title": "Titolo breve dell'analisi",
  "description": "Descrizione breve dell'analisi",
  "base_table": "opportunities",
  "joins": ["customers", "users"],
  "select": [
    {{
      "table": "opportunities",
      "field": "opened_at",
      "alias": "month",
      "label": "Mese",
      "transform": "month"
    }},
    {{
      "table": "opportunities",
      "field": "estimated_value",
      "alias": "sales_total",
      "label": "Vendite",
      "aggregation": "sum"
    }}
  ],
  "filters": [
    {{
      "table": "opportunities",
      "field": "status",
      "operator": "=",
      "value": "won"
    }}
  ],
  "group_by": [
    {{
      "table": "opportunities",
      "field": "opened_at",
      "transform": "month"
    }}
  ],
  "order_by": [
    {{
      "field": "month",
      "direction": "asc"
    }}
  ],
  "limit": 100,
  "chart": {{
    "x_field": "month",
    "y_field": "sales_total",
    "reason": "Motivazione sintetica della scelta degli assi"
  }}
}}

Regole obbligatorie:
- Usa solo tabelle e campi dello schema.
- Non usare SQL.
- Non usare campi sensibili non presenti nello schema.
- Se la richiesta parla di vendite, interpreta le vendite come opportunità con status = won.
- Per valore vendite usa sum(opportunities.estimated_value).
- Per numero opportunità usa count(opportunities.id).
- Per numero venditori usa count_distinct(opportunities.owner_user_id).
- Se la richiesta parla di andamento nel tempo, usa un campo temporale con transform month.
- Preferisci opened_at per analisi su creazione/apertura, closed_at per analisi su chiusura/vendite concluse.
- Se usi aggregazioni, aggiungi sempre group_by quando serve.
- Se usi campi di customers, aggiungi "customers" in joins.
- Se usi campi di users, aggiungi "users" in joins.
- L'asse X deve essere un alias presente in select.
- L'asse Y deve essere un alias numerico presente in select.
- Il risultato deve essere adatto a tabella e grafico X/Y.
"""


def extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "", 1).strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```", "", 1).strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    return json.loads(cleaned)


def interpret_with_gemini(user_prompt: str) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY non configurata.")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=get_ai_prompt(user_prompt),
    )

    return extract_json(response.text)