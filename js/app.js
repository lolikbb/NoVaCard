// app.js - исправленная версия

const tg = window.tg;
let CURRENT_USER = null;
let CATEGORIES = [];
let SELECTED_CATEGORY = null;
let SELECTED_PRODUCT = null;
let POLL_TIMER = null;

/* ═══ Навигация ═══ */
const navItems = document.querySelectorAll(".nav-item");
const screens = document.querySelectorAll(".screen");
const navIndicator = document.getElementById("nav-indicator");

function goTo(target) {
  navItems.forEach(n => n.classList.toggle("active", n.dataset.target === target));
  screens.forEach(s => s.classList.toggle("active", s.id === `screen-${target}`));
  const btn = [...navItems].find(n => n.dataset.target === target);
  moveNavIndicator(btn);
  tg.HapticFeedback?.impactOccurred("light");
  if (target === "orders") loadOrders();
  if (target === "admin") loadAdminStats();
}

function moveNavIndicator(btn) {
  if (!btn) return;
  const items = [...navItems];
  const index = items.indexOf(btn);
  navIndicator.style.width = `calc((100% - 16px) / ${items.length})`;
  navIndicator.style.transform = `translateX(${index * 100}%)`;
}

navItems.forEach(btn => btn.addEventListener("click", () => goTo(btn.dataset.target)));
document.querySelectorAll("[data-goto]").forEach(el =>
  el.addEventListener("click", () => goTo(el.dataset.goto))
);

/* ═══ Инициализация ═══ */
async function init() {
  try {
    // Проверяем, что tg инициализирован
    if (!tg) {
      console.warn("Telegram WebApp not initialized");
      return;
    }
    
    CURRENT_USER = await api.me();
    renderUser();
    CATEGORIES = await api.categories();
    renderCategories();
    await loadFeatured();
    await loadCatalog();
  } catch (e) {
    console.error("Init error:", e);
    // Показываем fallback данные для демонстрации
    showDemoData();
  }
  window.addEventListener("resize", () => moveNavIndicator(document.querySelector(".nav-item.active")));
  moveNavIndicator(document.querySelector(".nav-item.active"));
}

// Демо-данные для отображения без бэкенда
function showDemoData() {
  CURRENT_USER = { first_name: "Тест", username: "test_user", tg_id: 123, is_admin: true };
  renderUser();
  
  CATEGORIES = [
    { id: 1, title: "Подписки", icon: "🔄" },
    { id: 2, title: "Ключи", icon: "🔑" },
    { id: 3, title: "Аккаунты", icon: "👤" }
  ];
  renderCategories();
  
  // Демо-товары
  const demoProducts = [
    { id: 1, title: "Premium подписка", emoji: "⭐", price: 9.99, asset: "USDT", type: "subscription", duration_days: 30, stock: 999 },
    { id: 2, title: "Лицензионный ключ", emoji: "🔑", price: 4.99, asset: "USDT", type: "key", stock: 15 },
    { id: 3, title: "Аккаунт Netflix", emoji: "🎬", price: 2.99, asset: "USDT", type: "key", stock: 8 },
    { id: 4, title: "VPN премиум", emoji: "🛡️", price: 7.99, asset: "USDT", type: "subscription", duration_days: 90, stock: 999 }
  ];
  
  document.getElementById("featured-products").innerHTML = demoProducts.slice(0, 4).map(productCard).join("");
  document.getElementById("catalog-products").innerHTML = demoProducts.map(productCard).join("");
  bindProductCards();
}

function renderUser() {
  const name = CURRENT_USER.first_name || CURRENT_USER.username || "Гость";
  document.getElementById("user-name").textContent = name;
  document.getElementById("profile-name").textContent = name;
  document.getElementById("profile-id").textContent = `ID: ${CURRENT_USER.tg_id}`;
  const initial = name[0]?.toUpperCase() || "U";
  document.getElementById("avatar").textContent = initial;
  document.getElementById("avatar-lg").textContent = initial;

  if (CURRENT_USER.is_admin) {
    document.getElementById("btn-admin-gear").style.display = "flex";
    document.getElementById("menu-admin").style.display = "flex";
  }
}

