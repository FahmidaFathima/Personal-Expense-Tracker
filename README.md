# Personal Expense Tracker

A modern **Full-Stack Personal Expense Tracker** designed to help users efficiently manage their finances by tracking income and expenses, organizing transactions into categories, and visualizing spending patterns through an interactive dashboard.

The application provides a secure and user-friendly platform where users can monitor their financial activities, gain insights into their spending habits, and make informed budgeting decisions.

## Features

* 🔐 Secure user authentication and authorization
* 💰 Add, edit, and delete income and expense transactions
* 📂 Categorize transactions for better organization
* 📊 Interactive dashboard with charts and financial summaries
* 📅 Track daily, monthly, and yearly expenses
* 🔍 Search and filter transactions
* 📈 Expense analytics and spending insights
* 💾 Persistent database storage
* 📱 Responsive design for desktop and mobile devices

## Tech Stack

**Frontend**

* React.js
* HTML5
* CSS3
* JavaScript

**Backend**

* Node.js
* Express.js

**Database**

* MongoDB

**Authentication**

* JSON Web Token (JWT)

## Key Highlights

* Built using a modern full-stack architecture.
* RESTful API integration between frontend and backend.
* Secure authentication with protected routes.
* Clean, responsive, and intuitive user interface.
* Designed to help users develop better financial management habits.

## Future Enhancements

* Budget planning and goal tracking
* Recurring transactions
* Email notifications and reminders
* Export reports to PDF and CSV
* Multi-currency support
* Dark mode
* AI-powered spending insights



# Expense Tracker Backend

## Setup

1. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Run the app:
   ```
   python app.py
   ```

## API Endpoints

- `POST /register` - Register a new user
- `POST /login` - Login user
- `POST /add-expense` - Add expense
- `GET /expenses` - Get user's expenses
- `POST /set-budget` - Set budget
- `GET /spend-vs-budget` - Compare spend vs budget
- `GET /export-csv` - Export expenses to CSV
- `POST /ask-ai` - Ask AI questions about finances (local processing, no external APIs)
