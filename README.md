# 🍽️ DineEase –Restaurant Booking Chatbot

DineEase is a web-based restaurant booking chatbot designed to simplify table reservations and help customers explore an Indian restaurant menu through an interactive chat interface.

The chatbot allows customers to book tables, check availability, manage reservations, browse Indian dishes, and receive basic meal suggestions.

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

### 4. Meal Suggestions
Provides basic meal suggestions based on customer preferences and available menu information.

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
