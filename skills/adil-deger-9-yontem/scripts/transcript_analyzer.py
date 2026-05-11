"""
Transcript Analyzer — Adil Değer Skill v5.0 Etap 13 Fix-3
==========================================================

Bilanço sonrası earnings call transcript'i Kimi K2 Thinking ile analiz eder.

Mantık:
- Son earnings tarihi 10 gün içinde ise (analyst revizeleri henüz tamamlanmamış olabilir):
  1. FMP earning-call-transcript çek
  2. Kimi K2 Thinking'e gönder, key takeaways çıkar
  3. Markdown'a "Son Bilanço Bilgileri" bölümü ekle

OpenRouter API: https://openrouter.ai/api/v1/chat/completions
Model: moonshotai/kimi-k2-thinking ($0.60/M input, $2.50/M output, 262K context)

ENV: OPENROUTER_API_KEY (zorunlu, yoksa fonksiyon None döner)

finzora ai
"""

import os
import sys
import json
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
KIMI_MODEL = "moonshotai/kimi-k2-thinking"
EARNINGS_FRESHNESS_DAYS = 15  # T+10 gün eşiği


def get_last_earnings_date(fmp_get, ticker):
    """
    FMP'den şirketin son açıklanmış bilanço tarihini al.
    
    Args:
        fmp_get: FMP fetch fonksiyonu (zaten projesinde tanımlı)
        ticker: hisse sembolü
    
    Returns: (date_str 'YYYY-MM-DD' or None, eps_actual, rev_actual)
    """
    try:
        data = fmp_get("earnings", {"symbol": ticker, "limit": 8})
        if not isinstance(data, list):
            return (None, None, None)
        
        # Sadece actuals açıklanmış olanları al (epsActual != None)
        today = datetime.now().date()
        reported = []
        for d in data:
            if d.get('epsActual') is not None or d.get('revenueActual') is not None:
                try:
                    ed = datetime.fromisoformat(d['date']).date()
                    if ed <= today:
                        reported.append((ed, d.get('epsActual'), d.get('revenueActual')))
                except (ValueError, KeyError):
                    continue
        
        if not reported:
            return (None, None, None)
        
        reported.sort(key=lambda x: x[0], reverse=True)
        latest_date, eps_a, rev_a = reported[0]
        return (latest_date.isoformat(), eps_a, rev_a)
    
    except Exception as e:
        sys.stderr.write(f"⚠️ get_last_earnings_date hata: {e}\n")
        return (None, None, None)


def days_since_earnings(last_earnings_date_str):
    """Earnings tarihinden bugüne kaç gün geçti."""
    if not last_earnings_date_str:
        return None
    try:
        ed = datetime.fromisoformat(last_earnings_date_str).date()
        return (datetime.now().date() - ed).days
    except (ValueError, TypeError):
        return None


def get_earnings_transcript(fmp_get, ticker, year=None, quarter=None):
    """
    FMP earning-call-transcript endpoint'inden çek.
    
    Args:
        fmp_get: FMP fetch fonksiyonu
        ticker: hisse sembolü
        year: fiscal year (None ise current year)
        quarter: 1-4 veya None (None ise en yenisini al, bu endpoint için fiscal Q gerekli)
    
    Returns: dict {'content': str, 'date': str, 'year': int, 'quarter': int} veya None
    """
    if year is None:
        year = datetime.now().year
    
    # FMP earning-call-transcript için Q1-Q4 dene, en yenisini bul
    quarters_to_try = [quarter] if quarter else [3, 2, 1, 4]  # son fiscal Q'lar genelde
    
    for q in quarters_to_try:
        try:
            data = fmp_get("earning-call-transcript", {
                "symbol": ticker, "year": year, "quarter": q
            })
            if isinstance(data, list) and data:
                d = data[0]
                content = d.get('content', '')
                if content and len(content) > 1000:  # geçerli transcript
                    return {
                        'content': content,
                        'date': d.get('date', ''),
                        'year': d.get('year', year),
                        'quarter': d.get('quarter', q),
                    }
        except Exception:
            continue
    
    # Bir önceki yıl da dene
    if year > 2020:
        try:
            data = fmp_get("earning-call-transcript", {
                "symbol": ticker, "year": year - 1, "quarter": 4
            })
            if isinstance(data, list) and data:
                d = data[0]
                content = d.get('content', '')
                if content and len(content) > 1000:
                    return {
                        'content': content,
                        'date': d.get('date', ''),
                        'year': d.get('year', year - 1),
                        'quarter': d.get('quarter', 4),
                    }
        except Exception:
            pass
    
    return None


