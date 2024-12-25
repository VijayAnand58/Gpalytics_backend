from fastapi import FastAPI, HTTPException, Request, Depends, Form
from pydantic import BaseModel
from project import (
    insert,
    check,
    addcgpa,
    get_all_marks,
    assaign_marks,
    assaign_cgpa,
    get_percentile,
    get_max_and_min_gpa,
)
from starlette.middleware.sessions import SessionMiddleware
import secrets
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(16))

# User Details model for registration
class UserDetails(BaseModel):
    name: str
    regno: str
    password: str

# Endpoint for user registration
@app.post("/register/user")
async def create_user(user: UserDetails):
    try:
        value = insert(user.name, user.regno, user.password)
        if value == "Already exists":
            raise HTTPException(status_code=409, detail="Conflict: User already exists")
        
        if value == "Wrong register number":
            raise HTTPException(status_code=401, detail="Invalid Register Number Format")
        else:
            return {"message": "Successful"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred: {str(e)}"
        )

# Login details model
class Login(BaseModel):
    regno: str
    password: str

# Endpoint for user login
@app.post("/login")
async def login(user: Login, request: Request):
    result = check(user.regno, user.password)
    if result == "no user exists":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if result == "wrong password":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    else:
        request.session["username"] = user.regno
        return {"message": "Successful login", "username": user.regno}

# CGPA details model for storing CGPA
class CGPAdetails(BaseModel):
    cgpa: list
    semester: int

# Endpoint to store CGPA details
@app.post("/protected/cgpa")
async def store_cgpa(request: Request, userdata: CGPAdetails):
    username = request.session.get("username")
    if username:
        try:
            possible = ["O", "A+", "A", "B+", "B", "C", "F"]
            for details in userdata.cgpa:
                temp = details.keys()
                if "course_name" not in temp or "course_code" not in temp or "course_credit" not in temp or "grade" not in temp:
                    raise HTTPException(status_code=401, detail="Invalid CGPA Details")
                
                if details["grade"] in possible:
                    continue
                else:
                    raise HTTPException(status_code=401, detail="Invalid grade provided")

            # Perform operations to store CGPA details
            addcgpa(username, userdata.cgpa, userdata.semester)
            assaign_marks(username, userdata.semester)
            assaign_cgpa(username)
            return {"message": "Successfully added"}
        
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"An error occurred: {str(e)}"
            )
    else:
        raise HTTPException(status_code=401, detail="Unauthorized access: Please log in")
