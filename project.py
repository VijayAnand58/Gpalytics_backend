from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os

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


def insert(name: str, regno: str, password: str):
    if register.find_one({"regno": regno}):
        return "Already exists"
    if len(regno) != 15 or not regno[:2].isalpha():
        return "Wrong register number"
    try:
        register.insert_one({"name": name, "regno": regno, "password": password})
    except Exception as e:
        print("Error inserting data:", e)


def check(regno: str, password: str):
    user = register.find_one({"regno": regno})
    if not user:
        return "no user exists"
    if user["password"] == password:
        return "success"
    return "wrong password"
        
def addcgpa(regno,cgpadetails,semeseter):
    try:
        document = register.find_one({"regno": regno, "gpa-details.semester": semeseter})
        if document:
            result=register.update_one(
                {"regno":regno,"gpa-details.semester":semeseter},
                {"$set":{"gpa-details.$.grades":cgpadetails}}) 
            print("succesfully updated",semeseter,"marks")
        else:       
            result=register.update_one(
            {"regno": regno},
            {"$push": {"gpa-details": {"semester": semeseter, "grades": cgpadetails,"gpa":0}}})
            print(result)
    except Exception as e:
        print("Some error while updating",e)

def get_all_marks(regno,semester=None):
    try:
        if semester==None:
            document=register.find_one({"regno":regno},{"_id":0})
            print(document['gpa-details'])
            if document["cgpa_of_sem"]:
                return {"all result":document['gpa-details'],"CGPA":document["cgpa_of_sem"]}
            else:
                return document['gpa-details']
        else:
            document=register.find_one({"regno":regno,"gpa-details.semester": semester},{"_id": 0, "gpa-details.$": 1})
            print(document)
            return document    

    except Exception as e:
        print("Error while accessing")


def assaign_marks(regno,semester):
    try:
        grade_sub=[]
        total_credits=[]
        document=register.find_one({"regno":regno,"gpa-details.semester": semester},{"_id": 0, "gpa-details.$": 1})
        print(document)
        for details in document['gpa-details']:
            for course in details['grades']:
                # grades_list.append(course['grade'])
                # total_credits.append(course['course_credit'])
                grade_sub.append([course['grade'],course['course_credit']])
                total_credits.append(course["course_credit"])
        print(grade_sub)
        sum1=0
        for items in grade_sub:
            value=cgpa_details[items[0]]
            inter=value*items[1]
            sum1+=inter
        gpa=sum1/sum(total_credits)
        print("gpa  {:.2f}".format(gpa))
        # for details in document['gpa-details']:
        #     if details['semester']==semester:
        #         details["cgpa"]=gpa
        # print(document)
        result=register.update_one(
                {"regno":regno,"gpa-details.semester":semester},
                {"$set":{"gpa-details.$.gpa":gpa}}) 
        print("GPA updated successfully")
        # ,"gpa-details.semester":semester        
    except Exception as e:
        print("Error while accessing",e)


def assaign_cgpa(regno):
    try:
        document=register.find_one({'regno':regno})
        all_gpas=[]
        if document:
            for sem in document["gpa-details"]:
                all_gpas.append(sem['gpa'])
            cgpa=(sum(all_gpas)/len(all_gpas))
            register.update_one({'regno':regno},{"$set":{"cgpa_of_sem":cgpa}})
            print("succesfully added cgpa which was",cgpa)
        else:
            print("fatal error")
        
    except Exception as e:
        print("error occured ",e)
def get_percentile(regno,semseter):
    li=[]
    for doc in register.find():
        for inst in doc['gpa-details']:
            if (inst['semester']==semseter):
                li.append(inst['gpa'])
    if(len(li)==0):
        return "error"
    def find_percentile(value, list1): 
        sorted_values = sorted(list1)  
        rank = sorted_values.index(value) + 1 
        percentile = ((rank - 1) / (len(list1) - 1)) * 100 
        return percentile
    try:
        document=register.find_one({"regno":regno})
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

def get_max_and_min_gpa(semester):
    li=[]
    for doc in register.find():
        for inst in doc['gpa-details']:
            if (inst['semester']==semester):
                li.append(inst['gpa'])
    if (len(li)==0):
        return "error"
    else:
        maxgpa=max(li)
        mingpa=min(li)
        return {"Max_GPA":maxgpa,"Min_GPA":mingpa}
