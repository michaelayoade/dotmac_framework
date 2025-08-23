"""Identity API router for authentication, authorization, and user management."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel, EmailStr

from dotmac_isp.core.database import get_db
from dotmac_isp.shared.auth import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_current_tenant,
    verify_token,
)
from dotmac_isp.shared.enums import UserStatus
from .models import User, UserRole

router = APIRouter(tags=["identity"])


# Request/Response schemas
class UserLogin(BaseModel):
    """User login request schema."""

    email: EmailStr
    password: str


class UserRegister(BaseModel):
    """User registration request schema."""

    email: EmailStr
    password: str
    first_name: str
    last_name: str
    tenant_id: str = "default-tenant"


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserProfile(BaseModel):
    """User profile response schema."""

    id: str
    email: str
    username: str
    first_name: str
    last_name: str
    full_name: str
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime] = None
    tenant_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """User creation schema."""

    email: EmailStr
    username: str
    password: str
    first_name: str
    last_name: str
    tenant_id: str


class UserUpdate(BaseModel):
    """User update schema."""

    email: Optional[EmailStr] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None
    timezone: Optional[str] = None
    language: Optional[str] = None


class ChangePassword(BaseModel):
    """Change password schema."""

    current_password: str
    new_password: str


# Authentication endpoints
@router.post("/auth/login", response_model=TokenResponse)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return access tokens."""
    # Find user by email
    user = db.query(User).filter(User.email == user_credentials.email.lower()).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if account is locked
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is temporarily locked due to failed login attempts",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(user_credentials.password, user.password_hash):
        # Increment failed login attempts
        try:
            failed_attempts = int(user.failed_login_attempts or "0")
            failed_attempts += 1
            user.failed_login_attempts = str(failed_attempts)

            # Lock account after 5 failed attempts
            if failed_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=15)

            db.commit()
        except Exception:
            pass  # Don't fail login if we can't update attempts

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reset failed login attempts on successful login
    user.failed_login_attempts = "0"
    user.locked_until = None
    user.last_login = datetime.utcnow()
    db.commit()

    # Create tokens
    token_data = {"sub": user.id, "email": user.email, "tenant_id": user.tenant_id}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=900,  # 15 minutes in seconds
    )


@router.post(
    "/auth/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED
)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email.lower()).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Create username from email if not provided
    username = user_data.email.split("@")[0]

    # Check if username exists, make it unique
    base_username = username
    counter = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}{counter}"
        counter += 1

    # Create new user
    new_user = User(
        id=str(uuid4()),
        email=user_data.email.lower(),
        username=username,
        password_hash=hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        tenant_id=user_data.tenant_id,
        is_active=True,
        is_verified=False,
        created_at=datetime.utcnow(),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token."""
    try:
        payload = verify_token(refresh_token, "refresh")
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        # Create new access token
        token_data = {
            "sub": user_id,
            "email": payload.get("email"),
            "tenant_id": payload.get("tenant_id"),
        }
        access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)

        return TokenResponse(
            access_token=access_token, refresh_token=new_refresh_token, expires_in=900
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )


@router.post("/auth/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user (placeholder for token blacklisting)."""
    # In a production system, you would blacklist the token
    # For now, just return success
    return {"message": "Successfully logged out"}


# User management endpoints
@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile."""
    return current_user


@router.put("/me", response_model=UserProfile)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user's profile."""
    # Update allowed fields
    update_data = user_update.dict(exclude_unset=True)

    # Check if email is being changed and not already taken
    if "email" in update_data:
        existing_user = (
            db.query(User)
            .filter(
                and_(
                    User.email == update_data["email"].lower(),
                    User.id != current_user.id,
                )
            )
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already taken"
            )
        update_data["email"] = update_data["email"].lower()

    # Check if username is being changed and not already taken
    if "username" in update_data:
        existing_user = (
            db.query(User)
            .filter(
                and_(
                    User.username == update_data["username"], User.id != current_user.id
                )
            )
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
            )

    # Apply updates
    for field, value in update_data.items():
        setattr(current_user, field, value)

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)

    return current_user


@router.put("/me/password")
async def change_password(
    password_change: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change current user's password."""
    # Verify current password
    if not verify_password(
        password_change.current_password, current_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    current_user.password_hash = hash_password(password_change.new_password)
    current_user.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Password changed successfully"}


# Admin endpoints (require appropriate permissions)
@router.get("/users", response_model=List[UserProfile])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """List users (admin only)."""
    # In a full implementation, you would check permissions here
    users = (
        db.query(User)
        .filter(User.tenant_id == tenant_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return users


@router.post("/users", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new user (admin only)."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email.lower()).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Check if username is taken
    existing_username = (
        db.query(User).filter(User.username == user_data.username).first()
    )

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
        )

    # Create new user
    new_user = User(
        id=str(uuid4()),
        email=user_data.email.lower(),
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        tenant_id=user_data.tenant_id,
        is_active=True,
        is_verified=True,  # Admin-created users are verified
        created_at=datetime.utcnow(),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/users/{user_id}", response_model=UserProfile)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Get user by ID (admin only)."""
    user = (
        db.query(User)
        .filter(and_(User.id == user_id, User.tenant_id == tenant_id))
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    is_active: bool,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Update user status (admin only)."""
    user = (
        db.query(User)
        .filter(and_(User.id == user_id, User.tenant_id == tenant_id))
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Don't allow deactivating yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    user.is_active = is_active
    user.updated_at = datetime.utcnow()
    db.commit()

    return {
        "message": f"User {'activated' if is_active else 'deactivated'} successfully"
    }
