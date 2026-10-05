from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from core.database import engine
from models.database import Base
from routers import repos, webhooks, reviews, diary, auth

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FirstSenior API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repos.router)
app.include_router(webhooks.router)
app.include_router(reviews.router)
app.include_router(diary.router)
app.include_router(auth.router)

@app.get("/")
def root():
    return {"message": "FirstSenior API is running"}

@app.get("/test-groq")
def test_groq():
    from groq import Groq
    import os
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    models = client.models.list()
    return {"models": [m.id for m in models.data]}