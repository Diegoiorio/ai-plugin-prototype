# Setup Ambiente Virtuale Python

## Cos'è un ambiente virtuale

Un ambiente virtuale (venv) serve a isolare le dipendenze Python di un progetto.

Evita conflitti tra versioni diverse delle librerie tra progetti.

Esempio:

- Project A → fastapi 0.110
- Project B → fastapi 0.120

Senza ambiente virtuale → conflitti  
Con ambiente virtuale → tutto isolato

---

## Quando usarlo

Usalo sempre quando lavori su un progetto Python:

- Backend (FastAPI, Django, Flask)
- Script con dipendenze
- Tool CLI
- Progetti condivisi

---

## Creazione ambiente virtuale

Vai nella cartella del progetto:

cd backend

Crea l’ambiente virtuale:

python3 -m venv .venv

---

## Attivazione

Su Linux / WSL / Mac:

source .venv/bin/activate

Dovresti vedere:

(.venv) user@machine:~/backend#

---

## Installazione dipendenze

Installa le librerie:

pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv

---

## Salvataggio dipendenze

Salva le dipendenze nel file requirements.txt:

pip freeze > requirements.txt

---

## Riutilizzo progetto

Quando torni sul progetto:

cd backend
source .venv/bin/activate

Se serve reinstallare le dipendenze:

pip install -r requirements.txt

---

## Disattivazione ambiente

Per uscire:

deactivate

---

## Git ignore

NON committare .venv/

Aggiungi al .gitignore:

.venv/

---

## Avviare il backend

uvicorn main:app --reload --port 8000

Verifica sul browser con:
http://localhost:8000/health

---

## Struttura tipica progetto

backend/
├── .venv/
├── main.py
├── requirements.txt
└── ...

---

## Note

Dentro l’ambiente virtuale:

- python → punta a .venv
- pip → installa solo dentro il progetto

Fuori dall’ambiente:

- usa il Python globale del sistema