def analyze_transcript_with_kimi(transcript_text, ticker, date_str):
    """
    Kimi K2 Thinking'e gönder, key takeaways al.
    
    Args:
        transcript_text: tam transcript metni
        ticker: hisse sembolü
        date_str: bilanço tarihi
    
    Returns: dict {'guidance', 'revenue_q', 'beat_miss', 'key_themes', 'risks', 'raw'} 
             veya None (hata/key yok)
    """
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        return None  # Sessiz fallback
    
    # Çok uzun transcript'leri kısalt — 100K karakter yeterli (Kimi 262K context destekler ama maliyet)
    if len(transcript_text) > 100000:
        transcript_text = transcript_text[:100000] + "\n\n[... transcript truncated for length ...]"
    
    prompt = f"""You are a financial analyst. Analyze this earnings call transcript for {ticker} (date: {date_str}).

Extract the following in JSON format (no other text, just valid JSON):

{{
  "quarter_results": {{
    "revenue": "actual revenue figure with YoY % if mentioned",
    "eps": "actual EPS figure",
    "beat_or_miss": "BEAT/MEET/MISS vs expectations, brief explanation"
  }},
  "forward_guidance": {{
    "next_quarter": "guidance for next quarter if given",
    "full_year": "FY guidance if given (revenue, margins, capex)",
    "multi_year": "multi-year targets if any (e.g., 'targeting $5B revenue by 2028')"
  }},
  "key_themes": [
    "3-5 strategic themes management emphasized (e.g., new customer wins, product launches, capacity expansion)"
  ],
  "risks_mentioned": [
    "3-5 risks or challenges management acknowledged or analysts probed"
  ],
  "analyst_qa_signals": [
    "2-3 notable analyst questions and management's response style (defensive/confident/evasive)"
  ],
  "summary_one_sentence": "One sentence: was this a positive, neutral, or negative quarter and why?"
}}

Transcript:
{transcript_text}
"""
    
    payload = {
        "model": KIMI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 3000,
        "temperature": 0.2,  # Düşük sıcaklık, JSON çıktısı için
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/zeynelgun-afk/portfolio-tracker",  # OpenRouter recommend
        "X-Title": "Finzora AI - Adil Deger Skill",
    }
    
    try:
        req = Request(
            OPENROUTER_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST',
        )
        with urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        # Yanıtı parse et
        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        if not content:
            return None
        
        # JSON parse — Kimi bazen ```json fences ekleyebilir
        cleaned = content.strip()
        if cleaned.startswith('```'):
            # ```json ... ``` fence kaldır
            lines = cleaned.split('\n')
            cleaned = '\n'.join(lines[1:-1] if lines[-1].startswith('```') else lines[1:])
        
        try:
            parsed = json.loads(cleaned)
            parsed['raw'] = content  # debug için
            return parsed
        except json.JSONDecodeError as je:
            sys.stderr.write(f"⚠️ Kimi response JSON parse hatası: {je}\n")
            # Yine de raw içeriği dön
            return {'raw': content, 'parse_error': str(je)}
    
    except HTTPError as e:
        sys.stderr.write(f"⚠️ OpenRouter HTTP {e.code}: {e.reason}\n")
        return None
    except URLError as e:
        sys.stderr.write(f"⚠️ OpenRouter network: {e.reason}\n")
        return None
    except Exception as e:
        sys.stderr.write(f"⚠️ Kimi analiz hatası: {type(e).__name__}: {e}\n")
        return None


def get_freshness_analysis(fmp_get, ticker):
    """
    Bilanço tazelik analizi — son earnings tarihi ≤10 gün ise transcript analiz et.
    
    Args:
        fmp_get: FMP fetch fonksiyonu
        ticker: hisse sembolü
    
    Returns: dict {
        'last_earnings_date': str or None,
        'days_since': int or None,
        'is_fresh': bool,  # ≤10 gün mü
        'eps_actual': float or None,
        'revenue_actual': float or None,
        'transcript_analysis': dict or None,
    }
    """
    last_date, eps_a, rev_a = get_last_earnings_date(fmp_get, ticker)
    days = days_since_earnings(last_date)
    is_fresh = (days is not None and days <= EARNINGS_FRESHNESS_DAYS)
    
    result = {
        'last_earnings_date': last_date,
        'days_since': days,
        'is_fresh': is_fresh,
        'eps_actual': eps_a,
        'revenue_actual': rev_a,
        'transcript_analysis': None,
    }
    
    if is_fresh:
        # Transcript çek + analiz et
        transcript = get_earnings_transcript(fmp_get, ticker)
        if transcript:
            analysis = analyze_transcript_with_kimi(
                transcript['content'], ticker, transcript['date']
            )
            if analysis:
                analysis['transcript_date'] = transcript['date']
                analysis['transcript_year'] = transcript['year']
                analysis['transcript_quarter'] = transcript['quarter']
                result['transcript_analysis'] = analysis
    
    return result


