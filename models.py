import numpy as np
from sklearn.linear_model import LinearRegression

def predict_grades(all_sem:list, all_gpas:list):
    
    semesters=np.array(all_sem).reshape(-1,1)
    gpas=np.array(all_gpas)
    model=LinearRegression()
    model.fit(semesters,gpas)
    next_sem= np.array([[all_sem[-1]+1]])
    predict_gpa=model.predict(next_sem)

    return(predict_gpa[0])

# predict_grades([1,2,3],[9,8,9])