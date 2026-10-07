from sqlalchemy.orm import Session
from models.database import DiaryEntry
import re

def generate_and_save_diary_entry(
    db: Session,
    repo_id: int,
    commit_sha: str,
    changed_files: list,
    ai_review: str
) -> DiaryEntry:
    """
    Parses AI review and commit metadata to build a clean project diary entry.
    """
    # Extract senior tip from AI review if present
    tip_match = re.search(r'### Senior Tip\n([^\n]+)', ai_review)
    senior_feedback = tip_match.group(1).strip() if tip_match else ai_review[:300] + "..."

    summary = f"Reviewed {len(changed_files)} file(s)"
    changes_str = ", ".join(changed_files[:5])

    diary = DiaryEntry(
        repo_id=repo_id,
        commit_sha=commit_sha,
        summary=summary,
        changes_made=changes_str,
        senior_feedback=senior_feedback
    )
    db.add(diary)
    db.commit()
    db.refresh(diary)
    return diary