def format_freshness_markdown(freshness):
    """Markdown bölümünü üret — Yönetici Özeti altına veya ayrı bölüm olarak."""
    if not freshness or not freshness.get('last_earnings_date'):
        return []
    
    lines = []
    days = freshness.get('days_since')
    last_date = freshness.get('last_earnings_date')
    
    if freshness.get('is_fresh'):
        lines.append("## 📰 Son Bilanço Bilgileri (Taze Veri)")
        lines.append("")
        lines.append(f"⚠️ **Bilanço açıklandı: {last_date} ({days} gün önce)**")
        lines.append(f"Analyst forward EPS rakamları henüz revize olmamış olabilir. Adil değer hesabı stale data içerebilir.")
        lines.append("")
        
        eps_a = freshness.get('eps_actual')
        rev_a = freshness.get('revenue_actual')
        if eps_a is not None or rev_a is not None:
            lines.append(f"**Gerçekleşen:** ")
            if rev_a is not None:
                lines.append(f"- Revenue: ${rev_a/1e6:.1f}M")
            if eps_a is not None:
                lines.append(f"- EPS: ${eps_a:.2f}")
            lines.append("")
        
        analysis = freshness.get('transcript_analysis')
        if analysis and 'quarter_results' in analysis:
            lines.append(f"### Kimi K2 Thinking — Transcript Analizi")
            lines.append("")
            
            qr = analysis.get('quarter_results', {})
            if qr:
                lines.append(f"**Çeyrek Sonuçları:**")
                if qr.get('revenue'):
                    lines.append(f"- Revenue: {qr['revenue']}")
                if qr.get('eps'):
                    lines.append(f"- EPS: {qr['eps']}")
                if qr.get('beat_or_miss'):
                    lines.append(f"- Beat/Miss: {qr['beat_or_miss']}")
                lines.append("")
            
            fg = analysis.get('forward_guidance', {})
            if fg:
                lines.append(f"**Forward Guidance (yönetimin verdiği):**")
                if fg.get('next_quarter'):
                    lines.append(f"- Sonraki çeyrek: {fg['next_quarter']}")
                if fg.get('full_year'):
                    lines.append(f"- Tam yıl: {fg['full_year']}")
                if fg.get('multi_year'):
                    lines.append(f"- Çok yıllı: {fg['multi_year']}")
                lines.append("")
            
            themes = analysis.get('key_themes', [])
            if themes:
                lines.append(f"**Stratejik Temalar:**")
                for t in themes[:5]:
                    lines.append(f"- {t}")
                lines.append("")
            
            risks = analysis.get('risks_mentioned', [])
            if risks:
                lines.append(f"**Yönetimin/Analystlerin Belirttiği Riskler:**")
                for r in risks[:5]:
                    lines.append(f"- {r}")
                lines.append("")
            
            qa = analysis.get('analyst_qa_signals', [])
            if qa:
                lines.append(f"**Analyst Soru-Cevap Sinyalleri:**")
                for q in qa[:3]:
                    lines.append(f"- {q}")
                lines.append("")
            
            summary = analysis.get('summary_one_sentence', '')
            if summary:
                lines.append(f"**Tek Cümlelik Özet:** {summary}")
                lines.append("")
        
        elif analysis and 'raw' in analysis:
            # Parse hatası vs Kimi response
            lines.append("### Kimi K2 Thinking (raw, parse hatası)")
            lines.append("")
            lines.append(f"```\n{analysis['raw'][:2000]}\n```")
            lines.append("")
        
        elif not analysis and freshness.get('is_fresh'):
            lines.append("_Kimi K2 Thinking analizi yapılamadı (OPENROUTER_API_KEY env değişkeni eksik veya API hatası)._")
            lines.append("")
    
    return lines
