import os
import re
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, render_template, request, session


TIME_SLOTS = ("17:00", "17:30", "18:00", "18:30", "19:00", "19:30", "20:00", "20:30")
MENU_CATEGORIES = (
    "South Indian", "North Indian", "Starters & snacks", "Beverages", "Desserts",
)
MENU_IMAGES = {
    "South Indian": "https://images.unsplash.com/photo-1630383249896-424e482df921?auto=format&fit=crop&w=900&q=82",
    "North Indian": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?auto=format&fit=crop&w=900&q=82",
    "Starters & snacks": "https://images.unsplash.com/photo-1599487488170-d11ec9c172f0?auto=format&fit=crop&w=900&q=82",
    "Beverages": "https://images.unsplash.com/photo-1571934811356-5cc061b6821f?auto=format&fit=crop&w=900&q=82",
    "Desserts": "https://images.unsplash.com/photo-1488477181946-6428a0291777?auto=format&fit=crop&w=900&q=82",
}
INDIAN_MENU = (
    ("Masala Dosa", "South Indian", "Crisp rice crepe filled with spiced potato, served with sambar and chutneys.", 180, 1),
    ("Plain Dosa", "South Indian", "Golden, paper-thin rice and lentil crepe with sambar and coconut chutney.", 130, 1),
    ("Idli Sambar", "South Indian", "Steamed rice cakes served with lentil sambar and fresh coconut chutney.", 110, 1),
    ("Medu Vada", "South Indian", "Crisp, savoury lentil doughnuts with sambar and coconut chutney.", 100, 1),
    ("Onion Uttapam", "South Indian", "Soft, thick rice pancake topped with onion, tomato, and green chilli.", 160, 1),
    ("Pesarattu", "South Indian", "Andhra-style green gram crepe with ginger, chilli, and a side of chutney.", 150, 1),
    ("Paneer Butter Masala", "North Indian", "Paneer simmered in a rich tomato, butter, and cream gravy.", 280, 1),
    ("Butter Naan", "North Indian", "Tandoor-baked leavened flatbread brushed with butter.", 55, 1),
    ("Dal Makhani", "North Indian", "Slow-cooked black lentils and kidney beans finished with butter and cream.", 240, 1),
    ("Chole Bhature", "North Indian", "Punjabi chickpea curry served with fluffy fried bhature.", 190, 1),
    ("Veg Biryani", "North Indian", "Fragrant basmati rice layered with seasonal vegetables and warming spices.", 220, 1),
    ("Chicken Biryani", "North Indian", "Dum-cooked basmati rice with spiced chicken, herbs, and saffron.", 290, 0),
    ("Butter Chicken", "North Indian", "Tandoor-roasted chicken in a gently spiced tomato and butter sauce.", 340, 0),
    ("Paneer Tikka", "Starters & snacks", "Chargrilled paneer with peppers, yoghurt, and tandoori spices.", 260, 1),
    ("Gobi Manchurian", "Starters & snacks", "Crisp cauliflower tossed in a savoury Indo-Chinese sauce.", 190, 1),
    ("Veg Spring Rolls", "Starters & snacks", "Crisp rolls filled with seasoned vegetables and served with dipping sauce.", 180, 1),
    ("Chicken 65", "Starters & snacks", "Crispy fried chicken tossed with curry leaves, chilli, and spices.", 250, 0),
    ("Chicken Tikka", "Starters & snacks", "Tandoor-grilled chicken marinated in yoghurt and aromatic spices.", 300, 0),
    ("Filter Coffee", "Beverages", "South Indian filter coffee, brewed strong and served with milk.", 60, 1),
    ("Masala Chai", "Beverages", "Freshly brewed tea simmered with milk, ginger, and warming spices.", 45, 1),
    ("Fresh Lime Soda", "Beverages", "Fresh lime with soda, served sweet, salted, or half-and-half.", 80, 1),
    ("Mango Lassi", "Beverages", "Chilled yoghurt drink blended with mango.", 100, 1),
    ("Buttermilk", "Beverages", "Cooling, lightly spiced yoghurt drink with roasted cumin.", 50, 1),
    ("Gulab Jamun", "Desserts", "Soft milk-solid dumplings soaked in fragrant cardamom syrup.", 90, 1),
    ("Rasmalai", "Desserts", "Soft chenna patties in chilled saffron and cardamom milk.", 120, 1),
    ("Gajar Ka Halwa", "Desserts", "Slow-cooked carrot pudding with milk, ghee, and nuts.", 130, 1),
    ("Kulfi", "Desserts", "Traditional dense milk ice cream with cardamom and pistachio.", 80, 1),
)


