"""
agent/k_engine.py için unit testler.

Kapsam (şimdilik):
- k13_position_size: VIX bazlı sektör pozisyon büyüklüğü karar matrisi
  (K-13 v4.2 — docs/TRADING_PLAYBOOK.md)

Bu modüldeki diğer fonksiyonlar (k05, k17, k18, k19, k20) FMP API
çağırıyor, onlar için ayrı mock'lu test suite gerek. Şimdilik en pure
fonksiyon olan k13_position_size'a odaklanıyoruz.

Çalıştırma:
    cd repo_root && python -m pytest tests/test_k_engine.py -v
"""

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "agent"))

import k_engine  # noqa: E402


# ── Fixture: kriz matrisini mock'la, dosyaya bağımlılık yok ───────────────────

@pytest.fixture
def mock_crisis_matrix(monkeypatch):
    """
    Sabit test matrisi: Defense, Energy, Gold faydalanıcı.
    Diğer her şey (Technology, Consumer, vs) faydalanıcı DEĞİL
    (kod elinde 'beneficiary olmayan = duyarlı' mantığı).
    """
    def fake_loader():
        return (
            {"Defense", "Energy", "Gold"},  # beneficiary
            {"Technology", "Consumer", "Travel"},  # sensitive (k13'te kullanılmıyor ama dönüş tipi için)
            "test_kriz",
        )
    monkeypatch.setattr(k_engine, "_load_crisis_matrix", fake_loader)


# ── Test grubu: VIX < 22 — tam pozisyon (sektör fark etmez) ───────────────────

class TestVixBelow22:
    """VIX 22'nin altı — tüm sektörlere tam pozisyon (K-13 v4.2)."""

    def test_beneficiary_full(self, mock_crisis_matrix):
        size, note = k_engine.k13_position_size(vix=15.0, sector="Defense", base_size=10000)
        assert size == 10000
        assert "tam pozisyon" in note

    def test_non_beneficiary_full(self, mock_crisis_matrix):
        size, note = k_engine.k13_position_size(vix=18.5, sector="Technology", base_size=10000)
        assert size == 10000, "VIX<22'de tüm sektörler tam alır"
        assert "tam pozisyon" in note

    def test_kriz_label_in_note(self, mock_crisis_matrix):
        _, note = k_engine.k13_position_size(vix=10.0, sector="Defense", base_size=5000)
        assert "test_kriz" in note


# ── Test grubu: 22 ≤ VIX < 28 — faydalanıcı tam, diğer yarım ──────────────────

class TestVix22to28:
    """22 ≤ VIX < 28 — faydalanıcı tam, faydalanıcı olmayan yarım."""

    def test_beneficiary_full(self, mock_crisis_matrix):
        size, note = k_engine.k13_position_size(vix=25.0, sector="Energy", base_size=10000)
        assert size == 10000
        assert "faydalanıcı" in note and "tam" in note

    def test_non_beneficiary_half(self, mock_crisis_matrix):
        size, note = k_engine.k13_position_size(vix=26.0, sector="Technology", base_size=10000)
        assert size == 5000
        assert "duyarlı" in note and "yarım" in note

    def test_boundary_vix_22_uses_22to28_path(self, mock_crisis_matrix):
        """VIX=22 tam sınır — 22-28 path'ine düşer (vix<22 değil ama vix<28)."""
        size, _ = k_engine.k13_position_size(vix=22.0, sector="Technology", base_size=10000)
        assert size == 5000  # non-beneficiary yarım

    def test_boundary_vix_27_99(self, mock_crisis_matrix):
        """VIX 27.99 hâlâ 22-28 zonunda."""
        size, _ = k_engine.k13_position_size(vix=27.99, sector="Gold", base_size=10000)
        assert size == 10000  # beneficiary tam


# ── Test grubu: 28 ≤ VIX < 35 — faydalanıcı yarım, diğer sıfır ───────────────

class TestVix28to35:
    """28 ≤ VIX < 35 — faydalanıcı yarım, faydalanıcı olmayan giriş yok."""

    def test_beneficiary_half(self, mock_crisis_matrix):
        size, note = k_engine.k13_position_size(vix=30.0, sector="Defense", base_size=10000)
        assert size == 5000
        assert "yarım" in note

    def test_non_beneficiary_zero(self, mock_crisis_matrix):
        size, note = k_engine.k13_position_size(vix=32.0, sector="Travel", base_size=10000)
        assert size == 0
        assert "giriş yok" in note


# ── Test grubu: VIX ≥ 35 — faydalanıcı çeyrek, diğer sıfır ────────────────────

class TestVixAbove35:
    """VIX ≥ 35 ekstrem — faydalanıcı çeyrek, faydalanıcı olmayan sıfır."""

    def test_beneficiary_quarter(self, mock_crisis_matrix):
        size, note = k_engine.k13_position_size(vix=40.0, sector="Gold", base_size=10000)
        assert size == 2500
        assert "çeyrek" in note

    def test_non_beneficiary_zero(self, mock_crisis_matrix):
        size, note = k_engine.k13_position_size(vix=45.0, sector="Consumer", base_size=10000)
        assert size == 0
        assert "giriş yok" in note

    def test_boundary_vix_35_exact(self, mock_crisis_matrix):
        """VIX=35 tam sınır — ≥35 path'ine düşer."""
        size, _ = k_engine.k13_position_size(vix=35.0, sector="Defense", base_size=10000)
        assert size == 2500  # beneficiary çeyrek


# ── Test grubu: Sektör string'i case-insensitive eşleşme ─────────────────────

class TestSectorMatching:
    """Sektör string'i case-insensitive ve substring eşleşmesi."""

    def test_lowercase_match(self, mock_crisis_matrix):
        """Sektör küçük harf — beneficiary set'inde 'Defense' var ama 'defense' geçerse de eşleşmeli."""
        size, _ = k_engine.k13_position_size(vix=25.0, sector="defense", base_size=10000)
        assert size == 10000  # eşleşme oldu, beneficiary tam

    def test_substring_match(self, mock_crisis_matrix):
        """'Defense & Aerospace' içinde 'Defense' geçtiği için faydalanıcı."""
        size, _ = k_engine.k13_position_size(vix=25.0, sector="Defense & Aerospace", base_size=10000)
        assert size == 10000

    def test_no_match_treated_as_non_beneficiary(self, mock_crisis_matrix):
        """Bilinmeyen sektör adı — eşleşmediği için faydalanıcı değil."""
        size, _ = k_engine.k13_position_size(vix=25.0, sector="Healthcare", base_size=10000)
        assert size == 5000  # non-beneficiary yarım


# ── Test grubu: base_size farklı değerler ────────────────────────────────────

class TestBaseSizeScaling:
    """Pozisyon büyüklüğü base_size ile orantılı ölçekleniyor."""

    def test_base_size_zero(self, mock_crisis_matrix):
        """base_size=0 → her durumda 0."""
        size, _ = k_engine.k13_position_size(vix=20.0, sector="Defense", base_size=0)
        assert size == 0

    def test_base_size_large(self, mock_crisis_matrix):
        """base_size=400000 (Agresif portföy) — çeyrek = 100000."""
        size, _ = k_engine.k13_position_size(vix=40.0, sector="Defense", base_size=400000)
        assert size == 100000

    def test_base_size_float_half(self, mock_crisis_matrix):
        """Yarım ondalık doğru."""
        size, _ = k_engine.k13_position_size(vix=25.0, sector="Technology", base_size=12345)
        assert size == pytest.approx(6172.5)
