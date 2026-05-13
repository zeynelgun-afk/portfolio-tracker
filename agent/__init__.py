"""
Finzora AI — agent package v2

Sadeleştirilmiş portfolio yönetim sistemi. 13 Mayıs 2026'da agent/legacy/ altına
arşivlenen eski sistem yerine yazıldı.

Felsefe:
- Tek data/portfolio.json (sleeve/tema disiplini yok)
- Pozisyon büyüklüğü kararı Zeynel'e ait, Claude kâtip + analist rolünde
- Otomatik karar dayatan kural yok
- Sade kod, anlaşılır API, minimal bağımlılık

Modüller:
- portfolio: CRUD + FMP price enrichment + metrics
- (yakında) reports: morning/closing report generators
- (yakında) monitor: position monitoring + alerts
- (yakında) telegram: Turkish message sender (group + DM)

Eski sistem: agent/legacy/ (50+ dosya, 3-portföy + sleeve mantığı)
Detay: notes/2026-05-13_SIMPLIFICATION.md
"""

__version__ = "2.0.0"
