from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from models.database import User
import httpx

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/sync-token")
async def sync_token(
    github_id: str,
    github_token: str,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.github_id == github_id).first()
    
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
    user.access_token = github_token
    db.commit()
    return {"message": "Token refreshed"}