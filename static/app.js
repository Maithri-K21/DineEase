const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const messages = document.querySelector("#messages");
const sendButton = document.querySelector("#send-button");
const quickActions = document.querySelector(".quick-actions");
const menuPanel = document.querySelector("#menu-panel");
const menuGrid = document.querySelector("#menu-grid");
const menuSearch = document.querySelector("#menu-search");
const menuCategory = document.querySelector("#menu-category");
const menuDiet = document.querySelector("#menu-diet");
const menuCount = document.querySelector("#menu-count");
const menuError = document.querySelector("#menu-error");
const retryMenu = document.querySelector("#retry-menu");
const dateSelection = document.querySelector("#date-selection");
const cartItems = document.querySelector("#cart-items");
const orderType = document.querySelector("#order-type");
const requestedArrival = document.querySelector("#requested-arrival");
const placeOrderButton = document.querySelector("#place-order");
const orderError = document.querySelector("#order-error");
const checkoutResult = document.querySelector("#checkout-result");
let menuItems = [];

function istDateTimeLocal() {
  return new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(new Date()).replace(" ", "T");
}

if (requestedArrival) requestedArrival.min = istDateTimeLocal();

function showChat() {
  document.querySelector(".conversation").hidden = false;
  menuPanel.hidden = true;
  input.type = "text";
  input.removeAttribute("min");
  input.placeholder = "Type a message...";
  dateSelection.hidden = true;
}

function showMenu() {
  document.querySelector(".conversation").hidden = true;
  menuPanel.hidden = false;
  dateSelection.hidden = true;
  loadMenu();
}

function setInputMode(result) {
  if (result.input_type === "date") {
    input.type = "date";
    input.min = result.min_date;
    input.setAttribute("aria-label", "Choose a reservation date");
    input.placeholder = "";
    dateSelection.hidden = false;
    dateSelection.textContent = input.value ? `Selected date: ${formatIsoDate(input.value)}` : "Choose a date from today onward.";
    return;
  }
  input.type = "text";
  input.removeAttribute("min");
  input.setAttribute("aria-label", "Your message");
  input.placeholder = "Type a message...";
  dateSelection.hidden = true;
}

function formatIsoDate(value) {
  const [year, month, day] = value.split("-");
  return `${day}-${month}-${year}`;
}

function renderMenu() {
  const search = menuSearch.value.trim().toLocaleLowerCase();
  const category = menuCategory.value;
  const diet = menuDiet.value;
  const filtered = menuItems.filter((item) => {
    const ingredients = Array.isArray(item.ingredients) ? item.ingredients.join(" ") : "";
    const matchesText = `${item.name} ${item.description} ${item.category} ${ingredients}`.toLocaleLowerCase().includes(search);
    const matchesCategory = category === "all" || item.category === category;
    const matchesDiet = diet === "all" || (diet === "veg" ? item.is_vegetarian : !item.is_vegetarian);
    return matchesText && matchesCategory && matchesDiet;
  });

  menuCount.textContent = `${filtered.length} dishes · Prices in Indian rupees`;
  menuGrid.replaceChildren();
  if (!filtered.length) {
    const empty = document.createElement("p");
    empty.className = "menu-empty";
    empty.textContent = "No dishes match those filters.";
    menuGrid.append(empty);
    return;
  }

  for (const item of filtered) {
    const card = document.createElement("article");
    card.className = "menu-card";
    const photoWrap = document.createElement("div");
    photoWrap.className = "menu-photo-wrap";
    const photo = document.createElement("img");
    photo.className = "menu-photo";
    photo.src = item.image_url;
    photo.alt = item.name;
    photo.loading = "lazy";
    photo.addEventListener("error", () => photo.remove(), { once: true });

    if (item.image_source_url) {
      const photoCredit = document.createElement("a");
      photoCredit.className = "photo-credit";
      photoCredit.href = item.image_source_url;
      photoCredit.target = "_blank";
      photoCredit.rel = "noopener noreferrer";
      photoCredit.textContent = "Photo source & license";
      photoCredit.setAttribute("aria-label", `Photo source and license for ${item.name}`);
      photoWrap.append(photoCredit);
    }

    const dietBadge = document.createElement("span");
    dietBadge.className = `diet-badge${item.is_vegetarian ? "" : " nonveg"}`;
    const marker = document.createElement("span");
    marker.className = "diet-mark";
    marker.setAttribute("aria-hidden", "true");
    dietBadge.append(marker, document.createTextNode(item.is_vegetarian ? "VEG" : "NON-VEG"));

    const availability = document.createElement("span");
    availability.className = `availability-badge${item.available ? "" : " unavailable"}`;
    availability.textContent = item.available ? "Available" : "Currently unavailable";
    photoWrap.append(photo, dietBadge, availability);

    const content = document.createElement("div");
    content.className = "menu-card-content";
    const heading = document.createElement("div");
    heading.className = "menu-card-top";
    const name = document.createElement("h2");
    name.textContent = item.name;
    const price = document.createElement("span");
    price.className = "menu-price";
    price.textContent = `₹${item.price_inr}`;
    heading.append(name, price);
    const description = document.createElement("p");
    description.className = "menu-description";
    description.textContent = item.description;
    const ingredients = document.createElement("details");
    ingredients.className = "menu-ingredients";
    const ingredientsSummary = document.createElement("summary");
    ingredientsSummary.textContent = "Typical ingredients";
    const ingredientList = document.createElement("p");
    const ingredientListItems = Array.isArray(item.ingredients) ? item.ingredients : [];
    ingredientList.textContent = ingredientListItems.length
      ? ingredientListItems.join(", ")
      : "Ingredient information is not available yet.";
    const ingredientNote = document.createElement("small");
    ingredientNote.textContent = "Recipes can vary. Please confirm allergens with restaurant staff.";
    ingredients.append(ingredientsSummary, ingredientList, ingredientNote);
    const preparation = document.createElement("p");
    preparation.className = "menu-preparation";
    preparation.textContent = Number.isFinite(item.preparation_minutes)
      ? `Estimated prep: ${item.preparation_minutes} min`
      : "Preparation estimate unavailable";
    const orderControls = document.createElement("div");
    orderControls.className = "menu-order-controls";
    const quantityLabel = document.createElement("label");
    quantityLabel.className = "quantity-label";
    quantityLabel.textContent = "Qty";
    const quantity = document.createElement("input");
    quantity.type = "number";
    quantity.min = "1";
    quantity.max = "20";
    quantity.value = "1";
    quantity.setAttribute("aria-label", `Quantity for ${item.name}`);
    const orderButton = document.createElement("button");
    orderButton.className = "menu-order-button";
    orderButton.type = "button";
    orderButton.dataset.itemId = item.id;
    orderButton.textContent = "Add to order";
    orderControls.append(quantityLabel, quantity, orderButton);
    content.append(heading, description, ingredients, preparation, orderControls);
    card.append(photoWrap, content);
    menuGrid.append(card);
  }
}

