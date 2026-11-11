import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app import ask_openai, create_app, format_date, ist_today, parse_date


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
        self.assertEqual(len({item["image_url"] for item in items}), len(items))
        self.assertTrue(all(item["image_source_url"] for item in items))

    def test_menu_questions_use_menu_data_and_do_not_guess_allergens(self):
        self.assertIn("₹280", self.send("How much is Paneer Butter Masala?"))
        self.assertIn("non-vegetarian", self.send("Is Chicken Biryani vegetarian?"))
        self.assertIn("currently available", self.send("Is Masala Dosa available?"))
        allergy_reply = self.send("Does Paneer Butter Masala contain nuts?")
        self.assertIn("does not include a complete ingredient or allergen list", allergy_reply)
        self.assertIn("confirm allergy requirements", allergy_reply)
        origin_reply = self.send("Where does Paneer Butter Masala come from?")
        self.assertIn("don’t have confirmed information", origin_reply)

    def test_open_ended_menu_question_uses_openai_assistant(self):
        self.app.config["OPENAI_API_KEY"] = "test-key"
        with patch("app.ask_openai", return_value={
            "reply": "Filter coffee has a rich roasted flavor.",
            "action": "chat",
            "items": [],
            "order_type": "unspecified",
        }):
            reply = self.send("Tell me a fun food fact about Filter Coffee")
        self.assertIn("roasted flavor", reply)

    def test_questions_during_booking_do_not_advance_the_booking(self):
        self.send("Book a table")
        self.assertIn("5:00 PM to 9:00 PM", self.send("What are your hours?"))
        self.assertIn("phone number", self.send("Jordan Lee").lower())

    def test_unknown_questions_are_not_answered_with_made_up_facts(self):
        reply = self.send("Do you offer delivery?")
        self.assertIn("don’t have confirmed delivery", reply)

    def test_menu_api_includes_ingredient_and_preparation_details(self):
        response = self.client.get("/api/menu")
        items = response.get_json()["items"]
        dosa = next(item for item in items if item["name"] == "Masala Dosa")
        self.assertIn("potato", dosa["ingredients"])
        self.assertGreater(dosa["preparation_minutes"], 0)
        self.assertTrue(dosa["image_url"].startswith("https://"))
        self.assertEqual(len({item["image_url"] for item in items}), len(items))

    def test_rule_based_fallback_answers_ingredient_questions(self):
        ingredients = self.send("What ingredients are in Masala Dosa?")
        self.assertIn("potato", ingredients)
        self.assertIn("allergens", ingredients)

    def test_food_combo_feature_is_removed(self):
        response = self.send("Suggest a dosa and coffee combination")
        self.assertIn("not available", response)

    def test_removed_combo_request_does_not_interrupt_reservation_flow(self):
        self.send("Book a table")
        self.assertIn("not available", self.send("Suggest a food combination"))
        self.assertIn("phone number", self.send("Jordan Lee").lower())

    def test_rule_based_fallback_places_order_and_reports_delivery_estimate(self):
        added = self.send("I want two dosas and one coffee")
        self.assertIn("2 × Masala Dosa", added)
        self.assertIn("1 × Filter Coffee", added)
        self.assertIn("₹420", added)
        cart = self.send("My cart")
        self.assertIn("2 × Masala Dosa", cart)
        self.assertIn("1 × Filter Coffee", cart)
        self.assertIn("₹420", cart)
        self.assertIn("delivery or pickup", self.send("Checkout"))
        placed = self.send("Delivery please")
        self.assertRegex(placed, r"DEO-[A-F0-9]{8}")
        self.assertIn("Estimated arrival", placed)
        self.assertIn("not live courier tracking", placed)

    def test_openai_failure_falls_back_to_rule_based_assistant(self):
        self.app.config["OPENAI_API_KEY"] = "test-key"
        with patch("app.ask_openai", side_effect=TimeoutError("request timed out")):
            response = self.client.post(
                "/api/chat", json={"message": "Can you make up a story about dinner?"}
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ai_fallback"])
        self.assertIn("don’t have enough confirmed information", response.get_json()["reply"])

    def test_ai_order_flow_validates_cart_and_creates_demo_delivery_estimate(self):
        self.app.config["OPENAI_API_KEY"] = "test-key"
        with patch("app.ask_openai", side_effect=[
            {
                "reply": "Added those dishes.",
                "action": "add_to_cart",
                "items": [
                    {"name": "Masala Dosa", "quantity": 2},
                    {"name": "Filter Coffee", "quantity": 1},
                ],
                "order_type": "unspecified",
            },
            {
                "reply": "Choose delivery or pickup.",
                "action": "place_order",
                "items": [],
                "order_type": "unspecified",
            },
            {
                "reply": "I’ll place it for delivery.",
                "action": "place_order",
                "items": [],
                "order_type": "delivery",
            },
        ]):
            added = self.client.post("/api/chat", json={"message": "Can you assemble a meal for me?"})
            self.assertIn("₹420", added.get_json()["reply"])
            cart = self.client.get("/api/cart").get_json()["cart"]
            self.assertEqual(cart["total_inr"], 420)

            waiting = self.client.post("/api/chat", json={"message": "Checkout"})
            self.assertIn("delivery or pickup", waiting.get_json()["reply"])

            placed = self.client.post("/api/chat", json={"message": "Delivery please"})
            result = placed.get_json()
            self.assertRegex(result["order_id"], r"DEO-[A-F0-9]{8}")
            self.assertIn("Estimated arrival", result["reply"])
            self.assertIn("not live courier tracking", result["reply"])
            self.assertEqual(self.client.get("/api/cart").get_json()["cart"]["total_inr"], 0)

            status = self.client.get("/api/orders/latest").get_json()["order"]
            self.assertEqual(status["order_type"], "delivery")
            self.assertEqual(status["total_inr"], 420)
            self.assertEqual(len(status["items"]), 2)

    def test_ai_cannot_add_unknown_or_unavailable_menu_names(self):
        self.app.config["OPENAI_API_KEY"] = "test-key"
        with patch("app.ask_openai", return_value={
            "reply": "Added the dish.",
            "action": "add_to_cart",
            "items": [{"name": "Imaginary Curry", "quantity": 1}],
            "order_type": "unspecified",
        }):
            response = self.client.post("/api/chat", json={"message": "Add imaginary curry"})
        self.assertIn("couldn’t match", response.get_json()["reply"])
        self.assertEqual(self.client.get("/api/cart").get_json()["cart"]["items"], [])

    def test_quantity_selection_and_scheduled_demo_order(self):
        menu = self.client.get("/api/menu").get_json()["items"]
        dosa_id = next(item["id"] for item in menu if item["name"] == "Masala Dosa")
        add = self.client.post("/api/cart", json={"item_id": dosa_id, "quantity": 3})
        self.assertEqual(add.status_code, 200)
        self.assertEqual(add.get_json()["cart"]["total_inr"], 540)
        checkout = self.client.post("/api/orders", json={
            "order_type": "delivery",
            "requested_arrival": (ist_today() + timedelta(days=1)).isoformat() + "T19:30",
        })
        self.assertEqual(checkout.status_code, 201)
        order = checkout.get_json()["order"]
        self.assertEqual(order["order_type"], "delivery")
        self.assertEqual(order["requested_arrival"].split("T")[1], "19:30")
        self.assertIn("arrival_start", order)
        self.assertEqual(self.client.get("/api/cart").get_json()["cart"]["items"], [])

    def test_quantity_and_requested_order_time_are_validated(self):
        menu = self.client.get("/api/menu").get_json()["items"]
        dosa_id = next(item["id"] for item in menu if item["name"] == "Masala Dosa")
        self.assertEqual(
            self.client.post("/api/cart", json={"item_id": dosa_id, "quantity": 0}).status_code,
            400,
        )
        self.client.post("/api/cart", json={"item_id": dosa_id, "quantity": 1})
        invalid_time = self.client.post("/api/orders", json={
            "order_type": "delivery",
            "requested_arrival": "not-a-time",
        })
        self.assertEqual(invalid_time.status_code, 400)
        past_time = (datetime.now(ZoneInfo("Asia/Kolkata")) - timedelta(hours=1)).replace(
            tzinfo=None
        ).isoformat(timespec="minutes")
        self.assertEqual(self.client.post("/api/orders", json={
            "order_type": "delivery",
            "requested_arrival": past_time,
        }).status_code, 400)

    def test_openai_request_uses_grounded_menu_context_and_structured_actions(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"choices":[{"message":{"tool_calls":[{"function":{"arguments":"{\\"reply\\":\\"Filter coffee has a rich roasted flavor.\\",\\"action\\":\\"chat\\",\\"items\\":[],\\"order_type\\":\\"unspecified\\"}"}}]}}]}'

        with patch("app.urlopen", return_value=FakeResponse()) as openai_request:
            result = ask_openai(
                "test-key", "gpt-4o-mini", "Tell me about Filter Coffee",
                [{"name": "Masala Dosa", "ingredients": ["rice", "potato"]}],
                [], None, [],
            )
        self.assertEqual(result["action"], "chat")
        request = openai_request.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        request_payload = json.loads(request.data.decode("utf-8"))
        menu_context = request_payload["messages"][1]["content"]
        self.assertIn("Masala Dosa", menu_context)
        self.assertIn("potato", menu_context)
        self.assertEqual(request_payload["tools"][0]["function"]["name"], "respond")

    def test_ai_order_status_and_cancellation(self):
        self.app.config["OPENAI_API_KEY"] = "test-key"
        with patch("app.ask_openai", side_effect=[
            {
                "reply": "Added.",
                "action": "add_to_cart",
                "items": [{"name": "Masala Dosa", "quantity": 1}],
                "order_type": "unspecified",
            },
            {
                "reply": "Order placed.",
                "action": "place_order",
                "items": [],
                "order_type": "pickup",
            },
            {
                "reply": "Order status.",
                "action": "order_status",
                "items": [],
                "order_type": "unspecified",
            },
            {
                "reply": "Cancelled.",
                "action": "cancel_order",
                "items": [],
                "order_type": "unspecified",
            },
        ]):
            self.send("Could you add a dish that suits me?")
            placed = self.send("Go ahead and finish my order")
            self.assertIn("confirmed", placed)
            self.assertIn("Estimated pickup-ready window", placed)
            self.assertIn("Estimated ready", self.send("Where is my order?"))
            self.assertIn("has been cancelled", self.send("Cancel my demo order"))

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