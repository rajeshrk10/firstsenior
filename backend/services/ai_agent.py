from groq import Groq
from models.database import Review, Repository
from core.database import SessionLocal
import os
import re
from services.github import (
    get_file_content,
    post_github_commit_comment,
    get_pr_changed_files,
    post_github_pr_comment
)
from services.rag import get_past_mistakes_context
from services.diary_writer import generate_and_save_diary_entry

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
    numbered_issues = len(re.findall(r'^\d+\.\s+', review_text, re.MULTILINE))
    return max(100.0 - (numbered_issues * 15), 20.0)

async def review_code(
    repo_id: int,
    repo_full_name: str,
    commit_sha: str,
    changed_files: list,
    github_token: str,
    pr_number: int = None
):
    db = SessionLocal()
    try:
        # If PR event and no changed files provided, fetch directly from GitHub
        if pr_number and not changed_files:
            changed_files = await get_pr_changed_files(repo_full_name, pr_number, github_token)

        print(f"ALL CHANGED FILES: {changed_files}")

        relevant_extensions = [
            ".js", ".jsx", ".ts", ".tsx", ".css", ".py", ".html",
            ".json", ".sql", ".yaml", ".yml", ".go", ".java", ".rs", ".c", ".cpp"
        ]
        relevant_files = [
            f for f in changed_files
            if any(f.endswith(ext) for ext in relevant_extensions)
        ]

        print(f"RELEVANT FILES: {relevant_files}")

        if not relevant_files:
            print("No relevant files found")
            db.close()
            return

        file_contents = ""
        for file_path in relevant_files[:5]:
            content = await get_file_content(
                repo_full_name,
                file_path,
                github_token
            )
            print(f"FETCHING: {file_path} → length: {len(content)}")
            if content:
                file_contents += f"\n\nFile: {file_path}\n{content[:2000]}"

        if not file_contents:
            print("No file contents fetched")
            db.close()
            return

        # Retrieve RAG context (past developer mistakes)
        past_mistakes = get_past_mistakes_context(db, repo_id)
        user_prompt = f"Please review these changed files:\n{file_contents}{past_mistakes}"

        # Fetch active Groq models directly from live API
        live_models = []
        try:
            models_data = client.models.list().data
            live_models = [m.id for m in models_data if "whisper" not in m.id.lower() and "embed" not in m.id.lower()]
            print(f"LIVE GROQ MODELS AVAILABLE: {live_models}")
        except Exception as err:
            print(f"Could not list Groq models: {err}")

        preferred = os.getenv("GROQ_MODEL")
        if preferred and preferred in live_models:
            live_models.remove(preferred)
            live_models.insert(0, preferred)

        if not live_models:
            raise Exception("No active Groq models available for your API key.")

        ai_review = None
        used_model = None

        for model in live_models:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=900,
                    temperature=0.3
                )
                ai_review = response.choices[0].message.content
                used_model = model
                print(f"GROQ MODEL {model} SUCCEEDED!")
                break
            except Exception as model_err:
                print(f"Model {model} failed: {model_err}. Trying next available model...")

        if not ai_review:
            raise Exception("All Groq models failed to generate review.")

        print(f"AI REVIEW SNIPPET: {ai_review[:200]}")

        # Try computing score from review text or call scoring completion
        try:
            score_response = client.chat.completions.create(
                model=used_model,
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
            health_score = float(''.join(filter(str.isdigit, score_text)))
            health_score = max(min(health_score, 100), 20)
        except Exception as score_err:
            print(f"Scoring fallback triggered: {score_err}")
            health_score = calculate_health_score(ai_review)

        print(f"HEALTH SCORE: {health_score}")

        # Save review
        review = Review(
            repo_id=repo_id,
            commit_sha=commit_sha,
            pr_number=pr_number,
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

        # Save changes to database first
        db.commit()

        # Generate and save diary entry using diary_writer service
        generate_and_save_diary_entry(
            db=db,
            repo_id=repo_id,
            commit_sha=commit_sha,
            changed_files=relevant_files,
            ai_review=ai_review
        )

        print("DATABASE UPDATED SUCCESSFULLY")

        # Post GitHub comment (PR comment or Commit comment)
        if pr_number:
            await post_github_pr_comment(
                repo_full_name,
                pr_number,
                ai_review,
                github_token
            )
        else:
            await post_github_commit_comment(
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