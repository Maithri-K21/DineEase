<<<<<<< HEAD
# DineEase - Restaurant Booking Chatbot

A chat-first restaurant reservation demo built with Python, Flask, SQLite, and plain HTML/CSS/JavaScript. There is no restaurant homepage; opening the app takes you straight to the chatbot.

## Current features

- Guided reservation conversation with validation for name, phone, party size, date, and time.
- Date picker prevents past selections using India Standard Time. Dates are stored as `YYYY-MM-DD` and shown to customers as `DD-MM-YYYY`.
- SQLite-backed availability using six sample tables, with a transaction to avoid assigning a table twice for the same seating time.
- Unique booking IDs, booking lookup, and cancellation (verified with the booking ID and phone number).
- Searchable Indian menu with 27 dishes, category and dietary filters, INR prices, availability, descriptions, and food photography.
- Simple meal suggestions based on available menu items and prices, plus basic restaurant hours/location answers.
- Friendly fallback replies for unknown requests and invalid inputs.

Menu prices, images, and restaurant details are demo data. Food pre-orders, customer/admin dashboards, and deployment are later stages; no paid AI service is used.

## Run locally on Windows

1. Open a terminal in this project folder.
2. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install Flask:

   ```powershell
   py -m pip install -r requirements.txt
   ```

4. Start the chatbot:

   ```powershell
   py app.py
   ```

5. Open http://127.0.0.1:5000 in your browser.

SQLite creates `instance/dineease.sqlite3` the first time the app starts. Use **Ctrl+C** in the terminal to stop it. To use a non-default session key locally, set it before starting Flask:

```powershell
$env:DINEEASE_SECRET_KEY = "replace-with-a-long-random-value"
py app.py
```

## Run tests

```powershell
py -m unittest discover -s tests -v
```
=======
# DineEase
Restaurant Booking Chatbot – A smart chatbot for table reservations, menu exploration, and food recommendations.
>>>>>>> 5d95404f15c9566297b5020222a985fc5d5c45dd
