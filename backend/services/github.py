import httpx
import base64
import os

GITHUB_API_BASE = "https://api.github.com"

async def get_github_headers(token: str) -> dict:
    """Helper to return standard GitHub API headers."""
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }

async def get_file_content(repo_full_name: str, file_path: str, github_token: str) -> str:
    """Fetch raw file content from GitHub repository."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{repo_full_name}/contents/{file_path}",
            headers=await get_github_headers(github_token)
        )
        if response.status_code == 200:
            data = response.json()
            content = data.get("content", "")
            if content:
                return base64.b64decode(content).decode("utf-8")
        return ""

async def get_commit_patch_diff(repo_full_name: str, commit_sha: str, github_token: str) -> list:
    """Fetch exact commit diff (lines added/removed) instead of whole files."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{repo_full_name}/commits/{commit_sha}",
            headers=await get_github_headers(github_token)
        )
        if response.status_code == 200:
            files = response.json().get("files", [])
            return [
                {
                    "filename": f["filename"],
                    "patch": f.get("patch", ""),
                    "status": f.get("status", "modified")
                }
                for f in files
            ]
        return []

async def post_github_commit_comment(repo_full_name: str, commit_sha: str, review_text: str, github_token: str):
    """Post AI review directly as a comment on GitHub commit."""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{GITHUB_API_BASE}/repos/{repo_full_name}/commits/{commit_sha}/comments",
            headers=await get_github_headers(github_token),
            json={"body": review_text}
        )

async def get_pr_changed_files(repo_full_name: str, pr_number: int, github_token: str) -> list:
    """Fetch changed files list for a GitHub Pull Request."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{repo_full_name}/pulls/{pr_number}/files",
            headers=await get_github_headers(github_token)
        )
        if response.status_code == 200:
            files = response.json()
            return [f["filename"] for f in files if "filename" in f]
        return []

async def post_github_pr_comment(repo_full_name: str, pr_number: int, review_text: str, github_token: str):
    """Post AI review as an issue/PR comment on GitHub."""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues/{pr_number}/comments",
            headers=await get_github_headers(github_token),
            json={"body": review_text}
        )

async def create_webhook(repo_full_name: str, webhook_url: str, secret: str, github_token: str) -> dict:
    """Register repository webhook on GitHub."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GITHUB_API_BASE}/repos/{repo_full_name}/hooks",
            headers=await get_github_headers(github_token),
            json={
                "name": "web",
                "active": True,
                "events": ["push", "pull_request"],
                "config": {
                    "url": webhook_url,
                    "content_type": "json",
                    "secret": secret
                }
            }
        )
        return response.json()
