# Log Retention Politikası

**Yürürlük:** 10 Mayıs 2026 itibarıyla
**Kaynak:** finzora ai
**İlgili dosyalar:** `scripts/log_rotation.py`, `.github/workflows/log_rotation.yml`

## 1. Sorun

`logs/events.jsonl` append-only observability log'u sonsuza büyür. Bu yazımı itibarıyla:

| Tarih aralığı | Boyut | Kayıt |
|---------------|-------|-------|
| 17 Şub - 11 May 2026 (84 gün) | 15.30 MB | 73,206 |

Trend yaklaşık 870 kayıt/gün ortalama, yıllık tahmin yaklaşık 200 MB. Git repo için ölçeklenebilir değil. Üstelik SQLite index'i (`data/finzora.db`) de paralel büyür.

## 2. Strateji

**Aylık archive + sıkıştırma:**

- `logs/events.jsonl` aktif dosyası sadece **şu anki ayın kayıtlarını** tutar
- Tamamlanmış aylar `logs/archive/events-YYYY-MM.jsonl.gz` olarak sıkıştırılır
- Sıkıştırma oranı yaklaşık 8-10x (JSONL highly compressible)
- Archive dosyaları git'te tutulur (gerektiğinde restore edilebilir, .gz dosyaları küçük)

**RAG ile uyum:**

Memory'deki RAG sistemi (`docs/RAG_SYSTEM.md`) `logs/events.jsonl`'i kaynak olarak kullanıyor. Aylık archive ile aktif window 1 ay olunca RAG için yeterince context kalır (son 30 gün karar geçmişi). Daha eski analiz için archive dosyaları manuel olarak ungzip + concat edilebilir.

## 3. Tool — `scripts/log_rotation.py`

### Komutlar

```bash
# Durum raporu (read-only, güvenli)
python scripts/log_rotation.py --stats

# Şu anki ay hariç tüm tamamlanmış ayları arşivle
python scripts/log_rotation.py --archive-completed

# Belirli ayı arşivle
python scripts/log_rotation.py --archive-month 2026-04

# Hepsi --dry-run ile simüle edilebilir (dosya yazmaz)
python scripts/log_rotation.py --archive-completed --dry-run
```

### Güvenlik garantileri

1. **Atomic swap**: Önce yeni aktif dosya `events.jsonl.tmp`'ye yazılır, archive `.gz.tmp`'ye yazılır. Sayım doğrulanır. Sonra atomic `shutil.move()` ile yer değiştirilir. Yarıda kalan rotation kayıp yaratmaz.
2. **Sayım doğrulama**: İlk pass'te beklenen sayılar hesaplanır, yazım sonrası karşılaştırılır. Uyuşmazlık varsa rollback.
3. **Çift archive yasak**: Aynı ay için `events-YYYY-MM.jsonl.gz` zaten varsa hata verir, üzerine yazmaz.
4. **Şu anki ay reddi**: Hâlâ kayıt gelen ayı arşivlemeye izin vermez (`HATA: 2026-05 arşivlenemez`).
5. **Malformed kayıt korunur**: JSON parse edilemeyen satırlar aktif dosyada kalır (kaybedilmez).

### Tipik akış

Her ayın başında (örnek 1 Haziran):

```bash
# Önce durum gör
python scripts/log_rotation.py --stats

# Mayıs ayını arşivle (artık tamamlandı)
python scripts/log_rotation.py --archive-month 2026-05 --dry-run  # önce simüle
python scripts/log_rotation.py --archive-month 2026-05            # gerçek archive

# Veya kısayolu: birkaç ay geriye kalmışsa hepsini birden
python scripts/log_rotation.py --archive-completed
```

## 4. Workflow — `.github/workflows/log_rotation.yml`

Memory kuralı gereği cron yok. Tetikleyiciler:

- **workflow_dispatch** (manuel): Zeynel Actions sekmesinden seçer
  - action: `stats` | `archive-completed` | `archive-month`
  - month: `YYYY-MM` (sadece archive-month için)
  - dry_run: default `true` (güvenli)
- **push paths**: `scripts/log_rotation.py` veya workflow değişimi → otomatik `--stats` smoke test

Gerçek archive (dry_run=false ve action != stats) sonucunda otomatik commit + push yapılır. Commit author standart bot: `Finzora Bot <finzora-bot@users.noreply.github.com>`, prefix `[bot/log-rotation]` (memory'deki Git Strategy konvansiyonu).

## 5. Restore (İade)

Bir archive ayını geri yüklemek gerekirse:

```bash
# Archive'ı aç ve aktif dosyanın başına ekle
gunzip -c logs/archive/events-2026-04.jsonl.gz > /tmp/restored.jsonl
cat logs/events.jsonl >> /tmp/restored.jsonl
mv /tmp/restored.jsonl logs/events.jsonl

# SQLite index'i yeniden kur (varsayılan: agent/observability.py rebuild_index)
python -c "from agent.observability import rebuild_index; rebuild_index()"
```

NOT: rebuild_index henüz yoksa, `data/finzora.db`'yi silip ilk log_event çağrısında otomatik yeniden inşa edilir.

## 6. İzlem

- `logs/events.jsonl` boyutu 50 MB'ı geçerse uyarı (gelecek: weekly_fmp_stats workflow'una ekle)
- `logs/archive/` toplam boyutu 200 MB'ı geçerse 12 aydan eski dosyaları gözden geçir
- Aylık rotation aksattığında: `--stats` çıktısı şu anki ay dışında ay gösterirse Zeynel haberdar olur (manuel workflow trigger)

---

**Son güncelleme:** 10 Mayıs 2026
**Kaynak:** finzora ai
