"""agent/ai_gate.py kalibrasyon entegrasyonu testleri.

Faz 2 — Adım 10b-iii-B: calibration_info → prompt entegrasyonu.

KAPSAM:
    - _build_calibration_section: 4 bayrak tipi için doğru rehber
    - Bayrak rehberi içeriği (DESTEK vs ÇELİŞKİ yönü)
    - Karışık bayraklar (conflict + confirm)
    - Bilinmeyen bayrak → atlanır
    - Boş flags → bölüm yok
    - Bozuk calibration_info → bölüm yok
    - _build_prompt geriye uyumluluk: calibration_info=None → bölüm yok
    - _build_prompt: calibration_info dolu → POLYMARKET KALİBRASYON başlığı
    - evaluate_signal calibration_info parametresi accept ediyor
"""
from __future__ import annotations

import pytest


# ── _build_calibration_section ─────────────────────────────────────────────────


class TestBuildCalibrationSection:
    def _import(self):
        from agent.ai_gate import _build_calibration_section
        return _build_calibration_section

    def test_pm_confirm_strong(self):
        build = self._import()
        info = {
            "flags": ["pm_confirm"],
            "multiplier": 1.20,
            "original_score": 0.6,
            "calibrated_score": 0.72,
        }
        result = build(info)
        assert "POLYMARKET KALİBRASYON" in result
        assert "DOĞRULAMA (güçlü)" in result
        assert "DESTEKLEYİCİ" in result
        assert "1.20x" in result
        assert "0.600 → 0.720" in result
        assert "destekliyor" in result.lower()
        # Conflict rehberi YOK
        assert "polymarket_conflict" not in result

    def test_pm_confirm_weak(self):
        build = self._import()
        info = {
            "flags": ["pm_confirm_weak"],
            "multiplier": 1.10,
            "original_score": 0.5,
            "calibrated_score": 0.55,
        }
        result = build(info)
        assert "DOĞRULAMA (zayıf)" in result
        assert "1.10x" in result

    def test_pm_conflict_strong(self):
        build = self._import()
        info = {
            "flags": ["pm_conflict"],
            "multiplier": 0.75,
            "original_score": 0.8,
            "calibrated_score": 0.60,
        }
        result = build(info)
        assert "ÇELİŞKİ (güçlü)" in result
        assert "UYUŞMUYOR" in result
        assert "0.75x" in result
        # LLM'in cautions listesine eklemesini iste
        assert "polymarket_conflict" in result
        assert "şüpheci" in result

    def test_pm_conflict_weak(self):
        build = self._import()
        info = {
            "flags": ["pm_conflict_weak"],
            "multiplier": 0.90,
            "original_score": 0.7,
            "calibrated_score": 0.63,
        }
        result = build(info)
        assert "ÇELİŞKİ (zayıf)" in result
        # Hâlâ conflict rehberi var
        assert "tezde gözden kaçan" in result

    def test_mixed_flags_conflict_priority(self):
        """Karışık bayrak → çelişki yönü öncelikli rehber."""
        build = self._import()
        info = {
            "flags": ["pm_confirm_weak", "pm_conflict"],
            "multiplier": 0.75,
            "original_score": 0.7,
            "calibrated_score": 0.525,
        }
        result = build(info)
        # Hem confirm hem conflict labels görünür
        assert "DOĞRULAMA (zayıf)" in result
        assert "ÇELİŞKİ (güçlü)" in result
        # Karışık sinyal rehberi
        assert "Karışık sinyal" in result
        assert "çelişki" in result.lower()

    def test_empty_flags_returns_empty(self):
        build = self._import()
        result = build({"flags": []})
        assert result == ""

    def test_no_flags_key_returns_empty(self):
        build = self._import()
        result = build({"multiplier": 1.0})
        assert result == ""

    def test_unknown_flag_skipped(self):
        build = self._import()
        info = {
            "flags": ["pm_unknown_xyz"],
            "multiplier": 1.0,
        }
        # Bilinmeyen tek bayrak → bölüm üretilmez
        result = build(info)
        assert result == ""

    def test_unknown_flag_filtered_among_valid(self):
        build = self._import()
        info = {
            "flags": ["pm_confirm", "pm_unknown_xyz"],
            "multiplier": 1.20,
        }
        result = build(info)
        # pm_confirm geçer, unknown atlanır
        assert "DOĞRULAMA (güçlü)" in result
        assert "pm_unknown_xyz" not in result

    def test_non_list_flags_returns_empty(self):
        build = self._import()
        result = build({"flags": "not-a-list"})
        assert result == ""

    def test_missing_multiplier_no_error(self):
        """Multiplier alanı eksik olsa bile bölüm hâlâ render edilir."""
        build = self._import()
        info = {"flags": ["pm_confirm"]}
        result = build(info)
        assert "DOĞRULAMA (güçlü)" in result
        # Çarpan satırı YOK (eksik veri sessiz)
        assert "Çarpan:" not in result

    def test_missing_scores_no_score_line(self):
        build = self._import()
        info = {"flags": ["pm_confirm"], "multiplier": 1.20}
        result = build(info)
        assert "1.20x" in result
        # Skor satırı yok (calibrated_score yok)
        assert "→" not in result

    def test_non_dict_flag_element_skipped(self):
        """flags listesinde dict gibi yanlış eleman varsa skip edilir."""
        build = self._import()
        info = {
            "flags": [{"weird": "object"}, "pm_confirm"],
            "multiplier": 1.20,
        }
        result = build(info)
        assert "DOĞRULAMA (güçlü)" in result


