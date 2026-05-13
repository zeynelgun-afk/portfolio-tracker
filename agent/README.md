# Finzora AI — agent package v2

Simplified agent system written 13 May 2026 to replace the 50+ file legacy
system archived under `agent/legacy/`. Driven by Zeynel's feedback that the
previous system "felt too institutional".

## Philosophy

- **Single source of truth:** `data/portfolio.json` (no sleeve / theme files)
- **Claude is a scribe + analyst**, not a portfolio manager
- **No automatic decision-imposing rules** (K-11, K-12, K-15c, K-22 removed)
- **English code, English file names, English reports.** Turkish only for
  Telegram bot messages and direct conversation with Zeynel.
- **Small, readable modules.** Each file should fit on a single screen if
  possible. No 2700-line orchestrators.

## Module status (as of 13 May 2026)

| Module | Status | Purpose |
|---|---|---|
| `portfolio.py` | ✅ Implemented | CRUD + FMP price enrichment + metrics |
| `reports/morning.py` | 🟡 TODO | Daily pre-session report generator |
| `reports/closing.py` | 🟡 TODO | Daily post-close report generator |
| `reports/weekly.py` | 🟡 TODO | Sunday weekly review |
| `monitor.py` | 🟡 TODO | Position alerts (K-13 VIX, K-23 drawdown) |
| `telegram.py` | 🟡 TODO | Turkish message sender (group + DM) |
| `fmp.py` | 🟡 TODO | FMP client wrapper (currently uses legacy/fmp_client) |

## Migration path

Each new module is written from scratch with the single-portfolio model.
When functional, the corresponding legacy module (e.g.
`agent/legacy/orchestrator.py`) is no longer called by Telegram bot or
GitHub Actions. Legacy modules remain on disk for reference but are not
maintained.

GitHub Actions workflows that reference legacy paths (`agent.yml`,
`agent_morning`, `agent_closing`, etc.) will be updated in a follow-up
commit once the morning/closing report modules are in place.

## Data schema (post-simplification)

Open position (8 fields):
```json
{
  "symbol": "TICKER",
  "sector": "Sector name",
  "entry_date": "YYYY-MM-DD",
  "entry_price": 0.00,
  "shares": 0,
  "entry_reason": "Detailed thesis — why entered, catalyst, etc.",
  "stop_loss": 0.00,
  "target": null
}
```

On close, the following fields are appended:
```json
{
  "exit_date": "YYYY-MM-DD",
  "exit_price": 0.00,
  "exit_reason": "Stop / target / thesis break / other",
  "pnl_pct": 0.00,
  "lessons": "Optional post-trade review"
}
```

## See also

- `notes/2026-05-13_SIMPLIFICATION.md` — full simplification record
- `docs/K_RULES_QUICK_REF.md` — current minimal K-rules
- `agent/legacy/README.md` — old system reference (do not extend)
