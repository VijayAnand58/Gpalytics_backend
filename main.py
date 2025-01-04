from fastapi import FastAPI, HTTPException, Request,Query,Depends,File,UploadFile
from pydantic import BaseModel
from typing import Optional, List
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import secrets
from project import (
    insert,check,addcgpa,get_all_marks,assaign_marks,assaign_cgpa,get_percentile,
    get_max_and_min_gpa,get_max_and_min_gpa_local,get_prediction_next_sem,get_full_user_details
)
from gemini import sharpen_image,process_result_card
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
    batch:int

# Endpoints
@app.post("/register/user")
async def create_user(user: UserDetails):
    try:
        value = insert(user.name, user.regno, user.password,user.batch)
        if value == "Already exists":
            raise HTTPException(status_code=409, detail="Conflict: User already exists")
        if value == "Wrong register number":
            raise HTTPException(status_code=400, detail="Invalid Register Number Format")
        if value == "wrong batch year":
            raise HTTPException(status_code=400, detail="Invalid batch year")
        if value=="Password doesnt have any digits":
            raise HTTPException(status_code=400,detail="Password doesnt have any digits")
        if value=="Password doesnt have any uppercase":
            raise HTTPException(status_code=400,detail="Password doesnt have any uppercase")
        if value=="Password doesnt have at least one special character":
            raise HTTPException(status_code=400,detail="Password doesnt have at least one special character")
        if value=="Password less than 8 characters":
            raise HTTPException(status_code=400,detail="Password less than 8 characters")
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
    if result =="None document return":
        raise HTTPException(status_code=404, detail="No document exist for that particular semester") 
    return result


@app.get("/protected/get-details")
async def get_user_details(request: Request):
    username = request.session.get("username")
    if username:
        result=get_full_user_details(username)
        if result =="error":
            raise HTTPException(status_code=500,detail="Internal server error")
        else:
            return result
    else:
        raise HTTPException(status_code=401, detail="Unauthorized access: Please log in")


class CourseDetails(BaseModel): 
    course_name: str 
    course_code: str 
    course_credit: int 
    grade: str

class CGPAdetails(BaseModel):
    cgpa: List[CourseDetails]
    semester: int

# local function
def store_cgpa_local(username,userdata:CGPAdetails):
    try:
        possible_grades = ["O", "A+", "A", "B+", "B", "C", "F"]
        for details in userdata.cgpa:
            if details.grade not in possible_grades:
                return "Invalid grade provided"
        cgpa_dicts = [course.model_dump() for course in userdata.cgpa]
        result_add_cgpa=addcgpa(username, cgpa_dicts, userdata.semester)
        result_assign_mark=assaign_marks(username, userdata.semester)
        result_assign_cgpa=assaign_cgpa(username)
        if result_add_cgpa=="error" or result_assign_cgpa=="error" or result_assign_mark=="error":
            return "internal server error"
        return "CGPA details added successfully"
    except Exception as e:
        print("error in local store gpa method",e)
        return "internal server error"

@app.post("/protected/cgpa")
async def store_cgpa(request: Request, userdata: CGPAdetails):
    username = request.session.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Unauthorized access: Please log in")
    try:
        possible_grades = ["O", "A+", "A", "B+", "B", "C", "F"]
        for details in userdata.cgpa:
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
            if result =="Database not populated":
                raise HTTPException(status_code=503,detail="Database isnt populated enough to find percentile, wait for some time")
            else:
                return {"percentile": result}
    else:
        raise HTTPException(status_code=401, detail="Unauthorized access, did not login with username")

class GetMinMax:
    def __init__(self,sem: int =Query(...,description="Semester info is required")):
        self.sem=sem

@app.get("/protected/get-min-max")
def min_max(request: Request, data: GetMinMax=Depends()):
    username = request.session.get("username")
    if username:
        result = get_max_and_min_gpa(username,data.sem)
        if result == "error":
            raise HTTPException(status_code=500, detail="internal server error")
        if result == "Database not populated":
            raise HTTPException(status_code=503,detail="Database isnt populated enough to find min max, wait for some time")
        else:
            return result
    else:
        raise HTTPException(status_code=401, detail="Unauthorized access, did not login with username")

@app.get("/protected/get-local-min-max")
def local_min_max(request:Request,data: GetMinMax=Depends()):
    username=request.session.get("username")
    if username:
        result=get_max_and_min_gpa_local(username,data.sem)
        if result=="No person exists, or no record exists":
            raise HTTPException(status_code=204,detail="No person exists, or no record exists")
        if result=="some internal error":
            raise HTTPException(status_code=500,detail="internal server error")
        else:
            return result
    else:
        raise HTTPException(status_code=401, detail="Unauthorized access, did not login with username")

@app.get("/protected/predict-next-sem")
async def predict_next_sem(request:Request):
    username=request.session.get("username")
    if username:
        result=get_prediction_next_sem(username)
        if result=="error in data collection":
            raise HTTPException(status_code=404,detail="The user document doesnt exist")
        elif result=="Error, insufficient data to predict next semester prediction":
            raise HTTPException(status_code=422,detail="Error, insufficient data present, there needs to be atleast 3 semester entries in the databse to perform the process")
        elif result=="Maximum semesters reached, cant calculate for unavailable semester":
            raise HTTPException(status_code=403, detail="you have reached semester 8, there are no semester ahead of this to calculate")
        elif result=="Error, person records doesnt contain info from from firstsem, till date":
            raise HTTPException(status_code=403,detail="Need all the info from first semester to current semester")
        elif result=="error":
            raise HTTPException(status_code=500,detail="Interanl server error")
        else:
            return {"Predicted GPA of next semester":result}
    else:
        raise HTTPException(status_code=401, detail="Unauthorized access, did not login with username")

@app.post("/protected/upload-image")
async def upload_image(request:Request,file: UploadFile=File(...)):
    username=request.session.get("username")
    if username:
        image_data= await file.read()
        sharpened_image_data = sharpen_image(image_data)
        if sharpened_image_data =="error":
            raise HTTPException(status_code=500, detail="Internal server error, error in image sharpening")   
        result = await process_result_card(sharpened_image_data, "AIzaSyCfgJjB605M7J9PcPwWjSzMr2P3KY_43JY")
        if result=="error":
            raise HTTPException(status_code=500,detail="Internal server error, error in gemini api result")
        if result=={"message": "error"}:
            raise HTTPException(status_code=400,detail="Wrong image sent, please give correct image format")
        else:
            try:
                recv_data=CGPAdetails(**result)
                response=store_cgpa_local(username,recv_data)
                if response=="CGPA details added successfully":
                    return {"message":"CGPA details added successfully","sem":result["semester"]}
                if response == "internal server error":
                    raise HTTPException(status_code=500,detail="Internal server error")
                if response =="Invalid grade provided":
                    raise HTTPException(status_code=500, detail="Grade is incorrect")
            except Exception as e:
                print("data validation error in upload image method",e)
                raise HTTPException(status_code=500,detail="data validation error")

    else:
        raise HTTPException(status_code=401, detail="Unauthorized access, did not login with username")        

@app.post("/logout")
async def logout(request: Request):
    username = request.session.get("username")
    if username is None:
        raise HTTPException(status_code=401, detail="Unauthorized access, did not login with username")
    request.session.clear()
    return {"message": "Logout successful", "User who logged out was": username}

@app.middleware("http") 
async def update_session_timeout(request: Request, call_next): 
    response = await call_next(request) 
    if "session" in request.session: 
        response.set_cookie("session", request.cookies["session"], max_age=2700) 
    return response