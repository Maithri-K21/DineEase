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
const dateSelection = document.querySelector("#date-selection");
let menuItems = [];

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
    const matchesText = `${item.name} ${item.description} ${item.category}`.toLocaleLowerCase().includes(search);
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
    content.append(heading, description);
    card.append(photoWrap, content);
    menuGrid.append(card);
  }
}

async function loadMenu() {
  menuError.hidden = true;
  menuGrid.replaceChildren();
  menuCount.textContent = "Loading menu...";
  try {
    const response = await fetch("/api/menu");
    if (!response.ok) throw new Error("Menu request failed");
    const result = await response.json();
    menuItems = result.items;
    renderMenu();
  } catch {
    menuCount.textContent = "";
    menuError.textContent = "The menu could not be loaded. Please try again.";
    menuError.hidden = false;
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

form.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(input.value);
});

quickActions.addEventListener("click", (event) => {
  const button = event.target.closest("[data-prompt]");
  if (button) sendMessage(button.dataset.prompt);
});

document.querySelector("#back-to-chat").addEventListener("click", showChat);
menuSearch.addEventListener("input", renderMenu);
menuCategory.addEventListener("change", renderMenu);
menuDiet.addEventListener("change", renderMenu);
input.addEventListener("change", () => {
  if (input.type === "date" && input.value) {
    dateSelection.textContent = `Selected date: ${formatIsoDate(input.value)}`;
  }
});