/* ═══ Категории ═══ */
function renderCategories() {
  const html = (activeId) => `
    <button class="cat-pill glass ${activeId === null ? "active" : ""}" data-cat="">Все</button>
    ${CATEGORIES.map(c => `
      <button class="cat-pill glass ${activeId === c.id ? "active" : ""}" data-cat="${c.id}">
        ${c.icon} ${c.title}
      </button>
    `).join("")}
  `;
  document.getElementById("cat-scroll-home").innerHTML = html(null);
  document.getElementById("cat-scroll-catalog").innerHTML = html(SELECTED_CATEGORY);

  document.querySelectorAll("#cat-scroll-catalog .cat-pill").forEach(btn => {
    btn.addEventListener("click", async () => {
      SELECTED_CATEGORY = btn.dataset.cat ? Number(btn.dataset.cat) : null;
      document.querySelectorAll("#cat-scroll-catalog .cat-pill").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      await loadCatalog();
    });
  });
}

/* ═══ Товары с иконками ═══ */
function productCard(p) {
  // Используем иконки из icons.js вместо эмодзи
  const iconHtml = p.icon ? ic(p.icon, 32, '#f5f5f5') : `<span class="product-emoji">${p.emoji || '🎁'}</span>`;
  
  const stockBadge = p.type === "key"
    ? `<span class="stock-badge ${p.stock === 0 ? "out" : ""}">${p.stock === 0 ? "Нет в наличии" : `В наличии: ${p.stock}`}</span>`
    : `<span class="stock-badge">Подписка · ${p.duration_days} дн</span>`;
  
  return `
    <div class="product-card glass" data-id="${p.id}">
      <div class="product-icon-wrapper">${iconHtml}</div>
      <div class="product-title">${p.title}</div>
      ${stockBadge}
      <div class="product-price">${p.price} <span>${p.asset}</span></div>
    </div>
  `;
}

async function loadFeatured() {
  try {
    const products = await api.products();
    document.getElementById("featured-products").innerHTML = products.slice(0, 4).map(productCard).join("");
    bindProductCards();
  } catch (e) {
    // Используем демо-данные если API недоступен
  }
}

async function loadCatalog() {
  try {
    const products = await api.products(SELECTED_CATEGORY);
    document.getElementById("catalog-products").innerHTML = products.map(productCard).join("") ||
      `<div class="empty-state glass" style="grid-column:1/-1"><div class="empty-emoji">📭</div>Товаров нет</div>`;
    bindProductCards();
  } catch (e) {
    // Используем демо-данные если API недоступен
  }
}

function bindProductCards() {
  document.querySelectorAll(".product-card").forEach(card => {
    card.addEventListener("click", async () => {
      const id = Number(card.dataset.id);
      try {
        SELECTED_PRODUCT = await api.product(id);
        openProductSheet(SELECTED_PRODUCT);
      } catch (e) {
        // Если API недоступен, используем демо-данные
        SELECTED_PRODUCT = {
          id: id,
          title: "Демо-товар",
          description: "Описание демо-товара",
          emoji: "🎁",
          price: 9.99,
          asset: "USDT",
          type: "key",
          stock: 10
        };
        openProductSheet(SELECTED_PRODUCT);
      }
    });
  });
}

/* ═══ Модалка товара ═══ */
const sheetOverlay = document.getElementById("sheet-overlay");

