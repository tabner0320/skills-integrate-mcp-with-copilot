"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from datetime import date
import base64
import hashlib
import hmac
import os
from pathlib import Path
import secrets

from fastapi import FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}

# In-memory account and session stores keep this exercise database-free.
accounts = {}
sessions = {}


class RegistrationRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    full_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    date_of_birth: date
    role: str = Field(default="student", pattern="^(student|club)$")


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"{base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def password_matches(password: str, stored_hash: str) -> bool:
    salt, expected_digest = stored_hash.split("$", 1)
    actual_digest = hash_password(password, base64.b64decode(salt)).split("$", 1)[1]
    return hmac.compare_digest(actual_digest, expected_digest)


def account_view(account: dict) -> dict:
    return {
        "username": account["username"],
        "full_name": account["full_name"],
        "email": account["email"],
        "date_of_birth": account["date_of_birth"],
        "role": account["role"],
    }


def get_current_account(request: Request) -> dict:
    token = request.cookies.get("session_token")
    username = sessions.get(token)
    account = accounts.get(username)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You must be logged in to perform this action",
        )
    return account


@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(request_data: RegistrationRequest):
    normalized_username = request_data.username.strip().lower()
    normalized_email = request_data.email.strip().lower()
    if normalized_username in accounts:
        raise HTTPException(status_code=400, detail="Username is already registered")
    if any(account["email"] == normalized_email for account in accounts.values()):
        raise HTTPException(status_code=400, detail="Email is already registered")

    accounts[normalized_username] = {
        "username": normalized_username,
        "full_name": request_data.full_name.strip(),
        "email": normalized_email,
        "date_of_birth": request_data.date_of_birth.isoformat(),
        "role": request_data.role,
        "password_hash": hash_password(request_data.password),
    }
    return account_view(accounts[normalized_username])


@app.post("/auth/login")
def login(request_data: LoginRequest, response: Response):
    account = accounts.get(request_data.username.strip().lower())
    if not account or not password_matches(request_data.password, account["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_urlsafe(32)
    sessions[token] = account["username"]
    response.set_cookie(
        "session_token",
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 8,
    )
    return account_view(account)


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    sessions.pop(token, None)
    response.delete_cookie("session_token")


@app.get("/auth/me")
def current_user(request: Request):
    return account_view(get_current_account(request))


@app.post("/auth/password")
def change_password(request_data: PasswordChangeRequest, request: Request):
    account = get_current_account(request)
    if not password_matches(request_data.current_password, account["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    account["password_hash"] = hash_password(request_data.new_password)
    return {"message": "Password changed successfully"}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, request: Request):
    """Sign up a student for an activity"""
    account = get_current_account(request)
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if account["email"] in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(account["email"])
    return {"message": f"Signed up {account['email']} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, request: Request):
    """Unregister a student from an activity"""
    account = get_current_account(request)
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if account["email"] not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(account["email"])
    return {"message": f"Unregistered {account['email']} from {activity_name}"}
