/* ═══════════════ Telegram init ═══════════════ */
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  tg.setHeaderColor?.('#000000');
  tg.setBackgroundColor?.('#000000');
}

/* ═══════════════ Navigation ═══════════════ */
const navItems = document.querySelectorAll('.nav-item');
const screens = document.querySelectorAll('.screen');
const indicator = document.querySelector('.nav-indicator');

function goTo(target) {
  navItems.forEach(n => n.classList.toggle('active', n.dataset.target === target));
  screens.forEach(s => s.classList.toggle('active', s.id === `screen-${target}`));
  const activeBtn = [...navItems].find(n => n.dataset.target === target);
  moveIndicator(activeBtn);
  tg?.HapticFeedback?.impactOccurred('light');
}

function moveIndicator(btn) {
  if (!btn) return;
  const index = [...navItems].indexOf(btn);
  indicator.style.transform = `translateX(${index * 100}%)`;
}

navItems.forEach(btn => btn.addEventListener('click', () => goTo(btn.dataset.target)));
document.querySelectorAll('[data-goto]').forEach(el =>
  el.addEventListener('click', () => goTo(el.dataset.goto))
);

window.addEventListener('load', () => moveIndicator(document.querySelector('.nav-item.active')));
window.addEventListener('resize', () => moveIndicator(document.querySelector('.nav-item.active')));

/* ═══════════════ Mock data render ═══════════════ */
const tx = [
  { name: 'Amazon.com', time: 'Сегодня, 14:32', amount: '-84.20', type: 'neg', icon: '🛒' },
  { name: 'Пополнение USDT', time: 'Сегодня, 09:10', amount: '+500.00', type: 'pos', icon: '⬇️' },
  { name: 'Netflix', time: 'Вчера, 20:00', amount: '-12.99', type: 'neg', icon: '🎬' },
  { name: 'Перевод от @alex', time: 'Вчера, 11:22', amount: '+120.00', type: 'pos', icon: '👤' },
];
document.getElementById('tx-list').innerHTML = tx.map(t => `
  <div class="tx-item">
    <div class="tx-ic">${t.icon}</div>
    <div class="tx-info">
      <div class="tx-name">${t.name}</div>
      <div class="tx-time">${t.time}</div>
    </div>
    <div class="tx-amount ${t.type}">${t.amount}</div>
  </div>
`).join('');

const assets = [
  { name: 'Tether', sym: 'USDT', amount: '10,420.00', change: '+0.02%', up: true, color: '#26A17B', logo: 'T' },
  { name: 'Bitcoin', sym: 'BTC', amount: '0.0842', change: '+3.1%', up: true, color: '#F7931A', logo: '₿' },
  { name: 'Ethereum', sym: 'ETH', amount: '1.204', change: '-1.4%', up: false, color: '#627EEA', logo: 'Ξ' },
  { name: 'USD Coin', sym: 'USDC', amount: '2,000.00', change: '+0.00%', up: true, color: '#2775CA', logo: 'U' },
];
document.getElementById('asset-list').innerHTML = assets.map(a => `
  <div class="asset-item">
    <div class="asset-logo" style="background:${a.color}">${a.logo}</div>
    <div class="asset-info">
      <div class="asset-name">${a.name}</div>
      <div class="asset-sub">${a.sym}</div>
    </div>
    <div class="asset-right">
      <div class="asset-amount">${a.amount}</div>
      <div class="asset-change ${a.up ? 'up' : 'down'}">${a.change}</div>
    </div>
  </div>
`).join('');

const recipients = ['Alex', 'Maria', 'John', 'Kate', 'Ivan'];
document.getElementById('recipients').innerHTML = recipients.map(r => `
  <div class="recipient">
    <div class="recipient-av">${r[0]}</div>
    <div class="recipient-name">${r}</div>
  </div>
`).join('');

const miniCards = [
  { title: 'Основная карта', sub: '•••• 7743 · USDT TRC20', active: true },
  { title: 'Карта для подписок', sub: '•••• 2210 · USDC ERC20', active: true },
];
document.getElementById('mini-card-list').innerHTML = miniCards.map(c => `
  <div class="mini-card-item">
    <div class="mini-card-chip-ic">💳</div>
    <div class="mini-card-info">
      <div class="mini-card-title">${c.title}</div>
      <div class="mini-card-sub">${c.sub}</div>
    </div>
    <div class="status-dot"></div>
  </div>
`).join('');

const growItems = [
  { name: 'USDT Flexible', sub: 'Гибкий стейкинг', apy: '12.4%', color: '#26A17B', logo: 'T' },
  { name: 'ETH Staking', sub: 'Заморозка 30 дней', apy: '8.9%', color: '#627EEA', logo: 'Ξ' },
  { name: 'BTC Vault', sub: 'Заморозка 90 дней', apy: '6.2%', color: '#F7931A', logo: '₿' },
];
document.getElementById('grow-list').innerHTML = growItems.map(g => `
  <div class="grow-item">
    <div class="grow-logo" style="background:${g.color}">${g.logo}</div>
    <div class="grow-info">
      <div class="grow-name">${g.name}</div>
      <div class="grow-sub">${g.sub}</div>
    </div>
    <div class="grow-apy">${g.apy}<div class="grow-apy-label">APY</div></div>
  </div>
`).join('');

/* ═══════════════ Card copy interaction ═══════════════ */
document.getElementById('card-visual')?.addEventListener('click', () => {
  tg?.HapticFeedback?.impactOccurred('medium');
});