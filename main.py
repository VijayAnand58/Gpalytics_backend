from fastapi import FastAPI, HTTPException, Request,Depends,Form
from pydantic import BaseModel
from project import insert,check,addcgpa,get_all_marks,assaign_marks,assaign_cgpa,get_percentile
from typing import Dict
from starlette.middleware.sessions import SessionMiddleware
import secrets
app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(16))

class UserDetails(BaseModel):
    name: str
    regno: str
    password: str

@app.post("/register/user")
async def create_user(user: UserDetails):
    try:
        value=insert(user.name, user.regno, user.password)
        if value =="Already exists":
            raise HTTPException(status_code=409,detail="conflict, message exists")
        
        if value =="Wrong register number":
            raise HTTPException(status_code=401,detail="Invalid Format")
        else:
            return {"message": "Successful"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred: {str(e)}"
        )

class Login(BaseModel):
    regno:str
    password:str
    
@app.post("/login")
async def login(user:Login,request:Request):
    result=check(user.regno,user.password)
    if result=="no user exists":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if result=="wrong password":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    else:
        request.session["username"]=user.regno
        return {"message":"successful login","username":user.regno}

class CGPAdetails(BaseModel):
    cgpa:list
    semester:int

@app.post('/protected/cgpa')
async def StoreCgpa(request:Request,userdata:CGPAdetails):
    username=request.session.get('username')
    if username:
        try:
            possible=["O","A+","A","B+","B","C","F"]
            for details in userdata.cgpa:
                temp=details.keys()
                if "course_name" not in temp or "course_code" not in temp or "course_credit" not in temp or "grade" not in temp:
                    raise HTTPException(status_code=401, detail="Invalid credentials") #TODO change the message given to the application
                if details['grade'] in possible:
                    pass
                else:
                    raise HTTPException(status_code=401, detail="Invalid credentials, grades not proper")
            addcgpa(username,userdata.cgpa,userdata.semester)
            assaign_marks(username,userdata.semester)
            assaign_cgpa(username)
            return {"message":"succesfully added"}

        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"An error occurred: {str(e)}"
            )
    else:
        raise HTTPException(status_code=401,detail="unauthorized access")

@app.get('/protected/get-details')
async def get_details(request:Request):
    username=request.session.get('username')
    if username:
        result=get_all_marks(username)
        print(result)
        return result
    else:
        raise HTTPException(status_code=401,detail="unauthorized access")
class get_percent(BaseModel):
    sem:int

@app.get("/protected/get-percentile")
async def get_percentile_func(request:Request,data:get_percent):
    username=request.session.get('username')
    if username:
        if data.sem:
            result=get_percentile(username,data.sem)
            if result=="error":
                raise HTTPException(status_code=402,detail="invalid semester details")
            else:
                return{"percentile":result}
    else:
        raise HTTPException(status_code=401,detail="Unauthorized access, did not login with username")

@app.post('/logout')
async def logout(request: Request): 
    request.session.clear() 
    return {"message": "Logged out successfully"}