async function loadMenu() {
  menuError.hidden = true;
  if (retryMenu) retryMenu.hidden = true;
  menuGrid.replaceChildren();
  menuCount.textContent = "Loading menu...";
  try {
    const response = await fetch("/api/menu");
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `Menu request failed (${response.status})`);
    }
    const result = await response.json();
    if (!Array.isArray(result.items)) throw new Error("Menu response is missing its items list.");
    menuItems = result.items;
    renderMenu();
    try {
      await loadCart();
    } catch (error) {
      console.error("Could not load cart:", error);
      if (orderError) {
        orderError.textContent = "Your cart could not be loaded. Please retry.";
        orderError.hidden = false;
      }
    }
  } catch (error) {
    menuCount.textContent = "";
    console.error("Could not load menu:", error);
    menuError.textContent = `The menu could not be loaded: ${error.message}`;
    menuError.hidden = false;
    if (retryMenu) retryMenu.hidden = false;
  }
}

function renderCart(cart) {
  cartItems.replaceChildren();
  if (!cart.items.length) {
    cartItems.textContent = "Your cart is empty.";
    return;
  }
  for (const item of cart.items) {
    const row = document.createElement("div");
    row.className = "cart-row";
    const label = document.createElement("span");
    label.textContent = `${item.quantity} × ${item.name} · ₹${item.line_total_inr}`;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "cart-remove";
    remove.dataset.removeItemId = item.item_id;
    remove.textContent = "Remove";
    remove.setAttribute("aria-label", `Remove ${item.name} from order`);
    row.append(label, remove);
    cartItems.append(row);
  }
  const total = document.createElement("strong");
  total.className = "cart-total";
  total.textContent = `Total: ₹${cart.total_inr}`;
  cartItems.append(total);
}

async function loadCart() {
  const response = await fetch("/api/cart");
  if (!response.ok) throw new Error(`Cart request failed (${response.status})`);
  const result = await response.json();
  renderCart(result.cart);
}

async function updateCart(itemId, quantity) {
  const response = await fetch("/api/cart", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item_id: Number(itemId), quantity }),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Could not update your cart.");
  renderCart(result.cart);
}

async function checkout() {
  orderError.hidden = true;
  checkoutResult.hidden = true;
  if (!requestedArrival.value) {
    orderError.textContent = "Choose your requested arrival or pickup time first.";
    orderError.hidden = false;
    return;
  }
  placeOrderButton.disabled = true;
  try {
    const response = await fetch("/api/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        order_type: orderType.value,
        requested_arrival: requestedArrival.value,
      }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not place demo order.");
    const order = result.order;
    const requested = order.requested_arrival
      ? new Intl.DateTimeFormat([], {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "Asia/Kolkata",
      })
        .format(new Date(`${order.requested_arrival}:00+05:30`))
      : "not selected";
    checkoutResult.textContent =
      `Demo order ${order.id} confirmed. Requested arrival/pickup: ${requested}. ` +
      `Estimated preparation: ${order.prep_min}–${order.prep_max} minutes. ` +
      (order.order_type === "delivery"
        ? `Estimated delivery window: ${order.arrival_min}–${order.arrival_max} minutes after checkout (${order.arrival_start}–${order.arrival_end} IST). `
        : `Estimated pickup-ready: ${order.ready_start}–${order.ready_end} IST. `) +
      "No payment or dispatch is connected; the requested time is not guaranteed.";
    checkoutResult.hidden = false;
    await loadCart();
  } catch (error) {
    orderError.textContent = error.message;
    orderError.hidden = false;
  } finally {
    placeOrderButton.disabled = false;
  }
}

