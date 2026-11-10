import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from app import create_app, format_date, ist_today, parse_date


class ChatbotTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database = str(Path(self.temp_dir.name) / "test.sqlite3")
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": database,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def send(self, message):
        response = self.client.post("/api/chat", json={"message": message})
        self.assertEqual(response.status_code, 200)
        return response.get_json()["reply"]

    def complete_booking(self, booking_time="7:00 PM", party="2"):
        self.send("Book a table")
        self.assertIn("phone number", self.send("Jordan Lee").lower())
        self.assertIn("how many people", self.send("+1 555 123 4567").lower())
        self.assertIn("date", self.send(party).lower())
        self.assertIn("Available times", self.send((ist_today() + timedelta(days=1)).isoformat()))
        self.send(booking_time)
        return self.send("None")

    def test_booking_flow_confirms_and_stores_reservation(self):
        reply = self.complete_booking()
        self.assertIn("table is confirmed", reply)
        self.assertRegex(reply, r"DE-[A-F0-9]{8}")

    def test_all_tables_for_party_size_cannot_be_double_booked(self):
        first = self.complete_booking(party="8")
        self.assertIn("table is confirmed", first)
        self.client.post("/api/reset")
        self.send("Book a table")
        self.send("Jordan Lee")
        self.send("+1 555 123 4567")
        self.send("8")
        self.send((ist_today() + timedelta(days=1)).isoformat())
        self.send("7:00 PM")
        reply = self.send("None")
        self.assertIn("That time just filled up", reply)
        self.assertIn("Available times", reply)

    def test_invalid_inputs_are_reprompted(self):
        self.send("Book a table")
        self.assertIn("at least two", self.send("1"))
        self.send("Jordan Lee")
        self.assertIn("7 to 15 digits", self.send("not a phone number"))

    def test_menu_and_basic_questions(self):
        menu_reply = self.send("Show me the menu")
        self.assertIn("Masala Dosa", menu_reply)
        self.assertIn("₹", menu_reply)
        self.assertIn("open daily", self.send("What are your hours?"))

    def test_menu_api_returns_indian_dishes_and_categories(self):
        response = self.client.get("/api/menu")
        self.assertEqual(response.status_code, 200)
        items = response.get_json()["items"]
        self.assertEqual(len(items), 27)
        self.assertIn("Chicken Biryani", {item["name"] for item in items})
        self.assertIn("South Indian", {item["category"] for item in items})
        self.assertTrue(all(item["available"] for item in items))

    def test_dates_are_validated_in_ist_and_formatted_for_customers(self):
        today = ist_today()
        self.assertEqual(parse_date(today.isoformat()), today.isoformat())
        self.assertEqual(parse_date(today.strftime("%d-%m-%Y")), today.isoformat())
        self.assertIsNone(parse_date((today - timedelta(days=1)).isoformat()))
        self.assertIsNone(parse_date("31-02-2027"))
        self.assertEqual(format_date("2027-01-09"), "09-01-2027")

    def test_chat_asks_for_date_with_ist_minimum(self):
        self.send("Book a table")
        self.send("Jordan Lee")
        self.send("+1 555 123 4567")
        response = self.client.post("/api/chat", json={"message": "2"})
        payload = response.get_json()
        self.assertEqual(payload["input_type"], "date")
        self.assertEqual(payload["min_date"], ist_today().isoformat())
        self.assertIn("date", payload["reply"].lower())

    def test_booking_can_be_checked_and_cancelled(self):
        reply = self.complete_booking()
        booking_id = reply.split("Booking ID: ")[1].splitlines()[0]
        self.send("Check booking")
        self.send(booking_id)
        checked = self.send("+1 555 123 4567")
        self.assertIn("is confirmed", checked)
        self.send("Cancel booking")
        self.send(booking_id)
        cancelled = self.send("+1 555 123 4567")
        self.assertIn("has been cancelled", cancelled)


if __name__ == "__main__":
    unittest.main()