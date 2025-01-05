from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os
import bcrypt
from datetime import datetime
from models import predict_grades
import random
import greets
# Load environment variables
load_dotenv()

# MongoDB connection string from .env
mongo_url = os.getenv("MONGO_DB_URL")
client = MongoClient(mongo_url, server_api=ServerApi('1'))

# Database setup
try:
    client.admin.command('ping')
    print("Pinged your deployment. Successfully connected to MongoDB!")
except Exception as e:
    print("Error connecting to MongoDB:", e)

db = client.gpalyticsdb
register = db.register

cgpa_details = {"O": 10, "A+": 9, "A": 8, "B+": 7, "B": 6, "C": 5, "F": 0}

def hash_password(plain_password):  
    salt = bcrypt.gensalt() 
    hashed_password = bcrypt.hashpw(plain_password.encode('utf-8'), salt) 
    return hashed_password

def check_password(plain_password, hashed_password): 
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)

# a gloabl variable called list_of_year to check the whether the year is in the correct range
current_year=datetime.now().year
list_of_years=list(range(2015,current_year+1))

def insert(name: str, regno: str, password: str, batch:int):
    if register.find_one({"regno": regno}):
        return "Already exists"
    if len(regno) != 15 or not regno[:2].isalpha() or any(c.islower() for c in regno[:2])or not(regno[2:].isdigit()):
        return "Wrong register number"
    if len(password)<8:
        return "Password less than 8 characters"
    if not(any(k.isupper() for k in password)):
        return "Password doesnt have any uppercase"
    if not(any(k.isdigit() for k in password)):
        return "Password doesnt have any digits"
    if not(any( not(k.isalnum()) for k in password)):
        return "Password doesnt have at least one special character"
    global list_of_years
    if batch not in list_of_years:
        return "wrong batch year"
    try:
        hashedpassword=hash_password(password)
        register.insert_one({"name": name, "regno": regno, "password": hashedpassword,"batch_year": batch})
    except Exception as e:
        print("Error inserting data:", e)


def check(regno: str, password: str):
    user = register.find_one({"regno": regno})
    if not user:
        return "no user exists"
    try:
        if check_password(password,user["password"]):
            return "success"
        else:
            return "wrong password"
    except Exception as e:
        print("Error in password checking function and the error is ",e)
        return "error"
        
def addcgpa(regno,cgpadetails,semeseter):
    try:
        document = register.find_one({"regno": regno, "gpa-details.semester": semeseter})
        if document:
            result=register.update_one(
                {"regno":regno,"gpa-details.semester":semeseter},
                {"$set":{"gpa-details.$.grades":cgpadetails}}) 
        else:       
            result=register.update_one(
            {"regno": regno},
            {"$push": {"gpa-details": {"semester": semeseter, "grades": cgpadetails,"gpa":0,"credits_sem":0}}})
    except Exception as e:
        print("Some error while updating",e)
        return "error"

def get_all_marks(regno:str,semester=None):
    try:
        if semester==None:
            document=register.find_one({"regno":regno},{"_id":0})
            if document is not None:
                if document["cgpa_of_sem"]:
                    data1={"all result":document['gpa-details'],"CGPA":document["cgpa_of_sem"]}
                    data1["all result"] = sorted(data1["all result"], key=lambda x: x["semester"])
                    return data1
                else:
                    return document['gpa-details']
            else:
                return "None document return"
        else:
            document=register.find_one({"regno":regno,"gpa-details.semester": semester},{"_id": 0, "gpa-details.$": 1})
            if document is not None:
                random_num=random.randint(1,6)
                greet_msg=None
                gpa_value = document["gpa-details"][0]["gpa"]
                if gpa_value==10:
                    greet_msg=greets.greet_10[random_num]
                elif gpa_value<10 and gpa_value>=9:
                    greet_msg=greets.greet_9_9_to_9[random_num]
                elif gpa_value<9 and gpa_value>=8:
                    greet_msg=greets.greet_8_9_to_8[random_num]
                elif gpa_value<8 and gpa_value>=7:
                    greet_msg=greets.greet_7_9_to_7[random_num]
                elif gpa_value<7 and gpa_value>=6:
                    greet_msg=greets.greet_6_9_to_6[random_num]
                elif gpa_value<6 and gpa_value>=5:
                    greet_msg=greets.greet_5_9_to_5[random_num]
                elif gpa_value<5 and gpa_value>=0:
                    greet_msg=greets.greet_less_than_5[random_num]
                document["greet_msg"]=document.get("greet_msg",greet_msg)
                return document
            else:
                return "None document return"  
    except Exception as e:
        print("Error while accessing",e)
        return "error"

def get_full_user_details(regno:str):
    try:
        document=register.find_one({"regno": regno}, {"_id": 0,"name":1,"regno":1})
        if document:
            document["profilePicture"] = document.get("profilePicture", "https://i.pravatar.cc/150")
            return document
        else:
            return "error"
    except Exception as e:
        print("Error in get user details function",e)
        return "error"

