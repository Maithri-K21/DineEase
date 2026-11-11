# 🍽️ DineEase –Restaurant Booking Chatbot

DineEase is a web-based restaurant assistant for table reservations, AI-assisted menu questions, and demo food orders.

The assistant can answer menu questions, build a cart from natural-language requests, and create demo orders.

## ✨ Features

### 1. Restaurant Booking Chatbot
- Interactive chatbot interface.
- Collects customer name and phone number.
- Accepts number of guests, booking date and time.
- Checks table availability.
- Generates a unique booking ID.
- Provides alternative time suggestions when tables are unavailable.

### 2. Reservation Management
- Check existing reservations using a booking ID.
- Cancel existing bookings.
- Prevent double bookings.
- Validate booking dates.
- Display booking dates in DD-MM-YYYY format.
- Uses Indian Standard Time (IST) for date validation.

### 3. Indian Food Menu
Explore a variety of Indian dishes, including:

- **South Indian:** Masala Dosa, Idli Sambar, Medu Vada, Uttapam.
- **North Indian:** Paneer Butter Masala, Dal Makhani, Butter Naan.
- **Non-Vegetarian:** Chicken Biryani, Butter Chicken, Chicken 65.
- **Beverages:** Filter Coffee, Masala Chai, Mango Lassi.
- **Desserts:** Gulab Jamun, Rasmalai, Kulfi.

Customers can search dishes and filter the menu by category and dietary preference.

### 4. AI and Rule-Based Chat
- With an OpenAI API key, the assistant uses the current menu and order context to answer questions and interpret natural-language requests.
- Without a key, or when the AI service is temporarily unavailable, a rule-based assistant still answers supported menu questions, lists typical ingredients, manages the cart, and guides demo checkout.
- Both paths use the restaurant's stored menu and validate cart items against the database; unsupported facts are not guessed.

### 5. AI Food Ordering (Demo)
- Ask for available menu items in natural language, review or edit the cart, and explicitly confirm checkout.
- Search menu items by name, description, category, or ingredient; each card shows its dish photo, price, ingredients, and preparation estimate.
- Select a quantity per dish, choose delivery or pickup, and enter a requested arrival/pickup time before placing an order.
- Demo orders are stored in SQLite and can be checked or cancelled in the same chat.
- Pickup-ready and delivery time windows are estimates only; no payment, restaurant dispatch, courier integration, or live tracking is provided.
- Ingredient lists are typical recipe information, not allergy guarantees. Customers with allergies must confirm with restaurant staff.

## OpenAI Configuration

The AI assistant requires an OpenAI API key. Keep it on the server and never put it in browser code or commit it to the repository.

Windows PowerShell (for the current terminal session):

```powershell
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_MODEL = "gpt-4o-mini" # optional
py app.py
```

Without a key, the rule-based assistant and reservation flows remain available. Configuring a key enables open-ended AI responses; if the AI service fails, supported requests fall back to the rule-based assistant.

The demo estimates kitchen preparation from each dish's preparation-time value. Delivery estimates add a fixed 20–30 minute illustrative travel allowance; they are not based on a real restaurant or courier and should not be used as a real arrival commitment. The chosen arrival/pickup time is a request, not a confirmed time.

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Flask | Web application framework |
| HTML5 | Webpage structure |
| CSS3 | Styling and responsive design |
| JavaScript | Chatbot interactions |
| SQLite | Database management |

## 📁 Project Structure

```text
DineEase/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── static/
│   ├── app.css
│   └── app.js
│
├── templates/
│   └── index.html
│
└── tests/
    └── test_app.py
```

## ⚙️ Installation and Setup

### Prerequisites
- Python 3.10 or above
- Git
- Visual Studio Code

### Step 1: Clone the Repository

```bash
git clone https://github.com/Maithri-K21/DineEase.git
```

### Step 2: Open the Project

```bash
cd DineEase
```

### Step 3: Install Dependencies

```bash
py -m pip install -r requirements.txt
```

### Step 4: Run the Application

```bash
py app.py
```

### Step 5: Open in Browser

Visit:

http://127.0.0.1:5000

## 🧪 Testing

Run the following command to execute the project tests:

```bash
py -m unittest discover -s tests -v
``

---

*DineEase – Making restaurant reservations simpler, smarter and more convenient.*
