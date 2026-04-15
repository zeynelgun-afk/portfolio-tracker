/**
 * Finzora Telegram Bot — Node.js versiyonu
 * Node.js app'e entegre — ayrı python gerekmez
 * 
 * Kullanım: node scripts/finzora-bot.js
 * Veya mevcut app'in start script'ine ekle:
 *   require('./scripts/finzora-bot.js')
 */

const https = require('https');

const BOT_TOKEN    = process.env.TELEGRAM_TOKEN    || '8749931249:AAGTLVKLHx5grcGlJhuodg-DbFDkFYjpCcI';
const PRIVATE_CHAT = process.env.TELEGRAM_PRIVATE_CHAT || '1403072107';
const GROUP_CHAT   = '-1003827034395';
const FMP_KEY      = process.env.FMP_API_KEY       || 'g1GFJZtV5rCP49UCir4WuP56VjhmA6F8';
const FMP_BASE     = 'https://financialmodelingprep.com/stable';
const TG_BASE      = `https://api.telegram.org/bot${BOT_TOKEN}`;

const IZINLI = new Set([PRIVATE_CHAT, GROUP_CHAT, String(PRIVATE_CHAT)]);

// Yaygın kelimeler — ticker sanılmasın
const DISI = new Set([
  'VE','DE','DA','BU','ŞU','BİR','IKI','UC','BES','ON','YOK','VAR',
  'GEL','GIT','THE','AND','FOR','ARE','BUT','NOT','YOU','ALL','CAN',
  'HER','WAS','ONE','OUR','OUT','DAY','GET','HAS','HIM','HIS','HOW',
  'ITS','WHO','NOW','OLD','SEE','TWO','WAY','MAY','NEW','OIL','SET',
]);

// ── HTTP yardımcıları ─────────────────────────────────────────────

function httpGet(url) {
  return new Promise((resolve, reject) => {
    https.get(url, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch(e) { reject(e); }
      });
    }).on('error', reject);
  });
}

function httpPost(url, body) {
  return new Promise((resolve, reject) => {
    const payload = JSON.stringify(body);
    const opts = {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) }
    };
    const req = https.request(url, opts, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch(e) { reject(e); }
      });
    });
    req.on('error', reject);
    req.write(payload);
    req.end();
  });
}

// ── Telegram API ──────────────────────────────────────────────────

async function tgGet(method, params = {}) {
  const qs = new URLSearchParams(params).toString();
  return httpGet(`${TG_BASE}/${method}?${qs}`);
}

async function tgSend(chatId, text, replyTo = null) {
  const body = { chat_id: chatId, text, parse_mode: 'HTML', disable_web_page_preview: true };
  if (replyTo) body.reply_to_message_id = replyTo;
  try {
    const r = await httpPost(`${TG_BASE}/sendMessage`, body);
    if (!r.ok) console.log('[Bot] Gönderim hatası:', r.description);
    return r.ok;
  } catch(e) {
    console.error('[Bot] tgSend hatası:', e.message);
    return false;
  }
}

// ── FMP API ───────────────────────────────────────────────────────

async function fmpGet(endpoint, params = {}) {
  params.apikey = FMP_KEY;
  const qs = new URLSearchParams(params).toString();
  try {
    return await httpGet(`${FMP_BASE}/${endpoint}?${qs}`);
  } catch(e) {
    return null;
  }
}

// ── Analiz ───────────────────────────────────────────────────────

