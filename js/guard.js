(function () {
  const tg = window.Telegram && window.Telegram.WebApp;
  const hasValidInitData = tg && typeof tg.initData === "string" && tg.initData.length > 20;

  if (!hasValidInitData) {
    document.body.innerHTML = `
      <div class="blocked-screen">
        <div class="blocked-card glass">
          <div class="blocked-icon">🔒</div>
          <h1>Только через Telegram</h1>
          <p>Это приложение работает исключительно внутри Telegram-бота.<br>Открой его через кнопку в чате с ботом.</p>
          <a class="blocked-btn glass-active" href="https://t.me/your_bot_username">Открыть бота</a>
        </div>
      </div>
    `;
    document.body.classList.add("blocked");
    throw new Error("Blocked: not opened inside Telegram");
  }

  tg.ready();
  tg.expand();
  tg.setHeaderColor && tg.setHeaderColor("#000000");
  tg.setBackgroundColor && tg.setBackgroundColor("#000000");
  window.tg = tg;
})();