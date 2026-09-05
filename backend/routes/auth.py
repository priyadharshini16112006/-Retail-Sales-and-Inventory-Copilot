from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_validator
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import os
from ..database import get_db, User
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

SECRET_KEY = os.environ.get("SESSION_SECRET", "stockpilot-secret-key-change-in-production")
serializer = URLSafeTimedSerializer(SECRET_KEY)
SESSION_COOKIE = "sp_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


# ---- Helpers ----

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_session_token(user_id: int) -> str:
    return serializer.dumps({"user_id": user_id})

def decode_session_token(token: str):
    try:
        data = serializer.loads(token, max_age=SESSION_MAX_AGE)
        return data.get("user_id")
    except (BadSignature, SignatureExpired):
        return None

def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    user_id = decode_session_token(token)
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()

def require_auth(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


# ---- Page routes ----

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    # If already logged in, redirect to dashboard
    token = request.cookies.get(SESSION_COOKIE)
    if token and decode_session_token(token):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None, "success": None})

@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None})

@router.get("/logout")
def logout(response: Response):
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie(SESSION_COOKIE)
    return resp


# ---- API POST routes ----

class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    confirm_password: str

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/auth/register")
def register(request: Request, db: Session = Depends(get_db),
             full_name: str = Form(...),
             email: str = Form(...),
             password: str = Form(...),
             confirm_password: str = Form(...)):
    errors = []

    full_name = full_name.strip()
    email = email.strip().lower()

    if not full_name:
        errors.append("Full name is required.")
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        errors.append("Please enter a valid email address.")
    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if password != confirm_password:
        errors.append("Passwords do not match.")

    if errors:
        return templates.TemplateResponse("register.html", {
            "request": request, "error": " ".join(errors)
        })

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return templates.TemplateResponse("register.html", {
            "request": request, "error": "An account with this email already exists."
        })

    new_user = User(
        full_name=full_name,
        email=email,
        password_hash=hash_password(password),
        created_at=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()

    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": None,
        "success": "Account created successfully. Please log in."
    })


@router.post("/auth/login")
def login(request: Request, response: Response, db: Session = Depends(get_db),
          email: str = Form(...),
          password: str = Form(...),
          remember: str = Form(default="")):
    email = email.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid email or password.",
            "success": None
        })

    token = create_session_token(user.id)
    max_age = SESSION_MAX_AGE if remember else None

    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        max_age=max_age,
        samesite="lax"
    )
    return resp


# ---- API: current user info and profile updates ----
@router.get("/api/me")
def get_me(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Format date nicely
    created_str = user.created_at.strftime("%B %Y") if user.created_at else "Unknown"
    
    return {
        "id": user.id, 
        "full_name": user.full_name, 
        "email": user.email,
        "created_at": created_str
    }

class ProfileUpdate(BaseModel):
    full_name: str
    email: str

@router.post("/api/profile")
def update_profile(data: ProfileUpdate, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    full_name = data.full_name.strip()
    email = data.email.strip().lower()
    
    if not full_name:
        raise HTTPException(status_code=400, detail="Full name is required.")
        
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required.")
        
    if email != user.email:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise HTTPException(status_code=400, detail="That email is already in use.")
            
    user.full_name = full_name
    user.email = email
    db.commit()
    
    return {"message": "Profile updated successfully."}

class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

@router.post("/api/password")
def update_password(data: PasswordUpdate, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password.")
        
    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match.")
        
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters.")
        
    user.password_hash = hash_password(data.new_password)
    db.commit()
    
    return {"message": "Password changed successfully."}

