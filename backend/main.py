from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, Text, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

app = FastAPI(title="AI Plugin Prototype API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PromptRequest(Base):
    __tablename__ = "prompt_requests"

    id = Column(Integer, primary_key=True, index=True)
    prompt = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PromptCreate(BaseModel):
    prompt: str


class AiQueryRequest(BaseModel):
    prompt: str


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


ALLOWED_FIELDS = {
    "month": {
        "label": "Mese",
        "type": "temporal",
    },
    "sellers_count": {
        "label": "Venditori",
        "type": "number",
    },
    "sales_total": {
        "label": "Vendite",
        "type": "number",
    },
    "opportunities_count": {
        "label": "Opportunità",
        "type": "number",
    },
}


def interpret_prompt_safely(prompt: str):
    normalized_prompt = prompt.lower()

    if "vendit" in normalized_prompt and "venditor" in normalized_prompt:
        return {
            "title": "Vendite rispetto ai venditori nel tempo",
            "description": "Analisi mensile del numero di venditori attivi e del valore totale delle opportunità vinte.",
            "fields": ["month", "sellers_count", "sales_total", "opportunities_count"],
            "chart": {
                "x_field": "sellers_count",
                "y_field": "sales_total",
                "reason": "Il numero di venditori è usato come asse X per valutare la relazione con il valore delle vendite.",
            },
        }

    raise HTTPException(
        status_code=422,
        detail="Non riesco ancora a interpretare questa richiesta. Per ora prova con una richiesta su vendite e venditori.",
    )


def validate_interpretation(interpretation: dict):
    for field in interpretation["fields"]:
        if field not in ALLOWED_FIELDS:
            raise HTTPException(
                status_code=400,
                detail=f"Campo non consentito: {field}",
            )

    x_field = interpretation["chart"]["x_field"]
    y_field = interpretation["chart"]["y_field"]

    if x_field not in interpretation["fields"]:
        raise HTTPException(status_code=400, detail="Asse X non presente nei risultati.")

    if y_field not in interpretation["fields"]:
        raise HTTPException(status_code=400, detail="Asse Y non presente nei risultati.")

    if ALLOWED_FIELDS[y_field]["type"] != "number":
        raise HTTPException(status_code=400, detail="L'asse Y deve essere numerico.")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/prompts")
def create_prompt(payload: PromptCreate, db: Session = Depends(get_db)):
    item = PromptRequest(prompt=payload.prompt)
    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "id": item.id,
        "prompt": item.prompt,
        "created_at": item.created_at,
    }


@app.get("/prompts")
def list_prompts(db: Session = Depends(get_db)):
    items = db.query(PromptRequest).order_by(PromptRequest.id.desc()).all()

    return [
        {
            "id": item.id,
            "prompt": item.prompt,
            "created_at": item.created_at,
        }
        for item in items
    ]


@app.post("/ai/query")
def ai_query(payload: AiQueryRequest, db: Session = Depends(get_db)):
    interpretation = interpret_prompt_safely(payload.prompt)
    validate_interpretation(interpretation)

    sql = text("""
        SELECT
            TO_CHAR(DATE_TRUNC('month', o.opened_at), 'YYYY-MM') AS month,
            COUNT(DISTINCT o.owner_user_id)::int AS sellers_count,
            COALESCE(SUM(
                CASE 
                    WHEN o.status = 'won' THEN o.estimated_value 
                    ELSE 0 
                END
            ), 0)::float AS sales_total,
            COUNT(o.id)::int AS opportunities_count
        FROM opportunities o
        GROUP BY DATE_TRUNC('month', o.opened_at)
        ORDER BY DATE_TRUNC('month', o.opened_at);
    """)

    result = db.execute(sql).mappings().all()
    rows = [dict(row) for row in result]

    columns = [
        {
            "key": field,
            "label": ALLOWED_FIELDS[field]["label"],
            "type": ALLOWED_FIELDS[field]["type"],
        }
        for field in interpretation["fields"]
    ]

    compatible_x_fields = [
        column for column in columns
        if column["type"] in ["temporal", "number"]
    ]

    compatible_y_fields = [
        column for column in columns
        if column["type"] == "number"
    ]

    return {
        "title": interpretation["title"],
        "description": interpretation["description"],
        "columns": columns,
        "rows": rows,
        "chart": {
            "x_field": interpretation["chart"]["x_field"],
            "y_field": interpretation["chart"]["y_field"],
            "reason": interpretation["chart"]["reason"],
            "compatible_x_fields": compatible_x_fields,
            "compatible_y_fields": compatible_y_fields,
        },
    }