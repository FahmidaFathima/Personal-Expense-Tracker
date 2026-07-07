from flask import Flask, request, jsonify
from flask_cors import CORS
from database import db
from models import User, Expense, Budget
from datetime import datetime
import csv
from io import StringIO
import re
from difflib import SequenceMatcher

app = Flask(__name__)
CORS(app)

# Define financial query templates for semantic matching
query_templates = {
    'total_spending': [
        'What is my total spending?',
        'How much have I spent in total?',
        'Total expenditure',
        'Overall spending'
    ],
    'this_month': [
        'How much did I spend this month?',
        'Spending this month',
        'Current month expenditure',
        'This month spending'
    ],
    'monthly_expense': [
        'What is my expenditure in September 2025?',
        'Spending in specific month',
        'Monthly expenditure',
        'How much spent in'
    ],
    'report': [
        'Generate a financial report',
        'Create financial summary',
        'Show my financial report',
        'Generate report'
    ],
    'suggestions': [
        'Any suggestions to save money?',
        'Give me financial advice',
        'How can I save money?',
        'Financial recommendations'
    ],
    'category_spending': [
        'How much did I spend on groceries?',
        'Spending by category',
        'Category breakdown',
        'How much on specific category?'
    ]
}

def semantic_similarity(query, template):
    """Calculate semantic similarity between query and template using SequenceMatcher"""
    query_lower = query.lower()
    template_lower = template.lower()
    
    # Use SequenceMatcher to calculate similarity ratio
    matcher = SequenceMatcher(None, query_lower, template_lower)
    similarity = matcher.ratio()
    
    # Boost similarity if key words match
    query_words = set(query_lower.split())
    template_words = set(template_lower.split())
    word_overlap = len(query_words & template_words) / max(len(query_words), len(template_words))
    
    # Weighted average: 60% sequence match, 40% word overlap
    final_similarity = (similarity * 0.6) + (word_overlap * 0.4)
    return final_similarity

def find_best_query_type(user_query):
    """Find the best matching query type using semantic similarity"""
    best_match = None
    best_score = 0
    
    for query_type, templates in query_templates.items():
        for template in templates:
            score = semantic_similarity(user_query, template)
            if score > best_score:
                best_score = score
                best_match = query_type
    
    return best_match, best_score


# -------------------- PASSWORD VALIDATION --------------------
def validate_password(password):
    """
    Validate password requirements and return detailed feedback
    Returns: (is_valid, requirements_dict)
    """
    requirements = {
        'empty': not bool(password),
        'lowercase': len(re.findall(r'[a-z]', password)) >= 6,
        'special': bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password)),
        'number': bool(re.search(r'[0-9]', password))
    }
    
    is_valid = all([requirements['lowercase'], requirements['special'], requirements['number']]) and not requirements['empty']
    
    return is_valid, requirements

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()


# -------------------- HOME --------------------
@app.route("/")
def home():
    return jsonify({"message": "Expense Tracker Running 🚀"})


# -------------------- REGISTER --------------------
@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.json
        
        # Validate that data exists
        if not data:
            return jsonify({"message": "Request body required"}), 400
        
        # Check if username and password are provided
        if "username" not in data or not data.get("username"):
            return jsonify({"message": "Username is required"}), 400
        
        if "password" not in data or not data.get("password"):
            return jsonify({"message": "Password is required"}), 400

        username = data["username"].strip()
        password = data["password"]

        # Check if username already exists
        if User.query.filter_by(username=username).first():
            return jsonify({"message": "User already exists"}), 400

        # Validate password - MUST PASS before registration
        is_valid, requirements = validate_password(password)
        if not is_valid:
            return jsonify({
                "message": "Password does not meet requirements",
                "requirements": requirements
            }), 400

        # Create new user only if password validation passes
        user = User(
            username=username,
            password=password
        )

        db.session.add(user)
        db.session.commit()

        return jsonify({"message": "Registered successfully"}), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error: {str(e)}"}), 500


# -------------------- LOGIN --------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json

    if "username" not in data or "password" not in data:
        return jsonify({"message": "Username and password required"}), 400

    user = User.query.filter_by(
        username=data["username"],
        password=data["password"]
    ).first()

    if not user:
        return jsonify({"message": "Invalid username or password"}), 401

    return jsonify({
        "message": "Login successful",
        "user_id": user.id
    })


