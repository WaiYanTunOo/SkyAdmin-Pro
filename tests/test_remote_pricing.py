"""Remote pricing + signing alignment helpers."""

from skyadmin_pro.services.remote_pricing import fetch_pricing_tiers


def test_fetch_pricing_tiers_fallback_without_network(monkeypatch):
    monkeypatch.setattr(
        "skyadmin_pro.services.remote_pricing.API_BASE_URL",
        "",
    )
    tiers, over = fetch_pricing_tiers()
    assert len(tiers) >= 4
    assert "WhatsApp" in over
