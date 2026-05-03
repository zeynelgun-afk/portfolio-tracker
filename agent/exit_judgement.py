# -*- coding: utf-8 -*-
"""
EXIT JUDGEMENT LAYER — Claude akilli cikis karari
======================================================
Mevcut k_engine.run_exit_checks() kural-tabanli (K-06/07/09/11/15c/ZST).
Sorunu: bagimsiz kontrol ediyor, baglami gormez.

Ornekler:
- K-09 stop yakini ama hisse yarın earnings + tahmin yuksek → BEKLE
- K-11 RSI 80 ama tema henuz baslangic + sektor outperform → KISMI yetersiz
- K-ZST 10g uyari ama momentum ivme + hacim kuvvetli → ALARM degil

YENI LAYER (3 katman):

1. KURAL (k_engine.run_exit_checks) → mevcut, hizli
2. CONTEXT — makro/haber/tema/earnings/sektor analizi
3. CONFLICT DETECTION → kural çelişiyor mu context ile?
4. LLM JUDGEMENT (sadece celiski varsa) — Claude API call

Kullanim:
    from exit_judgement import judge_exit
    sonuc = judge_exit(pozisyon, market_ctx, kural_sonucu)
    # sonuc: {action, reasoning, confidence, layer_used}

Akil kararlari sadece celiski olan durumlara LLM cagrisi yapilir
(maliyet kontrolu).
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

REPO_ROOT = Path(__file__).resolve().parents[1]
TR = timezone(timedelta(hours=3))


def get_pozisyon_context(pos: dict, pf_name: str = "") -> dict:
    """
    Pozisyon icin zengin baglam:
    - Earnings yaklasıyor mu (K-05 tetigi)?
    - Tema gucu (theme_scores)?
    - Sektor performansi?
    - VIX ortami?
    - Kazanç açıklamasi onumuzdeki 7 gun mu?
    """
    sym = pos.get("sembol", "") or pos.get("symbol", "")
    ctx = {"sembol": sym, "portfoy": pf_name}
    
    # Tema gucu
    try:
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from theme_tracker import TEMALAR as _TEMALAR
        th_path = REPO_ROOT / "data" / "theme_scores.json"
        if th_path.exists():
            th = json.load(open(th_path))
            for tema_key, t in th.get("temalar", {}).items():
                if sym in _TEMALAR.get(tema_key, {}).get("semboller", []):
                    ctx["tema"] = {
                        "ad": t.get("ad"),
                        "skor": t.get("skor"),
                        "seviye": t.get("seviye"),
                        "rs_vs_spy": t.get("rs_vs_spy"),
                    }
                    break
    except Exception as _te:
        ctx["tema_hata"] = str(_te)[:60]
    
    # Earnings tarihi
    try:
        import requests
        KEY = os.environ.get("FMP_API_KEY", "")
        if KEY and sym:
            r = requests.get(
                "https://financialmodelingprep.com/stable/earnings",
                params={"symbol": sym, "limit": 4, "apikey": KEY},
                timeout=8
            )
            if r.status_code == 200:
                d = r.json()
                if isinstance(d, list):
                    bugun = datetime.now(TR).date()
                    for e in d:
                        try:
                            tarih_str = e.get("date") or e.get("fiscalDate")
                            if tarih_str:
                                tarih = datetime.strptime(tarih_str[:10], "%Y-%m-%d").date()
                                gun_fark = (tarih - bugun).days
                                if 0 <= gun_fark <= 14:
                                    ctx["earnings_yakin"] = {
                                        "tarih": tarih_str[:10],
                                        "gun_kala": gun_fark,
                                    }
                                    break
                        except Exception:
                            continue
    except Exception:
        pass
    
    # Sektor performansi (swing_entry_engine.check_sector_strength yeniden kullan)
    try:
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from swing_entry_engine import check_sector_strength
        ss = check_sector_strength(sym)
        if ss:
            ctx["sektor"] = {
                "ad": ss.get("sektor"),
                "etf": ss.get("etf"),
                "rs_vs_spy": ss.get("fark"),
                "outperform": ss.get("outperform"),
            }
    except Exception:
        pass
    
    # K-23 drawdown durumu
    try:
        from portfolio_drawdown_guard import analiz_yap as _k23_a
        s = _k23_a()
        if pf_name and pf_name in s.get("portfoyler", {}):
            ctx["drawdown"] = {
                "pct": s["portfoyler"][pf_name]["drawdown"]["drawdown_pct"],
                "k23_seviye": s["portfoyler"][pf_name]["k23"]["seviye"],
                "k23_kod": s["portfoyler"][pf_name]["k23"]["kod"],
            }
    except Exception:
        pass
    
    # Pozisyon yası ve kar/zarar
    try:
        giris_t = pos.get("giris_tarihi") or pos.get("entry_date")
        if giris_t:
            gd = datetime.strptime(giris_t[:10], "%Y-%m-%d")
            ctx["yas_gun"] = (datetime.now() - gd).days
        cf = pos.get("guncel_fiyat") or pos.get("son_fiyat")
        mb = pos.get("maliyet_baz")
        if cf and mb:
            ctx["kar_zarar_pct"] = round((cf - mb) / mb * 100, 2)
    except Exception:
        pass
    
    return ctx


def detect_conflict(kural_sonuc: dict, ctx: dict) -> dict:
    """
    Kural ile baglami karsilastir, celisik durum var mi?
    
    Celisik senaryolar:
    1. K-09/K-11 EXIT/PARTIAL ama earnings 0-7 gun + tema GUCLU → CELISKI
    2. K-ZST WARN ama tema GUCLU + sektor outperform → CELISKI
    3. K-15c PARTIAL ama momentum hala yukselen + tema gucleniyor → CELISKI
    4. K-06 EXIT ama drawdown DEFANSIF + alternatif sembol yok → SUPHE
    5. Her HOLD durumu ama drawdown HEDGE+ → CELISKI (ters)
    """
    aksiyon = kural_sonuc.get("action", "HOLD")
    sebep = kural_sonuc.get("reason", "")
    celiski = False
    celiski_nedenleri = []
    
    # K-06 zaten kesin EXIT — celiski yok
    if "K-06" in sebep:
        return {"celiski": False, "neden": "K-06 stop kesin tetik"}
    
    # 1. EXIT/PARTIAL ama tema GUCLU + earnings yok → kar realize'i sorgula
    if aksiyon in ("EXIT_NOW", "PARTIAL"):
        tema_skor = ctx.get("tema", {}).get("skor", 5)
        earnings = ctx.get("earnings_yakin")
        if tema_skor >= 8 and not earnings:
            celiski = True
            celiski_nedenleri.append(
                f"Kural EXIT/PARTIAL diyor ama tema {ctx['tema']['ad']} skor {tema_skor} GUCLU + earnings yakin degil"
            )
        # Sektor de pozitifse double conflict
        sek_rs = ctx.get("sektor", {}).get("rs_vs_spy", 0)
        if tema_skor >= 7 and sek_rs > 2:
            celiski = True
            celiski_nedenleri.append(
                f"Sektor {ctx['sektor']['ad']} SPY'i {sek_rs:+.1f}% gectiyor — momentum saglikli"
            )
    
    # 2. WARN (K-ZST) — context gucluyse uyariyi indir
    if aksiyon == "WARN":
        tema_skor = ctx.get("tema", {}).get("skor", 5)
        sek_rs = ctx.get("sektor", {}).get("rs_vs_spy", 0)
        kar = ctx.get("kar_zarar_pct", 0)
        if tema_skor >= 8 and sek_rs > 0 and kar > 5:
            celiski = True
            celiski_nedenleri.append(
                f"K-ZST uyari ama tema {tema_skor} GUCLU + sektor +{sek_rs:.1f}% + kar {kar}% — momentum hala saglikli"
            )
    
    # 3. HOLD ama drawdown HEDGE+ → ters celiski
    if aksiyon == "HOLD":
        dd_kod = ctx.get("drawdown", {}).get("k23_kod", 0)
        if dd_kod >= 3:  # HEDGE seviyesi
            celiski = True
            celiski_nedenleri.append(
                f"Kural HOLD diyor ama portfoy drawdown {ctx['drawdown']['k23_seviye']} — risk azaltma sart"
            )
    
    # 4. EXIT ama drawdown UYARI'da bile alternatif yok
    if aksiyon == "EXIT_NOW" and ctx.get("drawdown", {}).get("k23_kod", 0) >= 2:
        # Defansif veya hedge seviye — exit makul, celiski yok
        return {"celiski": False, "neden": "EXIT + drawdown defansif uyumlu"}
    
    return {
        "celiski": celiski,
        "nedenler": celiski_nedenleri,
    }


def llm_judgement(pos: dict, ctx: dict, kural_sonuc: dict) -> dict:
    """
    Claude'a celisikli durumda karari sor.
    Sadece celiski durumunda cagirilir.
    """
    sym = ctx.get("sembol", "?")
    
    sistem_msg = """You are Finzora's portfolio manager deciding swing/portfolio exits.