async function analizEt(symbol) {
  console.log(`[Bot] ${symbol} analiz ediliyor...`);

  const [quote, rtm, mttm, inc, pt, cons] = await Promise.all([
    fmpGet('quote', { symbol }),
    fmpGet('ratios-ttm', { symbol }),
    fmpGet('key-metrics-ttm', { symbol }),
    fmpGet('income-statement', { symbol, period: 'annual', limit: 3 }),
    fmpGet('price-target-summary', { symbol }),
    fmpGet('grades-consensus', { symbol }),
  ]);

  if (!quote || !quote[0]) return null;

  const q   = quote[0];
  const r   = (rtm  && rtm[0])  ? rtm[0]  : {};
  const m   = (mttm && mttm[0]) ? mttm[0] : {};
  const pt0 = (pt   && pt[0])   ? pt[0]   : {};
  const c   = (cons && cons[0]) ? cons[0] : {};

  const price  = q.price || 0;
  const pe     = r.priceToEarningsRatioTTM || r.peRatioTTM || m.peRatioTTM;
  const eps    = r.netIncomePerShareTTM;
  const bvps   = r.bookValuePerShareTTM;
  const fcfps  = r.freeCashFlowPerShareTTM;
  const roe    = m.returnOnEquityTTM;
  const fcfY   = m.freeCashFlowYieldTTM;
  const divY   = (r.dividendYieldTTM || 0) * 100;
  const evEbit = m.evToEbitdaTTM || m.enterpriseValueOverEBITDATTM;
  const mktcap = q.marketCap;

  // Basit adil değer: EPS × sektör P/E (faiz bazlı)
  const bond_y = 4.3; // yaklaşık 10Y
  const ratePE = Math.max(4, Math.min(30, 100 / bond_y));

  // EPS büyümesi
  let epsGr = 0.10;
  if (inc && inc.length >= 2 && inc[1].eps && inc[1].eps > 0) {
    epsGr = Math.max(-0.20, Math.min(0.60, (inc[0].eps / inc[1].eps) - 1));
  }

  // 3 basit yöntemle adil değer
  let adil = 0; let metodSayisi = 0;

  if (eps && eps > 0) {
    adil += eps * ratePE; metodSayisi++;             // Net Kazanç
    adil += eps * (1 + epsGr) * ratePE; metodSayisi++; // Forward
  }
  if (bvps && bvps > 0 && eps && eps > 0) {
    adil += Math.sqrt(22.5 * eps * bvps); metodSayisi++; // Graham
  }

  if (metodSayisi === 0) return null;
  adil = adil / metodSayisi;

  const fark = price > 0 ? (price / adil - 1) * 100 : 0;

  // Analist
  const analistHedef = pt0.lastQuarterAvgPriceTarget;
  const sb = c.strongBuy || 0;
  const b  = c.buy || 0;
  const h  = c.hold || 0;
  const s  = (c.sell || 0) + (c.strongSell || 0);
  const totalAn = sb + b + h + s;
  const alPct = totalAn > 0 ? Math.round((sb + b) / totalAn * 100) : null;

  return { price, adil, fark, eps, epsGr, pe, roe, fcfY, divY, evEbit,
           mktcap, analistHedef, alPct, totalAn, sector: q.sector || '' };
}

// ── Mesaj Formatları ──────────────────────────────────────────────

function formatAnaliz(symbol, d) {
  if (!d) return `❌ <b>${symbol}</b> için veri bulunamadı.`;

  const sinyal = d.fark < -20 ? '🟢 <b>UCUZ</b>'
               : d.fark > 20  ? '🔴 <b>PAHALI</b>'
               :                 '🟡 <b>ADİL</b>';

  const divStr = d.divY > 0.5 ? `\n  Temettü: %${d.divY.toFixed(1)}` : '';

  let lines = [
    `<b>📊 ${symbol} — Adil Değer Analizi</b>`,
    d.sector ? `<i>${d.sector}</i>` : '',
    '',
    `💵 Güncel fiyat:  <b>$${d.price.toFixed(2)}</b>`,
    `🎯 Adil değer:    <b>$${d.adil.toFixed(2)}</b>`,
    `📏 Fark:         <b>${d.fark > 0 ? '+' : ''}${d.fark.toFixed(1)}%</b>  →  ${sinyal}`,
    '',
    `<b>📐 Temel Metrikler:</b>`,
  ];

  if (d.pe)    lines.push(`  P/E TTM:      ${d.pe.toFixed(1)}x`);
  if (d.evEbit) lines.push(`  EV/EBITDA:    ${d.evEbit.toFixed(1)}x`);
  if (d.roe)   lines.push(`  ROE:          %${(d.roe * 100).toFixed(1)}`);
  if (d.fcfY)  lines.push(`  FCF Verimi:   %${(d.fcfY * 100).toFixed(1)}`);
  if (divStr)  lines.push(divStr);
  lines.push(`  EPS büyüme:   %${(d.epsGr * 100).toFixed(1)}`);

  if (d.analistHedef) {
    const atDiff = (d.price / d.analistHedef - 1) * 100;
    const consStr = d.alPct !== null ? ` | AL:%${d.alPct} (${d.totalAn} analist)` : '';
    lines.push('', `<b>📈 Analist:</b>`);
    lines.push(`  Hedef: $${d.analistHedef.toFixed(2)} (${atDiff > 0 ? '+' : ''}${atDiff.toFixed(1)}%)${consStr}`);
  }

  lines.push('');
  lines.push(`📊 Bantlar: <b>$${(d.adil * 0.8).toFixed(2)}</b> ← ADİL → <b>$${(d.adil * 1.2).toFixed(2)}</b>`);
  lines.push('', `<i>finzora.ai — yatırım tavsiyesi değildir</i>`);

  return lines.filter(l => l !== undefined).join('\n');
}

