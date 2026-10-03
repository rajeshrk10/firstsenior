from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from models.database import Review, Repository, User

router = APIRouter(prefix="/reviews", tags=["reviews"])

@router.get("/{repo_id}")
def get_reviews(repo_id: int, db: Session = Depends(get_db)):
    reviews = db.query(Review).filter(
        Review.repo_id == repo_id
    ).order_by(Review.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "commit_sha": r.commit_sha[:7] if r.commit_sha else "",
            "files_changed": r.files_changed,
            "ai_review": r.ai_review,
            "health_score": r.health_score,
            "created_at": r.created_at
        }
        for r in reviews
    ]

@router.get("/latest/{github_id}")
def get_latest_reviews(github_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.github_id == github_id).first()
    if not user:
        return []
    repos = db.query(Repository).filter(
        Repository.user_id == user.id
    ).all()
    repo_ids = [r.id for r in repos]
    reviews = db.query(Review).filter(
        Review.repo_id.in_(repo_ids)
    ).order_by(Review.created_at.desc()).limit(10).all()
    
    repo_map = {r.id: r.name for r in repos}
    return [
        {
            "id": r.id,
            "repo_name": repo_map.get(r.repo_id, ""),
            "commit_sha": r.commit_sha[:7] if r.commit_sha else "",
            "files_changed": r.files_changed,
            "ai_review": r.ai_review,
            "health_score": r.health_score,
            "created_at": r.created_at
        }
        for r in reviews
    ]