A rule has triggered but context conflicts with it — perform a deep analysis.

OUTPUT FORMAT (strict — exact labels, values where indicated):
ACTION: [HOLD / EXIT_NOW / PARTIAL_25 / PARTIAL_50 / TIGHTEN]
CONFIDENCE: [yuksek/orta/dusuk]
REASONING: [3-5 sentences in Turkish]
RISK: [bear case in 1 Turkish sentence]

Use the evidence tags KESİN / MUHTEMEL / SPEKÜLATİF (in Turkish) inside REASONING.
Cover the bear case as carefully as the bull case.
Output prose (REASONING/RISK) MUST be Turkish."""
    
    user_msg = f"""POZİSYON: {sym} ({ctx.get('portfoy', '?')})
Yaş: {ctx.get('yas_gun', '?')} gün | Kar/Zarar: {ctx.get('kar_zarar_pct', 0):+.1f}%

KURAL TETİĞİ: {kural_sonuc.get('action')}
SEBEP: {kural_sonuc.get('reason')}

BAĞLAM:
"""
    if "tema" in ctx:
        t = ctx["tema"]
        user_msg += f"- Tema: {t['ad']} skor {t['skor']}/10 ({t['seviye']}), RS:{t['rs_vs_spy']:+.1f}%\n"
    if "sektor" in ctx:
        s = ctx["sektor"]
        user_msg += f"- Sektor: {s['ad']} ({s['etf']}), RS:{s['rs_vs_spy']:+.1f}% vs SPY\n"
    if "earnings_yakin" in ctx:
        e = ctx["earnings_yakin"]
        user_msg += f"- ⚠️ EARNINGS: {e['tarih']} ({e['gun_kala']} gün kala)\n"
    if "drawdown" in ctx:
        d = ctx["drawdown"]
        user_msg += f"- Portföy drawdown: %{d['pct']:.1f} ({d['k23_seviye']})\n"
    
    user_msg += """