def assaign_marks(regno:str,semester:int):
    try:
        grade_sub=[]
        total_credits=[]
        document=register.find_one({"regno":regno,"gpa-details.semester": semester},{"_id": 0, "gpa-details.$": 1})
        for details in document['gpa-details']:
            for course in details['grades']:
                grade_sub.append([course['grade'],course['course_credit']])
                total_credits.append(course["course_credit"])
        sum1=0
        for items in grade_sub:
            value=cgpa_details[items[0]]
            inter=value*items[1]
            sum1+=inter
        gpa=sum1/sum(total_credits)
        result=register.update_one(
                {"regno":regno,"gpa-details.semester":semester},
                {"$set":{"gpa-details.$.gpa":round(gpa,2),"gpa-details.$.credits_sem":sum(total_credits)}}) 
        print("GPA updated successfully")      
    except Exception as e:
        print("Error while accessing",e)
        return "error"
def assaign_cgpa(regno:str):
    try:
        document=register.find_one({'regno':regno})
        all_gpas=[]
        all_credits=[]
        if document:
            for sem in document["gpa-details"]:
                all_gpas.append(sem['gpa'])
                all_credits.append(sem["credits_sem"])
            cgpa=(sum(all_gpas)/len(all_gpas))
            register.update_one({'regno':regno},{"$set":{"cgpa_of_sem":round(cgpa,2),"total_credits":sum(all_credits)}})
            print("succesfully added cgpa which was",cgpa)
            print("succesfully added credits which was",sum(all_credits))
        else:
            print("fatal error")
            return "error"
        
    except Exception as e:
        print("error occured ",e)
        return "error"

def get_percentile(regno:str,semseter:int):
    li=[]
    global list_of_years
    try:
        checkbatch=register.find_one({"regno":regno,"batch_year":{"$exists": True}},{"batch_year":1,"_id":0})
        batch=checkbatch.get("batch_year")
    except Exception as e:
        print("Error in get percentile while checking for batch",e)
        return "error"
    if batch  not in list_of_years:
        return "error"
    for doc in register.find({"gpa-details":{"$exists": True},"batch_year":{"$exists": True,"$eq":batch}}):
        for inst in doc['gpa-details']:
            if (inst['semester']==semseter):
                li.append(inst['gpa'])
    if(len(li)==0):
        return "error"
    if(len(li)==1):
        return "Database not populated"
    
    def find_percentile(value, list1): 
        sorted_values = sorted(list1)  
        rank = sorted_values.index(value) + 1 
        percentile = ((rank - 1) / (len(list1) - 1)) * 100 
        return percentile
    
    try:
        document=register.find_one({"regno":regno,"gpa-details":{"$exists": True}})
        found=False
        if document:
            for details in document['gpa-details']:
                if details['semester']==semseter:
                    found=True
                    gpa_inst=details['gpa']
            if found:
                print(gpa_inst)
                return find_percentile(gpa_inst,li)
            else:
                print("error while finding percentile")
                return "error"
        else:
            print("document doesnt  exist")
            return 'error'
    except Exception as e:
        print("error in percentile function , error is : ",e)
        return 'error'

def get_max_and_min_gpa(regno:str,semester:int):
    li=[]
    global list_of_years
    try:
        checkbatch=register.find_one({"regno":regno,"batch_year":{"$exists": True}},{"batch_year":1,"_id":0})
        batch=checkbatch.get("batch_year")
    except Exception as e:
        print("Error in get percentile while checking for batch",e)
        return "error"
    if batch  not in list_of_years:
        return "error"
    for doc in register.find({"gpa-details":{"$exists": True},"batch_year":{"$exists": True,"$eq":batch}}):
        for inst in doc['gpa-details']:
            if (inst['semester']==semester):
                li.append(inst['gpa'])
    if (len(li)==0):
        return "error"
    if(len(li)==1):
        return "Database not populated"
    else:
        maxgpa=max(li)
        mingpa=min(li)
        return {"Max_GPA":maxgpa,"Min_GPA":mingpa}
    
