import os

#importing fastapi to create the API, and importing necessary modules for database connection, environment variable loading, and routing.
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

#method to load environment variables from a .env file into the system's environment variables
from dotenv import load_dotenv

#importing the database engine and base class for SQLAlchemy models, as well as the routers for different API endpoints.
from core.database import engine
from models.database import Base

#importing routers for different API endpoints, including repositories, webhooks, reviews, diary entries, and authentication.
from routers import repos, webhooks, reviews, diary, auth

load_dotenv()

# creating the database tables based on the SQLAlchemy models defined in the models.database module. This ensures that the necessary tables are created in the database when the application starts.
Base.metadata.create_all(bind=engine)

# creating an instance of the FastAPI class, which will be used to define the API endpoints and handle incoming requests.
app = FastAPI(title="FirstSenior API")

# fetching the frontend URL from environment variables, defaulting to "http://localhost:3000" if not set
frontend_url =  os.getenv("FRONTEND_URL", "http://localhost:3000")

# CORS (Cross-Origin Resource Sharing) middleware configuration to allow requests from the frontend URL and localhost for development purposes
allowed_origins = [frontend_url, "http://localhost:3000"]

# adding CORS middleware to the FastAPI application.
app.add_middleware(
    CORSMiddleware, #enables cross-origin  handling
    allow_origins=allowed_origins, #permits requests from the specified origins
    allow_credentials=True, # allows cookies and authentication headers to be included in requests
    allow_methods=["*"], # allows all HTTP methods (GET, POST, PUT, DELETE, etc.) to be used in requests
    allow_headers=["*"], # allows all headers to be included in requests
)

# app.include_router() method is used to include the routers for different API endpoints into the main FastAPI application.

app.include_router(repos.router) # router created in backend/routers/repos.py
app.include_router(webhooks.router) # router created in backend/routers/webhooks.py
app.include_router(reviews.router) # router created in backend/routers/reviews.py
app.include_router(diary.router) # router created in backend/routers/diary.py
app.include_router(auth.router) # router created in backend/routers/auth.py



#defining a root endpoint, when browser send request to the root url ("/"), it will run a function called root() that returns a JSON response indicating that the FirstSenior API is running.
@app.get("/")
def root():
    return {"message": "FirstSenior API is running"}

@app.get("/test-groq")
def test_groq():
    from groq import Groq
    import os
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))# got this api key after creating an account on groq.dev and creating a project. The api key is stored in the .env file for security reasons.
    models = client.models.list()
    return {"models": [m.id for m in models.data]}