ÇELİŞKİ NEDENLERİ:
"""
    for n in kural_sonuc.get("celiski_nedenleri", []):
        user_msg += f"  - {n}\n"
    
    user_msg += "\nSomut karar ver. Sadece reasoning değil, ACTION mutlaka belirt."
    
    try:
        from claude_agent import get_claude_decision
        cevap = get_claude_decision(user_msg, mode="exit_judgement", 
                                      system_override=sistem_msg, rag_enabled=False)
        return {"llm_cevap": cevap, "ok": True}
    except Exception as e:
        return {"llm_cevap": f"LLM hata: {e}", "ok": False}


def parse_llm_cevap(llm_text: str) -> dict:
    """LLM cevabini ACTION/CONFIDENCE/REASONING'e parse et"""
    import re
    sonuc = {"action": "HOLD", "confidence": "dusuk", "reasoning": "", "risk": ""}
    
    if not llm_text:
        return sonuc
    
    # ACTION
    m = re.search(r'ACTION:\s*(HOLD|EXIT_NOW|PARTIAL_25|PARTIAL_50|TIGHTEN)', llm_text, re.IGNORECASE)
    if m:
        sonuc["action"] = m.group(1).upper()
    
    # CONFIDENCE
    m = re.search(r'CONFIDENCE:\s*(yuksek|orta|dusuk|yüksek|düşük)', llm_text, re.IGNORECASE)
    if m:
        sonuc["confidence"] = m.group(1).lower().replace("yüksek", "yuksek").replace("düşük", "dusuk")
    
    # REASONING
    m = re.search(r'REASONING:\s*(.+?)(?=RISK:|$)', llm_text, re.DOTALL | re.IGNORECASE)
    if m:
        sonuc["reasoning"] = m.group(1).strip()[:500]
    
    # RISK
    m = re.search(r'RISK:\s*(.+?)(?=\n\n|\Z)', llm_text, re.DOTALL | re.IGNORECASE)
    if m:
        sonuc["risk"] = m.group(1).strip()[:300]
    
    return sonuc