# -------------------- PASSWORD VALIDATION (Real-time) --------------------
@app.route("/validate-password", methods=["POST"])
def validate_password_endpoint():
    data = request.json
    password = data.get("password", "")
    
    is_valid, requirements = validate_password(password)
    
    return jsonify({
        "is_valid": is_valid,
        "requirements": requirements
    })


# -------------------- ADD EXPENSE --------------------
@app.route("/add-expense", methods=["POST"])
def add_expense():
    data = request.json

    expense = Expense(
        user_id=int(data["user_id"]),
        amount=float(data["amount"]),
        category=data["category"],
        date=datetime.strptime(data["date"], "%Y-%m-%d")
    )

    db.session.add(expense)
    db.session.commit()

    return jsonify({"message": "Expense Added"})


# -------------------- GET EXPENSES --------------------
@app.route("/expenses", methods=["GET"])
def get_expenses():
    user_id = int(request.args.get("user_id"))
    start = request.args.get("start")
    end = request.args.get("end")

    query = Expense.query.filter_by(user_id=user_id)

    if start and end:
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")
        query = query.filter(Expense.date.between(start_date, end_date))

    expenses = query.all()

    result = []
    for e in expenses:
        result.append({
            "id": e.id,
            "amount": e.amount,
            "category": e.category,
            "date": e.date.strftime("%Y-%m-%d")
        })

    return jsonify(result)


# -------------------- SET BUDGET --------------------
@app.route("/set-budget", methods=["POST"])
def set_budget():
    data = request.json

    budget = Budget(
        user_id=int(data["user_id"]),
        category=data["category"],
        month=int(data["month"]),
        year=int(data["year"]),
        monthly_limit=float(data["monthly_limit"])
    )

    db.session.add(budget)
    db.session.commit()

    return jsonify({"message": "Budget Saved"})


# -------------------- SPEND VS BUDGET --------------------
@app.route("/spend-vs-budget", methods=["GET"])
def spend_vs_budget():
    user_id = int(request.args.get("user_id"))
    month = int(request.args.get("month"))
    year = int(request.args.get("year"))

    budgets = Budget.query.filter_by(
        user_id=user_id,
        month=month,
        year=year
    ).all()

    result = []

    for b in budgets:
        total_spent = db.session.query(
            db.func.sum(Expense.amount)
        ).filter(
            Expense.user_id == user_id,
            Expense.category == b.category,
            db.extract('month', Expense.date) == month,
            db.extract('year', Expense.date) == year
        ).scalar() or 0

        result.append({
            "category": b.category,
            "budget": float(b.monthly_limit),
            "spent": float(total_spent),
            "remaining": float(b.monthly_limit - total_spent)
        })

    return jsonify(result)


# -------------------- EXPORT CSV --------------------
@app.route("/export-csv", methods=["GET"])
def export_csv():
    user_id = int(request.args.get("user_id"))

    expenses = Expense.query.filter_by(user_id=user_id).all()

    si = StringIO()
    cw = csv.writer(si)

    cw.writerow(["Amount", "Category", "Date"])

    for e in expenses:
        cw.writerow([e.amount, e.category, e.date.strftime("%Y-%m-%d")])

    output = si.getvalue()

    return app.response_class(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=expenses.csv"}
    )


