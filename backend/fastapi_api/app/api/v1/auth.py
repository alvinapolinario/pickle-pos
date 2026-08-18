from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.domain.auth import AuthenticatedUser
from core.domain.exceptions import AuthenticationError
from core.services.auth_service import AuthService
from fastapi_api.app.dependencies.auth import get_auth_service, get_current_user
from fastapi_api.app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter()


class MessageResponse(BaseModel):
    message: str


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    if not payload.password and not payload.pin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password or PIN is required",
        )

    try:
        user = auth_service.authenticate_user(
            username=payload.username,
            password=payload.password,
            pin=payload.pin,
            device_code=payload.device_code,
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message) from exc

    auth_user = auth_service.build_authenticated_user(user)
    access_token = auth_service.create_access_token(auth_user)

    device = None
    if payload.device_code:
        from apps.accounts.models import Device

        device = Device.objects.filter(device_code=payload.device_code).first()

    refresh_token, _ = auth_service.create_refresh_token(user, device)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=auth_service.settings.jwt_access_token_expire_minutes * 60,
        user=UserResponse.from_domain(auth_user),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, auth_service: AuthService = Depends(get_auth_service)):
    try:
        access_token, refresh_token, _ = auth_service.rotate_refresh_token(payload.refresh_token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message) from exc

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=auth_service.settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/logout", response_model=MessageResponse)
def logout(payload: RefreshRequest, auth_service: AuthService = Depends(get_auth_service)):
    auth_service.revoke_refresh_token(payload.refresh_token)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserResponse)
def me(current_user: AuthenticatedUser = Depends(get_current_user)):
    return UserResponse.from_domain(current_user)
