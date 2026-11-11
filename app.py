import json
import os
import re
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, render_template, request, session


TIME_SLOTS = ("17:00", "17:30", "18:00", "18:30", "19:00", "19:30", "20:00", "20:30")
MENU_CATEGORIES = (
    "South Indian", "North Indian", "Starters & snacks", "Beverages", "Desserts",
)
MENU_IMAGES = {
    "Masala Dosa": ("https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/Masala_dosa_01.jpg/960px-Masala_dosa_01.jpg", "https://commons.wikimedia.org/wiki/File:Masala_dosa_01.jpg"),
    "Plain Dosa": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/d/d0/Plain_Dosa_from_North_India.jpg/960px-Plain_Dosa_from_North_India.jpg", "https://commons.wikimedia.org/wiki/File:Plain_Dosa_from_North_India.jpg"),
    "Idli Sambar": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/0/02/Idli_Sambar-Noida-UP-SP004.jpg/960px-Idli_Sambar-Noida-UP-SP004.jpg", "https://commons.wikimedia.org/wiki/File:Idli_Sambar-Noida-UP-SP004.jpg"),
    "Medu Vada": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/0/06/%E0%B4%89%E0%B4%B4%E0%B5%81%E0%B4%A8%E0%B5%8D%E0%B4%A8%E0%B5%81%E0%B4%B5%E0%B4%9F%E0%B4%95%E0%B5%BE.JPG/960px-%E0%B4%89%E0%B4%B4%E0%B5%81%E0%B4%A8%E0%B5%8D%E0%B4%A8%E0%B5%81%E0%B4%B5%E0%B4%9F%E0%B4%95%E0%B5%BE.JPG", "https://commons.wikimedia.org/wiki/File:%E0%B4%89%E0%B4%B4%E0%B5%81%E0%B4%A8%E0%B5%8D%E0%B4%A8%E0%B5%81%E0%B4%B5%E0%B4%9F%E0%B4%95%E0%B5%BE.JPG"),
    "Onion Uttapam": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/b/ba/Onion_%22Uttapam%22.jpg/960px-Onion_%22Uttapam%22.jpg", "https://commons.wikimedia.org/wiki/File:Onion_%22Uttapam%22.jpg"),
    "Pesarattu": ("https://upload.wikimedia.org/wikipedia/commons/6/6c/Pesarattu.jpg", "https://commons.wikimedia.org/wiki/File:Pesarattu.jpg"),
    "Paneer Butter Masala": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/1/19/Paneer_butter_masala_2.jpg/960px-Paneer_butter_masala_2.jpg", "https://commons.wikimedia.org/wiki/File:Paneer_butter_masala_2.jpg"),
    "Butter Naan": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/1/1d/Naan_baked_in_Tandoor.jpg/960px-Naan_baked_in_Tandoor.jpg", "https://commons.wikimedia.org/wiki/File:Naan_baked_in_Tandoor.jpg"),
    "Dal Makhani": ("https://upload.wikimedia.org/wikipedia/commons/f/f8/Dal_Makhani.jpg", "https://commons.wikimedia.org/wiki/File:Dal_Makhani.jpg"),
    "Chole Bhature": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/7/76/Chole_Bhature_5.jpg/960px-Chole_Bhature_5.jpg", "https://commons.wikimedia.org/wiki/File:Chole_Bhature_5.jpg"),
    "Veg Biryani": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/2/2f/Veg_biryani.jpg/960px-Veg_biryani.jpg", "https://commons.wikimedia.org/wiki/File:Veg_biryani.jpg"),
    "Chicken Biryani": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/0/04/Bengali_style_chicken_biryani%2C_Kolkata_-_West_Bengal_-_DSC_0020.jpg/960px-Bengali_style_chicken_biryani%2C_Kolkata_-_West_Bengal_-_DSC_0020.jpg", "https://commons.wikimedia.org/wiki/File:Bengali_style_chicken_biryani,_Kolkata_-_West_Bengal_-_DSC_0020.jpg"),
    "Butter Chicken": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3c/Chicken_makhani.jpg/960px-Chicken_makhani.jpg", "https://commons.wikimedia.org/wiki/File:Chicken_makhani.jpg"),
    "Paneer Tikka": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/f/f9/Panir_Tikka_Indian_cheese_grilled.jpg/960px-Panir_Tikka_Indian_cheese_grilled.jpg", "https://commons.wikimedia.org/wiki/File:Panir_Tikka_Indian_cheese_grilled.jpg"),
    "Gobi Manchurian": ("https://upload.wikimedia.org/wikipedia/commons/e/e8/Gobi_manchurian.jpg", "https://commons.wikimedia.org/wiki/File:Gobi_manchurian.jpg"),
    "Veg Spring Rolls": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/2/21/Veg_spring_roll.jpg/960px-Veg_spring_roll.jpg", "https://commons.wikimedia.org/wiki/File:Veg_spring_roll.jpg"),
    "Chicken 65": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/1/1e/Chicken_65_3.jpg/960px-Chicken_65_3.jpg", "https://commons.wikimedia.org/wiki/File:Chicken_65_3.jpg"),
    "Chicken Tikka": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/3/31/Chicken_tikka_in_Araku_Valley%2C_Andhra_Pradesh_01.jpg/960px-Chicken_tikka_in_Araku_Valley%2C_Andhra_Pradesh_01.jpg", "https://commons.wikimedia.org/wiki/File:Chicken_tikka_in_Araku_Valley,_Andhra_Pradesh_01.jpg"),
    "Filter Coffee": ("https://upload.wikimedia.org/wikipedia/commons/8/84/Indian_filter_coffee_in_Dabarah.jpg", "https://commons.wikimedia.org/wiki/File:Indian_filter_coffee_in_Dabarah.jpg"),
    "Masala Chai": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/6/6a/Masala_Chai.jpg/960px-Masala_Chai.jpg", "https://commons.wikimedia.org/wiki/File:Masala_Chai.jpg"),
    "Fresh Lime Soda": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/6/64/Nimbu_Soda_Or_Lemon_Soda.jpg/960px-Nimbu_Soda_Or_Lemon_Soda.jpg", "https://commons.wikimedia.org/wiki/File:Nimbu_Soda_Or_Lemon_Soda.jpg"),
    "Mango Lassi": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/5/5e/Mango_Lassi_and_Butter_Milk_-_Vel_South_Indian_Kitchen_%2B_Bar.jpg/960px-Mango_Lassi_and_Butter_Milk_-_Vel_South_Indian_Kitchen_%2B_Bar.jpg", "https://commons.wikimedia.org/wiki/File:Mango_Lassi_and_Butter_Milk_-_Vel_South_Indian_Kitchen_%2B_Bar.jpg"),
    "Buttermilk": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/8/8f/Masala_Buttermilk.JPG/960px-Masala_Buttermilk.JPG", "https://commons.wikimedia.org/wiki/File:Masala_Buttermilk.JPG"),
    "Gulab Jamun": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/5/58/Two_Gulab_Jamun_in_a_plate_01.jpg/960px-Two_Gulab_Jamun_in_a_plate_01.jpg", "https://commons.wikimedia.org/wiki/File:Two_Gulab_Jamun_in_a_plate_01.jpg"),
    "Rasmalai": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/6/6b/Rasmalai_Secretlondon_09.jpg/960px-Rasmalai_Secretlondon_09.jpg", "https://commons.wikimedia.org/wiki/File:Rasmalai_Secretlondon_09.jpg"),
    "Gajar Ka Halwa": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/9/96/Delicious_Gajar_Ka_Halwa.jpg/960px-Delicious_Gajar_Ka_Halwa.jpg", "https://commons.wikimedia.org/wiki/File:Delicious_Gajar_Ka_Halwa.jpg"),
    "Kulfi": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/9/9b/Frozen_dairy_dessert_of_India_-_Kulfi.jpg/960px-Frozen_dairy_dessert_of_India_-_Kulfi.jpg", "https://commons.wikimedia.org/wiki/File:Frozen_dairy_dessert_of_India_-_Kulfi.jpg"),
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
MENU_DETAILS = {
    "Masala Dosa": (["rice", "urad dal", "potato", "onion", "mustard seeds", "curry leaves", "oil", "sambar", "chutney"], 18),
    "Plain Dosa": (["rice", "urad dal", "fenugreek", "oil", "sambar", "coconut chutney"], 12),
    "Idli Sambar": (["rice", "urad dal", "sambar lentils", "mixed vegetables", "spices", "coconut chutney"], 15),
    "Medu Vada": (["urad dal", "ginger", "green chilli", "curry leaves", "oil", "sambar", "coconut chutney"], 15),
    "Onion Uttapam": (["rice", "urad dal", "onion", "tomato", "green chilli", "oil", "chutney"], 15),
    "Pesarattu": (["green gram", "ginger", "green chilli", "cumin", "oil", "chutney"], 15),
    "Paneer Butter Masala": (["paneer", "tomato", "butter", "cream", "cashew", "onion", "spices"], 20),
    "Butter Naan": (["wheat flour", "yoghurt", "yeast", "butter"], 10),
    "Dal Makhani": (["black lentils", "kidney beans", "butter", "cream", "tomato", "spices"], 20),
    "Chole Bhature": (["chickpeas", "wheat flour", "yoghurt", "onion", "tomato", "spices", "oil"], 20),
    "Veg Biryani": (["basmati rice", "mixed vegetables", "yoghurt", "onion", "herbs", "whole spices"], 25),
    "Chicken Biryani": (["basmati rice", "chicken", "yoghurt", "onion", "herbs", "saffron", "spices"], 30),
    "Butter Chicken": (["chicken", "tomato", "butter", "cream", "yoghurt", "spices"], 25),
    "Paneer Tikka": (["paneer", "bell peppers", "yoghurt", "ginger", "garlic", "tandoori spices"], 18),
    "Gobi Manchurian": (["cauliflower", "cornflour", "soy sauce", "garlic", "ginger", "spring onion"], 18),
    "Veg Spring Rolls": (["wheat wrappers", "cabbage", "carrot", "spring onion", "soy sauce"], 15),
    "Chicken 65": (["chicken", "yoghurt", "rice flour", "chilli", "curry leaves", "spices"], 20),
    "Chicken Tikka": (["chicken", "yoghurt", "ginger", "garlic", "tandoori spices"], 22),
    "Filter Coffee": (["coffee", "milk", "sugar"], 7),
    "Masala Chai": (["black tea", "milk", "ginger", "cardamom", "sugar"], 7),
    "Fresh Lime Soda": (["lime", "soda water", "sugar or salt"], 5),
    "Mango Lassi": (["mango", "yoghurt", "milk", "sugar"], 7),
    "Buttermilk": (["yoghurt", "water", "roasted cumin", "herbs", "salt"], 5),
    "Gulab Jamun": (["milk solids", "flour", "sugar", "cardamom", "ghee"], 10),
    "Rasmalai": (["chenna", "milk", "sugar", "saffron", "cardamom", "pistachio"], 12),
    "Gajar Ka Halwa": (["carrot", "milk", "ghee", "sugar", "nuts", "cardamom"], 12),
    "Kulfi": (["milk", "cream", "sugar", "cardamom", "pistachio"], 8),
}


def create_app(test_config=None):
    app = Flask(__name__)
    instance_dir = Path(app.instance_path)
    instance_dir.mkdir(parents=True, exist_ok=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("DINEEASE_SECRET_KEY", "local-development-key-change-before-deploy"),
        DATABASE=str(instance_dir / "dineease.sqlite3"),
        OPENAI_API_KEY=os.environ.get("OPENAI_API_KEY", ""),
        OPENAI_MODEL=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
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
                          is_vegetarian, available, image_url, image_source_url,
                          ingredients, preparation_minutes
                   FROM menu_items ORDER BY id"""
            ).fetchall()
        return jsonify(items=[
            {
                **dict(item),
                "is_vegetarian": bool(item["is_vegetarian"]),
                "available": bool(item["available"]),
                "ingredients": json.loads(item["ingredients"]),
            }
            for item in items
        ])

    @app.post("/api/chat")
    def chat():
        payload = request.get_json(silent=True) or {}
        message = str(payload.get("message", "")).strip()
        if not message:
            return jsonify(reply="Please type a message and I’ll help you."), 400
        had_flow = bool(session.get("flow"))
        if re.search(r"\b(combo|combos|combination|combinations|pairing|pairings)\b", message, re.I):
            result = {"reply": "Food combination suggestions are not available. You can browse the menu or ask about a specific dish."}
        elif had_flow:
            result = rule_based_food_reply(app.config["DATABASE"], message)
            if result is None:
                result = {"reply": respond(app.config["DATABASE"], message)}
        elif re.search(r"\b(show|view|browse)?\s*menu\b", message, re.I):
            result = {"reply": menu_reply(app.config["DATABASE"]), "show_menu": True}
        else:
            result = rule_based_food_reply(app.config["DATABASE"], message)
            rule_based_request = re.search(
                r"\b(book|reservation|reserve|cancel booking|check booking|booking status|"
                r"hours?|opening|closing|address|location|recommend|vegetarian|veggie|budget)\b",
                message,
                re.I,
            )
            if result is None and rule_based_request:
                result = {"reply": respond(app.config["DATABASE"], message)}
            elif result is None and not app.config["OPENAI_API_KEY"]:
                result = {"reply": respond(app.config["DATABASE"], message)}
            elif result is None:
                try:
                    intent = ask_openai(
                        app.config["OPENAI_API_KEY"],
                        app.config["OPENAI_MODEL"],
                        message,
                        get_menu_context(app.config["DATABASE"]),
                        session.get("cart", []),
                        session.get("latest_order_id"),
                        session.get("chat_history", []),
                    )
                except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as error:
                    app.logger.warning("OpenAI chat request failed: %s", error)
                    result = rule_based_food_reply(app.config["DATABASE"], message)
                    if result is None:
                        result = {"reply": respond(app.config["DATABASE"], message)}
                    result["ai_fallback"] = True
                else:
                    result = handle_ai_intent(app.config["DATABASE"], intent)
                    session.setdefault("chat_history", []).append(
                        {"user": message[:250], "assistant": result["reply"][:400]}
                    )
                    session["chat_history"] = session["chat_history"][-2:]
        session.modified = True
        if not had_flow and "menu" in message.casefold():
            result["show_menu"] = True
        flow = session.get("flow", {})
        if flow.get("kind") == "booking" and flow.get("step") == "date":
            result["input_type"] = "date"
            result["min_date"] = ist_today().isoformat()
        return jsonify(result)

    @app.get("/api/cart")
    def get_cart():
        return jsonify(cart=build_cart(app.config["DATABASE"], session.get("cart", [])))

    @app.post("/api/cart")
    def update_cart():
        payload = request.get_json(silent=True) or {}
        item_id = payload.get("item_id")
        quantity = payload.get("quantity")
        if not isinstance(item_id, int) or isinstance(item_id, bool):
            return jsonify(error="Select a valid menu item."), 400
        if not isinstance(quantity, int) or isinstance(quantity, bool) or not 1 <= quantity <= 20:
            return jsonify(error="Choose a quantity from 1 to 20."), 400

        with closing(connect_db(app.config["DATABASE"])) as connection:
            item = connection.execute(
                "SELECT id, name, available FROM menu_items WHERE id = ?", (item_id,)
            ).fetchone()
        if not item or not item["available"]:
            return jsonify(error="That menu item is unavailable."), 404

        cart = session.get("cart", [])
        quantities = {
            entry["item_id"]: entry["quantity"]
            for entry in cart
            if isinstance(entry.get("item_id"), int) and isinstance(entry.get("quantity"), int)
        }
        quantities[item_id] = min(20, quantities.get(item_id, 0) + quantity)
        session["cart"] = [
            {"item_id": selected_id, "quantity": selected_quantity}
            for selected_id, selected_quantity in quantities.items()
        ]
        return jsonify(cart=build_cart(app.config["DATABASE"], session["cart"]))

    @app.delete("/api/cart/<int:item_id>")
    def remove_cart_item(item_id):
        session["cart"] = [
            entry for entry in session.get("cart", [])
            if entry.get("item_id") != item_id
        ]
        return jsonify(cart=build_cart(app.config["DATABASE"], session["cart"]))

    @app.post("/api/orders")
    def place_demo_order():
        payload = request.get_json(silent=True) or {}
        order_type = payload.get("order_type")
        if order_type not in {"delivery", "pickup"}:
            return jsonify(error="Choose delivery or pickup."), 400
        requested_arrival = payload.get("requested_arrival")
        if requested_arrival is not None:
            try:
                arrival = datetime.fromisoformat(requested_arrival)
            except (TypeError, ValueError):
                return jsonify(error="Choose a valid requested arrival time."), 400
            if arrival <= datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None):
                return jsonify(error="Choose an arrival time in the future."), 400
        summary = build_cart(app.config["DATABASE"], session.get("cart", []))
        if not summary["items"]:
            return jsonify(error="Your cart is empty."), 400
        unavailable = [item["name"] for item in summary["items"] if not item["available"]]
        if unavailable:
            return jsonify(error=f"Unavailable items: {', '.join(unavailable)}."), 409
        order = create_demo_order(
            app.config["DATABASE"], summary, order_type, requested_arrival
        )
        session["cart"] = []
        session["latest_order_id"] = order["id"]
        return jsonify(order=order), 201

    @app.get("/api/orders/latest")
    def get_latest_order():
        order_id = session.get("latest_order_id")
        if not order_id:
            return jsonify(order=None)
        with closing(connect_db(app.config["DATABASE"])) as connection:
            order = connection.execute(
                """SELECT id, status, order_type, total_inr, items_json, requested_arrival,
                          prep_min_minutes, prep_max_minutes,
                          delivery_min_minutes, delivery_max_minutes, created_at
                   FROM orders WHERE id = ?""",
                (order_id,),
            ).fetchone()
        return jsonify(order=order_summary(order) if order else None)

    @app.get("/api/status")
    def get_status():
        return jsonify(
            ai_enabled=bool(app.config["OPENAI_API_KEY"]),
            rule_fallback_enabled=True,
            demo_orders=True,
        )

    @app.post("/api/reset")
    def reset_chat():
        session.pop("flow", None)
        session.pop("cart", None)
        session.pop("chat_history", None)
        return jsonify(reply="All set. What would you like to do next?")

    return app


def get_menu_context(database):
    with closing(connect_db(database)) as connection:
        rows = connection.execute(
            """SELECT id, name, category, description, price_inr, is_vegetarian,
                      available, ingredients, preparation_minutes
               FROM menu_items ORDER BY id"""
        ).fetchall()
    return [
        {
            **dict(row),
            "is_vegetarian": bool(row["is_vegetarian"]),
            "available": bool(row["available"]),
            "ingredients": json.loads(row["ingredients"]),
        }
        for row in rows
    ]


def ask_openai(api_key, model, message, menu, cart, latest_order_id, history=None):
    instructions = (
        "You are DineEase, a friendly restaurant ordering assistant. Use only the supplied menu "
        "and order context. Answer ingredient questions from the listed typical ingredients and "
        "always warn that recipes can vary and customers with allergies must confirm with staff. "
        "Do not suggest food combinations or pairings; that feature is not available. "
        "Never invent menu items, ingredients, prices, availability, delivery partners, or live tracking. "
        "Only add/remove menu items when the user requests it. Treat 'order X' as adding X to the cart; "
        "place an order only after the user clearly says checkout/place/confirm the order. Before placing, "
        "ask delivery or pickup if not specified. This app creates demo orders only, has no payment and "
        "does not dispatch food. Explain delivery time as a rough demo estimate, not live tracking. "
        "Use view_cart to review the cart, order_status for questions about a placed order or arrival time, "
        "and cancel_order only when the user explicitly asks to cancel. Call the respond tool with a concise "
        "user-facing reply and the appropriate action. Use exact menu item names and quantities for cart changes."
    )
    messages = [{"role": "system", "content": instructions}]
    messages.append({
        "role": "system",
        "content": (
            "Current menu JSON (ingredients are typical, not allergy guarantees): "
            + json.dumps(menu, ensure_ascii=False)
            + "\nCurrent cart JSON: "
            + json.dumps(cart, ensure_ascii=False)
            + f"\nLatest order ID: {latest_order_id or 'none'}"
        ),
    })
    for turn in (history or [])[-6:]:
        messages.extend([
            {"role": "user", "content": turn["user"]},
            {"role": "assistant", "content": turn["assistant"]},
        ])
    messages.append({"role": "user", "content": message})
    tool = {
        "type": "function",
        "function": {
            "name": "respond",
            "description": "Respond to the user and request a validated cart or order action.",
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "reply": {"type": "string"},
                    "action": {
                        "type": "string",
                        "enum": [
                            "chat", "add_to_cart", "remove_from_cart", "view_cart",
                            "place_order", "order_status", "cancel_order",
                        ],
                    },
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "name": {"type": "string"},
                                "quantity": {"type": "integer", "minimum": 1, "maximum": 20},
                            },
                            "required": ["name", "quantity"],
                        },
                    },
                    "order_type": {
                        "type": "string",
                        "enum": ["delivery", "pickup", "unspecified"],
                    },
                },
                "required": ["reply", "action", "items", "order_type"],
            },
        },
    }
    request = UrlRequest(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": messages,
            "tools": [tool],
            "tool_choice": {"type": "function", "function": {"name": "respond"}},
            "temperature": 0.3,
        }).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=25) as response:
        result = json.loads(response.read().decode("utf-8"))
    arguments = result["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"]
    intent = json.loads(arguments)
    if not isinstance(intent, dict) or not isinstance(intent.get("reply"), str):
        raise ValueError("OpenAI returned an invalid assistant response")
    return intent


def build_cart(database, cart):
    cart_by_id = {}
    for entry in cart:
        item_id = entry.get("item_id")
        quantity = entry.get("quantity")
        if isinstance(item_id, int) and isinstance(quantity, int) and 1 <= quantity <= 20:
            cart_by_id[item_id] = min(20, cart_by_id.get(item_id, 0) + quantity)
    if not cart_by_id:
        return {"items": [], "total_inr": 0}
    placeholders = ",".join("?" for _ in cart_by_id)
    with closing(connect_db(database)) as connection:
        rows = connection.execute(
            f"""SELECT id, name, price_inr, available FROM menu_items
                WHERE id IN ({placeholders}) ORDER BY id""",
            list(cart_by_id),
        ).fetchall()
    items = [
        {
            "item_id": row["id"],
            "name": row["name"],
            "quantity": cart_by_id[row["id"]],
            "unit_price_inr": row["price_inr"],
            "line_total_inr": cart_by_id[row["id"]] * row["price_inr"],
            "available": bool(row["available"]),
        }
        for row in rows
    ]
    return {"items": items, "total_inr": sum(item["line_total_inr"] for item in items)}


def handle_ai_intent(database, intent):
    action = intent.get("action", "chat")
    reply = intent["reply"].strip()
    if not reply:
        reply = "What would you like to order?"
    requested_items = intent.get("items", [])
    item_by_name = {
        item["name"].casefold(): item
        for item in get_menu_context(database)
        if item["available"]
    }
    selected_items = []
    for requested in requested_items:
        if not isinstance(requested, dict):
            continue
        name = requested.get("name", "")
        quantity = requested.get("quantity")
        if not isinstance(name, str) or not isinstance(quantity, int) or isinstance(quantity, bool) or not 1 <= quantity <= 20:
            continue
        item = item_by_name.get(name.casefold())
        if item:
            selected_items.append((item, quantity))

    order_type = intent.get("order_type", "unspecified")
    if order_type in {"delivery", "pickup"}:
        session["order_type"] = order_type
    if action == "add_to_cart":
        if not selected_items:
            return {"reply": "I couldn’t match those items to our available menu. Which listed dish would you like?"}
        cart = session.get("cart", [])
        quantities = {
            entry["item_id"]: entry["quantity"]
            for entry in cart
            if isinstance(entry.get("item_id"), int) and isinstance(entry.get("quantity"), int)
        }
        for item, quantity in selected_items:
            quantities[item["id"]] = min(20, quantities.get(item["id"], 0) + quantity)
        session["cart"] = [
            {"item_id": item_id, "quantity": quantity}
            for item_id, quantity in quantities.items()
        ]
        summary = build_cart(database, session["cart"])
        lines = ", ".join(f"{item['quantity']} × {item['name']}" for item in summary["items"])
        return {"reply": f"Added to your demo cart: {lines}. Cart total: ₹{summary['total_inr']}. Say “show my cart” to review or “place my order” when you’re ready."}
    if action == "remove_from_cart":
        remove = {item["id"]: quantity for item, quantity in selected_items}
        cart = session.get("cart", [])
        for entry in cart:
            item_id = entry.get("item_id")
            if item_id in remove:
                entry["quantity"] -= remove[item_id]
        session["cart"] = [entry for entry in cart if entry.get("quantity", 0) > 0]
        summary = build_cart(database, session["cart"])
        return {"reply": f"Updated your cart. It now contains {len(summary['items'])} dish types and totals ₹{summary['total_inr']}."}
    if action == "view_cart":
        summary = build_cart(database, session.get("cart", []))
        if not summary["items"]:
            return {"reply": "Your cart is empty. Tell me which available menu items you’d like to add."}
        lines = ", ".join(f"{item['quantity']} × {item['name']} (₹{item['line_total_inr']})" for item in summary["items"])
        return {"reply": f"Your cart: {lines}. Total: ₹{summary['total_inr']}. Demo order only; no payment is taken."}
    if action == "place_order":
        cart = session.get("cart", [])
        summary = build_cart(database, cart)
        if not summary["items"]:
            return {"reply": "Your cart is empty. Add menu items before placing a demo order."}
        unavailable = [item["name"] for item in summary["items"] if not item["available"]]
        if unavailable:
            return {"reply": f"These cart items are no longer available: {', '.join(unavailable)}. Remove them or choose another dish before placing the order."}
        chosen_type = session.get("order_type")
        if order_type in {"delivery", "pickup"}:
            chosen_type = order_type
        if chosen_type not in {"delivery", "pickup"}:
            session["pending_order"] = True
            return {"reply": "Would you like this demo order for delivery or pickup? There is no payment or real dispatch."}
        order = create_demo_order(database, summary, chosen_type)
        session["cart"] = []
        session["pending_order"] = False
        session["latest_order_id"] = order["id"]
        session.pop("order_type", None)
        if chosen_type == "delivery":
            timing = (
                f"Estimated delivery window: {order['arrival_min']}–{order['arrival_max']} "
                f"({order['arrival_start']}–{order['arrival_end']} IST). This is a demo estimate, "
                "not live courier tracking."
            )
        else:
            timing = (
                f"Estimated pickup-ready window: {order['prep_min']}–{order['prep_max']} minutes "
                f"({order['ready_start']}–{order['ready_end']} IST)."
            )
        return {
            "reply": (
                f"Demo order {order['id']} confirmed (no payment or restaurant dispatch). "
                f"Total: ₹{order['total_inr']}. Estimated kitchen preparation: "
                f"{order['prep_min']}–{order['prep_max']} minutes. {timing}"
            ),
            "order_id": order["id"],
        }
    if action == "order_status":
        order_id = session.get("latest_order_id")
        if not order_id:
            return {"reply": "I don’t see an order placed in this chat yet."}
        with closing(connect_db(database)) as connection:
            row = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return {"reply": format_order_status(row) if row else "I couldn’t find the latest order in this session."}
    if action == "cancel_order":
        order_id = session.get("latest_order_id")
        if not order_id:
            return {"reply": "There is no demo order in this chat to cancel."}
        with closing(connect_db(database)) as connection:
            connection.execute(
                "UPDATE orders SET status = 'cancelled' WHERE id = ? AND status = 'confirmed'",
                (order_id,),
            )
            connection.commit()
        return {"reply": f"Demo order {order_id} has been cancelled."}

    if session.get("pending_order") and order_type in {"delivery", "pickup"}:
        return handle_ai_intent(database, {
            **intent,
            "action": "place_order",
            "order_type": order_type,
        })
    return {"reply": reply}


def rule_based_food_reply(database, message):
    normalized = message.casefold().strip()
    menu = get_menu_context(database)
    available = [item for item in menu if item["available"]]
    name_matches = []
    for item in sorted(available, key=lambda entry: len(entry["name"]), reverse=True):
        match = re.search(rf"(?<!\w){re.escape(item['name'].casefold())}(?!\w)", normalized)
        if match:
            name_matches.append((item, match.start(), match.end()))

    aliases = {
        "dosa": "Masala Dosa",
        "idli": "Idli Sambar",
        "vada": "Medu Vada",
        "uttapam": "Onion Uttapam",
        "naan": "Butter Naan",
        "biryani": "Veg Biryani",
        "coffee": "Filter Coffee",
        "chai": "Masala Chai",
        "tea": "Masala Chai",
    }
    mentions = list(name_matches)
    for alias, item_name in aliases.items():
        match = re.search(rf"(?<!\w){re.escape(alias)}s?(?!\w)", normalized)
        if match and not any(
            start <= match.start() < end
            for _, start, end in name_matches
        ):
            item = next((entry for entry in available if entry["name"] == item_name), None)
            if item:
                mentions.append((item, match.start(), match.end()))

    quantity_words = {
        "one": 1, "a": 1, "an": 1, "two": 2, "three": 3, "four": 4,
        "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    }
    selected = {}
    for item, start, end in sorted(mentions, key=lambda entry: entry[1]):
        prefix = normalized[max(0, start - 20):start]
        quantity_match = re.search(r"\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|a|an)\s*(?:x\s*)?$", prefix)
        quantity = 1
        if quantity_match:
            raw_quantity = quantity_match.group(1)
            quantity = int(raw_quantity) if raw_quantity.isdigit() else quantity_words[raw_quantity]
        selected[item["id"]] = (item, min(quantity, 20))

    if re.search(r"\b(ingredient|ingredients|made of|what's in|what is in|contain)\b", normalized):
        if not selected:
            return {"reply": "Which menu dish would you like ingredient information for? You can also browse all dishes in the menu."}
        item = next(iter(selected.values()))[0]
        ingredients = ", ".join(item["ingredients"]) or "not listed"
        return {
            "reply": (
                f"Typical ingredients in {item['name']}: {ingredients}. Recipes can vary. The menu "
                "does not include a complete ingredient or allergen list; please confirm allergy "
                "requirements and allergens with restaurant staff."
            )
        }

    if re.search(r"\b(arrive|arrival|eta|delivery time|how long|when will|ready time)\b", normalized):
        order_id = session.get("latest_order_id")
        if order_id:
            with closing(connect_db(database)) as connection:
                order = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
            return {"reply": format_order_status(order) if order else "I couldn’t find an order in this chat."}
        if selected:
            item = next(iter(selected.values()))[0]
            return {
                "reply": (
                    f"{item['name']} takes about {item['preparation_minutes']} minutes to prepare. "
                    "A delivery estimate is available after checkout; timing is illustrative, not live tracking."
                )
            }
        return {"reply": "Place a demo order to see its estimated preparation and delivery window. Estimates are not live tracking."}

    if re.search(r"\b(show|view|what is in|my)\b.*\bcart\b|\bcart\b", normalized):
        cart = build_cart(database, session.get("cart", []))
        if not cart["items"]:
            return {"reply": "Your cart is empty. Tell me which available menu dishes you’d like to add."}
        lines = ", ".join(
            f"{item['quantity']} × {item['name']} (₹{item['line_total_inr']})"
            for item in cart["items"]
        )
        return {"reply": f"Your cart: {lines}. Total: ₹{cart['total_inr']}. Demo order only; no payment is taken."}

    if re.search(r"\b(cancel|remove|delete)\b.*\b(order|demo order)\b", normalized):
        order_id = session.get("latest_order_id")
        if not order_id:
            return {"reply": "There is no demo order in this chat to cancel."}
        with closing(connect_db(database)) as connection:
            connection.execute(
                "UPDATE orders SET status = 'cancelled' WHERE id = ? AND status = 'confirmed'",
                (order_id,),
            )
            connection.commit()
        return {"reply": f"Demo order {order_id} has been cancelled."}

    if re.search(r"\b(remove|delete|take out)\b", normalized) and selected:
        remove = {item_id: quantity for item_id, (_, quantity) in selected.items()}
        cart = session.get("cart", [])
        for entry in cart:
            if entry.get("item_id") in remove:
                entry["quantity"] -= remove[entry["item_id"]]
        session["cart"] = [entry for entry in cart if entry.get("quantity", 0) > 0]
        updated = build_cart(database, session["cart"])
        return {"reply": f"Removed the requested dishes. Your cart total is now ₹{updated['total_inr']}."}

    if session.get("pending_order") and re.search(r"\b(delivery|deliver|pickup|pick up)\b", normalized):
        order_type = "pickup" if re.search(r"\b(pickup|pick up)\b", normalized) else "delivery"
        cart = build_cart(database, session.get("cart", []))
        if not cart["items"]:
            session["pending_order"] = False
            return {"reply": "Your cart is empty. Add a dish before placing a demo order."}
        order = create_demo_order(database, cart, order_type)
        session["cart"] = []
        session["pending_order"] = False
        session["latest_order_id"] = order["id"]
        return {"reply": format_order_status({
            **order,
            "status": "confirmed",
            "items_json": json.dumps(cart["items"]),
            "prep_min_minutes": order["prep_min"],
            "prep_max_minutes": order["prep_max"],
            "delivery_min_minutes": order["arrival_min"],
            "delivery_max_minutes": order["arrival_max"],
            "created_at": datetime.now(ZoneInfo("Asia/Kolkata")).replace(second=0, microsecond=0).isoformat(),
        }), "order_id": order["id"]}

    if re.search(r"\b(checkout|place (?:my )?order|confirm (?:my )?order|buy now)\b", normalized):
        cart = build_cart(database, session.get("cart", []))
        if not cart["items"]:
            return {"reply": "Your cart is empty. Add a dish before placing a demo order."}
        session["pending_order"] = True
        return {"reply": "Would you like this demo order for delivery or pickup? There is no payment or real dispatch."}

    order_request = bool(re.search(r"\b(add|order|want|would like|i'd like|i would like|can i have|give me|get me)\b", normalized))
    if order_request and selected:
        quantities = {
            entry["item_id"]: entry["quantity"]
            for entry in session.get("cart", [])
            if isinstance(entry.get("item_id"), int) and isinstance(entry.get("quantity"), int)
        }
        for item_id, (_, quantity) in selected.items():
            quantities[item_id] = min(20, quantities.get(item_id, 0) + quantity)
        session["cart"] = [
            {"item_id": item_id, "quantity": quantity}
            for item_id, quantity in quantities.items()
        ]
        cart = build_cart(database, session["cart"])
        lines = ", ".join(f"{item['quantity']} × {item['name']}" for item in cart["items"])
        return {"reply": f"Added to your demo cart: {lines}. Total: ₹{cart['total_inr']}. Say “show my cart” or “checkout” when you’re ready."}

    if selected and re.search(r"\b(price|cost|ingredients?|describe|description|available|vegetarian|non.?veg)\b", normalized):
        answer = answer_restaurant_question(database, normalized)
        if answer:
            return {"reply": answer}

    return None


def create_demo_order(database, cart, order_type, requested_arrival=None):
    prep_min = max(item["preparation_minutes"] for item in get_menu_context(database) if any(
        selected["item_id"] == item["id"] for selected in cart["items"]
    ))
    prep_min += min(15, max(0, (len(cart["items"]) - 1) * 3))
    prep_max = prep_min + 10
    delivery_min = prep_min + 20
    delivery_max = prep_max + 30
    order_id = "DEO-" + uuid.uuid4().hex[:8].upper()
    created = datetime.now(ZoneInfo("Asia/Kolkata")).replace(second=0, microsecond=0)
    connection = connect_db(database)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """INSERT INTO orders
               (id, status, order_type, total_inr, items_json, prep_min_minutes,
                prep_max_minutes, delivery_min_minutes, delivery_max_minutes,
                requested_arrival, created_at)
               VALUES (?, 'confirmed', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                order_id, order_type, cart["total_inr"],
                json.dumps(cart["items"], ensure_ascii=False),
                prep_min, prep_max, delivery_min, delivery_max,
                requested_arrival, created.isoformat(),
            ),
        )
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback()
        raise
    finally:
        connection.close()
    return {
        "id": order_id,
        "order_type": order_type,
        "total_inr": cart["total_inr"],
        "prep_min": prep_min,
        "prep_max": prep_max,
        "arrival_min": delivery_min,
        "arrival_max": delivery_max,
        "requested_arrival": requested_arrival,
        "ready_start": (created + timedelta(minutes=prep_min)).strftime("%I:%M %p").lstrip("0"),
        "ready_end": (created + timedelta(minutes=prep_max)).strftime("%I:%M %p").lstrip("0"),
        "arrival_start": (created + timedelta(minutes=delivery_min)).strftime("%I:%M %p").lstrip("0"),
        "arrival_end": (created + timedelta(minutes=delivery_max)).strftime("%I:%M %p").lstrip("0"),
    }


def order_summary(order):
    if not order:
        return None
    result = dict(order)
    result["items"] = json.loads(result.pop("items_json"))
    created = datetime.fromisoformat(result["created_at"])
    result["ready_start"] = (created + timedelta(minutes=result["prep_min_minutes"])).strftime("%I:%M %p").lstrip("0")
    result["ready_end"] = (created + timedelta(minutes=result["prep_max_minutes"])).strftime("%I:%M %p").lstrip("0")
    result["arrival_start"] = (created + timedelta(minutes=result["delivery_min_minutes"])).strftime("%I:%M %p").lstrip("0")
    result["arrival_end"] = (created + timedelta(minutes=result["delivery_max_minutes"])).strftime("%I:%M %p").lstrip("0")
    return result


def format_order_status(order):
    result = order_summary(order)
    if result["status"] == "cancelled":
        return f"Demo order {result['id']} is cancelled."
    if result["order_type"] == "pickup":
        return (
            f"Demo order {result['id']} is confirmed for pickup. Estimated ready "
            f"{result['ready_start']}–{result['ready_end']} IST."
        )
    return (
        f"Demo order {result['id']} is confirmed for delivery. Estimated arrival "
        f"{result['arrival_start']}–{result['arrival_end']} IST; this is not live courier tracking."
    )


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
                image_url TEXT NOT NULL,
                image_source_url TEXT NOT NULL DEFAULT '',
                ingredients TEXT NOT NULL DEFAULT '[]',
                preparation_minutes INTEGER NOT NULL DEFAULT 15 CHECK (preparation_minutes > 0)
            );
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'confirmed',
                order_type TEXT NOT NULL CHECK (order_type IN ('delivery', 'pickup')),
                total_inr INTEGER NOT NULL CHECK (total_inr >= 0),
                items_json TEXT NOT NULL,
                prep_min_minutes INTEGER NOT NULL,
                prep_max_minutes INTEGER NOT NULL,
                delivery_min_minutes INTEGER NOT NULL,
                delivery_max_minutes INTEGER NOT NULL,
                requested_arrival TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        columns = {
            column["name"]
            for column in connection.execute("PRAGMA table_info(menu_items)").fetchall()
        }
        if "image_source_url" not in columns:
            connection.execute(
                "ALTER TABLE menu_items ADD COLUMN image_source_url TEXT NOT NULL DEFAULT ''"
            )
        if "ingredients" not in columns:
            connection.execute(
                "ALTER TABLE menu_items ADD COLUMN ingredients TEXT NOT NULL DEFAULT '[]'"
            )
        if "preparation_minutes" not in columns:
            connection.execute(
                "ALTER TABLE menu_items ADD COLUMN preparation_minutes INTEGER NOT NULL DEFAULT 15"
            )
        order_columns = {
            column["name"]
            for column in connection.execute("PRAGMA table_info(orders)").fetchall()
        }
        if "requested_arrival" not in order_columns:
            connection.execute("ALTER TABLE orders ADD COLUMN requested_arrival TEXT")
        if connection.execute("SELECT COUNT(*) FROM restaurant_tables").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO restaurant_tables(seats) VALUES (?)",
                [(2,), (2,), (4,), (4,), (6,), (8,)],
            )
        connection.executemany(
            """INSERT OR IGNORE INTO menu_items
               (name, category, description, price_inr, is_vegetarian, available,
                image_url, image_source_url, ingredients, preparation_minutes)
               VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?)""",
            [
                (*dish, *MENU_IMAGES[dish[0]], json.dumps(MENU_DETAILS[dish[0]][0]),
                 MENU_DETAILS[dish[0]][1])
                for dish in INDIAN_MENU
            ],
        )
        connection.executemany(
            """UPDATE menu_items
               SET image_url = ?, image_source_url = ?, ingredients = ?, preparation_minutes = ?
               WHERE name = ?""",
            [
                (image, source, json.dumps(MENU_DETAILS[name][0]), MENU_DETAILS[name][1], name)
                for name, (image, source) in MENU_IMAGES.items()
            ],
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
    normalized = message.casefold()
    budget_match = re.search(
        r"(?:₹|rs\.?|inr)\s*(\d+(?:\.\d{1,2})?)|"
        r"\b(?:under|below|within|budget(?:\s+of)?|less than|up to|max(?:imum)?(?:\s+budget)?)"
        r"\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d{1,2})?)",
        message,
        re.IGNORECASE,
    )
    budget = float(next(value for value in budget_match.groups() if value)) if budget_match else None
    non_vegetarian = bool(re.search(r"\b(non[- ]?veg(?:etarian)?|chicken|meat)\b", normalized))
    vegetarian = not non_vegetarian and bool(
        re.search(r"\b(vegetarian|veggie|veg|meat-free)\b", normalized)
    )
    query = "SELECT name, price_inr, is_vegetarian FROM menu_items WHERE available = 1"
    parameters = []
    if vegetarian:
        query += " AND is_vegetarian = 1"
    elif non_vegetarian:
        query += " AND is_vegetarian = 0"
    if "dessert" in normalized or "sweet" in normalized:
        query += " AND category = 'Desserts'"
    elif "drink" in normalized or "beverage" in normalized:
        query += " AND category = 'Beverages'"
    if budget is not None:
        query += " AND price_inr <= ?"
        parameters.append(budget)
    with closing(connect_db(database)) as connection:
        candidates = connection.execute(query + " ORDER BY price_inr LIMIT 5", parameters).fetchall()
    if not candidates:
        return "I don’t see an available menu item matching that budget and preference. Try another budget or ask to see the menu."
    picks = ", ".join(f"{item['name']} (₹{item['price_inr']})" for item in candidates)
    return f"Based on the menu details, these may fit: {picks}. Ask to see the menu for the full list."


def answer_restaurant_question(database, message):
    normalized = message.casefold().strip()

    if re.search(r"\b(party size|guests?|people|large group)\b", normalized) and re.search(
        r"\b(book|booking|reservation|table|seat|accommodate|capacity|bring|fit)\b", normalized
    ):
        return "We can take reservations for parties of 1 to 8 people."
    if re.search(r"\b(seating times?|reservation times?)\b", normalized) or re.search(
        r"\b(book|reservation)\b.*\b(times?|available)\b", normalized
    ):
        times = ", ".join(format_time(slot) for slot in TIME_SLOTS)
        return f"Reservation times are {times}."
    if re.search(r"\b(hours?|opening|closing)\b", normalized) or re.search(
        r"\b(?:when|what time)\b.*\b(?:open|close)\b|\b(?:are you|is the restaurant)\s+(?:open|closed)\b",
        normalized,
    ):
        return "We’re open daily from 5:00 PM to 9:00 PM."
    if re.search(r"\b(address|location|located)\b", normalized) or re.search(
        r"\bwhere\b.*\b(?:restaurant|you|find)\b", normalized
    ):
        return "This demo restaurant is at 14 Garden Street."
    if re.search(r"\b(delivery|deliver|takeaway|take away)\b", normalized):
        return "I don’t have confirmed delivery or takeaway information for this restaurant."

    with closing(connect_db(database)) as connection:
        items = connection.execute(
            """SELECT name, category, description, price_inr, is_vegetarian, available
               FROM menu_items ORDER BY id"""
        ).fetchall()

    item = next(
        (
            candidate for candidate in items
            if re.search(rf"(?<!\w){re.escape(candidate['name'].casefold())}(?!\w)", normalized)
        ),
        None,
    )
    if item:
        if re.search(r"\b(allerg(y|ies)|allergen|gluten|nuts?|dairy|ingredients?)\b", normalized):
            return (
                f"The menu description says: {item['description']} "
                "It does not include a complete ingredient or allergen list, so please confirm "
                "allergy requirements with restaurant staff before ordering."
            )
        if re.search(r"\b(vegan|halal|gluten.?free|nut.?free)\b", normalized):
            return f"The menu does not confirm whether {item['name']} is vegan, halal, gluten-free, or nut-free. Please check with restaurant staff before ordering."
        if re.search(r"\b(price|cost|much|₹|rupees?)\b", normalized):
            return f"{item['name']} is ₹{item['price_inr']}."
        if re.search(r"\b(vegetarian|non.?veg|meat|chicken|veg)\b", normalized):
            diet = "vegetarian" if item["is_vegetarian"] else "non-vegetarian"
            return f"{item['name']} is listed as {diet}."
        if re.search(r"\b(available|in stock|order|do you have|serve|offer)\b", normalized):
            status = "currently available" if item["available"] else "currently unavailable"
            return f"{item['name']} is {status}."
        if not item["available"]:
            return f"{item['name']} is currently unavailable."
        if re.search(r"\b(what is|what's|describe|description|tell me about|menu description|show)\b", normalized):
            return f"{item['name']} (₹{item['price_inr']}) — {item['description']}"
        return (
            f"I don’t have confirmed information to answer that about {item['name']}. "
            "I can confirm its menu description, price, and vegetarian label."
        )

    if re.search(r"\b(vegetarian|veggie|veg dishes|veg options)\b", normalized):
        dishes = [item["name"] for item in items if item["is_vegetarian"] and item["available"]]
        return "Vegetarian dishes on the menu include: " + ", ".join(dishes) + "."
    if re.search(r"\b(non.?veg|meat|chicken dishes)\b", normalized):
        dishes = [item["name"] for item in items if not item["is_vegetarian"] and item["available"]]
        return "Non-vegetarian dishes on the menu include: " + ", ".join(dishes) + "."
    if re.search(r"\b(vegan|halal|gluten.?free|nut.?free)\b", normalized):
        return "The menu does not confirm that dishes are vegan, halal, gluten-free, or nut-free. Please check with restaurant staff before ordering."

    if "menu" in normalized:
        return menu_reply(database)
    return None


def respond(database, message):
    normalized = message.casefold().strip()
    flow = session.get("flow")

    if normalized in {"restart", "start over", "reset"}:
        session.pop("flow", None)
        return "No problem. What would you like to do? You can book a table, check a booking, cancel a booking, or view the menu."

    if re.search(r"\b(what|when|where|which|how|is|are|do|does|can|could|tell me|menu)\b", normalized) or "?" in normalized:
        answer = answer_restaurant_question(database, normalized)
        if answer:
            return answer

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
    if any(term in normalized for term in ("recommend", "suggest", "vegetarian", "veggie", "budget", "under ₹", "under rs")):
        return recommendation_reply(database, message)
    if any(term in normalized for term in ("hour", "open", "address", "location", "where are")):
        answer = answer_restaurant_question(database, normalized)
        if answer:
            return answer
    if any(term in normalized for term in ("hello", "hi", "hey")):
        return "Hi there! I can book a table, check or cancel a reservation, show the menu, and answer basic questions. What can I help with?"
    return (
        "I don’t have enough confirmed information to answer that accurately. I can help with "
        "reservations, menu prices and descriptions, dietary labels, opening hours, or the restaurant location."
    )


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")