def create_app(test_config=None):
    app = Flask(__name__)
    instance_dir = Path(app.instance_path)
    instance_dir.mkdir(parents=True, exist_ok=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("DINEEASE_SECRET_KEY", "local-development-key-change-before-deploy"),
        DATABASE=str(instance_dir / "dineease.sqlite3"),
    )
    if test_config:
        app.config.update(test_config)

    init_db(app.config["DATABASE"])

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/menu")
    def get_menu():
        with closing(connect_db(app.config["DATABASE"])) as connection:
            items = connection.execute(
                """SELECT id, name, category, description, price_inr,
                          is_vegetarian, available, image_url
                   FROM menu_items ORDER BY id"""
            ).fetchall()
        return jsonify(items=[
            {**dict(item), "is_vegetarian": bool(item["is_vegetarian"]), "available": bool(item["available"])}
            for item in items
        ])

    @app.post("/api/chat")
    def chat():
        payload = request.get_json(silent=True) or {}
        message = str(payload.get("message", "")).strip()
        if not message:
            return jsonify(reply="Please type a message and I’ll help you."), 400
        had_flow = bool(session.get("flow"))
        reply = respond(app.config["DATABASE"], message)
        session.modified = True
        result = {"reply": reply}
        if not had_flow and "menu" in message.casefold():
            result["show_menu"] = True
        flow = session.get("flow", {})
        if flow.get("kind") == "booking" and flow.get("step") == "date":
            result["input_type"] = "date"
            result["min_date"] = ist_today().isoformat()
        return jsonify(result)

    @app.post("/api/reset")
    def reset_chat():
        session.pop("flow", None)
        return jsonify(reply="All set. What would you like to do next?")

    return app


def connect_db(database):
    connection = sqlite3.connect(database, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(database):
    Path(database).parent.mkdir(parents=True, exist_ok=True)
    with closing(connect_db(database)) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS restaurant_tables (
                id INTEGER PRIMARY KEY,
                seats INTEGER NOT NULL CHECK (seats > 0)
            );
            CREATE TABLE IF NOT EXISTS bookings (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                party_size INTEGER NOT NULL CHECK (party_size > 0),
                booking_date TEXT NOT NULL,
                booking_time TEXT NOT NULL,
                special_requests TEXT NOT NULL DEFAULT '',
                table_id INTEGER NOT NULL REFERENCES restaurant_tables(id),
                status TEXT NOT NULL DEFAULT 'confirmed',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS bookings_slot_status
                ON bookings(booking_date, booking_time, status, table_id);
            CREATE TABLE IF NOT EXISTS menu_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                price_inr INTEGER NOT NULL CHECK (price_inr > 0),
                is_vegetarian INTEGER NOT NULL CHECK (is_vegetarian IN (0, 1)),
                available INTEGER NOT NULL DEFAULT 1 CHECK (available IN (0, 1)),
                image_url TEXT NOT NULL
            );
            """
        )
        if connection.execute("SELECT COUNT(*) FROM restaurant_tables").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO restaurant_tables(seats) VALUES (?)",
                [(2,), (2,), (4,), (4,), (6,), (8,)],
            )
        connection.executemany(
            """INSERT OR IGNORE INTO menu_items
               (name, category, description, price_inr, is_vegetarian, available, image_url)
               VALUES (?, ?, ?, ?, ?, 1, ?)""",
            [(*dish, MENU_IMAGES[dish[1]]) for dish in INDIAN_MENU],
        )
        connection.commit()


def available_tables(connection, booking_date, booking_time, party_size):
    return connection.execute(
        """
        SELECT id FROM restaurant_tables AS tables
        WHERE seats >= ? AND NOT EXISTS (
            SELECT 1 FROM bookings
            WHERE bookings.table_id = tables.id
              AND bookings.booking_date = ?
              AND bookings.booking_time = ?
              AND bookings.status = 'confirmed'
        )
        ORDER BY seats, id
        """,
        (party_size, booking_date, booking_time),
    ).fetchall()


def available_times(database, booking_date, party_size):
    with closing(connect_db(database)) as connection:
        return [
            slot for slot in TIME_SLOTS
            if available_tables(connection, booking_date, slot, party_size)
        ]


def ist_today():
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()


def parse_date(value):
    formats = (
        (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"),
        (r"\d{2}-\d{2}-\d{4}", "%d-%m-%Y"),
        (r"\d{1,2}/\d{1,2}/\d{4}", "%m/%d/%Y"),
        (r"\d{1,2}/\d{1,2}/\d{2}", "%m/%d/%y"),
    )
    for expression, pattern in formats:
        if not re.fullmatch(expression, value.strip()):
            continue
        try:
            parsed = datetime.strptime(value.strip(), pattern).date()
            if parsed >= ist_today():
                return parsed.isoformat()
            return None
        except ValueError:
            return None
    return None


def format_date(value):
    return datetime.strptime(value, "%Y-%m-%d").strftime("%d-%m-%Y")


def parse_time(value):
    cleaned = value.strip().upper().replace(".", "")
    for pattern in ("%H:%M", "%I:%M %p", "%I %p"):
        try:
            parsed = datetime.strptime(cleaned, pattern).strftime("%H:%M")
            return parsed if parsed in TIME_SLOTS else None
        except ValueError:
            continue
    return None


def format_time(value):
    return datetime.strptime(value, "%H:%M").strftime("%I:%M %p").lstrip("0")


def start_booking():
    session["flow"] = {"kind": "booking", "step": "name", "details": {}}
    return "Sure, let’s find you a table. What name should I put the reservation under?"


def save_booking(database, details):
    booking_id = "DE-" + uuid.uuid4().hex[:8].upper()
    connection = connect_db(database)
    try:
        connection.execute("BEGIN IMMEDIATE")
        tables = available_tables(
            connection, details["date"], details["time"], details["party_size"]
        )
        if not tables:
            connection.rollback()
            return None
        connection.execute(
            """INSERT INTO bookings
               (id, name, phone, party_size, booking_date, booking_time,
                special_requests, table_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                booking_id, details["name"], details["phone"], details["party_size"],
                details["date"], details["time"], details["requests"], tables[0]["id"],
            ),
        )
        connection.commit()
        return booking_id
    except sqlite3.IntegrityError:
        connection.rollback()
        return None
    finally:
        connection.close()


