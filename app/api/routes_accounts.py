"""Account, session, and privacy-controlled history endpoints."""

import re

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.services import account_service as accounts

router = APIRouter(prefix="/api/v1/auth", tags=["accounts"])
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class HistoryPreference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


def current_user(medguide_session: str | None = Cookie(default=None)):
    user = accounts.get_user_for_session(medguide_session)
    if user is None:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    return user


def _validate_credentials(payload):
    email = payload.email.strip()
    if not EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    if len(payload.password) < 12:
        raise HTTPException(status_code=422, detail="Choose a password with at least 12 characters.")
    return email


def _set_session(response, token):
    response.set_cookie(
        accounts.SESSION_COOKIE,
        token,
        max_age=accounts.SESSION_TTL_SECONDS,
        httponly=True,
        secure=settings.app_env != "development",
        samesite="strict",
        path="/",
    )


@router.post("/signup", summary="Create an account")
def signup(payload: Credentials, response: Response):
    email = _validate_credentials(payload)
    try:
        user = accounts.create_account(email, payload.password)
    except ValueError:
        raise HTTPException(status_code=409, detail="Could not create this account. Check the email or sign in.") from None
    _set_session(response, accounts.create_session(user["id"]))
    return {"user": user}


@router.post("/login", summary="Sign in")
def login(payload: Credentials, response: Response):
    email = payload.email.strip()
    if not EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    user = accounts.authenticate(email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    _set_session(response, accounts.create_session(user["id"]))
    return {"user": user}


@router.post("/logout", summary="Sign out")
def logout(response: Response, medguide_session: str | None = Cookie(default=None)):
    accounts.revoke_session(medguide_session)
    response.delete_cookie(accounts.SESSION_COOKIE, path="/", httponly=True, samesite="strict")
    return {"status": "signed_out"}


@router.get("/me", summary="Get the signed-in account")
def me(user=Depends(current_user)):
    return {"user": user}


@router.patch("/history", summary="Set encrypted conversation-history preference")
def history_preference(payload: HistoryPreference, user=Depends(current_user)):
    if payload.enabled:
        try:
            accounts.ensure_encryption_available()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from None
    accounts.set_history_enabled(user["id"], payload.enabled)
    return {"history_enabled": payload.enabled}


@router.get("/history", summary="Read the signed-in account's saved conversations")
def history(user=Depends(current_user)):
    if not user["history_enabled"]:
        return {"history_enabled": False, "conversations": []}
    try:
        conversations = accounts.list_conversations(user["id"])
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    return {"history_enabled": True, "conversations": conversations}


@router.delete("/account", summary="Delete the signed-in account and its data")
def delete_user(response: Response, user=Depends(current_user), medguide_session: str | None = Cookie(default=None)):
    accounts.revoke_session(medguide_session)
    accounts.delete_account(user["id"])
    response.delete_cookie(accounts.SESSION_COOKIE, path="/", httponly=True, samesite="strict")
    return {"status": "deleted"}