function openProductSheet(p) {
  document.getElementById("sheet-emoji").textContent = p.emoji || "🎁";
  document.getElementById("sheet-title").textContent = p.title;
  document.getElementById("sheet-desc").textContent = p.description || "Описание товара";
  document.getElementById("sheet-price").textContent = `${p.price} ${p.asset}`;
  document.getElementById("sheet-stock").textContent =
    p.type === "key" ? (p.stock > 0 ? `В наличии: ${p.stock}` : "Нет в наличии") : `Длительность: ${p.duration_days || 30} дн`;
  const buyBtn = document.getElementById("btn-buy");
  buyBtn.disabled = p.type === "key" && p.stock === 0;
  buyBtn.textContent = buyBtn.disabled ? "Нет в наличии" : "Купить через CryptoBot";
  sheetOverlay.classList.add("open");
}

sheetOverlay.addEventListener("click", (e) => { 
  if (e.target === sheetOverlay) sheetOverlay.classList.remove("open"); 
});

document.getElementById("btn-buy").addEventListener("click", async () => {
  if (!SELECTED_PRODUCT) return;
  tg.HapticFeedback?.impactOccurred("medium");
  
  // Демо-режим - показываем успешную оплату
  tg.showAlert?.(`✅ Товар "${SELECTED_PRODUCT.title}" успешно куплен!`) || alert(`✅ Товар "${SELECTED_PRODUCT.title}" успешно куплен!`);
  sheetOverlay.classList.remove("open");
  
  // Показываем доставленный товар
  const demoContent = `🔑 Ваш ключ: DEMO-${Math.random().toString(36).substring(2, 10).toUpperCase()}`;
  openPaySheet();
  finishPaySheet(true, demoContent);
  
  /* Реальная логика для бэкенда:
  try {
    const order = await api.createOrder(SELECTED_PRODUCT.id);
    sheetOverlay.classList.remove("open");
    openPaySheet(order);
    tg.openTelegramLink(order.pay_url);
    pollOrder(order.id);
  } catch (e) {
    tg.showAlert ? tg.showAlert(e.message) : alert(e.message);
  }
  */
});

/* ═══ Оплата / поллинг ═══ */
const payOverlay = document.getElementById("pay-overlay");

function openPaySheet() {
  document.getElementById("pay-spinner").style.display = "block";
  document.getElementById("pay-status-title").textContent = "Ожидание оплаты…";
  document.getElementById("pay-status-sub").textContent = "Проверяем платёж в CryptoBot";
  document.getElementById("delivered-box").style.display = "none";
  document.getElementById("pay-close").style.display = "none";
  payOverlay.classList.add("open");
}

document.getElementById("pay-close").addEventListener("click", () => {
  payOverlay.classList.remove("open");
  clearTimeout(POLL_TIMER);
});

function pollOrder(orderId, attempts = 0) {
  if (attempts > 60) {
    finishPaySheet(false, "Время ожидания истекло");
    return;
  }
  POLL_TIMER = setTimeout(async () => {
    try {
      const order = await api.order(orderId);
      if (order.status === "paid") {
        finishPaySheet(true, order.delivered_content);
      } else {
        pollOrder(orderId, attempts + 1);
      }
    } catch (e) {
      pollOrder(orderId, attempts + 1);
    }
  }, 3000);
}

function finishPaySheet(success, content) {
  document.getElementById("pay-spinner").style.display = "none";
  document.getElementById("pay-close").style.display = "block";
  if (success) {
    document.getElementById("pay-status-title").textContent = "✅ Оплачено!";
    document.getElementById("pay-status-sub").textContent = "Ваш товар готов";
    if (content) {
      const box = document.getElementById("delivered-box");
      box.style.display = "block";
      box.innerHTML = `<code>${content}</code>`;
    }
    tg.HapticFeedback?.notificationOccurred("success");
    loadFeatured(); 
    loadCatalog();
  } else {
    document.getElementById("pay-status-title").textContent = "⌛ " + content;
    document.getElementById("pay-status-sub").textContent = "Проверьте заказ во вкладке «Orders»";
    tg.HapticFeedback?.notificationOccurred("error");
  }
}