# -------------------- SEMANTIC SEARCH QUERY PROCESSING --------------------
def process_financial_query(user_id, query):
    """
    Process user query using semantic similarity matching (Vector DB concept)
    This is scalable, efficient, and uses semantic matching instead of keyword matching
    """
    expenses = Expense.query.filter_by(user_id=user_id).all()
    budgets = Budget.query.filter_by(user_id=user_id).all()
    user = User.query.filter_by(id=user_id).first()
    user_name = user.username if user else "there"

    # Get time-based greeting
    now = datetime.now()
    hour = now.hour
    if hour < 12:
        greeting = f"Good morning, {user_name}!"
    elif hour < 17:
        greeting = f"Good afternoon, {user_name}!"
    else:
        greeting = f"Good evening, {user_name}!"

    # Find the best matching query type using semantic similarity
    best_match, score = find_best_query_type(query)

    # Only process if similarity score is reasonable
    if score < 0.3:
        return f"{greeting} 🤔 I can help you with:\n\n• 📊 Total spending analysis across all your expenses\n• 📅 Monthly expenditure details with category breakdowns\n• 🏷️ Category-wise spending patterns and trends\n• 📋 Comprehensive financial reports with insights\n• 💡 Personalized budget suggestions and saving tips\n• 📈 Visual spending trends and comparisons\n\n💭 Try rephrasing your question or ask about specific months/years for detailed analysis!"

    # Execute appropriate query handler
    now = datetime.now()
    total_spending = sum(e.amount for e in expenses)
    this_month_expenses = [e for e in expenses if e.date.month == now.month and e.date.year == now.year]
    this_month_spending = sum(e.amount for e in this_month_expenses)
    
    if best_match == 'total_spending':
        num_expenses = len(expenses)
        avg_transaction = total_spending / num_expenses if num_expenses > 0 else 0
        categories_count = len(set(e.category for e in expenses))

        response = f"{greeting} 📊 Here's your complete spending overview:\n\n"
        response += f"💰 Total Spending: ₹{total_spending:.2f} across {num_expenses} transactions\n"
        response += f"📊 Average Transaction: ₹{avg_transaction:.2f}\n"
        response += f"🏷️ Categories Used: {categories_count}\n\n"

        # Top spending categories
        categories = {}
        for e in expenses:
            categories[e.category] = categories.get(e.category, 0) + e.amount

        response += "🥇 Top Spending Categories:\n"
        for cat, amt in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]:
            percentage = (amt / total_spending * 100) if total_spending > 0 else 0
            response += f"• {cat}: ₹{amt:.2f} ({percentage:.1f}%)\n"

        response += f"\n💡 Insight: Your largest expense category represents {percentage:.1f}% of total spending.\n"

        # Visual output data for client chart rendering
        response += "\n📊 Visual Data:\n"
        response += f"CATEGORY_DATA:{','.join(str(categories.get(cat, 0)) for cat in sorted(categories.keys()))}\n"
        response += f"CATEGORY_LABELS:{','.join(sorted(categories.keys()))}\n"
        response += "CHART_TYPE:pie\n"

        return response

    elif best_match == 'this_month':
        num_transactions = len(this_month_expenses)
        avg_daily = this_month_spending / 30  # Rough estimate
        days_recorded = len(set(e.date.day for e in this_month_expenses))

        response = f"{greeting} 📅 Your {now.strftime('%B %Y')} spending analysis:\n\n"
        response += f"💰 Total This Month: ₹{this_month_spending:.2f}\n"
        response += f"📊 Transactions: {num_transactions}\n"
        response += f"📅 Days Recorded: {days_recorded}\n"
        response += f"💵 Average Daily Spending: ₹{avg_daily:.2f}\n\n"

        # Category breakdown for this month
        categories = {}
        for e in this_month_expenses:
            categories[e.category] = categories.get(e.category, 0) + e.amount

        response += "💰 Monthly Category Breakdown:\n"
        for cat, amt in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            percentage = (amt / this_month_spending * 100) if this_month_spending > 0 else 0
            response += f"• {cat}: ₹{amt:.2f} ({percentage:.1f}%)\n"

        # Budget comparison if available
        if budgets:
            response += "\n📊 Budget Status:\n"
            for b in budgets:
                if b.month == now.month and b.year == now.year:
                    spent = categories.get(b.category, 0)
                    remaining = b.monthly_limit - spent
                    status = "✅ Within Budget" if remaining >= 0 else "⚠️ Over Budget"
                    response += f"• {b.category}: ₹{spent:.2f} / ₹{b.monthly_limit:.2f} {status}\n"

        # Visual output data for client chart rendering
        response += "\n📊 Visual Data:\n"
        response += f"CATEGORY_DATA:{','.join(str(categories.get(cat, 0)) for cat in sorted(categories.keys()))}\n"
        response += f"CATEGORY_LABELS:{','.join(sorted(categories.keys()))}\n"
        response += "CHART_TYPE:bar\n"

        return response
    
    elif best_match == 'monthly_expense':
        # Enhanced month/year extraction with better parsing
        month_year_match = re.search(r'(\w+)\s+(\d{4})', query)
        if month_year_match:
            month_name, year_str = month_year_match.groups()
            try:
                month_num = datetime.strptime(month_name, '%B').month
                year = int(year_str)
                month_expenses = [e for e in expenses if e.date.month == month_num and e.date.year == year]
                month_total = sum(e.amount for e in month_expenses)

                # Get category breakdown for the month
                category_breakdown = {}
                for e in month_expenses:
                    category_breakdown[e.category] = category_breakdown.get(e.category, 0) + e.amount

                response = f"📊 Your expenditure in {month_name} {year} is ₹{month_total:.2f}\n\n"
                response += "💰 Category Breakdown:\n"
                for cat, amt in sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True):
                    percentage = (amt / month_total * 100) if month_total > 0 else 0
                    response += f"• {cat}: ₹{amt:.2f} ({percentage:.1f}%)\n"

                # Add comparison with previous month
                prev_month = month_num - 1 if month_num > 1 else 12
                prev_year = year if month_num > 1 else year - 1
                prev_expenses = [e for e in expenses if e.date.month == prev_month and e.date.year == prev_year]
                prev_total = sum(e.amount for e in prev_expenses)

                if prev_total > 0:
                    change = ((month_total - prev_total) / prev_total * 100)
                    trend = "📈 increased" if change > 0 else "📉 decreased"
                    response += f"\n📊 Compared to {datetime(prev_year, prev_month, 1).strftime('%B %Y')}: {trend} by {abs(change):.1f}%"

                return response
            except ValueError:
                pass

        # Try MM/YYYY format
        mm_yyyy_match = re.search(r'(\d{1,2})/(\d{4})', query)
        if mm_yyyy_match:
            month, year = map(int, mm_yyyy_match.groups())
            if 1 <= month <= 12:
                month_expenses = [e for e in expenses if e.date.month == month and e.date.year == year]
                month_total = sum(e.amount for e in month_expenses)

                # Get category breakdown for the month
                category_breakdown = {}
                for e in month_expenses:
                    category_breakdown[e.category] = category_breakdown.get(e.category, 0) + e.amount

                month_name = datetime(year, month, 1).strftime('%B')
                response = f"📊 Your expenditure in {month_name} {year} is ₹{month_total:.2f}\n\n"
                response += "💰 Category Breakdown:\n"
                for cat, amt in sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True):
                    percentage = (amt / month_total * 100) if month_total > 0 else 0
                    response += f"• {cat}: ₹{amt:.2f} ({percentage:.1f}%)\n"

                return response

        # If no specific month/year found, provide entire year analysis with EMI calculation
        current_year = datetime.now().year
        year_expenses = [e for e in expenses if e.date.year == current_year]

        if not year_expenses:
            return f"📅 No expenses found for {current_year}. Start tracking your expenses to see detailed analysis!"

        # Calculate monthly spending for the year
        monthly_data = {}
        for i in range(1, 13):
            month_expenses = [e for e in year_expenses if e.date.month == i]
            monthly_data[i] = sum(e.amount for e in month_expenses)

        total_year_spending = sum(monthly_data.values())
        avg_monthly = total_year_spending / 12

        response = f"📊 Complete {current_year} Financial Analysis:\n\n"
        response += f"💰 Total Annual Spending: ₹{total_year_spending:.2f}\n"
        response += f"📅 Average Monthly Spending: ₹{avg_monthly:.2f}\n\n"

        response += "📈 Monthly Breakdown:\n"
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        for i in range(1, 13):
            amount = monthly_data[i]
            response += f"• {month_names[i-1]} {current_year}: ₹{amount:.2f}\n"

        # EMI Calculation (assuming this is for loan payments or similar)
        response += f"\n💳 EMI Calculation Analysis:\n"
        response += f"If you were paying off ₹{total_year_spending:.2f} over 12 months at 12% interest:\n"
        monthly_emi = (total_year_spending * 0.12 / 12) + (total_year_spending / 12)
        total_with_interest = monthly_emi * 12
        response += f"• Monthly EMI: ₹{monthly_emi:.2f}\n"
        response += f"• Total with Interest: ₹{total_with_interest:.2f}\n"
        response += f"• Interest Amount: ₹{total_with_interest - total_year_spending:.2f}\n\n"

        response += "📊 Visual Data for Charts:\n"
        response += f"MONTHLY_DATA:{','.join([str(monthly_data[i]) for i in range(1, 13)])}\n"
        response += f"YEAR_TOTAL:{total_year_spending}\n"
        response += f"AVG_MONTHLY:{avg_monthly}"

        return response
    
    elif best_match == 'report':
        categories = {}
        monthly_trends = {}
        yearly_totals = {}

        for e in expenses:
            # Category totals
            categories[e.category] = categories.get(e.category, 0) + e.amount

            # Monthly trends
            month_key = f"{e.date.year}-{e.date.month:02d}"
            monthly_trends[month_key] = monthly_trends.get(month_key, 0) + e.amount

            # Yearly totals
            yearly_totals[e.date.year] = yearly_totals.get(e.date.year, 0) + e.amount

        response = f"{greeting} 📊 Comprehensive Financial Report:\n\n"
        response += f"💰 Overall Statistics:\n"
        response += f"• Total Spending: ₹{total_spending:.2f}\n"
        response += f"• Total Transactions: {len(expenses)}\n"
        response += f"• Categories Used: {len(categories)}\n"
        response += f"• Average Transaction: ₹{total_spending/len(expenses):.2f}\n\n"

        response += "💰 Top Spending Categories:\n"
        for cat, amt in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]:
            percentage = (amt / total_spending * 100) if total_spending > 0 else 0
            response += f"• {cat}: ₹{amt:.2f} ({percentage:.1f}%)\n"

        response += "\n📈 Yearly Overview:\n"
        for year, amt in sorted(yearly_totals.items(), reverse=True):
            response += f"• {year}: ₹{amt:.2f}\n"

        if budgets:
            response += "\n📊 Budget Analysis:\n"
            current_month = now.month
            current_year = now.year
            for b in budgets:
                spent = sum(e.amount for e in expenses if e.category == b.category and e.date.month == current_month and e.date.year == current_year)
                remaining = b.monthly_limit - spent
                status = "✅ Within Budget" if remaining >= 0 else "⚠️ Over Budget"
                overage_pct = ((spent - b.monthly_limit) / b.monthly_limit * 100) if spent > b.monthly_limit else 0
                response += f"• {b.category} ({current_month}/{current_year}): ₹{spent:.2f} / ₹{b.monthly_limit:.2f}"
                if spent > b.monthly_limit:
                    response += f" ({overage_pct:.1f}% over)\n"
                else:
                    response += f" ({abs(overage_pct):.1f}% remaining)\n"

        # Add visual data for charts
        response += f"\n📊 Visual Data:\n"
        response += f"CATEGORY_DATA:{','.join([str(categories.get(cat, 0)) for cat in sorted(categories.keys())])}\n"
        response += f"CATEGORY_LABELS:{','.join(sorted(categories.keys()))}\n"
        response += f"YEARLY_DATA:{','.join([str(yearly_totals.get(year, 0)) for year in sorted(yearly_totals.keys(), reverse=True)])}\n"
        response += f"YEARLY_LABELS:{','.join([str(year) for year in sorted(yearly_totals.keys(), reverse=True)])}\n"
        response += "CHART_TYPE:bar"

        return response
    
    elif best_match == 'category_spending':
        categories = {}
        category_transactions = {}

        for e in expenses:
            categories[e.category] = categories.get(e.category, 0) + e.amount
            if e.category not in category_transactions:
                category_transactions[e.category] = []
            category_transactions[e.category].append(e)

        if not categories:
            return f"{greeting} 📝 You haven't recorded any expenses yet. Start by adding some transactions to see detailed category analysis!"

        # Find matching category using semantic similarity
        best_category = None
        best_category_score = 0
        for category in categories.keys():
            score = semantic_similarity(query, category)
            if score > best_category_score:
                best_category_score = score
                best_category = category

        if best_category and best_category_score > 0.3:
            # Detailed category analysis
            category_total = categories[best_category]
            category_percentage = (category_total / total_spending * 100) if total_spending > 0 else 0
            transactions = category_transactions[best_category]
            avg_transaction = category_total / len(transactions) if transactions else 0

            # Monthly trend for this category
            monthly_trend = {}
            for e in transactions:
                month_key = f"{e.date.year}-{e.date.month:02d}"
                monthly_trend[month_key] = monthly_trend.get(month_key, 0) + e.amount

            response = f"{greeting} 🏷️ Detailed Analysis for '{best_category}':\n\n"
            response += f"💰 Total Spent: ₹{category_total:.2f} ({category_percentage:.1f}% of all spending)\n"
            response += f"📊 Transactions: {len(transactions)}\n"
            response += f"💵 Average Transaction: ₹{avg_transaction:.2f}\n\n"

            # Recent activity
            recent_transactions = sorted(transactions, key=lambda x: x.date, reverse=True)[:5]
            if recent_transactions:
                response += "🕒 Recent Transactions:\n"
                for e in recent_transactions:
                    response += f"• {e.date.strftime('%b %d, %Y')}: ₹{e.amount:.2f}\n"

            # Monthly breakdown
            if len(monthly_trend) > 1:
                response += "\n📈 Monthly Trend:\n"
                for month_key in sorted(monthly_trend.keys(), reverse=True)[:6]:  # Last 6 months
                    year, month = map(int, month_key.split('-'))
                    month_name = datetime(year, month, 1).strftime('%b %Y')
                    response += f"• {month_name}: ₹{monthly_trend[month_key]:.2f}\n"

            # Budget comparison
            relevant_budgets = [b for b in budgets if b.category.lower() == best_category.lower()]
            if relevant_budgets:
                b = relevant_budgets[0]  # Take the most recent budget
                spent_this_period = sum(e.amount for e in transactions if e.date.month == b.month and e.date.year == b.year)
                remaining = b.monthly_limit - spent_this_period
                status = "✅ Within Budget" if remaining >= 0 else "⚠️ Over Budget"
                response += f"\n📊 Budget Status ({b.month}/{b.year}):\n"
                response += f"• Budget: ₹{b.monthly_limit:.2f}\n"
                response += f"• Spent: ₹{spent_this_period:.2f}\n"
                response += f"• Remaining: ₹{remaining:.2f} {status}\n"

            # Add visual data
            response += f"\n📊 Visual Data:\n"
            response += f"CATEGORY_TOTAL:{category_total}\n"
            response += f"TRANSACTION_COUNT:{len(transactions)}\n"
            response += f"MONTHLY_DATA:{','.join([str(monthly_trend.get(month_key, 0)) for month_key in sorted(monthly_trend.keys())])}\n"
            response += f"MONTHLY_LABELS:{','.join(sorted(monthly_trend.keys()))}\n"
            response += "CHART_TYPE:line"

            return response
        else:
            # Show all categories
            response = f"{greeting} 💰 Your Spending by Category:\n\n"
            for cat, amt in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                percentage = (amt / total_spending * 100) if total_spending > 0 else 0
                transaction_count = len(category_transactions[cat])
                response += f"🏷️ {cat}: ₹{amt:.2f} ({percentage:.1f}%) - {transaction_count} transactions\n"

            response += f"\n💡 Try asking about a specific category like 'How much on groceries?' or 'Spending on entertainment?'"
            return response
    
    elif best_match == 'suggestions':
        suggestions = []
        insights = []

        # Analyze spending patterns
        if total_spending > 0:
            # High spending analysis
            if total_spending > 50000:
                suggestions.append("💰 Your total spending is quite high. Consider implementing a '24-hour rule' for big purchases.")
                insights.append("High spender: Focus on needs vs wants")

            # Category analysis
            categories = {}
            for e in expenses:
                categories[e.category] = categories.get(e.category, 0) + e.amount

            if categories:
                max_category = max(categories.items(), key=lambda x: x[1])
                percentage = (max_category[1] / total_spending * 100)
                if percentage > 40:
                    suggestions.append(f"🎯 '{max_category[0]}' dominates your spending ({percentage:.1f}%). Look for ways to optimize this category.")
                    insights.append(f"Major expense category: {max_category[0]}")

                # Find categories with increasing trends
                # Calculate date 2 months ago
                if now.month > 2:
                    two_months_ago = datetime(now.year, now.month - 2, 1)
                else:
                    year_offset = 1 if now.month == 1 else 0
                    month_calc = 12 + (now.month - 2) if now.month <= 2 else now.month - 2
                    two_months_ago = datetime(now.year - year_offset, month_calc, 1)

                recent_months = [e for e in expenses if e.date >= two_months_ago]
                if recent_months:
                    recent_avg = sum(e.amount for e in recent_months) / len(set(e.date.strftime('%Y-%m') for e in recent_months))
                    suggestions.append(f"📈 Your recent monthly average is ₹{recent_avg:.2f}. Track this trend closely.")

        # Budget analysis
        budget_issues = []
        for b in budgets:
            spent = sum(e.amount for e in expenses if e.category == b.category and e.date.month == b.month and e.date.year == b.year)
            if spent > b.monthly_limit:
                overage = ((spent - b.monthly_limit) / b.monthly_limit * 100)
                budget_issues.append(f"⚠️ '{b.category}' is {overage:.1f}% over budget (₹{spent:.2f} vs ₹{b.monthly_limit:.2f})")
                suggestions.append(f"🔧 Reduce '{b.category}' spending by ₹{spent - b.monthly_limit:.2f} to stay within budget.")

        # Savings potential
        potential_savings = []
        if categories:
            # Dining out analysis
            dining_categories = [cat for cat in categories.keys() if 'food' in cat.lower() or 'dining' in cat.lower() or 'restaurant' in cat.lower()]
            if dining_categories:
                dining_total = sum(categories[cat] for cat in dining_categories)
                if dining_total > total_spending * 0.15:
                    potential_savings.append("🍽️ Consider cooking at home more often to save on dining expenses")

            # Subscription analysis
            sub_categories = [cat for cat in categories.keys() if 'subscription' in cat.lower() or 'netflix' in cat.lower() or 'prime' in cat.lower()]
            if sub_categories:
                sub_total = sum(categories[cat] for cat in sub_categories)
                potential_savings.append(f"📺 Review your ₹{sub_total:.2f} in subscriptions - cancel unused services")

        response = f"{greeting} 💡 Personalized Financial Advice:\n\n"

        if insights:
            response += "🔍 Key Insights:\n"
            for insight in insights:
                response += f"• {insight}\n"
            response += "\n"

        if budget_issues:
            response += "⚠️ Budget Alerts:\n"
            for issue in budget_issues:
                response += f"{issue}\n"
            response += "\n"

        response += "💡 Actionable Suggestions:\n"
        if suggestions:
            for suggestion in suggestions:
                response += f"• {suggestion}\n"
        else:
            response += "• ✨ Great job maintaining your finances! Keep tracking your expenses.\n"
            response += "• 📊 Consider setting monthly budgets for different categories.\n"
            response += "• 🎯 Focus on high-impact savings opportunities.\n"

        if potential_savings:
            response += "\n💰 Potential Savings:\n"
            for saving in potential_savings:
                response += f"• {saving}\n"

        response += "\n🎯 Next Steps:\n"
        response += "• Review your largest expense categories weekly\n"
        response += "• Set specific savings goals for each month\n"
        response += "• Track your progress and celebrate milestones\n"
        response += "• Consider automating your savings transfers"

        return response
    
    else:
        # Default response if similarity is too low
        return f"{greeting} 🤔 I can help you with:\n\n• 📊 Total spending analysis across all your expenses\n• 📅 Monthly expenditure details with category breakdowns\n• 🏷️ Category-wise spending patterns and trends\n• 📋 Comprehensive financial reports with insights\n• 💡 Personalized budget suggestions and saving tips\n• 📈 Visual spending trends and comparisons\n\n💭 Try rephrasing your question or ask about specific months/years for detailed analysis!"


@app.route("/ask-ai", methods=["POST"])
def ask_ai():
    data = request.json
    user_id = int(data["user_id"])
    query = data["query"]
    
    answer = process_financial_query(user_id, query)
    
    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(debug=True)
