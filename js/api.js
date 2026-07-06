// ⚠️ ЗАМЕНИ НА РЕАЛЬНЫЙ URL ТВОЕГО БЭКЕНДА
const API_BASE = "http://localhost:8000/api";

async function apiRequest(path, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "Authorization": `tma ${window.tg.initData}`,
        ...(options.headers || {}),
      },
    });
    if (!res.ok) {
      let err = {};
      try { err = await res.json(); } catch (e) {}
      throw new Error(err.detail || `Ошибка ${res.status}`);
    }
    return res.json();
  } catch (e) {
    // Реальная ошибка, НЕ показываем демо-данные
    console.error('API Error:', e);
    throw e;
  }
}

const api = {
  me: () => apiRequest("/me"),
  categories: () => apiRequest("/categories"),
  products: (categoryId) => apiRequest(`/products${categoryId ? `?category_id=${categoryId}` : ""}`),
  product: (id) => apiRequest(`/products/${id}`),
  createOrder: (productId) => apiRequest("/orders", { method: "POST", body: JSON.stringify({ product_id: productId }) }),
  orders: () => apiRequest("/orders"),
  order: (id) => apiRequest(`/orders/${id}`),
  admin: {
    stats: () => apiRequest("/admin/stats"),
    products: () => apiRequest("/admin/products"),
    createProduct: (data) => apiRequest("/admin/products", { method: "POST", body: JSON.stringify(data) }),
    deleteProduct: (id) => apiRequest(`/admin/products/${id}`, { method: "DELETE" }),
    orders: () => apiRequest("/admin/orders"),
    categories: () => apiRequest("/admin/categories"),
    createCategory: (data) => apiRequest("/admin/categories", { method: "POST", body: JSON.stringify(data) }),
    addKeys: (productId, keys) => apiRequest(`/admin/products/${productId}/keys`, { method: "POST", body: JSON.stringify({ keys }) }),
  },
};