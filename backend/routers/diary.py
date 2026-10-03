from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from models.database import DiaryEntry

router = APIRouter(prefix="/diary", tags=["diary"])

@router.get("/{repo_id}")
def get_diary(repo_id: int, db: Session = Depends(get_db)):
    entries = db.query(DiaryEntry).filter(
        DiaryEntry.repo_id == repo_id
    ).order_by(DiaryEntry.created_at.desc()).all()
    return [
        {
            "id": e.id,
            "commit_sha": e.commit_sha[:7] if e.commit_sha else "",
            "summary": e.summary,
            "changes_made": e.changes_made,
            "senior_feedback": e.senior_feedback,
            "created_at": e.created_at
        }
        for e in entries
    ]