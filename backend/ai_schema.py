"""Schema dati sicuro usato dal backend AI.

Responsabilita:
- Definire il sottoinsieme di tabelle, campi e relazioni che il layer AI puo usare.
- Fornire metadati semantici (`type`, `description`) per validazioni e mapping.

Ruolo nel flusso applicativo:
- Viene importato da `ai_service.py` per istruire Gemini su quali campi sono ammessi.
- Viene importato da `query_builder.py` per validare piani query e costruire SQL sicuro.

Dipendenze principali:
- Nessuna dipendenza runtime esterna: contiene solo costanti Python.

Cosa NON fa questo modulo:
- Non interroga il database.
- Non costruisce SQL.
- Non applica validazioni operative: espone solamente la whitelist strutturale.
"""

SAFE_DB_SCHEMA = {
    "tables": {
        "users": {
            "description": "Utenti della piattaforma commerciale",
            "fields": {
                "id": {"type": "number", "description": "Identificativo utente"},
                "first_name": {"type": "text", "description": "Nome utente"},
                "last_name": {"type": "text", "description": "Cognome utente"},
                "role": {"type": "category", "description": "Ruolo: seller, supervisor, manager"},
                "created_at": {"type": "temporal", "description": "Data creazione utente"}
            }
        },
        "customers": {
            "description": "Clienti aziendali",
            "fields": {
                "id": {"type": "number", "description": "Identificativo cliente"},
                "company_name": {"type": "text", "description": "Nome azienda cliente"},
                "city": {"type": "category", "description": "Città del cliente"},
                "province": {"type": "category", "description": "Provincia del cliente"},
                "country": {"type": "category", "description": "Paese del cliente"},
                "created_at": {"type": "temporal", "description": "Data creazione cliente"}
            }
        },
        "opportunities": {
            "description": "Opportunità commerciali",
            "fields": {
                "id": {"type": "number", "description": "Identificativo opportunità"},
                "customer_id": {"type": "number", "description": "Cliente collegato"},
                "owner_user_id": {"type": "number", "description": "Utente responsabile"},
                "title": {"type": "text", "description": "Titolo opportunità"},
                "status": {"type": "category", "description": "Stato opportunità"},
                "estimated_value": {"type": "number", "description": "Valore stimato opportunità"},
                "probability": {"type": "number", "description": "Probabilità di chiusura"},
                "opened_at": {"type": "temporal", "description": "Data apertura"},
                "closed_at": {"type": "temporal", "description": "Data chiusura"},
                "source": {"type": "category", "description": "Origine opportunità"},
                "priority": {"type": "category", "description": "Priorità opportunità"},
                "created_at": {"type": "temporal", "description": "Data creazione record"}
            }
        }
    },
    "relations": [
        {
            "name": "opportunities_customers",
            "from_table": "opportunities",
            "from_field": "customer_id",
            "to_table": "customers",
            "to_field": "id"
        },
        {
            "name": "opportunities_users",
            "from_table": "opportunities",
            "from_field": "owner_user_id",
            "to_table": "users",
            "to_field": "id"
        }
    ]
}