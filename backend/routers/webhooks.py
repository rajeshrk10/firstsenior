from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from models.database import Repository, User
from core.security import decrypt_token
import hmac
import hashlib
import os
import asyncio
from services.ai_agent import review_code

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

def verify_github_signature(payload: bytes, signature: str) -> bool:
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not secret:
        print("Warning: GITHUB_WEBHOOK_SECRET is not set.")
        return False
    expected = "sha256=" + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@router.post("/github")
async def github_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    # Get raw payload
    payload = await request.body()
    
    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_github_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse event
    event_type = request.headers.get("X-GitHub-Event")
    data = await request.json()

    commit_sha = ""
    changed_files = []
    pr_number = None

    if event_type == "push":
        commit_sha = data.get("after", "")
        commits = data.get("commits", [])
        if not commits:
            return {"message": "No commits found in push event"}
        for commit in commits:
            changed_files.extend(commit.get("added", []))
            changed_files.extend(commit.get("modified", []))
        changed_files = list(set(changed_files))

    elif event_type == "pull_request":
        action = data.get("action")
        if action not in ["opened", "synchronize", "reopened"]:
            return {"message": f"PR action {action} ignored"}
        pr = data.get("pull_request", {})
        pr_number = pr.get("number")
        commit_sha = pr.get("head", {}).get("sha", "")
        # Changed files will be fetched directly via GitHub API in review_code
    else:
        return {"message": f"Event {event_type} received but not processed"}

    # Get repo info from webhook payload
    repo_full_name = data.get("repository", {}).get("full_name")
    if not repo_full_name:
        return {"message": "Repository info missing"}

    # Find repo in database
    repo = db.query(Repository).filter(
        Repository.full_name == repo_full_name
    ).first()

    if not repo:
        return {"message": "Repository not connected to FirstSenior"}

    # Get user access token
    user = db.query(User).filter(
        User.id == repo.user_id
    ).first()

    if not user:
        return {"message": "User not found"}

    # Decrypt token for GitHub API operations
    plain_token = decrypt_token(user.access_token)

    # Trigger AI review in background
    asyncio.create_task(
        review_code(
            repo_id=repo.id,
            repo_full_name=repo_full_name,
            commit_sha=commit_sha,
            changed_files=changed_files,
            github_token=plain_token,
            pr_number=pr_number
        )
    )
    return {"message": "Webhook received. AI review started."}