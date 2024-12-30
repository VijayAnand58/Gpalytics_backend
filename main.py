from fastapi import FastAPI, HTTPException, Request,Query,Depends
from pydantic import BaseModel
from typing import Optional, List
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
    register
)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Explicitly define allowed origins for CORS
allowed_origins = [
    "http://localhost:3000",  # Local development
    "https://gpalytics.vercel.app",  # Production frontend
]

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Explicitly list allowed origins
    allow_credentials=True,  # Allow cookies and credentials
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Add session middleware with secure attributes
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", secrets.token_hex(16)),
    same_site="None",  # Required for cross-origin cookies
    https_only=True,  # Ensure cookies are sent only over HTTPS
    max_age=2700
)

class UserDetails(BaseModel):
    name: str
    regno: str
    password: str

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

class Login(BaseModel):
    regno: str
    password: str

@app.post("/login")
async def login(user: Login, request: Request):
    result = check(user.regno, user.password)
    if result == "no user exists":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if result == "wrong password":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if result == "error":
        raise HTTPException(status_code=500,detail="Internal server error")
    if result == "success":
        response = {"message": "Login successful", "username": user.regno}
        # Manually set cookies with secure attributes
        request.session["username"] = user.regno
        return response
    
    
@app.get("/protected/get-sem-details") 
async def get_user_details(request: Request, sem: Optional[int] = Query(None)): 
    username = request.session.get("username") 
    if not username: 
        raise HTTPException(status_code=401, detail="Not logged in") 
    if sem is not None: 
        result = get_all_marks(username, sem) 
    else: 
        result = get_all_marks(username) 
    if result == "error": 
        raise HTTPException(status_code=500, detail="Internal server error") 
    if result == "No data": 
        raise HTTPException(status_code=401, detail="invalid credentials") 
    return result

#temp code for backwards compatiblity
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
# temp code ends

class CourseDetails(BaseModel): 
    course_name: str 
    course_code: str 
    course_credit: int 
    grade: str

class CGPAdetails(BaseModel):
    cgpa: List[CourseDetails]
    semester: int

@app.post("/protected/cgpa")
async def store_cgpa(request: Request, userdata: CGPAdetails):
    username = request.session.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Unauthorized access: Please log in")
    try:
        possible_grades = ["O", "A+", "A", "B+", "B", "C", "F"]
        for details in userdata.cgpa:
            # if not all(key in details for key in ["course_name", "course_code", "course_credit", "grade"]):
            #     raise HTTPException(status_code=400, detail="Invalid CGPA details")
            if details.grade not in possible_grades:
                raise HTTPException(status_code=400, detail="Invalid grade provided")
        cgpa_dicts = [course.model_dump() for course in userdata.cgpa]
        result_add_cgpa=addcgpa(username, cgpa_dicts, userdata.semester)
        result_assign_mark=assaign_marks(username, userdata.semester)
        result_assign_cgpa=assaign_cgpa(username)
        if result_add_cgpa=="error" or result_assign_cgpa=="error" or result_assign_mark=="error":
            raise HTTPException(status_code=500,detail="internal server error")
        return {"message": "CGPA details added successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

class GetPercent:
    def __init__(self,sem: int =Query(...,description="Semester info is required")):
        self.sem=sem

@app.get("/protected/get-percentile")
async def get_percentile_func(request: Request, data: GetPercent=Depends()):
    username = request.session.get('username')
    if username:
        if data.sem:
            result = get_percentile(username, data.sem)
            if result == "error":
                raise HTTPException(status_code=402, detail="invalid semester details")
            else:
                return {"percentile": result}
    else:
        raise HTTPException(status_code=401, detail="Unauthorized access, did not login with username")

class GetMinMax:
    def __init__(self,sem: int =Query(...,description="Semester info is required")):
        self.sem=sem

@app.get("/protected/get_min_max")
def min_max(request: Request, data: GetMinMax=Depends()):
    username = request.session.get("username")
    if username:
        result = get_max_and_min_gpa(data.sem)
        if result == "error":
            raise HTTPException(
                status_code=500, detail="internal server error"
            )
        else:
            return result
    else:
        raise HTTPException(
            status_code=401, detail="Unauthorized access, did not login with username"
        )

@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logout successful"}

@app.middleware("http") 
async def update_session_timeout(request: Request, call_next): 
    response = await call_next(request) 
    if "session" in request.session: 
        response.set_cookie("session", request.cookies["session"], max_age=2700) 
    return response