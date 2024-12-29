from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import secrets
from project import (
    insert,
    check,
    addcgpa,
    get_all_marks,
    assaign_marks,
    assaign_cgpa,
    get_percentile,
    get_max_and_min_gpa,
    register,
)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Use origins from .env
    allow_credentials=True,  # Enable credentials (cookies, headers)
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Session middleware for secure cookies
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", secrets.token_hex(16)),  # Secure key from .env
    session_cookie_secure=True,  # Cookies sent only over HTTPS
    session_cookie_samesite="None",  # Required for cross-origin requests with credentials
)

# Models
class UserDetails(BaseModel):
    name: str
    regno: str
    password: str


class Login(BaseModel):
    regno: str
    password: str


class CGPAdetails(BaseModel):
    cgpa: list
    semester: int


# Endpoints
@app.post("/register/user")
async def create_user(user: UserDetails):
    try:
        value = insert(user.name, user.regno, user.password)
        if value == "Already exists":
            raise HTTPException(status_code=409, detail="Conflict: User already exists")
        if value == "Wrong register number":
            raise HTTPException(status_code=400, detail="Invalid Register Number Format")
        return {"message": "Registration successful"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@app.post("/login")
async def login(user: Login, request: Request):
    result = check(user.regno, user.password)
    if result == "no user exists":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if result == "wrong password":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    request.session["username"] = user.regno
    return {"message": "Login successful", "username": user.regno}


@app.get("/protected/get-details")
async def get_user_details(request: Request):
    username = request.session.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Not logged in")
    user_data = register.find_one({"regno": username}, {"_id": 0, "password": 0})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    user_data["profilePicture"] = user_data.get("profilePicture", "https://i.pravatar.cc/150")
    return user_data


@app.post("/protected/cgpa")
async def store_cgpa(request: Request, userdata: CGPAdetails):
    username = request.session.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Unauthorized access: Please log in")
    try:
        possible_grades = ["O", "A+", "A", "B+", "B", "C", "F"]
        for details in userdata.cgpa:
            if not all(key in details for key in ["course_name", "course_code", "course_credit", "grade"]):
                raise HTTPException(status_code=400, detail="Invalid CGPA details")
            if details["grade"] not in possible_grades:
                raise HTTPException(status_code=400, detail="Invalid grade provided")
        addcgpa(username, userdata.cgpa, userdata.semester)
        assaign_marks(username, userdata.semester)
        assaign_cgpa(username)
        return {"message": "CGPA details added successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logout successful"}