def ask_for_time(database, details, unavailable=False):
    slots = available_times(database, details["date"], details["party_size"])
    if unavailable:
        prefix = "That time just filled up."
    else:
        prefix = ""
    if slots:
        readable = ", ".join(format_time(slot) for slot in slots)
        return f"{prefix} Available times on {format_date(details['date'])}: {readable}. Which works for you?"
    return f"{prefix} We’re fully booked for {format_date(details['date'])}. Please choose another date."


def booking_conversation(database, message, flow):
    details = flow.setdefault("details", {})
    step = flow["step"]

    if step == "name":
        if len(message) < 2 or not re.fullmatch(r"[\w][\w .'-]{0,58}", message, re.UNICODE):
            return "I didn’t catch that name. Please enter at least two characters."
        details["name"] = message
        flow["step"] = "phone"
        return "Thanks. What phone number should we use for the reservation?"

    if step == "phone":
        digits = re.sub(r"\D", "", message)
        if not 7 <= len(digits) <= 15:
            return "That phone number doesn’t look right. Please enter 7 to 15 digits, including your country code if needed."
        details["phone"] = message
        flow["step"] = "party_size"
        return "How many people will be dining? We can seat parties of 1 to 8."

    if step == "party_size":
        if not message.isdigit() or not 1 <= int(message) <= 8:
            return "Please enter a party size from 1 to 8."
        details["party_size"] = int(message)
        flow["step"] = "date"
        return "Choose your booking date."

    if step == "date":
        parsed = parse_date(message)
        if not parsed:
            return f"Please choose a valid date on or after {format_date(ist_today().isoformat())}."
        details["date"] = parsed
        flow["step"] = "time"
        return ask_for_time(database, details)

    if step == "time":
        parsed = parse_time(message)
        if not parsed:
            times = ", ".join(format_time(slot) for slot in TIME_SLOTS)
            return f"Please choose one of our seating times: {times}. You can enter a time like 7:00 PM."
        details["time"] = parsed
        flow["step"] = "requests"
        return "Any special requests? You can say “none” if not."

    if step == "requests":
        details["requests"] = "" if message.casefold() in {"none", "no", "nope", "nothing"} else message[:500]
        booking_id = save_booking(database, details)
        if not booking_id:
            flow["step"] = "time"
            return ask_for_time(database, details, unavailable=True)
        session.pop("flow", None)
        time_label = format_time(details["time"])
        return (
            f"Your table is confirmed, {details['name']}!\n"
            f"Booking ID: {booking_id}\n"
            f"{format_date(details['date'])} at {time_label} for {details['party_size']}\n"
            "Keep your booking ID to check or cancel this reservation."
        )

    session.pop("flow", None)
    return "Let’s start that again. Type “book a table” whenever you’re ready."