function formatYardim() {
  return `<b>🤖 Finzora AI Bot</b>

<b>Hisse analizi:</b>
  <code>MRK</code>   → Merck adil değer analizi
  <code>NVDA</code>  → Nvidia analizi
  <code>/deger AAPL</code> → Apple analizi

<b>Diğer:</b>
  <code>/yardim</code> → Bu menü

<i>Yanıt süresi: ~3-5 saniye</i>`;
}

// ── Mesaj işleyici ────────────────────────────────────────────────

const TICKER_RE = /^[A-Z]{2,6}[0-9]?$/;

async function isleMesaj(msg) {
  const chatId = String(msg.chat?.id || '');
  const msgId  = msg.message_id;
  const text   = (msg.text || '').trim();

  if (!text || !IZINLI.has(chatId)) return;

  const textUp = text.toUpperCase();
  console.log(`[Bot] [${chatId}] ${msg.from?.first_name}: ${text.slice(0, 40)}`);

  // /yardim
  if (['/yardim', '/help', '/start'].includes(text.toLowerCase())) {
    await tgSend(chatId, formatYardim(), msgId);
    return;
  }

  // /deger AAPL
  let ticker = null;
  if (textUp.startsWith('/DEGER ')) {
    ticker = text.split(' ')[1]?.toUpperCase();
  } else if (TICKER_RE.test(textUp) && !DISI.has(textUp)) {
    ticker = textUp;
  }

  if (!ticker) return;

  await tgSend(chatId, `⏳ <b>${ticker}</b> analiz ediliyor...`, msgId);
  const data = await analizEt(ticker);
  await tgSend(chatId, formatAnaliz(ticker, data), msgId);
}

// ── Ana döngü ─────────────────────────────────────────────────────

let offset = 0;
let hataSayisi = 0;

async function tick() {
  try {
    const upd = await tgGet('getUpdates', { offset, timeout: 25, limit: 10 });
    if (!upd?.ok) { hataSayisi++; return; }

    hataSayisi = 0;
    for (const u of (upd.result || [])) {
      offset = Math.max(offset, u.update_id + 1);
      const msg = u.message || u.edited_message;
      if (msg) await isleMesaj(msg).catch(e => console.error('[Bot] isleMesaj hata:', e));
    }
  } catch(e) {
    hataSayisi++;
    console.error('[Bot] tick hata:', e.message);
  }
}

function basla() {
  console.log(`[Finzora Bot] Başladı — ${new Date().toISOString()}`);
  console.log(`[Finzora Bot] Private: ${PRIVATE_CHAT} | Group: ${GROUP_CHAT}`);

  const interval = setInterval(async () => {
    try { await tick(); }
    catch(e) { console.error('[Bot] interval hata:', e); }

    if (hataSayisi > 10) {
      console.error('[Bot] Çok fazla hata, yeniden başlıyor...');
      hataSayisi = 0;
    }
  }, 2000);

  // Graceful shutdown
  process.on('SIGTERM', () => { clearInterval(interval); process.exit(0); });
  process.on('SIGINT',  () => { clearInterval(interval); process.exit(0); });
}

// Direkt çalıştırma veya require ile import
if (require.main === module) {
  basla();
} else {
  module.exports = { basla };
}
