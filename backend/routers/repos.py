from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from models.database import Repository, User
import httpx
import os

router = APIRouter(prefix="/repos", tags=["repos"])

@router.get("/list")
async def list_github_repos(github_token: str, db: Session = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user/repos",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github.v3+json"
            },
            params={"sort": "updated", "per_page": 30}
        )
        repos = response.json()
        return [
            {
                "id": repo["id"],
                "name": repo["name"],
                "full_name": repo["full_name"],
                "private": repo["private"],
                "description": repo.get("description", ""),
                "language": repo.get("language", ""),
                "updated_at": repo["updated_at"]
            }
            for repo in repos
            if isinstance(repo, dict)
        ]

@router.post("/connect")
async def connect_repo(
    github_token: str,
    github_id: str,
    repo_full_name: str,
    repo_name: str,
    github_repo_id: str,
    db: Session = Depends(get_db)
):
    print(f"GITHUB TOKEN RECEIVED: {github_token[:20]}...")
    # Check if already connected
    existing = db.query(Repository).filter(
        Repository.github_repo_id == github_repo_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Repository already connected")

    # Get or create user
    user = db.query(User).filter(User.github_id == github_id).first()
    if not user:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {github_token}"}
            )
            profile = response.json()
        user = User(
            github_id=str(profile["id"]),
            username=profile["login"],
            avatar_url=profile["avatar_url"],
            access_token=github_token
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Create webhook on GitHub
    webhook_url = os.getenv(
        "WEBHOOK_URL",
        "https://firstsenior.railway.app/webhooks/github"
    )
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.github.com/repos/{repo_full_name}/hooks",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github.v3+json"
            },
            json={
                "name": "web",
                "active": True,
                "events": ["push", "pull_request"],
                "config": {
                    "url": webhook_url,
                    "content_type": "json",
                    "secret": os.getenv("GITHUB_WEBHOOK_SECRET")
                }
            }
        )
        webhook_data = response.json()

    # Save to database
    repo = Repository(
        user_id=user.id,
        github_repo_id=github_repo_id,
        name=repo_name,
        full_name=repo_full_name,
        webhook_id=str(webhook_data.get("id", "")),
        health_score=100.0
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    return {
        "message": "Repository connected successfully",
        "repo_id": repo.id
    }

@router.get("/connected")
async def get_connected_repos(github_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.github_id == github_id).first()
    if not user:
        return []
    repos = db.query(Repository).filter(
        Repository.user_id == user.id
    ).all()
    return [
        {
            "id": repo.id,
            "name": repo.name,
            "full_name": repo.full_name,
            "health_score": repo.health_score,
            "created_at": repo.created_at
        }
        for repo in repos
    ]