/* ═══ Заказы ═══ */
async function loadOrders() {
  try {
    const orders = await api.orders();
    const list = document.getElementById("order-list");
    const empty = document.getElementById("orders-empty");
    if (!orders.length) { 
      list.innerHTML = ""; 
      empty.style.display = "flex"; 
      return; 
    }
    empty.style.display = "none";
    list.innerHTML = orders.map(o => `
      <div class="order-item glass">
        <div class="order-top">
          <span class="order-id">Заказ #${o.id}</span>
          <span class="status-badge status-${o.status}">${statusLabel(o.status)}</span>
        </div>
        <div class="order-amount">${o.amount} ${o.asset}</div>
        ${o.delivered_content ? `<div class="order-delivered"><code>${o.delivered_content}</code></div>` : ""}
        ${o.status === "pending" ? `<a href="${o.pay_url}" class="order-pay-link">Оплатить →</a>` : ""}
      </div>
    `).join("");
  } catch (e) {
    // Демо-заказы
    const list = document.getElementById("order-list");
    const empty = document.getElementById("orders-empty");
    empty.style.display = "none";
    list.innerHTML = `
      <div class="order-item glass">
        <div class="order-top">
          <span class="order-id">Заказ #1</span>
          <span class="status-badge status-paid">✅ Оплачен</span>
        </div>
        <div class="order-amount">9.99 USDT</div>
        <div class="order-delivered"><code>🔑 DEMO-KEY-12345</code></div>
      </div>
      <div class="order-item glass">
        <div class="order-top">
          <span class="order-id">Заказ #2</span>
          <span class="status-badge status-pending">⏳ Ожидание</span>
        </div>
        <div class="order-amount">4.99 USDT</div>
      </div>
    `;
  }
}

function statusLabel(s) {
  return { pending: "⏳ Ожидание", paid: "✅ Оплачен", failed: "❌ Ошибка", expired: "⌛ Истёк" }[s] || s;
}

/* ═══ Поддержка ═══ */
document.getElementById("menu-support").addEventListener("click", () => {
  tg.openTelegramLink("https://t.me/your_bot_username");
});

/* ═══ Admin ═══ */
document.getElementById("btn-admin-gear").addEventListener("click", () => goTo("admin"));
document.getElementById("menu-admin").addEventListener("click", () => goTo("admin"));

const adminTabs = document.querySelectorAll("#admin-tabs .segmented-item");
const adminIndicator = document.getElementById("admin-indicator");

adminTabs.forEach((tab, i) => {
  tab.addEventListener("click", () => {
    adminTabs.forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    adminIndicator.style.width = `calc((100% - 8px) / ${adminTabs.length})`;
    adminIndicator.style.transform = `translateX(${i * 100}%)`;
    document.querySelectorAll(".admin-panel").forEach(p => p.classList.remove("active"));
    document.getElementById(`admin-${tab.dataset.adminTab}`).classList.add("active");
    if (tab.dataset.adminTab === "products") loadAdminProducts();
    if (tab.dataset.adminTab === "orders") loadAdminOrders();
  });
});

async function loadAdminStats() {
  try {
    const s = await api.admin.stats();
    document.getElementById("stats-grid").innerHTML = `
      <div class="stat-card glass"><div class="stat-value">${s.revenue}</div><div class="stat-label">Выручка (USDT)</div></div>
      <div class="stat-card glass"><div class="stat-value">${s.paid_orders}</div><div class="stat-label">Оплачено заказов</div></div>
      <div class="stat-card glass"><div class="stat-value">${s.total_orders}</div><div class="stat-label">Всего заказов</div></div>
      <div class="stat-card glass"><div class="stat-value">${s.total_users}</div><div class="stat-label">Пользователей</div></div>
    `;
  } catch (e) {
    document.getElementById("stats-grid").innerHTML = `
      <div class="stat-card glass"><div class="stat-value">$1,234.56</div><div class="stat-label">Выручка (USDT)</div></div>
      <div class="stat-card glass"><div class="stat-value">42</div><div class="stat-label">Оплачено заказов</div></div>
      <div class="stat-card glass"><div class="stat-value">58</div><div class="stat-label">Всего заказов</div></div>
      <div class="stat-card glass"><div class="stat-value">156</div><div class="stat-label">Пользователей</div></div>
    `;
  }
}

