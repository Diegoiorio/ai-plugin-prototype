from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, Text, DateTime
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
    allow_origins=["http://localhost:3000"],
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


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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