def get_max_and_min_gpa_local(regno,sem):
    try:
        document=register.find_one({"regno":regno,"gpa-details":{"$exists": True},"gpa-details.semester":sem})
        if document:
            #max min with respect to absolute grade
            maxgrade_list=[]
            for detail in document["gpa-details"]:
                if detail["semester"]==sem:
                    for records in detail["grades"]:
                        maxgrade_list.append(cgpa_details[records["grade"]])
            maxgrade_num=max(maxgrade_list)
            mingrade_num=min(maxgrade_list)
            maxgrade=None
            mingrade=None
            for key,value in cgpa_details.items():
                if value==maxgrade_num:
                    maxgrade=key
                if value==mingrade_num:
                    mingrade=key
            subjects_with_max_grade=[]
            subjects_with_min_grade=[]
            for detail in document["gpa-details"]:
                if detail["semester"]==sem:
                    for records in detail["grades"]:
                        if records["grade"]==maxgrade:
                            subjects_with_max_grade.append([records["course_name"],records["course_code"]])
                        if records["grade"]==mingrade:
                            subjects_with_min_grade.append([records["course_name"],records["course_code"]])
            # max min with respect to the credit points too
            subject_dict={}
            for detail in document["gpa-details"]:
                if detail["semester"]==sem:
                    for records in detail["grades"]:
                        subject_dict[records["course_name"]]=records["course_credit"]*cgpa_details[records["grade"]]
            min_points=min(subject_dict.values())
            max_points=max(subject_dict.values())
            maxpoint_list=[]
            minpoint_list=[]
            for key,values in subject_dict.items():
                if values==max_points:
                    maxpoint_list.append(key)
                if values==min_points:
                    minpoint_list.append(key)
            result_dict={"absolute_result":
            {"max_grade":{"subject":subjects_with_max_grade,"grade":maxgrade},
            "min_grade":{"subject":subjects_with_min_grade,"grade":mingrade}},
            "points_result":
            {"maxpoints":{"subject":maxpoint_list,"points":max_points},
            "minpoints":{"subject":minpoint_list,"points":min_points}}}
            return result_dict
        else:
            return "No person exists, or no record exists"

    except Exception as e:
        print("Error in local min max funtion with exception as ",e)
        return "some internal error"
def get_prediction_next_sem(regno):
    try:
        document=register.find_one({"regno":regno,"gpa-details":{"$exists": True}},{"_id":0,"gpa-details":1})
        if document:
            attended_sem_list=[]
            for details in document["gpa-details"]:
                attended_sem_list.append(details["semester"])
            if len(attended_sem_list)<3:
                return "Error, insufficient data to predict next semester prediction"
            if len(attended_sem_list)==8:
                return "Maximum semesters reached, cant calculate for unavailable semester"
            maxsem=max(attended_sem_list)
            sorted_attended_sem_list=sorted(attended_sem_list)
            if sorted_attended_sem_list != list(range(1,maxsem+1)):
                return "Error, person records doesnt contain info from from firstsem, till date"
            else:
                sorted_sem_grades=[]
                sorted_sem_credits=[]
                for sem in sorted_attended_sem_list:
                    for details in document["gpa-details"]:
                        if details["semester"]==sem:
                            sorted_sem_grades.append(details['gpa'])
                            sorted_sem_credits.append(details['credits_sem'])
                result=predict_grades(sorted_attended_sem_list,sorted_sem_grades)
                return result
        else:
            return "error in data collection"
    except Exception as e:
        print(e)
        return "error"

# def get_most_difficult_subject(regno:str):
#     try:
#         document=register.find_one({"regno":regno,"batch_year":{"$exists": True}},{"_id":0,"batch_year":1})
#         batch=document.get("batch_year")
#     except Exception as e:
#         print("Error in get most difficult subject while checking for batch",e)
#         return "error"
def get_top_10_records(data:dict):
    items=list(data.items())
    top_10=items[:10]
    return dict(top_10)

def list_of_people(regno:str,sem:int):
    try:
        batch_document=register.find_one({"regno":regno,"batch_year":{"$exists": True}},{"_id":0,"batch_year":1})
        batch=batch_document.get("batch_year")
        document=register.find({"gpa-details":{"$exists": True},"batch_year":{"$exists": True,"$eq":batch}},{"_id":0,"password":0})
        masterdoc={}
        if document is not None:
            for details in document:
                for semdetails in details["gpa-details"]:
                    if semdetails["semester"]==sem:
                        masterdoc[details["regno"]]=[details["name"],semdetails["gpa"]]
            if len(masterdoc)==0:
                return "None document return"
            sorted_masterdoc = dict(sorted(masterdoc.items(), key=lambda item: item[1][1]))
            return get_top_10_records(sorted_masterdoc)
        else:
            return "None document return"
    except Exception as e:
        print("Error in list of people function",e)
        return "error"

def list_of_people_cgpa(regno):
    try:
        batch_document=register.find_one({"regno":regno,"batch_year":{"$exists": True}},{"_id":0,"batch_year":1})
        batch=batch_document.get("batch_year")
        document=register.find({"gpa-details":{"$exists": True},"batch_year":{"$exists": True,"$eq":batch},"total_credits":{"$exists":True}},{"_id":0,"password":0,"gpa-details":0,"batch_year":0})
        masterdoc={}
        if document is not None:
            for details in document:
                masterdoc[details["regno"]]=[details["name"],details["total_credits"],details["cgpa_of_sem"]]
            sorted_masterdoc = dict(sorted(masterdoc.items(), key=lambda item: item[1][2]))
            return get_top_10_records(sorted_masterdoc)
        else:
            return "None document return"
    except Exception as e:
        print("Error in list of people cgpa method",e)
        return "error"