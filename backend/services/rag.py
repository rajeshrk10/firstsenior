from sqlalchemy.orm import Session
from models.database import Review
import re

def get_past_mistakes_context(db: Session, repo_id: int, max_reviews: int = 5) -> str:
    """
    Retrieves recent reviews for the repo, extracts common issues,
    and formats a 'Mistake Memory' prompt block for the AI mentor.
    """
    reviews = db.query(Review).filter(
        Review.repo_id == repo_id
    ).order_by(Review.created_at.desc()).limit(max_reviews).all()

    if not reviews:
        return ""

    past_issues = []
    for r in reviews:
        # Extract numbered issues under '### Issues Found' header
        issues = re.findall(r'^\d+\.\s+.*', r.ai_review  or "", re.MULTILINE)
        past_issues.extend(issues[:2])

    if not past_issues:
        return ""

    formatted_issues = "\n".join([f"- {issue}" for issue in past_issues[:6]])
    return (
        "\n\n### MISTAKE MEMORY (Developer's Past Anti-patterns):\n"
        "The developer has made these mistakes in recent commits. "
        "Check if they repeated any of them in this commit:\n"
        f"{formatted_issues}\n"
    )
