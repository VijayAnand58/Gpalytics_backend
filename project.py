from pymongo  import MongoClient

client= MongoClient("localhost",27017)

db=client.gpalyticsdb
register=db.register

cgpa_details={"O":10,"A+":9,"A":8,"B+":7,"B":6,"C":5,"F":0}

# register.insert_one({"name":"mike","age":30})
def insert(name:str,regno:str,password:str):
    if register.find_one({"regno":regno}):
        print("Already exists")
        return "Already exists"
    if len(regno) != 15 or not(regno[0:2].isalpha()):
        return "Wrong register number"
    else:
        try:
            register.insert_one({"name":name,"regno":regno,"password":password})
        except Exception as e:
            print("some error")
def check(regno:str,password:str):
    resultcheck=register.find_one({'regno':regno})
    if resultcheck==None:
        return "no user exists"
    if resultcheck:
        if password==resultcheck['password']:
            print("success")
            return "success"
        else:
            print("wrong password")
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
            if (inst['semester']==3):
                li.append(inst['gpa'])
    print(li)
    def find_percentile(value, list1): 
        # print(value)
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

    
    
# for person in register.find():
#     print(person)
# check("RA2211027020130","somethin")
# get_all_marks("RA2211027020114",4)
# assaign_marks("RA2211027020130",4)
# print([p for p in register.find({"name":"mike"})])
# # def insert()
# assaign_cgpa('RA2211027020130')
# addcgpa("RA2211027020130",{"maths":"o","physics":"o"},2)
# a=register.find_one({"regno":"RA22110270201"})


# print(get_percentile("RA2211027020130",3))