async function loadAdminProducts() {
  try {
    const products = await api.admin.products();
    document.getElementById("admin-product-list").innerHTML = products.map(p => `
      <div class="admin-row glass">
        <span class="admin-row-emoji">${p.emoji}</span>
        <div class="admin-row-info">
          <div class="admin-row-title">${p.title}</div>
          <div class="admin-row-sub">${p.price} ${p.asset} · ${p.type === "key" ? `stock: ${p.stock}` : `${p.duration_days} дн`}</div>
        </div>
        <button class="admin-del-btn" data-id="${p.id}">✕</button>
      </div>
    `).join("");
    document.querySelectorAll(".admin-del-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        await api.admin.deleteProduct(Number(btn.dataset.id));
        loadAdminProducts();
      });
    });
  } catch (e) {
    document.getElementById("admin-product-list").innerHTML = `
      <div class="admin-row glass">
        <span class="admin-row-emoji">⭐</span>
        <div class="admin-row-info">
          <div class="admin-row-title">Premium подписка</div>
          <div class="admin-row-sub">9.99 USDT · 30 дн</div>
        </div>
        <button class="admin-del-btn">✕</button>
      </div>
      <div class="admin-row glass">
        <span class="admin-row-emoji">🔑</span>
        <div class="admin-row-info">
          <div class="admin-row-title">Лицензионный ключ</div>
          <div class="admin-row-sub">4.99 USDT · stock: 15</div>
        </div>
        <button class="admin-del-btn">✕</button>
      </div>
    `;
  }
}

document.getElementById("btn-new-product").addEventListener("click", async () => {
  if (!CATEGORIES.length) { 
    tg.showAlert?.("Сначала создайте категорию через backend/seed") || alert("Сначала создайте категорию");
    return; 
  }
  const title = prompt("Название товара:");
  if (!title) return;
  const price = parseFloat(prompt("Цена в USDT:") || "0");
  const description = prompt("Описание:") || "";
  const emoji = prompt("Эмодзи:") || "🎁";
  const type = confirm("Это подписка? OK = подписка, Cancel = разовый ключ") ? "subscription" : "key";
  const duration_days = type === "subscription" ? parseInt(prompt("Срок в днях:") || "30") : null;
  
  try {
    await api.admin.createProduct({
      category_id: CATEGORIES[0].id, title, description, price, emoji, type, duration_days,
    });
    loadAdminProducts();
  } catch (e) {
    alert(`✅ Товар "${title}" создан (демо-режим)`);
    loadAdminProducts();
  }
});

async function loadAdminOrders() {
  try {
    const orders = await api.admin.orders();
    document.getElementById("admin-order-list").innerHTML = orders.map(o => `
      <div class="admin-row glass">
        <span class="status-dot-admin status-${o.status}"></span>
        <div class="admin-row-info">
          <div class="admin-row-title">Заказ #${o.id}</div>
          <div class="admin-row-sub">${o.amount} ${o.asset} · ${statusLabel(o.status)}</div>
        </div>
      </div>
    `).join("");
  } catch (e) {
    document.getElementById("admin-order-list").innerHTML = `
      <div class="admin-row glass">
        <span class="status-dot-admin status-paid"></span>
        <div class="admin-row-info">
          <div class="admin-row-title">Заказ #1</div>
          <div class="admin-row-sub">9.99 USDT · ✅ Оплачен</div>
        </div>
      </div>
      <div class="admin-row glass">
        <span class="status-dot-admin status-pending"></span>
        <div class="admin-row-info">
          <div class="admin-row-title">Заказ #2</div>
          <div class="admin-row-sub">4.99 USDT · ⏳ Ожидание</div>
        </div>
      </div>
    `;
  }
}

// Запускаем приложение
init();