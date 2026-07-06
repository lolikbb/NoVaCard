/* ============================================================
   Иконки: SVG по API (api.iconify.design)
   Формат имени: 'shopping-cart' (набор lucide по умолчанию)
   или 'set:name' (например 'ph:lightning-bold').
   ============================================================ */

const ICON_API = 'https://api.iconify.design';
const ICON_DEFAULT_SET = 'lucide';

function iconUrl(name, color) {
  let set = ICON_DEFAULT_SET;
  let n = String(name || 'package').trim() || 'package';
  if (n.includes(':')) [set, n] = n.split(':');
  return `${ICON_API}/${encodeURIComponent(set)}/${encodeURIComponent(n)}.svg?color=${encodeURIComponent(color)}`;
}

/** HTML-строка с <img> SVG-иконкой из API */
function ic(name, size = 20, color = '#f5f5f5', cls = '') {
  const fallback = iconUrl('package', color);
  return `<img class="ic ${cls}" src="${iconUrl(name, color)}" width="${size}" height="${size}" alt=""
    loading="lazy" draggable="false" onerror="this.onerror=null;this.src='${fallback}'">`;
}

/** Иконка чёрного цвета (для белых поверхностей) */
function icDark(name, size = 20) {
  return ic(name, size, '#000000');
}

/** Иконка приглушённого цвета */
function icMuted(name, size = 20) {
  return ic(name, size, '#8f8f8f');
}
