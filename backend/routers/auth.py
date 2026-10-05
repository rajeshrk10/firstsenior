from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from models.database import User
import httpx
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

class SyncTokenRequest(BaseModel):
    github_id: str
    github_token: str

@router.post("/sync-token")
async def sync_token(
    body: SyncTokenRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.github_id == body.github_id).first()
    
    if not user:
        # User not found — will be created when they connect a repo
        return {"message": "User not found"}
    
    # Check if existing token is still valid
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {user.access_token}"}
        )
    
    if response.status_code == 200:
        # Token is still valid — no need to update
        return {"message": "Token is valid"}
    
    # Token expired — update with fresh one
    user.access_token = body.github_token
    db.commit()
    return {"message": "Token refreshed"}