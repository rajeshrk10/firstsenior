from groq import Groq
from sqlalchemy.orm import Session
from models.database import Review, Repository, DiaryEntry
from core.database import SessionLocal
import httpx
import os
import base64

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = (
    "You are FirstSenior — an experienced senior frontend engineer "
    "reviewing code for a junior developer who has no other guidance. "
    "You are their only mentor.\n\n"
    "Your review must:\n"
    "- Be specific to the exact code changed\n"
    "- Show the problematic code snippet\n"
    "- Show the exact fix with code example\n"
    "- Explain WHY in simple language a junior can understand\n"
    "- Be encouraging — you are their only mentor\n"
    "- Focus on React, Next.js, TypeScript best practices\n\n"
    "Format your review EXACTLY like this:\n\n"
    "## FirstSenior Review\n\n"
    "### What You Did Well\n"
    "[genuine positives]\n\n"
    "### Issues Found\n"
    "[each issue with: Issue name, File, Problem, Fix, Why]\n\n"
    "### Senior Tip\n"
    "[one architectural or best practice tip]\n\n"
    "### Health Score: X/100\n"
    "[brief explanation]"
)

async def get_file_content(
    repo_full_name: str,
    file_path: str,
    github_token: str
) -> str:
    async with httpx.AsyncClient() as client_http:
        response = await client_http.get(
            f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        if response.status_code == 200:
            content = response.json().get("content", "")
            return base64.b64decode(content).decode("utf-8")
        return ""

async def post_github_comment(
    repo_full_name: str,
    commit_sha: str,
    review: str,
    github_token: str
):
    async with httpx.AsyncClient() as client_http:
        await client_http.post(
            f"https://api.github.com/repos/{repo_full_name}/commits/{commit_sha}/comments",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github.v3+json"
            },
            json={"body": review}
        )

def calculate_health_score(review_text: str) -> float:
    score = 100.0
    issue_count = review_text.count("Issue:")
    issue_count += review_text.count("Problem:")
    issue_count += review_text.count("Critical:")
    issue_count += review_text.count("Security:")
    issue_count += review_text.count("Warning:")
    score -= issue_count * 10
    return max(score, 0.0)

async def review_code(
    repo_id: int,
    repo_full_name: str,
    commit_sha: str,
    changed_files: list,
    github_token: str,
):
    # Create a fresh database session
    db = SessionLocal()
    try:
        relevant_extensions = [
            ".js", ".jsx", ".ts", ".tsx",
            ".py", ".css", ".html"
        ]
        relevant_files = [
            f for f in changed_files
            if any(f.endswith(ext) for ext in relevant_extensions)
        ]

        if not relevant_files:
            return

        file_contents = ""
        for file_path in relevant_files[:5]:
            content = await get_file_content(
                repo_full_name,
                file_path,
                github_token
            )
            if content:
                file_contents += f"\n\nFile: {file_path}\n{content[:2000]}"

        if not file_contents:
            return

        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Please review these changed files:\n{file_contents}"
                }
            ],
            max_tokens=2000,
            temperature=0.3
        )

        ai_review = response.choices[0].message.content
        health_score = calculate_health_score(ai_review)
        print(f"AI REVIEW SNIPPET: {ai_review[:200]}")
        print(f"HEALTH SCORE: {health_score}")

        #save review and health score to the database
        review = Review(
            repo_id=repo_id,
            commit_sha=commit_sha,
            files_changed=", ".join(relevant_files),
            ai_review=ai_review,
            health_score=health_score
        )
        db.add(review)

        #update the repository's health score
        repo = db.query(Repository).filter(
            Repository.id == repo_id
        ).first()
        if repo:
            repo.health_score = health_score

        diary = DiaryEntry(
            repo_id=repo_id,
            commit_sha=commit_sha,
            summary=f"Reviewed {len(relevant_files)} files",
            changes_made=", ".join(relevant_files),
            senior_feedback=ai_review[:500]
        )
        db.add(diary)
        db.commit()

        print(f"Database updated successfully")

        #post the AI review as a comment on the GitHub commit
        await post_github_comment(
            repo_full_name,
            commit_sha,
            ai_review,
            github_token
        )

    except Exception as e:
        print(f"AI review error: {e}")
        db.rollback()
    finally:
        db.close()