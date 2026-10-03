from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from core.database import engine
from models.database import Base
from routers import repos, webhooks

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

@app.get("/")
def root():
    return {"message": "FirstSenior API is running"}

