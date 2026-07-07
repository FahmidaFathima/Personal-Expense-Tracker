import pandas as pd
from sklearn.linear_model import LinearRegression
from models import Expense

def predict_next_month():
    expenses = Expense.query.all()

    if len(expenses) < 3:
        return "Not enough data"

    data = []
    for e in expenses:
        data.append({
            "month": e.date.month,
            "amount": e.amount
        })

    df = pd.DataFrame(data)

    X = df[["month"]]
    y = df["amount"]

    model = LinearRegression()
    model.fit(X, y)

    next_month = [[df["month"].max() + 1]]
    prediction = model.predict(next_month)

    return round(float(prediction[0]), 2)
