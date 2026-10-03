from fastapi import FastAPI #import FastAPI class from fastapi module
from fastapi.middleware.cors import CORSMiddleware #middleware for handling CORS
from dotenv import load_dotenv #load environment variables from .env file
from core.database import engine #database engine from core.database module
from models.database import Base #import Base class from models.database module
from routers import repos #import repos router from routers module

load_dotenv()

# Create all tables on startup
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

@app.get("/")
def root():
    return {"message": "FirstSenior API is running"}