def start_booking_lookup(action):
    session["flow"] = {"kind": action, "step": "booking_id", "details": {}}
    verb = "check" if action == "lookup" else "cancel"
    return f"I can help {verb} a reservation. What is your booking ID?"


def lookup_conversation(database, message, flow):
    details = flow.setdefault("details", {})
    if flow["step"] == "booking_id":
        if not re.fullmatch(r"DE-[A-F0-9]{8}", message.strip().upper()):
            return "Please enter the booking ID in the format DE-1234ABCD."
        details["booking_id"] = message.strip().upper()
        flow["step"] = "phone"
        return "What phone number was used for the reservation?"

    connection = connect_db(database)
    try:
        booking = connection.execute(
            "SELECT * FROM bookings WHERE id = ? AND phone = ?",
            (details["booking_id"], message.strip()),
        ).fetchone()
        if not booking:
            session.pop("flow", None)
            return "I couldn’t find a reservation with that booking ID and phone number. Check the details and try again."
        if flow["kind"] == "cancel":
            if booking["status"] == "cancelled":
                result = f"Booking {booking['id']} was already cancelled."
            else:
                connection.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking["id"],))
                connection.commit()
                result = f"Booking {booking['id']} has been cancelled."
        elif booking["status"] == "cancelled":
            result = f"Booking {booking['id']} is cancelled."
        else:
            readable_time = format_time(booking["booking_time"])
            result = (
                f"Booking {booking['id']} is confirmed for {format_date(booking['booking_date'])} at {readable_time} "
                f"for {booking['party_size']} people under {booking['name']}."
            )
        session.pop("flow", None)
        return result
    finally:
        connection.close()


def menu_reply(database):
    with closing(connect_db(database)) as connection:
        items = connection.execute(
            "SELECT name, price_inr, is_vegetarian FROM menu_items WHERE available = 1 ORDER BY id"
        ).fetchall()
    lines = [
        f"{item['name']} - ₹{item['price_inr']} ({'Vegetarian' if item['is_vegetarian'] else 'Non-vegetarian'})"
        for item in items
    ]
    return "Here’s our Indian menu. I’ve opened the full menu so you can browse dishes and filters.\n" + "\n".join(lines)


def recommendation_reply(database, message):
    budget_match = re.search(r"[₹$]?\s*(\d+(?:\.\d{1,2})?)", message)
    budget = float(budget_match.group(1)) if budget_match else None
    vegetarian = any(word in message.casefold() for word in ("vegetarian", "veggie", "meat-free"))
    query = "SELECT name, price_inr, is_vegetarian FROM menu_items WHERE available = 1"
    parameters = []
    if vegetarian:
        query += " AND is_vegetarian = 1"
    if budget is not None:
        query += " AND price_inr <= ?"
        parameters.append(budget)
    with closing(connect_db(database)) as connection:
        candidates = connection.execute(query + " ORDER BY price_inr", parameters).fetchall()
    if not candidates:
        return "I don’t see an available menu item matching that budget and preference. Try another budget or ask to see the menu."
    picks = ", ".join(f"{item['name']} (₹{item['price_inr']})" for item in candidates)
    return f"Based on what you like, I’d suggest: {picks}. Ask to see the menu for the full list."


def respond(database, message):
    normalized = message.casefold().strip()
    flow = session.get("flow")

    if normalized in {"restart", "start over", "reset"}:
        session.pop("flow", None)
        return "No problem. What would you like to do? You can book a table, check a booking, cancel a booking, or view the menu."

    if flow:
        if flow["kind"] == "booking":
            return booking_conversation(database, message, flow)
        return lookup_conversation(database, message, flow)

    if any(term in normalized for term in ("cancel booking", "cancel reservation", "cancel my")):
        return start_booking_lookup("cancel")
    if any(term in normalized for term in ("check booking", "check reservation", "my booking", "booking status")):
        return start_booking_lookup("lookup")
    if any(term in normalized for term in ("book", "reservation", "reserve a table", "table for")):
        return start_booking()
    if "menu" in normalized:
        return menu_reply(database)
    if any(term in normalized for term in ("recommend", "suggest", "vegetarian", "veggie", "budget")):
        return recommendation_reply(message)
    if any(term in normalized for term in ("hour", "open", "address", "location", "where are")):
        return "We’re open daily from 5:00 PM to 9:00 PM. This demo restaurant is at 14 Garden Street."
    if any(term in normalized for term in ("hello", "hi", "hey")):
        return "Hi there! I can book a table, check or cancel a reservation, show the menu, and answer basic questions. What can I help with?"
    return "I can help book a table, check or cancel a booking, show the menu, suggest a meal, or answer questions about our hours and location. What would you like to do?"


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")