def _log_judgement(pos: dict, kural_sonuc: dict, ctx: dict, judgement: dict):
    """Tum judgement kararlarini logla — sonradan post-mortem icin"""
    try:
        log_path = REPO_ROOT / "logs" / "exit_judgement.jsonl"
        log_path.parent.mkdir(exist_ok=True)
        rec = {
            "tarih": datetime.now(TR).isoformat(),
            "sembol": ctx.get("sembol"),
            "portfoy": ctx.get("portfoy"),
            "kural_action": kural_sonuc.get("action"),
            "kural_reason": kural_sonuc.get("reason"),
            "tema": ctx.get("tema"),
            "sektor_rs": ctx.get("sektor", {}).get("rs_vs_spy"),
            "yas_gun": ctx.get("yas_gun"),
            "kar_pct": ctx.get("kar_zarar_pct"),
            "earnings": ctx.get("earnings_yakin"),
            "drawdown": ctx.get("drawdown"),
            "celiski": judgement.get("celiski"),
            "celiski_nedenleri": judgement.get("celiski_nedenleri", []),
            "layer_used": judgement.get("layer_used"),
            "final_action": judgement.get("action"),
            "confidence": judgement.get("confidence"),
            "reasoning": judgement.get("reasoning", "")[:300],
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as _le:
        print(f"[Judgement log] {_le}")


def judge_exit(pos: dict, kural_sonuc: dict, pf_name: str = "", 
               force_llm: bool = False) -> dict:
    """
    ANA FONKSIYON — pozisyonun cikis karari icin 3 katmanli analiz.
    
    pos: pozisyon dict (sembol, fiyat, stop, vb.)
    kural_sonuc: k_engine.run_exit_checks() sonucu
    pf_name: portfoy adi (balanced/aggressive/dividend/swing)
    force_llm: True ise her zaman LLM cagir (test icin)
    
    Donus:
        {
            "action": HOLD/EXIT_NOW/PARTIAL/TIGHTEN/WARN,
            "reasoning": str,
            "confidence": yuksek/orta/dusuk,
            "layer_used": "kural"/"context"/"llm",
            "kural_sonuc": orijinal kural cıktısı,
            "celiski": bool,
            "ctx": baglam dict,
        }
    """
    # 1. Context al
    ctx = get_pozisyon_context(pos, pf_name)
    
    # 2. Conflict tespit
    conflict = detect_conflict(kural_sonuc, ctx)
    
    # 3. Final action
    if not conflict["celiski"] and not force_llm:
        # Celiski yok, kural net — sadece kural sonucunu dondur
        sonuc = {
            "action": kural_sonuc.get("action", "HOLD"),
            "reasoning": kural_sonuc.get("reason", ""),
            "confidence": "yuksek",
            "layer_used": "kural",
            "kural_sonuc": kural_sonuc,
            "celiski": False,
            "ctx": ctx,
        }
        _log_judgement(pos, kural_sonuc, ctx, sonuc)
        return sonuc
    
    # 4. Celiski var → LLM judgement
    kural_with_celiski = {
        **kural_sonuc,
        "celiski_nedenleri": conflict.get("nedenler", []),
    }
    llm_r = llm_judgement(pos, ctx, kural_with_celiski)
    
    if not llm_r["ok"]:
        # LLM hatasi — kural sonucuna geri don
        sonuc = {
            "action": kural_sonuc.get("action", "HOLD"),
            "reasoning": f"LLM hatasi, kurala geri donildi: {kural_sonuc.get('reason')}",
            "confidence": "orta",
            "layer_used": "kural-fallback",
            "kural_sonuc": kural_sonuc,
            "celiski": True,
            "celiski_nedenleri": conflict.get("nedenler", []),
            "ctx": ctx,
        }
        _log_judgement(pos, kural_sonuc, ctx, sonuc)
        return sonuc
    
    # 5. LLM cevabini parse et
    parsed = parse_llm_cevap(llm_r["llm_cevap"])
    sonuc = {
        "action": parsed["action"],
        "reasoning": parsed["reasoning"] or llm_r["llm_cevap"][:300],
        "risk": parsed.get("risk", ""),
        "confidence": parsed["confidence"],
        "layer_used": "llm",
        "kural_sonuc": kural_sonuc,
        "celiski": True,
        "celiski_nedenleri": conflict.get("nedenler", []),
        "llm_full": llm_r["llm_cevap"],
        "ctx": ctx,
    }
    _log_judgement(pos, kural_sonuc, ctx, sonuc)
    return sonuc


# Standalone test
if __name__ == "__main__":
    # Mock pozisyon: 8g tema alimi, +%10 kar, RSI 78, sektor outperform
    test_pos = {
        "sembol": "MU",
        "guncel_fiyat": 145.0,
        "maliyet_baz": 132.0,
        "stop_loss": 130.0,
        "giris_tarihi": "2026-04-20",
        "giris_fiyat": 132.0,
    }
    test_kural = {
        "action": "PARTIAL",
        "pct": 25,
        "reason": "K-11 katman 2: RSI 78 + kar %10",
    }
    print("Test: K-11 PARTIAL ama tema GUCLU + sektor outperform")
    sonuc = judge_exit(test_pos, test_kural, "aggressive")
    print(f"Layer kullanilan: {sonuc['layer_used']}")
    print(f"Action: {sonuc['action']}")
    print(f"Confidence: {sonuc['confidence']}")
    print(f"Reasoning: {sonuc['reasoning'][:200]}")
    if sonuc.get("celiski"):
        print(f"Celiski: YES")
        for n in sonuc.get("celiski_nedenleri", []):
            print(f"  - {n}")
    print(f"\nContext:")
    for k, v in sonuc["ctx"].items():
        print(f"  {k}: {v}")