function addMessage(text, kind) {
  const row = document.createElement("div");
  row.className = `message-row ${kind === "user" ? "user-row" : "bot-row"}`;

  if (kind === "bot") {
    const avatar = document.createElement("div");
    avatar.className = "bot-avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = "D";
    row.append(avatar);
  }

  const bubble = document.createElement("div");
  bubble.className = `message ${kind === "user" ? "user-message" : "bot-message"}`;
  const textNode = document.createElement("p");
  textNode.textContent = text;
  const time = document.createElement("span");
  time.className = "message-time";
  time.textContent = new Intl.DateTimeFormat([], { hour: "numeric", minute: "2-digit" }).format(new Date());
  bubble.append(textNode, time);
  row.append(bubble);
  messages.append(row);
  row.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function showTyping() {
  const row = document.createElement("div");
  row.className = "message-row bot-row";
  row.dataset.typing = "true";
  row.innerHTML = '<div class="bot-avatar" aria-hidden="true">D</div><div class="message bot-message"><span class="typing" aria-label="DineEase is typing"><i></i><i></i><i></i></span></div>';
  messages.append(row);
  row.scrollIntoView({ behavior: "smooth", block: "nearest" });
  return row;
}

async function sendMessage(text) {
  const message = text.trim();
  if (!message) return;
  showChat();
  addMessage(message, "user");
  input.value = "";
  input.focus();
  sendButton.disabled = true;
  const typing = showTyping();

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const result = await response.json();
    typing.remove();
    if (!response.ok) {
      addMessage(result.reply || "Sorry, I couldn’t process that. Please try again.", "bot");
      return;
    }
    addMessage(result.reply || "Sorry, I couldn’t process that. Please try again.", "bot");
    setInputMode(result);
    if (result.show_menu) showMenu();
  } catch {
    typing.remove();
    addMessage("I’m having trouble connecting. Please try sending that again.", "bot");
  } finally {
    sendButton.disabled = false;
  }
}

async function loadServiceStatus() {
  const serviceNote = document.querySelector("#service-note");
  if (!serviceNote) return;
  try {
    const response = await fetch("/api/status");
    if (!response.ok) throw new Error("Status request failed");
    const status = await response.json();
    serviceNote.textContent = status.ai_enabled
      ? "AI assistant with rule-based fallback · Demo orders only"
      : "Rule-based assistant active · Set OPENAI_API_KEY for AI replies · Demo orders only";
  } catch {
    serviceNote.textContent = "Demo orders only · No payment or live delivery tracking";
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(input.value);
});

quickActions.addEventListener("click", (event) => {
  const button = event.target.closest("[data-prompt], [data-action]");
  if (!button) return;
  if (button.dataset.action === "show-cart") {
    showMenu();
    document.querySelector(".order-panel").scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }
  if (button.dataset.prompt) sendMessage(button.dataset.prompt);
});

menuGrid.addEventListener("click", (event) => {
  const button = event.target.closest("[data-item-id]");
  if (!button) return;
  const card = button.closest(".menu-card");
  const quantity = Number(card.querySelector('input[type="number"]').value);
  if (!Number.isInteger(quantity) || quantity < 1 || quantity > 20) {
    orderError.textContent = "Choose a quantity from 1 to 20.";
    orderError.hidden = false;
    return;
  }
  updateCart(button.dataset.itemId, quantity)
    .then(() => {
      if (orderError) orderError.hidden = true;
    })
    .catch((error) => {
      if (orderError) {
        orderError.textContent = error.message;
        orderError.hidden = false;
      }
    });
});

if (cartItems) {
  cartItems.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-item-id]");
    if (!button) return;
    fetch(`/api/cart/${button.dataset.removeItemId}`, { method: "DELETE" })
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || "Could not remove item.");
        renderCart(result.cart);
      })
      .catch((error) => {
        if (orderError) {
          orderError.textContent = error.message;
          orderError.hidden = false;
        }
      });
  });
}

if (placeOrderButton) placeOrderButton.addEventListener("click", checkout);
if (retryMenu) retryMenu.addEventListener("click", loadMenu);

document.querySelector("#back-to-chat").addEventListener("click", showChat);
menuSearch.addEventListener("input", renderMenu);
menuCategory.addEventListener("change", renderMenu);
menuDiet.addEventListener("change", renderMenu);
input.addEventListener("change", () => {
  if (input.type === "date" && input.value) {
    dateSelection.textContent = `Selected date: ${formatIsoDate(input.value)}`;
  }
});

loadServiceStatus();