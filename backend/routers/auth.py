
# APIRouter groups related API endpoints.
# Depends allows FastAPI to provide a database session.
# HTTPException lets us return appropriate HTTP error responses.
from fastapi import APIRouter, Depends, HTTPException

# BaseModel validates the incoming request body.
# Field adds basic validation, such as rejecting empty strings.
from pydantic import BaseModel, Field

# Session represents a SQLAlchemy database session.
from sqlalchemy.orm import Session

# SQLAlchemyError lets us handle database operation failures.
from sqlalchemy.exc import SQLAlchemyError

# httpx makes HTTP requests to GitHub's API.
import httpx

# Our existing database session provider.
from core.database import get_db

# Functions for encrypting and decrypting GitHub tokens.
from core.security import encrypt_token, decrypt_token

# User is the database model containing GitHub user information.
from models.database import User


# Keep the existing URL prefix and API tag unchanged.
# The complete endpoint remains POST /auth/sync-token.
router = APIRouter(prefix="/auth", tags=["auth"])


class SyncTokenRequest(BaseModel):
    """
    Defines the JSON request body expected by this endpoint.

    Example:
    {
        "github_id": "12345678",
        "github_token": "ghp_example_token"
    }
    """
    github_id: str = Field(min_length=1)
    github_token: str = Field(min_length=1)


async def verify_github_token(token: str):
    """
    Ask GitHub to validate the supplied token.

    If valid, GitHub returns information about the account
    associated with that token.
    """
    try:
        # AsyncClient allows the backend to make an asynchronous
        # HTTP request without blocking the event loop while waiting.
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.github.com/user",
                headers={
                    # GitHub uses this header to authenticate the request.
                    "Authorization": f"Bearer {token}",

                    # Request GitHub's standard JSON API response.
                    "Accept": "application/vnd.github+json",
                },
            )

    except httpx.RequestError:
        # This is a network/connection failure, not proof that
        # the supplied token is invalid.
        raise HTTPException(
            status_code=502,
            detail="Unable to contact GitHub",
        ) from None

    if response.status_code == 401:
        # GitHub rejected the token as unauthenticated.
        raise HTTPException(
            status_code=401,
            detail="The supplied GitHub token is invalid",
        )

    if response.status_code != 200:
        # Do not assume every other response means the token is invalid.
        raise HTTPException(
            status_code=502,
            detail="GitHub could not verify the supplied token",
        )

    # Convert GitHub's JSON response into a Python dictionary.
    return response.json()


@router.post("/sync-token")
async def sync_token(
    body: SyncTokenRequest,
    db: Session = Depends(get_db),
):
    """
    Verify the incoming GitHub token and refresh the stored token
    only when the existing stored token is no longer valid.
    """

    # STEP 1:
    # Verify the new token directly with GitHub.
    github_user = await verify_github_token(body.github_token)

    # STEP 2:
    # Check that the GitHub account returned by GitHub matches
    # the ID supplied in the request.
    #
    # Convert the returned ID to a string because the request model
    # declares github_id as a string.
    if str(github_user.get("id")) != body.github_id:
        raise HTTPException(
            status_code=403,
            detail="GitHub account ID does not match the token",
        )

    # STEP 3:
    # Find the corresponding user in our own database.
    #
    # filter() builds the database condition.
    # first() returns the first matching user or None.
    user = (
        db.query(User)
        .filter(User.github_id == body.github_id)
        .first()
    )

    if not user:
        # Preserve the original endpoint's response for a missing user.
        return {"message": "User not found"}

    # STEP 4:
    # If a token is already stored, decrypt it so we can check
    # whether GitHub still accepts that existing token.
    if user.access_token:
        try:
            old_token = decrypt_token(user.access_token)

        except (RuntimeError, ValueError):
            # Never silently replace a token that we cannot decrypt.
            # That could hide an encryption-key or data problem.
            raise HTTPException(
                status_code=500,
                detail="Unable to access stored GitHub credentials",
            ) from None

        try:
            # Ask GitHub whether the stored token still works.
            async with httpx.AsyncClient(timeout=10.0) as client:
                old_response = await client.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {old_token}",
                        "Accept": "application/vnd.github+json",
                    },
                )

        except httpx.RequestError:
            # A connection failure does not mean the old token is invalid.
            raise HTTPException(
                status_code=502,
                detail="Unable to verify the existing GitHub connection",
            ) from None

        if old_response.status_code == 200:
            # The stored token still works, so no database update is needed.
            return {"message": "Token is valid"}

        if old_response.status_code != 401:
            # Only replace the token when GitHub specifically rejects
            # the existing token with 401 Unauthorized.
            raise HTTPException(
                status_code=502,
                detail="Unable to verify the existing GitHub connection",
            )

    # STEP 5:
    # The stored token is missing or GitHub rejected it.
    # Encrypt the verified new token before saving it.
    try:
        encrypted_token = encrypt_token(body.github_token)

    except (RuntimeError, ValueError):
        raise HTTPException(
            status_code=500,
            detail="Unable to securely store GitHub credentials",
        ) from None

    # STEP 6:
    # Update the database and commit the transaction.
    try:
        # Change the token in the current SQLAlchemy session.
        user.access_token = encrypted_token

        # Persist the change to PostgreSQL.
        db.commit()

    except SQLAlchemyError:
        # Undo uncommitted changes if the database operation fails.
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to save GitHub connection",
        ) from None

    # Report success only after the database commit succeeds.
    return {"message": "Token refreshed"}
