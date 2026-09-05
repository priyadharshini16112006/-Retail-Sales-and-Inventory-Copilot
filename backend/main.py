from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
import os

# Load .env (or .env.example) so env vars are available inside the uvicorn process
if os.path.exists(".env"):
    load_dotenv(".env", override=True)
elif os.path.exists(".env.example"):
    load_dotenv(".env.example", override=True)

from .routes import dashboard, inventory, sales, alerts, chat, scenarios, data_entry
from .routes.auth import router as auth_router, get_current_user, SESSION_COOKIE, decode_session_token
from .database import engine, Base, get_db

load_dotenv()

# Create all tables (including 'users' if new)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="StockPilot AI API")

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

# Auth routes (no prefix — /login, /register, /logout, /auth/login, /auth/register)
app.include_router(auth_router)

# Protected API routes
app.include_router(dashboard.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")
app.include_router(sales.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(scenarios.router, prefix="/api")
app.include_router(data_entry.router, prefix="/api")

# Middleware: protect all /api/* routes
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # Always allow: static files, login page, register page, auth endpoints
    public_paths = ["/login", "/register", "/auth/login", "/auth/register",
                    "/logout", "/static", "/api/health"]
    
    is_public = any(path.startswith(p) for p in public_paths)
    
    if not is_public:
        token = request.cookies.get(SESSION_COOKIE)
        user_id = decode_session_token(token) if token else None
        if not user_id:
            # API calls get 401, page requests get redirect
            if path.startswith("/api"):
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "Not authenticated"}, status_code=401)
            return RedirectResponse("/login", status_code=302)

    return await call_next(request)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/")
async def serve_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
