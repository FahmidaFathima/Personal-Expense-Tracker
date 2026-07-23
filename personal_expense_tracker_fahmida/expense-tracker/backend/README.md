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
