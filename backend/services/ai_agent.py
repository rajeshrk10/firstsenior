from groq import Groq
from sqlalchemy.orm import Session
from models.database import Review, Repository, DiaryEntry
from core.database import SessionLocal
import httpx
import os
import base64
import re

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
    "Format your review like this:\n\n"
    "## FirstSenior Review\n\n"
    "### What You Did Well\n"
    "[genuine positives]\n\n"
    "### Issues Found\n"
    "[numbered list of issues with: problem, fix, why]\n\n"
    "### Senior Tip\n"
    "[one actionable tip]\n\n"
    "At the end always write:\n"
    "### Health Score: X/100"
)

def calculate_health_score(review_text: str) -> float:
    # Fallback only — counts numbered issues
    numbered_issues = len(re.findall(r'^\d+\.\s+', review_text, re.MULTILINE))
    return max(100.0 - (numbered_issues * 15), 20.0)

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

async def review_code(
    repo_id: int,
    repo_full_name: str,
    commit_sha: str,
    changed_files: list,
    github_token: str
):
    db = SessionLocal()
    try:
        relevant_extensions = [
            ".js", ".jsx", ".ts", ".tsx", ".css"
        ]
        relevant_files = [
            f for f in changed_files
            if any(f.endswith(ext) for ext in relevant_extensions)
        ]

        if not relevant_files:
            print("No relevant files found")
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
            print("No file contents fetched")
            return

        # First call — get the full review
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Please review these changed files:\n{file_contents}"
                }
            ],
            max_tokens=900,
            temperature=0.3
        )

        ai_review = response.choices[0].message.content
        print(f"AI REVIEW SNIPPET: {ai_review[:200]}")

        # Second call — ask AI to score based on its own review
        score_response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Based on this code review:\n{ai_review}\n\n"
                        "Calculate a health score from 0 to 100.\n"
                        "Consider how severely each issue affects the app:\n"
                        "- App crashes or security hole: deduct 25\n"
                        "- Causes bugs or bad performance: deduct 15\n"
                        "- Hard to maintain: deduct 8\n"
                        "- Minor style issue: deduct 3\n"
                        "Start from 100. Reply with ONLY a number. Example: 65"
                    )
                }
            ],
            max_tokens=10,
            temperature=0.1
        )

        score_text = score_response.choices[0].message.content.strip()
        print(f"AI SCORE RESPONSE: {score_text}")

        try:
            health_score = float(''.join(filter(str.isdigit, score_text)))
            health_score = max(min(health_score, 100), 20)
        except:
            health_score = calculate_health_score(ai_review)

        print(f"HEALTH SCORE: {health_score}")

        # Save review
        review = Review(
            repo_id=repo_id,
            commit_sha=commit_sha,
            files_changed=", ".join(relevant_files),
            ai_review=ai_review,
            health_score=health_score
        )
        db.add(review)

        # Update repo health score
        repo = db.query(Repository).filter(
            Repository.id == repo_id
        ).first()
        if repo:
            repo.health_score = health_score
            db.add(repo)

        # Write diary entry
        diary = DiaryEntry(
            repo_id=repo_id,
            commit_sha=commit_sha,
            summary=f"Reviewed {len(relevant_files)} files",
            changes_made=", ".join(relevant_files),
            senior_feedback=ai_review[:500]
        )
        db.add(diary)
        db.commit()

        print("DATABASE UPDATED SUCCESSFULLY")

        # Post comment to GitHub
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