# ── _build_prompt entegrasyonu ─────────────────────────────────────────────────


class TestBuildPromptCalibrationIntegration:
    def _build(self, **kwargs):
        from agent.ai_gate import _build_prompt
        defaults = {
            "symbol": "LMT",
            "signal_type": "tematik",
            "signal_data": {"momentum": "strong"},
            "context": {
                "watchlist_size": 50,
                "watchlist_max": 300,
                "portfolio_symbols": [],
                "active_themes": [],
                "dying_themes": [],
            },
        }
        defaults.update(kwargs)
        return _build_prompt(**defaults)

    def test_calibration_none_no_section(self):
        """Geriye uyumluluk: calibration_info=None → mevcut davranış."""
        prompt = self._build()
        assert "POLYMARKET KALİBRASYON" not in prompt

    def test_calibration_dict_adds_section(self):
        prompt = self._build(calibration_info={
            "flags": ["pm_confirm"],
            "multiplier": 1.20,
            "original_score": 0.6,
            "calibrated_score": 0.72,
        })
        assert "POLYMARKET KALİBRASYON" in prompt
        assert "DOĞRULAMA (güçlü)" in prompt

    def test_calibration_empty_flags_no_section(self):
        prompt = self._build(calibration_info={"flags": []})
        assert "POLYMARKET KALİBRASYON" not in prompt

    def test_calibration_non_dict_safe(self):
        """calibration_info bozuk tip → exception yok, bölüm de yok."""
        prompt = self._build(calibration_info="not-a-dict")  # type: ignore[arg-type]
        assert "POLYMARKET KALİBRASYON" not in prompt

    def test_calibration_section_after_signal_guidance(self):
        """Kalibrasyon bölümü 'BU SİNYAL TİPİ İÇİN REHBER' SONRA, 'GÖREV' ÖNCE."""
        prompt = self._build(calibration_info={
            "flags": ["pm_conflict"],
            "multiplier": 0.75,
        })
        # Sıralama kontrolü
        idx_guidance = prompt.find("BU SİNYAL TİPİ İÇİN REHBER")
        idx_calibration = prompt.find("POLYMARKET KALİBRASYON")
        idx_task = prompt.find("GÖREV:")
        assert idx_guidance < idx_calibration < idx_task


# ── evaluate_signal parametre kabul testi ──────────────────────────────────────


class TestEvaluateSignalParam:
    """evaluate_signal calibration_info parametresini kabul ediyor mu — imza testi.

    Gerçek LLM çağrısı yok; sadece parametrenin geçilebildiğinden emin oluyoruz.
    LLM çağrısı zaten _call_llm üzerinden mock'lanır.
    """

    def test_accepts_calibration_info_kwarg(self, monkeypatch):
        from agent import ai_gate

        # _call_llm'i mock'la — gerçek API çağırma
        captured_prompts = []

        def fake_call_llm(prompt):
            captured_prompts.append(prompt)
            return {
                "action": "EKLE",
                "score": 70,
                "reason": "test",
                "theme_match": None,
                "cautions": [],
            }

        monkeypatch.setattr(ai_gate, "_call_llm", fake_call_llm)

        # Watchlist/portfolio çakışma yok
        from agent import watchlist as wl_mod

        # is_in_portfolio mock'u
        try:
            monkeypatch.setattr(wl_mod, "is_in_portfolio", lambda s: False)
            monkeypatch.setattr(wl_mod, "is_excluded", lambda s: False)
        except AttributeError:
            pass  # zaten yoksa atla

        # Default context'i mock'la
        monkeypatch.setattr(ai_gate, "_build_default_context", lambda: {
            "watchlist_size": 0, "watchlist_max": 300,
            "portfolio_symbols": [], "active_themes": [], "dying_themes": [],
        })

        cal_info = {
            "flags": ["pm_conflict"],
            "multiplier": 0.75,
            "original_score": 0.8,
            "calibrated_score": 0.6,
        }
        result = ai_gate.evaluate_signal(
            "LMT", "tematik", {"momentum": "strong"},
            calibration_info=cal_info,
        )
        # Sonuç dict'i (gerçek LLM çağrısı mock)
        assert result["action"] == "EKLE"
        # Prompt içine kalibrasyon bölümü konuldu
        assert len(captured_prompts) == 1
        assert "POLYMARKET KALİBRASYON" in captured_prompts[0]
        assert "ÇELİŞKİ (güçlü)" in captured_prompts[0]

    def test_default_no_calibration_info(self, monkeypatch):
        """calibration_info verilmezse prompt'a kalibrasyon bölümü girmez."""
        from agent import ai_gate

        captured_prompts = []

        def fake_call_llm(prompt):
            captured_prompts.append(prompt)
            return {"action": "EKLE", "score": 70, "reason": "ok",
                    "theme_match": None, "cautions": []}

        monkeypatch.setattr(ai_gate, "_call_llm", fake_call_llm)
        monkeypatch.setattr(ai_gate, "_build_default_context", lambda: {
            "watchlist_size": 0, "watchlist_max": 300,
            "portfolio_symbols": [], "active_themes": [], "dying_themes": [],
        })

        from agent import watchlist as wl_mod
        try:
            monkeypatch.setattr(wl_mod, "is_in_portfolio", lambda s: False)
            monkeypatch.setattr(wl_mod, "is_excluded", lambda s: False)
        except AttributeError:
            pass

        ai_gate.evaluate_signal("LMT", "tematik", {"momentum": "strong"})

        assert len(captured_prompts) == 1
        assert "POLYMARKET KALİBRASYON" not in captured_prompts[0]
