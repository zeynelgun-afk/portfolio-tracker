"""
Analist Takip — DM Filter Ayarları

Hangi karar tiplerinin DM olarak gönderileceğini kontrol eder.
Runtime'da değiştirilebilir (telegram komutu ile).

Dosya: data/analist_takip/dm_settings.json
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import ANALIST_STATE_DIR


DM_SETTINGS_PATH = f"{ANALIST_STATE_DIR}/dm_settings.json"

# Önceden tanımlı preset'ler
PRESETS = {
    "sadece-al": {
        "name": "Sadece AL",
        "description": "BUY ve STRONG_BUY DM'leri",
        "enabled_decisions": ["BUY", "STRONG_BUY"],
        "drift_expired_big_raise": False,
    },
    "sat-da": {
        "name": "AL + SAT",
        "description": "BUY/STRONG_BUY + SELL/STRONG_SELL",
        "enabled_decisions": ["BUY", "STRONG_BUY", "SELL", "STRONG_SELL"],
        "drift_expired_big_raise": False,
    },
    "hepsi": {
        "name": "Hepsi (en geniş)",
        "description": "Aksiyon kararları + drift dışı büyük raise (WATCH)",
        "enabled_decisions": ["BUY", "STRONG_BUY", "SELL", "STRONG_SELL"],
        "drift_expired_big_raise": True,
    },
    "sadece-guclu": {
        "name": "Sadece güçlü sinyaller",
        "description": "Yalnız STRONG_BUY ve STRONG_SELL",
        "enabled_decisions": ["STRONG_BUY", "STRONG_SELL"],
        "drift_expired_big_raise": False,
    },
}

PRESET_ALIASES = {
    "sadece-guclu": "sadece-guclu",
    "sadece-güçlü": "sadece-guclu",
    "guclu": "sadece-guclu",
    "güçlü": "sadece-guclu",
    "strong": "sadece-guclu",
    "sadece-al": "sadece-al",
    "al": "sadece-al",
    "buy": "sadece-al",
    "sat-da": "sat-da",
    "sat": "sat-da",
    "sell": "sat-da",
    "hepsi": "hepsi",
    "all": "hepsi",
    "full": "hepsi",
}

DEFAULT_PRESET = "sadece-al"


def _ensure_dirs():
    Path(ANALIST_STATE_DIR).mkdir(parents=True, exist_ok=True)


def _load() -> dict:
    """Ayar dosyasını oku, yoksa default oluştur."""
    _ensure_dirs()
    p = Path(DM_SETTINGS_PATH)
    if not p.exists():
        return _save_preset(DEFAULT_PRESET)
    try:
        with open(p) as f:
            data = json.load(f)
        # Şema doğrulama
        if "enabled_decisions" not in data:
            return _save_preset(DEFAULT_PRESET)
        return data
    except Exception:
        return _save_preset(DEFAULT_PRESET)


def _save_preset(preset_key: str) -> dict:
    """Preset'i kaydet ve dön."""
    _ensure_dirs()
    if preset_key not in PRESETS:
        preset_key = DEFAULT_PRESET
    preset = PRESETS[preset_key]
    data = {
        "preset": preset_key,
        "preset_name": preset["name"],
        "preset_description": preset["description"],
        "enabled_decisions": preset["enabled_decisions"],
        "drift_expired_big_raise": preset["drift_expired_big_raise"],
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    with open(DM_SETTINGS_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


def get_settings() -> dict:
    """Mevcut ayarları dön."""
    return _load()


def set_preset(preset_arg: str) -> dict:
    """
    Preset'i değiştir.
    
    Args:
        preset_arg: Preset adı veya alias (sadece-al, sat-da, hepsi, sadece-guclu)
    
    Returns:
        {"success": bool, "settings": dict, "message": str}
    """
    arg = preset_arg.strip().lower().replace(" ", "-")
    preset_key = PRESET_ALIASES.get(arg)
    if not preset_key:
        return {
            "success": False,
            "settings": _load(),
            "message": (
                f"Bilinmeyen preset: '{preset_arg}'\n"
                f"Geçerli: sadece-al, sat-da, hepsi, sadece-guclu"
            ),
        }
    data = _save_preset(preset_key)
    return {
        "success": True,
        "settings": data,
        "message": f"DM filter '{data['preset_name']}' olarak ayarlandı",
    }


def should_send_dm(decision_dict: dict) -> bool:
    """
    Bir decision için DM atılması gerekiyor mu?
    
    Args:
        decision_dict: analyze_signals çıktısı
    
    Returns:
        True/False
    """
    settings = _load()
    decision = decision_dict.get("decision", "")
    enabled = settings.get("enabled_decisions", [])
    drift_expired_flag = settings.get("drift_expired_big_raise", False)
    
    # Doğrudan aksiyon kararları (BUY/SELL/STRONG_*)
    if decision in enabled:
        return True
    
    # Drift expired + büyük raise (WATCH özel durumu)
    if decision == "WATCH" and drift_expired_flag:
        if (decision_dict.get("drift_status") == "expired"
                and decision_dict.get("biggest_raise")
                and (decision_dict["biggest_raise"].get("pct") or 0) >= 30):
            return True
    
    return False


def format_settings_message() -> str:
    """
    /analist dm — mevcut ayarları göster (HTML format).
    """
    s = _load()
    enabled = s.get("enabled_decisions", [])
    drift_flag = s.get("drift_expired_big_raise", False)
    
    decision_emoji = {
        "STRONG_BUY": "🟢🟢", "BUY": "🟢",
        "WATCH": "🟡", "NEUTRAL": "⚪",
        "SELL": "🔴", "STRONG_SELL": "🔴🔴",
    }
    decision_tr = {
        "STRONG_BUY": "GÜÇLÜ AL", "BUY": "AL",
        "WATCH": "İZLE", "NEUTRAL": "NÖTR",
        "SELL": "SAT", "STRONG_SELL": "GÜÇLÜ SAT",
    }
    
    lines = [
        f"<b>📨 DM Filter Ayarları</b>",
        "",
        f"<b>Aktif Preset:</b> <code>{s.get('preset')}</code>",
        f"<i>{s.get('preset_description', '')}</i>",
        "",
        f"<b>DM atılan kararlar:</b>",
    ]
    
    for d in ["STRONG_BUY", "BUY", "SELL", "STRONG_SELL"]:
        emoji = decision_emoji.get(d, "")
        title = decision_tr.get(d, d)
        check = "✅" if d in enabled else "❌"
        lines.append(f"  {check} {emoji} {title}")
    
    if drift_flag:
        lines.append(f"  ✅ 🟡 İZLE (drift dışı büyük raise)")
    else:
        lines.append(f"  ❌ 🟡 İZLE")
    
    lines.append("")
    lines.append("<b>Değiştirmek için:</b>")
    lines.append("  <code>/analist dm sadece-al</code> — Sadece AL")
    lines.append("  <code>/analist dm sat-da</code> — AL + SAT")
    lines.append("  <code>/analist dm hepsi</code> — Aksiyon + drift dışı izleme")
    lines.append("  <code>/analist dm sadece-guclu</code> — Sadece STRONG_*")
    
    last_updated = s.get("updated_at", "")[:19]
    if last_updated:
        lines.append("")
        lines.append(f"<i>Son güncelleme: {last_updated} UTC</i>")
    
    return "\n".join(lines)


def format_set_result(result: dict) -> str:
    """set_preset çıktısını DM mesajına çevir."""
    if not result["success"]:
        return f"❌ {result['message']}\n\n{format_settings_message()}"
    s = result["settings"]
    enabled = s.get("enabled_decisions", [])
    drift_flag = s.get("drift_expired_big_raise", False)
    
    decision_titles = {
        "STRONG_BUY": "🟢🟢 GÜÇLÜ AL",
        "BUY": "🟢 AL",
        "SELL": "🔴 SAT",
        "STRONG_SELL": "🔴🔴 GÜÇLÜ SAT",
    }
    items = [decision_titles[d] for d in enabled if d in decision_titles]
    if drift_flag:
        items.append("🟡 İZLE (drift dışı büyük raise)")
    
    lines = [
        f"✅ <b>DM Filter güncellendi</b>",
        "",
        f"<b>Preset:</b> {s['preset_name']}",
        f"<i>{s['preset_description']}</i>",
        "",
        f"<b>Şu kararlarda DM gelecek:</b>",
    ]
    for item in items:
        lines.append(f"  • {item}")
    
    return "\n".join(lines)
