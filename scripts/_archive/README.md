# scripts/_archive/

Aktif sistemden çıkarılmış ama tarihsel/referans değer için saklanan scriptler.

**Bu klasörden hiçbir şey aktif çağrılmamalı.** Eğer bir dosyaya tekrar ihtiyaç olursa
`scripts/`'e geri taşınması ve agent kodunda neye/nereye bağlandığının netleştirilmesi gerek.

## İçerik (2026-05-03 arşivlemesi)

| Dosya | Yerini alan |
|---|---|
| `swing_technical.py` | `agent/swing_manager.py` + `scripts/swing_ichimoku.py` |
| `swing_full_universe.py` | `scripts/full_universe_screener.py` |
| `portfolio_scan_aggressive.py` | `scripts/full_universe_screener.py` (mode=aggressive) |
| `judgement_review.py` | `agent/exit_judgement.py` (LLM override layer) |
| `k_rule_performance.py` | `scripts/k_rules_backtest.py` (orchestrator subprocess) |
| `trade_memory.py` | `agent/memory_manager.py` + RAG (`scripts/rag/`) |
| `k16_sell_the_news_score.py` | `scripts/weekly_pre_check.py:283` inline kullanır |

## Geri çekme

Bir dosyaya tekrar ihtiyaç olursa:

```bash
git mv scripts/_archive/<dosya>.py scripts/<dosya>.py
# kullanan kodu güncelle
```

## Tamamen silme

Eğer bir dosya 6 ay aktif olarak referans edilmediyse silinebilir:

```bash
git rm scripts/_archive/<dosya>.py
```
