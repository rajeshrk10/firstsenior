#importing APIRouter for creating route groups.
#importing Depends for providing database session.
from fastapi import APIRouter, Depends

#importing Session for database session management from SQLAlchemy.
from sqlalchemy.orm import Session

#importing get_db function from core.database to get a database session for each request
from core.database import get_db

#importing User model from models.database to interact with the users table in the database
from models.database import User

#importing encrypt_token and decrypt_token functions from core.security to handle encryption and decryption of GitHub access tokens
from core.security import encrypt_token, decrypt_token
import httpx #library used to make asynchronous HTTP requests to external APIs.
from pydantic import BaseModel #BaseModel is used to check request body data structure and type validation. 

#Same as typescript but typescript runs at "compile time" and pydantic runs at "runtime".

# assigning the prefix "/auth" for this router.
router = APIRouter(prefix="/auth", tags=["auth"])

#using Basemodel to define the expected structure and type of the request body.
class SyncTokenRequest(BaseModel):
    github_id: str
    github_token: str

#we used "/auth"in prefix so we dont need to add before /sync-token
@router.post("/sync-token")
async def sync_token(
    body: SyncTokenRequest, #assigning the request body to the SyncTokenRequest model.
    db: Session = Depends(get_db) #telling FastAPI to provide a database session for this route using the get_db function.
):
    user = db.query(User).filter(User.github_id == body.github_id).first()
    
    if not user:
        # User not found — will be created when they connect a repo
        return {"message": "User not found"}

    # Decrypt the existing token to check its validity
    decrypted = decrypt_token(user.access_token)
    
    # Check if existing token is still valid
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {decrypted}"}
        )
    
    if response.status_code == 200:
        # Token is still valid — no need to update
        return {"message": "Token is valid"}
    
    # Token expired — update with encrypted fresh one
    user.access_token = encrypt_token(body.github_token)

    # Commit the changes to the database
    db.commit()
    return {"message": "Token refreshed"}