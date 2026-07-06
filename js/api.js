/* ============================================================
   API-клиент: все запросы подписываются Telegram initData
   ============================================================ */

const API = {
  initData: (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData) || '',

  async request(method, path, body) {
    let res;
    try {
      res = await fetch(path, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'X-Init-Data': API.initData,
        },
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch (e) {
      throw new Error('Нет соединения с сервером');
    }
    let data = {};
    try { data = await res.json(); } catch (e) { /* пустой ответ */ }
    if (!res.ok) {
      const err = new Error(data.error || `Ошибка ${res.status}`);
      err.status = res.status;
      throw err;
    }
    return data;
  },

  get: (path) => API.request('GET', path),
  post: (path, body) => API.request('POST', path, body ?? {}),
  put: (path, body) => API.request('PUT', path, body ?? {}),
  del: (path) => API.request('DELETE', path),
};
