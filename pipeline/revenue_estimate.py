"""Revenue estimation — predict AdSense earnings per video.

YouTube AdSense pays based on views × CPM, where CPM varies wildly by niche
and geography. We maintain a table of median CPM by category + audience
country, let the user pick, and estimate.

Not a replacement for real AdSense data — but useful for "is this worth
making?" decisions and for sales calls ("your 100K view video would earn
≈$180").

CPM reference data sourced from public industry reports (Tubefilter,
Mediakix, Influencer Marketing Hub 2024-2025 aggregates).
"""

from __future__ import annotations


# Rough median CPM (USD per 1000 monetized views) by niche.
# These are AFTER YouTube's 45% cut — what the creator actually earns.
CPM_BY_NICHE = {
    "technology":      4.50,
    "finance_crypto":  12.00,
    "business":        8.00,
    "education":       3.50,
    "gaming":          2.20,
    "music":           1.60,
    "comedy":          2.00,
    "news_politics":   3.20,
    "lifestyle":       2.80,
    "health_fitness":  3.00,
    "food_cooking":    2.50,
    "travel":          2.40,
    "autos":           3.80,
    "science_nature":  3.00,
    "beauty_fashion":  2.20,
    "kids_family":     1.80,
    "sports":          2.40,
    "general":         2.00,
}

# Country multiplier applied on top of niche baseline — e.g. US/UK audiences
# pay 1.3-1.8x vs. global average. Set on channel preset.
COUNTRY_MULTIPLIER = {
    "US":     1.50,  "GB":     1.30,  "AU":     1.25,
    "CA":     1.20,  "DE":     1.10,  "FR":     1.05,
    "TR":     0.45,  "IN":     0.30,  "BR":     0.45,
    "RU":     0.40,  "ES":     0.85,  "IT":     0.90,
    "default": 1.00,
}

# What % of views are actually monetized (rest are ad-blocked, under-age, etc)
MONETIZATION_RATE = 0.65


def estimate(
    *, views: int, niche: str = "general", country: str = "default",
    duration_sec: float = 60.0,
) -> dict:
    """Return {cpm_usd, earnings_usd, monetized_views, breakdown}.

    Shorts (<60s) currently earn via the Shorts Fund — much lower RPM than
    long-form. We apply a Shorts penalty: ~0.05-0.10 USD per 1000 views for
    pre-roll-ineligible videos.
    """
    niche_cpm = CPM_BY_NICHE.get(niche.lower(), CPM_BY_NICHE["general"])
    country_mult = COUNTRY_MULTIPLIER.get(country.upper(),
                                           COUNTRY_MULTIPLIER["default"])
    effective_cpm = niche_cpm * country_mult

    # Shorts penalty — pre-roll ads typically require >60s
    is_short = duration_sec < 60
    if is_short:
        # Shorts monetize via the YouTube Shorts Fund / Ad Rev-share → lower
        # Typical range $0.02 – $0.07 per 1000 views; we pick the middle
        effective_cpm = 0.05 * country_mult
        monetization = 1.0  # Shorts rev-share applies to all views
    else:
        monetization = MONETIZATION_RATE

    monetized = int(views * monetization)
    earnings = (monetized / 1000.0) * effective_cpm

    return {
        "views_input": views,
        "monetized_views": monetized,
        "cpm_usd": round(effective_cpm, 3),
        "earnings_usd": round(earnings, 2),
        "niche": niche,
        "country": country.upper(),
        "is_short": is_short,
        "breakdown": {
            "niche_cpm_base": niche_cpm,
            "country_multiplier": country_mult,
            "monetization_rate": monetization,
            "shorts_penalty_applied": is_short,
        },
    }


def forecast_monthly(
    *, videos_per_month: int, avg_views_per_video: int,
    niche: str = "general", country: str = "default",
    duration_sec: float = 60.0,
) -> dict:
    """Monthly earning forecast — for customer onboarding ROI sell."""
    per_video = estimate(views=avg_views_per_video, niche=niche,
                         country=country, duration_sec=duration_sec)
    monthly = per_video["earnings_usd"] * videos_per_month
    return {
        "videos_per_month": videos_per_month,
        "avg_views_per_video": avg_views_per_video,
        "earnings_per_video_usd": per_video["earnings_usd"],
        "monthly_earnings_usd": round(monthly, 2),
        "annual_earnings_usd": round(monthly * 12, 2),
        "detail": per_video,
    }
