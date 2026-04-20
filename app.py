# -*- coding: utf-8 -*-
"""RE-Tube -- YouTube Shorts Pipeline Dashboard"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

# --- Paths -------------------------------------------------------
SKILL_DIR = Path.home() / ".youtube-shorts-pipeline"
CONFIG_FILE = SKILL_DIR / "config.json"
DRAFTS_DIR = SKILL_DIR / "drafts"
MEDIA_DIR = SKILL_DIR / "media"
PROJECT_DIR = Path(__file__).resolve().parent

# --- i18n --------------------------------------------------------
TEXTS = {
    "tr": {
        "dashboard": "Kontrol Paneli",
        "pipeline": "Üretim Hattı",
        "trends": "Trendler",
        "videos": "Videolarım",
        "history": "Geçmiş",
        "settings": "Ayarlar",
        "system_status": "SİSTEM DURUMU",
        "welcome_title": "Tekrar hoş geldin",
        "welcome_sub": "Bugün üretimlerinde neler oluyor, bir bakalım.",
        "total_prod": "Toplam Üretim",
        "videos_label": "Videolar",
        "success_rate": "Başarı Oranı",
        "active_pipeline": "Aktif Pipeline",
        "all_time": "Toplam işlem sayısı",
        "videos_produced": "Üretilen videolar",
        "upload_success": "Yükleme başarı oranı",
        "in_progress": "Şu an devam eden",
        "recent_prod": "Son Üretimler",
        "recent_prod_sub": "Son video işlem aktivitesi",
        "production": "ÜRETİM",
        "status": "DURUM",
        "progress": "İLERLEME",
        "created": "OLUŞTURULMA",
        "no_prod": "Henüz üretim yok. İlk videonuzu oluşturmak için Üretim Hattı’na gidin.",
        "active_providers": "Aktif Sağlayıcılar",
        "last_video": "Son Üretilen Video",
        "new_production": "Yeni Üretim",
        "topic_label": "Konu / Haber Başlığı",
        "topic_placeholder": "örn. NASA yarım asırdan sonra ilk insanlı Ay görevini başlattı",
        "channel_ctx_label": "Kanal Bağlamı (opsiyonel)",
        "channel_ctx_placeholder": "örn. Yapay zekâ ve uzay odaklı teknoloji haber kanalı",
        "pipeline_mode": "Pipeline Modu",
        "mode_full": "Tam Pipeline (Taslak + Video + Yükleme)",
        "mode_video": "Taslak + Video (yüklemesiz)",
        "mode_draft": "Sadece Taslak",
        "language": "Dil",
        "force_redo": "Tüm aşamaları yeniden yap",
        "video_format": "Video Formatı",
        "format_shorts": "Shorts (9:16 Dikey)",
        "format_video": "Video (16:9 Yatay)",
        "video_duration": "Video Süresi",
        "dur_short": "Kısa (~70 sn)",
        "dur_3min": "3 Dakika",
        "dur_5min": "5 Dakika",
        "dur_10min": "10 Dakika",
        "manual_prod": "Manuel Üretim",
        "manual_desc": "Kendi script'inizi ve görsel prompt'larınızı girin, pipeline sadece üretim yapar.",
        "script_input": "Video Script'i",
        "script_placeholder": "Video script'inizi buraya yapıştırın...",
        "broll_prompts_label": "Görsel Prompt'ları",
        "broll_prompt_ph": "Görsel için İngilizce prompt girin",
        "add_prompt": "Prompt Ekle",
        "remove_prompt": "Kaldır",
        "num_visuals": "Görsel Sayısı",
        "manual_start": "Manuel Üretimi Başlat",
        "no_script": "Script girilmedi.",
        "manual_saving": "Taslak kaydediliyor...",
        "manual_producing": "Video üretiliyor...",
        "start_prod": "Üretimi Başlat",
        "selected_providers": "Seçili Sağlayıcılar",
        "pipeline_running": "Pipeline çalışıyor... Bu birkaç dakika sürebilir.",
        "prod_complete": "Üretim tamamlandı!",
        "pipeline_error": "Pipeline hatası",
        "claude_required": "Claude erişimi gerekli. Ayarlar’ı kontrol edin.",
        "trending_topics": "Trend Konular",
        "trends_desc_tr": "Türkiye Trendleri",
        "trends_desc_world": "Dünya Trendleri",
        "results_limit": "Sonuç Limiti",
        "discover": "Keşfet",
        "searching": "Aranıyor...",
        "produced_videos": "Üretilmiş Videolar",
        "no_videos": "Henüz video üretilmedi.",
        "size": "Boyut",
        "prod_history": "Üretim Geçmişi",
        "produce": "Üret",
        "upload": "Yükle",
        "force_redo_btn": "Yeniden Yap",
        "delete": "SİL",
        "delete_confirm": "Bu taslak kalıcı olarak silinecek. Emin misiniz?",
        "producing": "Üretiliyor...",
        "uploading": "Yükleniyor...",
        "redoing": "Yeniden yapılıyor...",
        "done": "Tamamlandı!",
        "settings_title": "Ayarlar",
        "provider_selection": "Sağlayıcı Seçimi",
        "script_ai": "Script AI Sağlayıcısı",
        "image_provider": "Görsel Sağlayıcısı",
        "tts_provider": "TTS Sağlayıcısı",
        "video_provider": "Video Sağlayıcısı",
        "cost_calculator": "Maliyet Hesaplayıcı",
        "cost_per_video": "Video Başına Tahmini Maliyet",
        "total_cost": "Toplam",
        "batch_cost": "Toplu Üretim Maliyeti",
        "batch_count": "Video Sayısı",
        "tier_free": "Ücretsiz",
        "tier_cheapest": "En Ucuz",
        "tier_budget": "Bütçe Dostu",
        "tier_mid": "Orta",
        "tier_premium": "Premium",
        "openai_key": "OpenAI API Key",
        "google_tts_key": "Google Cloud TTS Key",
        "api_keys": "API Anahtarları",
        "save_config": "Yapılandırmayı Kaydet",
        "config_saved": "Yapılandırma kaydedildi!",
        "yt_oauth": "YouTube OAuth",
        "yt_configured": "YouTube OAuth token’ı yapılandırıldı.",
        "yt_not_configured": "YouTube OAuth yapılandırılmamış. Terminalde `python scripts/setup_youtube_oauth.py` çalıştırın.",
        "system_info": "Sistem Bilgisi",
        "updates": "Güncellemeler",
        "check_updates": "Güncelleme Kontrol Et",
        "apply_update": "Güncelle",
        "up_to_date": "Program güncel.",
        "update_available": "Güncelleme mevcut!",
        "update_success": "Güncelleme başarılı! Sayfayı yenileyin.",
        "update_failed": "Güncelleme hatası.",
        "repo_url": "GitHub Repo URL",
        "no_repo": "Repo URL ayarlanmamış.",
        "version_label": "Sürüm",
        "channels": "YouTube Kanalları",
        "add_channel": "Kanal Ekle",
        "channel_name": "Kanal Adı",
        "channel_name_ph": "örn. Ana Kanal, İkinci Kanal",
        "setup_channel": "OAuth Bağla",
        "remove_channel": "Kaldır",
        "select_channel": "Yükleme Kanalı",
        "no_channels": "Henüz kanal eklenmemiş.",
        "channel_added": "Kanal eklendi!",
        "channel_removed": "Kanal kaldırıldı.",
        "channel_auth_info": "Terminalde çalıştırın:",
        "component": "Bileşen",
        "status_col": "Durum",
        "connected": "Bağlı",
        "not_connected": "Bağlı değil",
        "installed": "Yüklü",
        "not_found": "Bulunamadı",
        "configured": "Yapılandırıldı",
        "missing": "Eksik",
        "coming_soon": "Yakında",
        "free": "Ücretsiz",
        "needs_key": "API anahtarı gerekli",
        "needs_billing": "Faturalandırma gerekli",
        "premium": "Premium",
        "success_label": "Başarılı",
        "error_label": "Hata",
        "processing_label": "İşleniyor",
        "draft_label": "Taslak",
        "stages_label": "aşama",
        "ago_s": "sn önce",
        "ago_m": "dk önce",
        "ago_h": "sa önce",
        "ago_d": "g önce",
    },
    "en": {
        "dashboard": "Dashboard",
        "pipeline": "Pipeline",
        "trends": "Trends",
        "videos": "My Videos",
        "history": "History",
        "settings": "Settings",
        "system_status": "SYSTEM STATUS",
        "welcome_title": "Welcome back",
        "welcome_sub": "Here's what's happening with your productions today.",
        "total_prod": "Total Productions",
        "videos_label": "Videos",
        "success_rate": "Success Rate",
        "active_pipeline": "Active Pipeline",
        "all_time": "All time videos processed",
        "videos_produced": "Videos produced",
        "upload_success": "Upload success rate",
        "in_progress": "Currently in progress",
        "recent_prod": "Recent Productions",
        "recent_prod_sub": "Latest video processing activity",
        "production": "PRODUCTION",
        "status": "STATUS",
        "progress": "PROGRESS",
        "created": "CREATED",
        "no_prod": "No productions yet. Go to Pipeline to create your first video.",
        "active_providers": "Active Providers",
        "last_video": "Last Produced Video",
        "new_production": "New Production",
        "topic_label": "Topic / News Headline",
        "topic_placeholder": "e.g. NASA launches first crewed lunar mission in half a century",
        "channel_ctx_label": "Channel Context (optional)",
        "channel_ctx_placeholder": "e.g. Tech news channel focused on AI and space",
        "pipeline_mode": "Pipeline Mode",
        "mode_full": "Full Pipeline (Draft + Video + Upload)",
        "mode_video": "Draft + Video (no upload)",
        "mode_draft": "Draft Only",
        "language": "Language",
        "force_redo": "Force redo all stages",
        "video_format": "Video Format",
        "format_shorts": "Shorts (9:16 Portrait)",
        "format_video": "Video (16:9 Landscape)",
        "video_duration": "Video Duration",
        "dur_short": "Short (~70s)",
        "dur_3min": "3 Minutes",
        "dur_5min": "5 Minutes",
        "dur_10min": "10 Minutes",
        "manual_prod": "Manual Production",
        "manual_desc": "Enter your own script and visual prompts. Pipeline handles the rest.",
        "script_input": "Video Script",
        "script_placeholder": "Paste your video script here...",
        "broll_prompts_label": "Visual Prompts",
        "broll_prompt_ph": "Enter image/video prompt in English",
        "add_prompt": "Add Prompt",
        "remove_prompt": "Remove",
        "num_visuals": "Number of Visuals",
        "manual_start": "Start Manual Production",
        "no_script": "No script provided.",
        "manual_saving": "Saving draft...",
        "manual_producing": "Producing video...",
        "start_prod": "Start Production",
        "selected_providers": "Selected Providers",
        "pipeline_running": "Pipeline running... This may take a few minutes.",
        "prod_complete": "Production complete!",
        "pipeline_error": "Pipeline error",
        "claude_required": "Claude access required. Check Settings.",
        "trending_topics": "Trending Topics",
        "trends_desc_tr": "Turkey Trends",
        "trends_desc_world": "World Trends",
        "results_limit": "Results Limit",
        "discover": "Discover",
        "searching": "Searching...",
        "produced_videos": "Produced Videos",
        "no_videos": "No videos produced yet.",
        "size": "Size",
        "prod_history": "Production History",
        "produce": "Produce",
        "upload": "Upload",
        "force_redo_btn": "Force Redo",
        "delete": "DELETE",
        "delete_confirm": "This draft will be permanently deleted. Are you sure?",
        "producing": "Producing...",
        "uploading": "Uploading...",
        "redoing": "Redoing...",
        "done": "Done!",
        "settings_title": "Settings",
        "provider_selection": "Provider Selection",
        "script_ai": "Script AI Provider",
        "image_provider": "Image Provider",
        "tts_provider": "TTS Provider",
        "video_provider": "Video Provider",
        "cost_calculator": "Cost Calculator",
        "cost_per_video": "Estimated Cost Per Video",
        "total_cost": "Total",
        "batch_cost": "Batch Production Cost",
        "batch_count": "Number of Videos",
        "tier_free": "Free",
        "tier_cheapest": "Cheapest",
        "tier_budget": "Budget",
        "tier_mid": "Mid-Range",
        "tier_premium": "Premium",
        "openai_key": "OpenAI API Key",
        "google_tts_key": "Google Cloud TTS Key",
        "api_keys": "API Keys",
        "save_config": "Save Configuration",
        "config_saved": "Configuration saved!",
        "yt_oauth": "YouTube OAuth",
        "yt_configured": "YouTube OAuth token is configured.",
        "yt_not_configured": "YouTube OAuth not configured. Run `python scripts/setup_youtube_oauth.py` in terminal.",
        "system_info": "System Info",
        "updates": "Updates",
        "check_updates": "Check for Updates",
        "apply_update": "Update Now",
        "up_to_date": "Program is up to date.",
        "update_available": "Update available!",
        "update_success": "Update successful! Refresh the page.",
        "update_failed": "Update failed.",
        "repo_url": "GitHub Repo URL",
        "no_repo": "Repo URL not configured.",
        "version_label": "Version",
        "channels": "YouTube Channels",
        "add_channel": "Add Channel",
        "channel_name": "Channel Name",
        "channel_name_ph": "e.g. Main Channel, Second Channel",
        "setup_channel": "Connect OAuth",
        "remove_channel": "Remove",
        "select_channel": "Upload Channel",
        "no_channels": "No channels added yet.",
        "channel_added": "Channel added!",
        "channel_removed": "Channel removed.",
        "channel_auth_info": "Run in terminal:",
        "component": "Component",
        "status_col": "Status",
        "connected": "Connected",
        "not_connected": "Not connected",
        "installed": "Installed",
        "not_found": "Not found",
        "configured": "Configured",
        "missing": "Missing",
        "coming_soon": "Coming Soon",
        "free": "Free",
        "needs_key": "Needs API key",
        "needs_billing": "Needs billing",
        "premium": "Premium",
        "success_label": "Success",
        "error_label": "Error",
        "processing_label": "Processing",
        "draft_label": "Draft",
        "stages_label": "stages",
        "ago_s": "s ago",
        "ago_m": "min ago",
        "ago_h": "h ago",
        "ago_d": "d ago",
    },
}


def t(key):
    """Return translated text for current language."""
    lang = st.session_state.get("lang", "tr")
    return TEXTS.get(lang, TEXTS["tr"]).get(key, key)


# --- Branding (white-label) --------------------------------------
try:
    from pipeline import branding as _branding
    _brand = _branding.load()
except Exception:
    _brand = {
        "product_name": "RE-Tube", "short_name": "RT",
        "tagline": "YouTube Otomasyon",
        "accent": "#C9A96E",
        "accent_dim": "rgba(201, 169, 110, 0.10)",
        "bg_deep": "#0F0D0A",
        "logo_path": "", "favicon_path": "",
        "hide_retube_credit": False,
    }

# --- Page Config -------------------------------------------------
_page_title = f"{_brand.get('product_name', 'RE-Tube')} Dashboard"
_page_icon_default = "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>▶</text></svg>"
_favicon = _brand.get("favicon_path") or _page_icon_default
st.set_page_config(
    page_title=_page_title,
    page_icon=_favicon if _favicon.startswith(("http", "data:")) else _page_icon_default,
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Session State Defaults --------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "tr"

# White-label CSS override — applied BEFORE base theme so base wins unless
# branding specifies a value
try:
    _brand_override = _branding.css_override()
    st.markdown(f"<style>{_brand_override}\n.nav-brand-logo {{ width: 32px; height: 32px; object-fit: contain; border-radius: 6px; }}</style>", unsafe_allow_html=True)
except Exception:
    pass

# --- CSS: Obsidian & Champagne Theme -----------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

    :root {
        --bg-deep: #0c0b0e;
        --bg-surface: #141318;
        --bg-card: #1a191f;
        --bg-elevated: #201f26;
        --border-subtle: #2a2930;
        --border-medium: #3a3940;
        --text-bright: #f0ede6;
        --text-normal: #c8c4bb;
        --text-dim: #7d7a72;
        --text-ghost: #4a4843;
        --accent-primary: #c9a96e;
        --accent-primary-dim: rgba(201, 169, 110, 0.12);
        --accent-primary-glow: rgba(201, 169, 110, 0.06);
        --status-success: #6bbd7b;
        --status-warning: #d4a853;
        --status-error: #c45c5c;
        --status-info: #6b9fc4;
        --brand: #a83232;
        --brand-dim: rgba(168, 50, 50, 0.12);
    }

    html, body, [data-testid="stAppViewContainer"] {
        background-color: var(--bg-deep) !important;
        color: var(--text-normal) !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
    }

    .main .block-container {
        max-width: 1400px;
        padding: 1.5rem 2rem 2rem 2rem;
    }

    /* -- Hide Streamlit chrome (keep sidebar toggle visible) -- */
    #MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }
    .stDeployButton { display: none !important; }
    header[data-testid="stHeader"] {
        background: transparent !important;
        backdrop-filter: none !important;
    }
    /* Ensure ALL sidebar toggle variants are visible */
    button[data-testid="stSidebarCollapse"],
    button[data-testid="stSidebarExpand"],
    button[data-testid="stSidebarNavToggle"],
    [data-testid="collapsedControl"],
    [data-testid="collapsedControl"] * {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        z-index: 99999 !important;
    }
    button[data-testid="stSidebarCollapse"],
    button[data-testid="stSidebarNavToggle"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 8px !important;
        color: var(--text-dim) !important;
        transition: all 0.25s ease !important;
    }
    button[data-testid="stSidebarCollapse"]:hover,
    button[data-testid="stSidebarNavToggle"]:hover {
        border-color: var(--accent-primary) !important;
        color: var(--accent-primary) !important;
    }
    /* Custom fixed expand button when sidebar is collapsed */
    .sidebar-expand-btn {
        position: fixed;
        top: 14px;
        left: 14px;
        z-index: 999999;
        width: 38px;
        height: 38px;
        background: var(--bg-elevated);
        border: 1px solid var(--border-medium);
        border-radius: 10px;
        color: var(--accent-primary);
        font-size: 1.1rem;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        backdrop-filter: blur(10px);
    }
    .sidebar-expand-btn:hover {
        transform: scale(1.12);
        border-color: var(--accent-primary);
        box-shadow: 0 6px 25px rgba(201, 169, 110, 0.2);
        background: var(--bg-card);
    }
    /* Hide custom button when sidebar is open */
    section[data-testid="stSidebar"][aria-expanded="true"] ~ .main .sidebar-expand-btn {
        display: none;
    }

    /* -- Sidebar -- */
    section[data-testid="stSidebar"] {
        background: var(--bg-deep) !important;
        border-right: 1px solid var(--border-subtle);
    }
    section[data-testid="stSidebar"] > div {
        padding-top: 0 !important;
    }
    /* Sidebar slide-in on load */
    section[data-testid="stSidebar"] > div > div {
        animation: sidebarSlideIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
    }
    @keyframes sidebarSlideIn {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }

    /* -- Top bar -- */
    .topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem 0 1.5rem 0;
        border-bottom: 1px solid var(--border-subtle);
        margin-bottom: 1.5rem;
        animation: fadeIn 0.4s ease both;
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    .topbar-title {
        font-size: 1.2rem;
        font-weight: 500;
        color: var(--text-bright);
        letter-spacing: 0.3px;
    }
    .topbar-right {
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .user-avatar {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: var(--accent-primary-dim);
        border: 1px solid var(--accent-primary);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 500;
        font-size: 0.7rem;
        color: var(--accent-primary);
        letter-spacing: 1px;
    }

    /* -- Welcome section -- */
    .welcome {
        margin-bottom: 1.8rem;
        animation: welcomeIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.1s both;
    }
    @keyframes welcomeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .welcome h2 {
        font-size: 1.5rem;
        font-weight: 500;
        color: var(--text-bright);
        margin: 0 0 0.4rem 0;
    }
    .welcome p {
        color: var(--text-dim);
        font-size: 0.88rem;
        margin: 0;
    }

    /* -- Stat cards -- */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-bottom: 2.5rem;
    }
    .stat-card {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 14px;
        padding: 1.5rem;
        position: relative;
        transition: border-color 0.3s ease, transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease;
        animation: cardReveal 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
    }
    .stats-grid .stat-card:nth-child(1) { animation-delay: 0.05s; }
    .stats-grid .stat-card:nth-child(2) { animation-delay: 0.12s; }
    .stats-grid .stat-card:nth-child(3) { animation-delay: 0.19s; }
    .stats-grid .stat-card:nth-child(4) { animation-delay: 0.26s; }
    @keyframes cardReveal {
        from { opacity: 0; transform: translateY(15px) scale(0.97); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }
    .stat-card:hover {
        border-color: var(--accent-primary);
        transform: translateY(-3px);
        box-shadow: 0 10px 30px rgba(201, 169, 110, 0.06);
    }
    .stat-label {
        font-size: 0.65rem;
        color: var(--text-ghost);
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 0.6rem;
    }
    .stat-value {
        font-size: 2.4rem;
        font-weight: 300;
        color: var(--text-bright);
        margin: 0;
        line-height: 1;
    }
    .stat-change {
        font-size: 0.72rem;
        font-weight: 500;
        margin-top: 0.5rem;
    }
    .stat-change.positive { color: var(--status-success); }
    .stat-change.negative { color: var(--status-error); }
    .stat-change.neutral { color: var(--text-ghost); }
    .stat-icon {
        position: absolute;
        top: 1.5rem;
        right: 1.5rem;
        width: 36px;
        height: 36px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
    }
    .stat-icon.gold { background: var(--accent-primary-dim); color: var(--accent-primary); }
    .stat-icon.info { background: rgba(107, 159, 196, 0.10); color: var(--status-info); }
    .stat-icon.success { background: rgba(107, 189, 123, 0.10); color: var(--status-success); }
    .stat-icon.warn { background: rgba(212, 168, 83, 0.10); color: var(--status-warning); }

    /* -- Table -- */
    .table-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    .table-header h3 {
        font-size: 1rem;
        font-weight: 500;
        margin: 0;
        color: var(--text-bright);
    }
    .table-header p {
        color: var(--text-dim);
        font-size: 0.78rem;
        margin: 0.2rem 0 0 0;
    }

    .prod-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
    }
    .prod-table thead th {
        padding: 0.8rem 1rem;
        font-size: 0.65rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: var(--text-ghost);
        border-bottom: 1px solid var(--border-subtle);
        text-align: left;
        background: transparent;
    }
    .prod-table tbody tr {
        transition: background 0.2s ease, transform 0.2s ease;
        animation: rowSlideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
    }
    .prod-table tbody tr:nth-child(1) { animation-delay: 0.1s; }
    .prod-table tbody tr:nth-child(2) { animation-delay: 0.15s; }
    .prod-table tbody tr:nth-child(3) { animation-delay: 0.2s; }
    .prod-table tbody tr:nth-child(4) { animation-delay: 0.25s; }
    .prod-table tbody tr:nth-child(5) { animation-delay: 0.3s; }
    .prod-table tbody tr:nth-child(6) { animation-delay: 0.35s; }
    .prod-table tbody tr:nth-child(7) { animation-delay: 0.4s; }
    .prod-table tbody tr:nth-child(8) { animation-delay: 0.45s; }
    @keyframes rowSlideIn {
        from { opacity: 0; transform: translateX(-8px); }
        to { opacity: 1; transform: translateX(0); }
    }
    .prod-table tbody tr:hover {
        background: rgba(201, 169, 110, 0.04);
    }
    .prod-table tbody td {
        padding: 1rem;
        font-size: 0.88rem;
        color: var(--text-normal);
        border-bottom: 1px solid var(--border-subtle);
        vertical-align: middle;
    }
    .prod-title {
        font-weight: 500;
        color: var(--text-bright);
        font-size: 0.88rem;
    }
    .prod-id {
        color: var(--text-ghost);
        font-size: 0.72rem;
        margin-top: 3px;
        letter-spacing: 0.5px;
    }

    /* -- Status badges -- */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.3rem 0.8rem;
        border-radius: 100px;
        font-size: 0.72rem;
        font-weight: 500;
    }
    .status-success {
        background: rgba(107, 189, 123, 0.10);
        color: var(--status-success);
    }
    .status-processing {
        background: rgba(107, 159, 196, 0.10);
        color: var(--status-info);
    }
    .status-error {
        background: rgba(196, 92, 92, 0.10);
        color: var(--status-error);
    }
    .status-pending {
        background: rgba(125, 122, 114, 0.08);
        color: var(--text-dim);
    }
    .status-dot {
        width: 5px;
        height: 5px;
        border-radius: 50%;
        display: inline-block;
    }
    .status-dot.green { background: var(--status-success); }
    .status-dot.blue { background: var(--status-info); animation: breathe 2s ease infinite; }
    .status-dot.red { background: var(--status-error); animation: pulseRed 3s ease infinite; }

    @keyframes breathe {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.3; transform: scale(0.8); }
    }
    @keyframes pulseRed {
        0%, 100% { opacity: 0.7; }
        50% { opacity: 1; }
    }

    /* ── Premium Production Cards ────────────────────────────── */
    .prod-cards {
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin-top: 0.5rem;
    }
    .prod-card {
        position: relative;
        display: grid;
        grid-template-columns: 4px 1fr auto;
        gap: 1rem;
        padding: 14px 18px 14px 14px;
        background: linear-gradient(135deg, rgba(30,28,24,0.60) 0%, rgba(24,22,18,0.85) 100%);
        border: 1px solid rgba(201, 169, 110, 0.08);
        border-radius: 14px;
        transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
        overflow: hidden;
    }
    .prod-card:hover {
        transform: translateY(-1px);
        border-color: rgba(201, 169, 110, 0.22);
        box-shadow: 0 8px 28px -10px rgba(0,0,0,0.5), 0 0 0 1px rgba(201,169,110,0.05) inset;
    }
    .prod-card-accent {
        border-radius: 4px;
        align-self: stretch;
        opacity: 0.85;
    }
    .prod-card-main {
        display: flex;
        flex-direction: column;
        gap: 8px;
        min-width: 0;
    }
    .prod-card-head {
        display: flex;
        align-items: baseline;
        gap: 12px;
        flex-wrap: wrap;
    }
    .prod-card-title {
        font-size: 0.98rem;
        font-weight: 600;
        color: var(--text-bright);
        letter-spacing: -0.01em;
        line-height: 1.3;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 520px;
    }
    .prod-card-id {
        font-size: 0.68rem;
        font-family: 'JetBrains Mono', 'Menlo', monospace;
        color: var(--text-ghost);
        letter-spacing: 0.08em;
        padding: 2px 7px;
        background: rgba(201, 169, 110, 0.06);
        border: 1px solid rgba(201, 169, 110, 0.10);
        border-radius: 4px;
        white-space: nowrap;
    }
    .prod-card-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }
    .meta-chip {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 0.72rem;
        color: var(--text-dim);
        padding: 3px 8px;
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.04);
        border-radius: 6px;
    }
    .meta-chip.meta-ago { color: var(--text-ghost); }
    .prod-card-progress {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .prod-progress-track {
        flex: 1;
        height: 4px;
        background: rgba(255,255,255,0.04);
        border-radius: 99px;
        overflow: hidden;
    }
    .prod-progress-fill {
        height: 100%;
        border-radius: 99px;
        transition: width 0.4s ease;
        box-shadow: 0 0 8px currentColor;
    }
    .prod-progress-text {
        font-size: 0.7rem;
        color: var(--text-ghost);
        font-family: 'JetBrains Mono', 'Menlo', monospace;
        white-space: nowrap;
    }
    .prod-card-side {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .prod-status-chip {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        padding: 6px 12px;
        border-radius: 99px;
        font-size: 0.74rem;
        font-weight: 500;
        letter-spacing: 0.01em;
    }
    .prod-status-dot {
        width: 6px; height: 6px; border-radius: 50%;
    }
    .prod-status-done {
        background: rgba(107, 189, 123, 0.10);
        color: #8FD69F;
        border: 1px solid rgba(107, 189, 123, 0.18);
    }
    .prod-status-done .prod-status-dot { background: #8FD69F; box-shadow: 0 0 8px #8FD69F; }
    .prod-status-progress {
        background: rgba(107, 159, 196, 0.10);
        color: #8FB7D6;
        border: 1px solid rgba(107, 159, 196, 0.18);
    }
    .prod-status-progress .prod-status-dot {
        background: #8FB7D6;
        box-shadow: 0 0 8px #8FB7D6;
        animation: breathe 2s ease infinite;
    }
    .prod-status-failed {
        background: rgba(224, 107, 107, 0.10);
        color: #E99393;
        border: 1px solid rgba(224, 107, 107, 0.18);
    }
    .prod-status-failed .prod-status-dot {
        background: #E99393;
        box-shadow: 0 0 8px #E99393;
        animation: pulseRed 2s ease infinite;
    }
    .prod-status-pending {
        background: rgba(201, 169, 110, 0.08);
        color: #D9BB82;
        border: 1px solid rgba(201, 169, 110, 0.15);
    }
    .prod-status-pending .prod-status-dot { background: #D9BB82; }

    .prod-empty {
        text-align: center;
        padding: 3rem 1rem;
        color: var(--text-ghost);
        background: rgba(255,255,255,0.015);
        border: 1px dashed rgba(255,255,255,0.06);
        border-radius: 14px;
        font-size: 0.88rem;
    }

    /* ── YouTube recent video cards ─────────────────── */
    .yt-cards {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
        gap: 12px;
        margin-top: 0.5rem;
    }
    .yt-card {
        display: flex;
        flex-direction: column;
        background: rgba(30,28,24,0.6);
        border: 1px solid rgba(201,169,110,0.08);
        border-radius: 10px;
        overflow: hidden;
        text-decoration: none;
        color: inherit;
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    .yt-card:hover {
        transform: translateY(-2px);
        border-color: rgba(201,169,110,0.25);
    }
    .yt-thumb {
        width: 100%;
        aspect-ratio: 16/9;
        background-size: cover;
        background-position: center;
        background-color: rgba(255,255,255,0.04);
    }
    .yt-meta {
        padding: 10px 12px;
    }
    .yt-title {
        font-size: 0.85rem;
        font-weight: 500;
        color: var(--text-bright);
        line-height: 1.3;
        margin-bottom: 6px;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }
    .yt-stats {
        display: flex;
        gap: 10px;
        font-size: 0.72rem;
        color: var(--text-dim);
        flex-wrap: wrap;
    }
    .yt-stats .yt-date {
        margin-left: auto;
        color: var(--text-ghost);
    }

    /* ── Cost breakdown bars ─────────────────────────── */
    .cost-breakdown {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-top: 0.5rem;
    }
    .cost-row {
        display: grid;
        grid-template-columns: 180px 1fr 80px;
        align-items: center;
        gap: 12px;
        padding: 6px 0;
    }
    .cost-name {
        font-size: 0.84rem;
        color: var(--text-dim);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .cost-bar-wrap {
        background: rgba(255,255,255,0.04);
        border-radius: 99px;
        height: 8px;
        overflow: hidden;
    }
    .cost-bar {
        height: 100%;
        background: linear-gradient(90deg, #C9A96E 0%, #D9BB82 100%);
        border-radius: 99px;
        transition: width 0.4s ease;
        box-shadow: 0 0 10px rgba(201, 169, 110, 0.3);
    }
    .cost-amount {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        color: var(--text-bright);
        text-align: right;
    }

    @media (max-width: 900px) {
        .prod-card { grid-template-columns: 4px 1fr; }
        .prod-card-side { grid-column: 1 / -1; padding-left: 14px; }
        .prod-card-title { max-width: 100%; white-space: normal; }
    }

    /* -- Reduced motion -- */
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }

    /* -- Sidebar nav -- */
    .nav-brand {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1.3rem 1rem 1.5rem 1rem;
        border-bottom: 1px solid var(--border-subtle);
        margin-bottom: 0.8rem;
        animation: brandFadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.1s both;
    }
    @keyframes brandFadeIn {
        from { opacity: 0; transform: translateY(-8px) scale(0.96); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }
    .nav-brand-icon {
        width: 32px;
        height: 32px;
        background: var(--brand);
        border-radius: 9px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #f0ede6;
        font-size: 0.9rem;
        transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease;
        cursor: pointer;
    }
    .nav-brand:hover .nav-brand-icon {
        transform: scale(1.1) rotate(-4deg);
        box-shadow: 0 0 20px rgba(168, 50, 50, 0.25);
    }
    .nav-brand-text {
        font-size: 1.08rem;
        font-weight: 500;
        color: var(--text-bright);
        letter-spacing: 0.5px;
    }

    .settings-section {
        margin-top: 1.5rem;
        padding: 0 0.5rem;
    }
    .settings-title {
        font-size: 0.65rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: var(--text-ghost);
        padding: 0.5rem 1rem;
    }
    .key-status {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem 1rem;
        margin: 0.15rem 0.5rem;
        border-radius: 8px;
        font-size: 0.8rem;
        transition: background 0.2s ease, transform 0.2s ease;
        animation: statusFadeIn 0.4s ease both;
    }
    .key-status:nth-child(1) { animation-delay: 0.3s; }
    .key-status:nth-child(2) { animation-delay: 0.38s; }
    .key-status:nth-child(3) { animation-delay: 0.46s; }
    .key-status:nth-child(4) { animation-delay: 0.54s; }
    .key-status:nth-child(5) { animation-delay: 0.62s; }
    .key-status:nth-child(6) { animation-delay: 0.70s; }
    @keyframes statusFadeIn {
        from { opacity: 0; transform: translateX(-10px); }
        to { opacity: 1; transform: translateX(0); }
    }
    .key-status:hover {
        background: rgba(201, 169, 110, 0.04);
        transform: translateX(3px);
    }
    .key-status .label { color: var(--text-dim); transition: color 0.2s ease; }
    .key-status:hover .label { color: var(--text-normal); }
    .key-status .dot-ok { color: var(--status-success); font-size: 0.65rem; }
    .key-status .dot-err { color: var(--status-error); font-size: 0.65rem; }
    .key-status .dot-ok, .key-status .dot-err {
        transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    }
    .key-status:hover .dot-ok, .key-status:hover .dot-err {
        transform: scale(1.4);
    }

    /* -- Pipeline stage pills -- */
    .pipeline-stages {
        display: flex;
        gap: 0.4rem;
        flex-wrap: wrap;
        margin: 0.8rem 0;
    }
    .stage-pill {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 100px;
        padding: 0.3rem 0.7rem;
        font-size: 0.68rem;
        color: var(--text-ghost);
        display: flex;
        align-items: center;
        gap: 0.3rem;
        letter-spacing: 0.3px;
        transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        animation: pillPop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both;
    }
    .pipeline-stages .stage-pill:nth-child(1) { animation-delay: 0.05s; }
    .pipeline-stages .stage-pill:nth-child(2) { animation-delay: 0.09s; }
    .pipeline-stages .stage-pill:nth-child(3) { animation-delay: 0.13s; }
    .pipeline-stages .stage-pill:nth-child(4) { animation-delay: 0.17s; }
    .pipeline-stages .stage-pill:nth-child(5) { animation-delay: 0.21s; }
    .pipeline-stages .stage-pill:nth-child(6) { animation-delay: 0.25s; }
    .pipeline-stages .stage-pill:nth-child(7) { animation-delay: 0.29s; }
    .pipeline-stages .stage-pill:nth-child(8) { animation-delay: 0.33s; }
    .pipeline-stages .stage-pill:nth-child(9) { animation-delay: 0.37s; }
    @keyframes pillPop {
        from { opacity: 0; transform: scale(0.8); }
        to { opacity: 1; transform: scale(1); }
    }
    .stage-pill:hover {
        border-color: var(--accent-primary);
        color: var(--accent-primary);
        transform: translateY(-2px) scale(1.05);
    }
    .stage-pill.done {
        border-color: rgba(107, 189, 123, 0.3);
        color: var(--status-success);
    }
    .stage-pill.failed {
        border-color: rgba(196, 92, 92, 0.3);
        color: var(--status-error);
    }

    /* -- Detail panel -- */
    .detail-panel {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 14px;
        padding: 1.5rem;
        margin-top: 1rem;
    }
    .detail-panel h4 {
        font-size: 0.95rem;
        font-weight: 500;
        margin: 0 0 1rem 0;
        color: var(--text-bright);
    }

    /* -- Charts & Uptime -- */
    .charts-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
        margin-bottom: 2rem;
        animation: cardReveal 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.3s both;
    }
    .chart-card {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 14px;
        padding: 1.5rem;
        transition: border-color 0.3s ease;
    }
    .chart-card:hover {
        border-color: var(--border-medium);
    }
    .chart-title {
        font-size: 0.65rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: var(--text-ghost);
        margin-bottom: 1rem;
    }
    /* Mini bar chart */
    .mini-bars {
        display: flex;
        align-items: flex-end;
        gap: 4px;
        height: 80px;
        padding-top: 8px;
    }
    .mini-bar {
        flex: 1;
        border-radius: 4px 4px 0 0;
        transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
        position: relative;
        min-width: 0;
    }
    .mini-bar:hover {
        filter: brightness(1.3);
        transform: scaleY(1.05);
        transform-origin: bottom;
    }
    .bar-labels {
        display: flex;
        gap: 4px;
        margin-top: 6px;
    }
    .bar-label {
        flex: 1;
        text-align: center;
        font-size: 0.55rem;
        color: var(--text-ghost);
        letter-spacing: 0.5px;
    }
    /* Uptime dots */
    .uptime-grid {
        display: flex;
        gap: 3px;
        flex-wrap: wrap;
        margin-bottom: 0.8rem;
    }
    .uptime-dot {
        width: 10px;
        height: 28px;
        border-radius: 3px;
        transition: all 0.2s ease;
    }
    .uptime-dot:hover {
        transform: scaleY(1.2);
        filter: brightness(1.3);
    }
    .uptime-dot.up { background: var(--status-success); opacity: 0.7; }
    .uptime-dot.up:hover { opacity: 1; }
    .uptime-dot.partial { background: var(--status-warning); opacity: 0.7; }
    .uptime-dot.down { background: var(--status-error); opacity: 0.7; }
    .uptime-legend {
        display: flex;
        justify-content: space-between;
        font-size: 0.6rem;
        color: var(--text-ghost);
        letter-spacing: 0.3px;
    }
    .uptime-stat {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-top: 0.8rem;
    }
    .uptime-pct {
        font-size: 1.8rem;
        font-weight: 300;
        color: var(--status-success);
    }
    .uptime-label {
        font-size: 0.72rem;
        color: var(--text-dim);
    }

    /* -- Provider badges -- */
    .provider-badges {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin: 0.8rem 0;
    }
    .provider-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.3rem 0.8rem;
        border-radius: 100px;
        font-size: 0.72rem;
        font-weight: 500;
        background: var(--accent-primary-dim);
        color: var(--accent-primary);
        border: 1px solid rgba(201, 169, 110, 0.15);
        transition: all 0.25s ease;
    }
    .provider-badge:hover {
        transform: translateY(-1px);
        box-shadow: 0 3px 10px rgba(201, 169, 110, 0.12);
    }
    .provider-badge.green {
        background: rgba(107, 189, 123, 0.08);
        color: var(--status-success);
        border-color: rgba(107, 189, 123, 0.15);
    }
    .provider-badge.muted {
        background: rgba(107, 159, 196, 0.08);
        color: var(--status-info);
        border-color: rgba(107, 159, 196, 0.15);
    }

    /* -- Contact footer -- */
    .sidebar-footer {
        position: fixed;
        bottom: 0;
        padding: 0.8rem 1rem;
        font-size: 0.68rem;
        color: var(--text-ghost);
        letter-spacing: 0.3px;
        animation: fadeUp 0.6s ease 0.8s both;
    }
    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .sidebar-footer a {
        color: var(--accent-primary);
        text-decoration: none;
        transition: color 0.2s ease, letter-spacing 0.3s ease;
    }
    .sidebar-footer a:hover {
        color: var(--text-bright);
        letter-spacing: 0.8px;
    }

    /* -- Streamlit overrides -- */
    .stButton > button {
        background: var(--accent-primary) !important;
        color: var(--bg-deep) !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 0.55rem 1.5rem !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.5px !important;
        transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
        position: relative !important;
        overflow: hidden !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) scale(1.02) !important;
        box-shadow: 0 8px 25px rgba(201, 169, 110, 0.2) !important;
        filter: brightness(1.08) !important;
    }
    .stButton > button:active {
        transform: translateY(0) scale(0.98) !important;
        box-shadow: none !important;
        transition-duration: 0.1s !important;
    }
    /* Shimmer sweep on hover */
    .stButton > button::after {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 60%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
        transition: left 0.5s ease;
    }
    .stButton > button:hover::after {
        left: 120%;
    }
    .stButton > button[kind="secondary"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        color: var(--text-normal) !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: var(--accent-primary) !important;
        color: var(--accent-primary) !important;
        box-shadow: 0 4px 15px rgba(201, 169, 110, 0.08) !important;
    }
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 10px !important;
        color: var(--text-bright) !important;
        font-size: 0.88rem !important;
        transition: border-color 0.3s ease, box-shadow 0.3s ease !important;
    }
    [data-testid="stTextInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus {
        border-color: var(--accent-primary) !important;
        box-shadow: 0 0 0 3px rgba(201, 169, 110, 0.08) !important;
    }
    [data-testid="stSelectbox"] > div > div {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 10px !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: var(--bg-surface);
        border-radius: 12px;
        padding: 4px;
        border: 1px solid var(--border-subtle);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        color: var(--text-dim);
        font-weight: 500;
        font-size: 0.85rem;
        padding: 0.5rem 1.2rem;
    }
    .stTabs [aria-selected="true"] {
        background: var(--bg-card) !important;
        color: var(--accent-primary) !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        display: none;
    }
    .stTabs [data-baseweb="tab-border"] {
        display: none;
    }
    .stExpander {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 14px !important;
    }
    .stExpander:hover {
        border-color: var(--border-medium) !important;
    }
    .stSpinner > div {
        border-top-color: var(--accent-primary) !important;
    }
    div[data-testid="stMetric"] {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 14px;
        padding: 1rem;
    }
    div[data-testid="stMetric"] label {
        color: var(--text-ghost) !important;
        font-size: 0.65rem !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: var(--text-bright) !important;
        font-weight: 300 !important;
    }
    /* -- Pipeline progress bar -- */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, var(--accent-primary), #dfc38a) !important;
        border-radius: 100px !important;
        transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1) !important;
        box-shadow: 0 0 15px rgba(201, 169, 110, 0.3) !important;
        position: relative !important;
    }
    .stProgress > div > div > div {
        background: var(--bg-card) !important;
        border-radius: 100px !important;
        border: 1px solid var(--border-subtle) !important;
        height: 10px !important;
    }
    .stProgress > div > div {
        padding: 0 !important;
    }
    /* Progress text */
    .stProgress > div > div + div {
        color: var(--text-normal) !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.3px !important;
        margin-top: 0.5rem !important;
    }
    [data-testid="stRadio"] label {
        color: var(--text-dim) !important;
    }
    [data-testid="stRadio"] label[data-checked="true"] {
        color: var(--accent-primary) !important;
    }

    /* -- Section headers -- */
    .section-label {
        font-size: 0.65rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: var(--text-ghost);
        margin-bottom: 0.8rem;
    }
    .section-title {
        font-size: 1rem;
        font-weight: 500;
        color: var(--text-bright);
        margin: 0;
    }

    /* -- Delete button override -- */
    .stButton > button[data-testid*="delete"],
    .delete-btn > button {
        background: transparent !important;
        border: 1px solid var(--status-error) !important;
        color: var(--status-error) !important;
    }
    .delete-btn > button:hover {
        background: rgba(196, 92, 92, 0.10) !important;
    }

    /* -- Markdown overrides -- */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-bright) !important;
        font-weight: 500 !important;
    }
    p, li, span {
        color: var(--text-normal);
    }
    a {
        color: var(--accent-primary);
    }
    hr {
        border-color: var(--border-subtle) !important;
    }

    /* -- Scrollbar -- */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg-deep); }
    ::-webkit-scrollbar-thumb { background: var(--border-subtle); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--border-medium); }
</style>
""", unsafe_allow_html=True)


# --- Helpers -----------------------------------------------------
def load_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    return {}


def save_config(config):
    SKILL_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_drafts():
    drafts = []
    if DRAFTS_DIR.exists():
        for f in sorted(DRAFTS_DIR.glob("*.json"), reverse=True):
            try:
                data = json.loads(f.read_text())
                data["_file"] = str(f)
                drafts.append(data)
            except Exception:
                pass
    return drafts


def get_media_files():
    if MEDIA_DIR.exists():
        return sorted(MEDIA_DIR.glob("*.mp4"), reverse=True)
    return []


def ensure_worker_running():
    """Start the background queue worker in a detached process if not already running."""
    try:
        from pipeline import queue as _q
    except Exception:
        return False
    if _q.worker_running():
        return True

    kwargs = {"cwd": str(PROJECT_DIR)}
    creationflags = 0
    if sys.platform == "win32":
        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
        creationflags = 0x00000008 | 0x00000200 | 0x08000000
        kwargs["creationflags"] = creationflags
    else:
        kwargs["start_new_session"] = True

    try:
        subprocess.Popen(
            [sys.executable, "-u", "-m", "pipeline", "worker"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
            **kwargs,
        )
        # Short grace period for lock creation
        for _ in range(6):
            time.sleep(0.25)
            if _q.worker_running():
                return True
        return True  # assume it will appear soon
    except Exception:
        return False


def enqueue_job(**kwargs):
    """Thin wrapper around pipeline.queue.enqueue + auto-start worker.

    If `channel` is set, missing kwargs fall back to the channel preset:
    lang, format, duration, context, playlist_id, script_ai/image/tts/music
    providers. User-supplied non-empty kwargs always win.
    """
    from pipeline import queue as _q
    from pipeline import channel_preset as _cp

    channel_id = kwargs.get("channel")
    if channel_id:
        preset = _cp.load_preset(channel_id)
        # Only fill fields the caller didn't set (or set to empty)
        if preset:
            # Simple scalar fallbacks
            for k in ("lang", "context"):
                if not kwargs.get(k) and preset.get(k):
                    kwargs[k] = preset[k]
            # video_format has different key in preset vs kwargs
            if kwargs.get("video_format") in (None, "") and preset.get("format"):
                kwargs["video_format"] = preset["format"]
            if kwargs.get("duration") in (None, "") and preset.get("duration"):
                kwargs["duration"] = preset["duration"]
            # Playlist / tone for downstream use — stored in `extra`
            extra = kwargs.get("extra") or {}
            for k in ("playlist_id", "tone", "voice_id_en", "voice_id_tr",
                      "script_ai", "image", "video_prov", "tts", "music"):
                if preset.get(k) and k not in extra:
                    extra[k] = preset[k]
            if extra:
                kwargs["extra"] = extra

    job = _q.enqueue(**kwargs)
    ensure_worker_running()
    return job


def run_pipeline_command(cmd):
    """Run pipeline without progress tracking (simple mode)."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pipeline"] + cmd,
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(PROJECT_DIR), timeout=1800,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout: işlem 10 dakikadan uzun sürdü", 1
    except Exception as e:
        return "", str(e), 1


# Pipeline stage detection from output lines
PIPELINE_STAGES = [
    {"key": "research",  "pct": 5,   "triggers": ["Researching topic", "DuckDuckGo"],
     "tr": "Konu araştırılıyor...", "en": "Researching topic..."},
    {"key": "draft",     "pct": 15,  "triggers": ["Claude", "script generation", "Claude raw output"],
     "tr": "Script üretiliyor...", "en": "Generating script..."},
    {"key": "draft_save","pct": 20,  "triggers": ["Draft saved"],
     "tr": "Taslak kaydedildi", "en": "Draft saved"},
    {"key": "broll1",    "pct": 25,  "triggers": ["b-roll frame 1", "b-roll video 1", "Generating b-roll", "Fetching b-roll frame 1", "Veo operation started"],
     "tr": "Görseller üretiliyor (1/6)...", "en": "Generating visuals (1/6)..."},
    {"key": "broll2",    "pct": 29,  "triggers": ["b-roll frame 2", "b-roll video 2", "Fetching b-roll frame 2"],
     "tr": "Görseller üretiliyor (2/6)...", "en": "Generating visuals (2/6)..."},
    {"key": "broll3",    "pct": 33,  "triggers": ["b-roll frame 3", "b-roll video 3", "Fetching b-roll frame 3"],
     "tr": "Görseller üretiliyor (3/6)...", "en": "Generating visuals (3/6)..."},
    {"key": "broll4",    "pct": 37,  "triggers": ["b-roll frame 4", "b-roll video 4", "Fetching b-roll frame 4"],
     "tr": "Görseller üretiliyor (4/6)...", "en": "Generating visuals (4/6)..."},
    {"key": "broll5",    "pct": 41,  "triggers": ["b-roll frame 5", "b-roll video 5", "Fetching b-roll frame 5"],
     "tr": "Görseller üretiliyor (5/6)...", "en": "Generating visuals (5/6)..."},
    {"key": "broll6",    "pct": 45,  "triggers": ["b-roll frame 6", "b-roll video 6", "Fetching b-roll frame 6"],
     "tr": "Görseller üretiliyor (6/6)...", "en": "Generating visuals (6/6)..."},
    {"key": "voiceover", "pct": 55,  "triggers": ["voiceover", "ElevenLabs", "Edge TTS"],
     "tr": "Seslendirme yapılıyor...", "en": "Generating voiceover..."},
    {"key": "whisper",   "pct": 65,  "triggers": ["Whisper", "word timestamps", "Running Whisper"],
     "tr": "Altyazılar oluşturuluyor...", "en": "Generating captions..."},
    {"key": "captions",  "pct": 70,  "triggers": ["SRT captions", "ASS captions"],
     "tr": "Altyazılar kaydedildi", "en": "Captions saved"},
    {"key": "music",     "pct": 75,  "triggers": ["music", "skipping background music"],
     "tr": "Müzik işleniyor...", "en": "Processing music..."},
    {"key": "assemble",  "pct": 85,  "triggers": ["Assembling video", "Video assembled"],
     "tr": "Video birleştiriliyor...", "en": "Assembling video..."},
    {"key": "thumbnail", "pct": 90,  "triggers": ["thumbnail", "Generating thumbnail"],
     "tr": "Thumbnail oluşturuluyor...", "en": "Generating thumbnail..."},
    {"key": "upload",    "pct": 95,  "triggers": ["Uploading", "Uploaded:"],
     "tr": "YouTube'a yükleniyor...", "en": "Uploading to YouTube..."},
    {"key": "done",      "pct": 100, "triggers": ["Done!", "Live:"],
     "tr": "Tamamlandı!", "en": "Complete!"},
]


def detect_stage(line: str) -> dict | None:
    """Detect which pipeline stage a log line belongs to."""
    for stage in PIPELINE_STAGES:
        for trigger in stage["triggers"]:
            if trigger.lower() in line.lower():
                return stage
    return None


def run_pipeline_with_progress(cmd, progress_bar, status_text, lang_key="tr"):
    """Run pipeline with real-time progress bar updates."""
    import io

    process = subprocess.Popen(
        [sys.executable, "-u", "-m", "pipeline"] + cmd,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(PROJECT_DIR),
        bufsize=1,
    )

    full_output = []
    current_pct = 0
    current_stage_text = {
        "tr": "Başlatılıyor...",
        "en": "Starting...",
    }[lang_key]

    # Update initial state
    progress_bar.progress(0, text=current_stage_text)

    try:
        for line in process.stdout:
            line = line.rstrip()
            if line:
                full_output.append(line)

            stage = detect_stage(line)
            if stage:
                new_pct = stage["pct"]
                if new_pct > current_pct:
                    current_pct = new_pct
                    current_stage_text = stage[lang_key]
                    progress_bar.progress(
                        min(current_pct, 100) / 100,
                        text=current_stage_text,
                    )
                    status_text.code("\n".join(full_output[-8:]), language="text")

        process.wait(timeout=1800)
    except subprocess.TimeoutExpired:
        process.kill()
        return "\n".join(full_output), "Timeout", 1
    except Exception as e:
        process.kill()
        return "\n".join(full_output), str(e), 1

    # Final state
    if process.returncode == 0:
        progress_bar.progress(1.0, text={"tr": "Tamamlandı!", "en": "Complete!"}[lang_key])
    else:
        progress_bar.progress(
            min(current_pct, 100) / 100,
            text={"tr": "Hata oluştu", "en": "Error occurred"}[lang_key],
        )

    return "\n".join(full_output), "", process.returncode


def check_claude_cli():
    import shutil
    if not shutil.which("claude"):
        return False
    try:
        creds = Path.home() / ".claude" / ".credentials.json"
        if creds.exists():
            d = json.loads(creds.read_text())
            return bool(d.get("claudeAiOauth", {}).get("accessToken"))
    except Exception:
        pass
    return False


def get_providers(config):
    """Return current provider settings with defaults."""
    providers = config.get("providers", {})
    return {
        "script_ai": providers.get("script_ai", "claude_cli"),
        "image": providers.get("image", "pexels"),
        "video": providers.get("video", "none"),
        "tts": providers.get("tts", "edge_tts"),
    }


def get_active_providers():
    providers = config.get("providers", {})
    return {
        "script_ai": providers.get("script_ai", "claude_cli"),
        "image": providers.get("image", "pexels"),
        "video": providers.get("video", "none"),
        "tts": providers.get("tts", "edge_tts"),
    }


def get_provider_display_name(provider_key):
    """Human-readable provider names from PROVIDERS catalog."""
    from pipeline.config import PROVIDERS
    for cat in PROVIDERS.values():
        if provider_key in cat:
            return cat[provider_key]["name"]
    return provider_key


def time_ago(job_id):
    """Return human-readable time ago string."""
    try:
        ts = int(job_id)
        diff = int(time.time()) - ts
        if diff < 60:
            return f"{diff} {t('ago_s')}"
        elif diff < 3600:
            return f"{diff // 60} {t('ago_m')}"
        elif diff < 86400:
            return f"{diff // 3600} {t('ago_h')}"
        else:
            return f"{diff // 86400} {t('ago_d')}"
    except Exception:
        return "-"


def draft_status_badge(state):
    """Return HTML badge for draft status."""
    if state.get("upload", {}).get("status") == "done":
        return f'<span class="status-badge status-success"><span class="status-dot green"></span>{t("success_label")}</span>'
    elif any(v.get("status") == "failed" for v in state.values() if isinstance(v, dict)):
        return f'<span class="status-badge status-error"><span class="status-dot red"></span>{t("error_label")}</span>'
    elif any(v.get("status") == "done" for v in state.values() if isinstance(v, dict)):
        return f'<span class="status-badge status-processing"><span class="status-dot blue"></span>{t("processing_label")}</span>'
    else:
        return f'<span class="status-badge status-pending">{t("draft_label")}</span>'


# --- Load Data ---------------------------------------------------
config = load_config()
providers = get_providers(config)

has_claude = check_claude_cli() or bool(config.get("ANTHROPIC_API_KEY"))
has_gemini = bool(config.get("GEMINI_API_KEY"))
has_pexels = bool(config.get("PEXELS_API_KEY"))
has_elevenlabs = bool(config.get("ELEVENLABS_API_KEY"))
has_openai = bool(config.get("OPENAI_API_KEY"))
has_google_tts = bool(config.get("GOOGLE_TTS_KEY"))
has_yt_token = (SKILL_DIR / "youtube_token.json").exists()
CHANNELS_DIR = SKILL_DIR / "channels"


def get_channels() -> list[dict]:
    """Get list of configured YouTube channels."""
    channels = []
    # Default channel (legacy token)
    default_token = SKILL_DIR / "youtube_token.json"
    if default_token.exists():
        channels.append({"name": "Varsayılan Kanal", "token_path": str(default_token), "id": "default", "connected": True})
    # Named channels
    if CHANNELS_DIR.exists():
        for d in sorted(CHANNELS_DIR.iterdir()):
            if d.is_dir():
                token_exists = (d / "youtube_token.json").exists()
                channels.append({
                    "name": d.name,
                    "token_path": str(d / "youtube_token.json"),
                    "id": d.name,
                    "connected": token_exists,
                })
    return channels


def add_channel(name: str):
    """Create a new channel directory."""
    safe_name = "".join(c for c in name if c.isalnum() or c in " -_").strip()
    if not safe_name:
        return
    channel_dir = CHANNELS_DIR / safe_name
    channel_dir.mkdir(parents=True, exist_ok=True)
    return channel_dir


def remove_channel(channel_id: str):
    """Remove a channel directory."""
    if channel_id == "default":
        token = SKILL_DIR / "youtube_token.json"
        if token.exists():
            token.unlink()
    else:
        import shutil
        channel_dir = CHANNELS_DIR / channel_id
        if channel_dir.exists():
            shutil.rmtree(channel_dir)
try:
    subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
    has_ffmpeg = True
except Exception:
    has_ffmpeg = False

drafts = get_drafts()
videos = get_media_files()

total_drafts = len(drafts)
total_videos = len(videos)
success_count = sum(
    1 for d in drafts
    if d.get("_pipeline_state", {}).get("upload", {}).get("status") == "done"
)
success_rate = (success_count / total_drafts * 100) if total_drafts > 0 else 0
active_count = sum(
    1 for d in drafts
    if any(
        d.get("_pipeline_state", {}).get(s, {}).get("status") == "done"
        for s in ["draft", "broll"]
    ) and d.get("_pipeline_state", {}).get("upload", {}).get("status") != "done"
)


# --- Floating Sidebar Toggle Button (JS via iframe) -------------
import streamlit.components.v1 as components
components.html("""
<script>
(function() {
    var parent = window.parent.document;

    function createBtn() {
        if (parent.getElementById('sidebar-expand-custom')) return;
        var btn = parent.createElement('button');
        btn.id = 'sidebar-expand-custom';
        btn.innerHTML = '&#9776;';
        btn.title = 'Open menu';
        Object.assign(btn.style, {
            position: 'fixed', top: '14px', left: '14px', zIndex: '999999',
            width: '40px', height: '40px', background: '#201f26',
            border: '1px solid #3a3940', borderRadius: '10px',
            color: '#c9a96e', fontSize: '1.2rem', cursor: 'pointer',
            display: 'none', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
            transition: 'all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
            fontFamily: 'Inter, sans-serif'
        });
        btn.onmouseover = function() {
            btn.style.transform = 'scale(1.12)';
            btn.style.borderColor = '#c9a96e';
            btn.style.boxShadow = '0 6px 25px rgba(201,169,110,0.2)';
        };
        btn.onmouseout = function() {
            btn.style.transform = 'scale(1)';
            btn.style.borderColor = '#3a3940';
            btn.style.boxShadow = '0 4px 20px rgba(0,0,0,0.5)';
        };
        btn.onclick = function() {
            var targets = [
                'button[data-testid="stSidebarExpand"]',
                '[data-testid="collapsedControl"] button',
                'button[data-testid="stSidebarNavToggle"]',
                'button[kind="headerNoPadding"]'
            ];
            for (var i = 0; i < targets.length; i++) {
                var el = parent.querySelector(targets[i]);
                if (el) { el.click(); return; }
            }
        };
        parent.body.appendChild(btn);
    }

    function watch() {
        var sidebar = parent.querySelector('section[data-testid="stSidebar"]');
        var btn = parent.getElementById('sidebar-expand-custom');
        if (!btn) { createBtn(); btn = parent.getElementById('sidebar-expand-custom'); }
        if (!sidebar || !btn) return;
        var exp = sidebar.getAttribute('aria-expanded');
        btn.style.display = (exp === 'false' || !exp) ? 'flex' : 'none';
    }

    createBtn();
    setInterval(watch, 250);
})();
</script>
""", height=0)

# --- Sidebar -----------------------------------------------------
with st.sidebar:
    # Brand — honors white-label logo_path if provided
    _brand_logo_html = ""
    _brand_logo_path = _brand.get("logo_path") or ""
    if _brand_logo_path:
        try:
            import base64 as _b64
            _logo_data = _branding.logo_bytes()
            if _logo_data:
                _ext = Path(_brand_logo_path).suffix.lstrip(".").lower() or "png"
                _mime = {"svg": "svg+xml"}.get(_ext, _ext)
                _b64_str = _b64.b64encode(_logo_data).decode("ascii")
                _brand_logo_html = f'<img src="data:image/{_mime};base64,{_b64_str}" class="nav-brand-logo" alt="logo"/>'
        except Exception:
            _brand_logo_html = ""

    _nav_icon = _brand_logo_html or '<div class="nav-brand-icon">▶</div>'
    _nav_name = _brand.get("product_name", "RE-Tube")
    st.markdown(f"""
    <div class="nav-brand">
        {_nav_icon}
        <div class="nav-brand-text">{_nav_name}</div>
    </div>
    """, unsafe_allow_html=True)

    # Language toggle
    lang_cols = st.columns(2)
    with lang_cols[0]:
        if st.button("TR", use_container_width=True, key="lang_tr"):
            st.session_state.lang = "tr"
            st.rerun()
    with lang_cols[1]:
        if st.button("EN", use_container_width=True, key="lang_en"):
            st.session_state.lang = "en"
            st.rerun()

    # Multi-tenant switcher — only when feature is enabled
    try:
        from pipeline import tenant as _tn
        if _tn.is_multi_tenant_enabled():
            _tenants = _tn.list_tenants()
            if _tenants:
                tenant_ids = [x["id"] for x in _tenants]
                current_id = _tn.current_tenant_id()
                if current_id not in tenant_ids:
                    current_id = tenant_ids[0]
                new_tid = st.selectbox(
                    "🏢 " + {"tr": "Aktif Müşteri", "en": "Active Tenant"}[st.session_state.lang],
                    options=tenant_ids,
                    index=tenant_ids.index(current_id),
                    format_func=lambda tid: next((x["name"] for x in _tenants if x["id"] == tid), tid),
                    key="active_tenant_sel",
                )
                if new_tid != current_id:
                    _tn.set_current_tenant(new_tid)
                    st.rerun()
    except Exception:
        pass

    # Navigation
    # Queue badge
    try:
        from pipeline import queue as _qmod
        _q_counts = _qmod.counts()
        _q_active = _q_counts.get("pending", 0) + _q_counts.get("producing", 0) + _q_counts.get("produced", 0) + _q_counts.get("uploading", 0)
    except Exception:
        _q_active = 0
    _queue_label = {"tr": "Kuyruk", "en": "Queue"}[st.session_state.lang]
    if _q_active:
        _queue_label = f"{_queue_label} ({_q_active})"

    _drafts_label = {"tr": "Draftlar", "en": "Drafts"}[st.session_state.lang]
    _comments_label = {"tr": "Yorumlar", "en": "Comments"}[st.session_state.lang]
    _tools_label = {"tr": "🧰 Araçlar", "en": "🧰 Tools"}[st.session_state.lang]

    # Unanswered question badge
    try:
        from pipeline import comment_moderator as _cm
        _qcount = _cm.counts(days=14).get("question", 0)
        _unhandled = [c for c in _cm.inbox(category="question", limit=200) if c.get("action") != "handled"]
        if _unhandled:
            _comments_label = f"{_comments_label} ({len(_unhandled)})"
    except Exception:
        pass

    # News matches badge
    try:
        from pipeline import news_watcher as _nw
        _unread_news = len([e for e in _nw.inbox(matched_only=True, limit=100)
                            if not e.get("queued_job_id")])
        if _unread_news:
            _tools_label = f"{_tools_label} ({_unread_news})"
    except Exception:
        pass

    nav_labels = [
        t("dashboard"), t("pipeline"), _queue_label, _drafts_label,
        _comments_label, _tools_label,
        t("manual_prod"), t("trends"), t("videos"),
        t("history"), t("settings"),
    ]
    nav_keys = ["Dashboard", "Pipeline", "Queue", "Drafts", "Comments",
                "Tools", "Manual", "Trends", "Videos", "History", "Settings"]

    page = st.radio(
        "Navigation",
        nav_keys,
        format_func=lambda x: nav_labels[nav_keys.index(x)],
        label_visibility="collapsed",
    )

    # System status
    st.markdown(f'<div class="settings-title">{t("system_status")}</div>', unsafe_allow_html=True)

    services = [
        ("Claude AI", has_claude),
        ("Gemini Vision", has_gemini),
        ("OpenAI", has_openai),
        ("Pexels Photos", has_pexels),
        ("ElevenLabs TTS", has_elevenlabs),
        ("Google Cloud TTS", has_google_tts),
        ("FFmpeg", has_ffmpeg),
        ("YouTube OAuth", has_yt_token),
    ]
    for name, ok in services:
        dot = "dot-ok" if ok else "dot-err"
        st.markdown(f"""
        <div class="key-status">
            <span class="label">{name}</span>
            <span class="{dot}">●</span>
        </div>
        """, unsafe_allow_html=True)

    # Update check button
    st.markdown("")  # spacer
    from updater import load_version_info, check_for_updates, apply_update, init_repo, has_git as has_git_cmd

    ver_info = load_version_info()
    repo_url = ver_info.get("repo_url", "")
    ver_label = f"v{ver_info.get('current_version', '1.0.0')}"

    if repo_url and has_git_cmd():
        if st.button(f"🔄  {t('check_updates')}", use_container_width=True, key="sidebar_update_check"):
            with st.spinner("..."):
                init_repo(repo_url, ver_info.get("branch", "main"))
                has_upd, local_h, remote_h = check_for_updates(repo_url, ver_info.get("branch", "main"))
                if has_upd:
                    st.warning(f"{t('update_available')}")
                    if st.button(t("apply_update"), use_container_width=True, key="sidebar_apply_update"):
                        ok, msg = apply_update(ver_info.get("branch", "main"))
                        if ok:
                            st.success(t("update_success"))
                        else:
                            st.error(msg[:100])
                else:
                    st.success(f"✓ {t('up_to_date')}")

    st.caption(f"RE-Tube {ver_label}")

    # Contact footer
    st.markdown("""
    <div class="sidebar-footer">
        Telegram: <a href="https://t.me/reworar" target="_blank">t.me/reworar</a>
    </div>
    """, unsafe_allow_html=True)


# =====================================================================
# DASHBOARD PAGE
# =====================================================================
if page == "Dashboard":
    st.markdown(f"""
    <div class="topbar">
        <div class="topbar-title">{t("dashboard")}</div>
        <div class="topbar-right">
            <div class="user-avatar">YT</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Welcome
    st.markdown(f"""
    <div class="welcome">
        <h2>{t("welcome_title")}</h2>
        <p>{t("welcome_sub")}</p>
    </div>
    """, unsafe_allow_html=True)

    # Stats
    st.markdown(f"""
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-icon gold">▦</div>
            <div class="stat-label">{t("total_prod")}</div>
            <div class="stat-value">{total_drafts}</div>
            <div class="stat-change neutral">{t("all_time")}</div>
        </div>
        <div class="stat-card">
            <div class="stat-icon info">◫</div>
            <div class="stat-label">{t("videos_label")}</div>
            <div class="stat-value">{total_videos}</div>
            <div class="stat-change positive">{t("videos_produced")}</div>
        </div>
        <div class="stat-card">
            <div class="stat-icon success">◎</div>
            <div class="stat-label">{t("success_rate")}</div>
            <div class="stat-value">{success_rate:.1f}%</div>
            <div class="stat-change positive">{t("upload_success")}</div>
        </div>
        <div class="stat-card">
            <div class="stat-icon warn">⚡</div>
            <div class="stat-label">{t("active_pipeline")}</div>
            <div class="stat-value">{active_count}</div>
            <div class="stat-change neutral">{t("in_progress")}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- Charts Row: Production Activity + System Uptime ---
    import random
    random.seed(42)  # Consistent visual

    # Generate production activity bars from real drafts (last 14 days)
    day_labels = []
    day_counts = []
    now_ts = int(time.time())
    for i in range(13, -1, -1):
        day_start = now_ts - (i * 86400)
        day_end = day_start + 86400
        count = sum(1 for d in drafts if day_start <= int(d.get("job_id", "0")) < day_end)
        day_counts.append(count)
        from datetime import datetime as dt
        day_labels.append(dt.fromtimestamp(day_start).strftime("%d"))

    max_count = max(day_counts) if any(day_counts) else 1
    bars_html = ""
    for i, c in enumerate(day_counts):
        h = max(4, int((c / max(max_count, 1)) * 70))
        color = "var(--accent-primary)" if c > 0 else "var(--border-subtle)"
        opacity = 0.5 + (c / max(max_count, 1)) * 0.5 if c > 0 else 0.3
        bars_html += f'<div class="mini-bar" style="height:{h}px; background:{color}; opacity:{opacity};"></div>'
    labels_html = "".join(f'<div class="bar-label">{l}</div>' for l in day_labels)

    # System uptime dots (last 30 days - simulated from service availability)
    active_services = sum(1 for _, ok in services if ok)
    total_services = len(services)
    uptime_pct = (active_services / total_services * 100) if total_services > 0 else 0
    uptime_dots = ""
    for i in range(30):
        if i < 28:
            uptime_dots += '<div class="uptime-dot up"></div>'
        elif i == 28 and not has_elevenlabs:
            uptime_dots += '<div class="uptime-dot partial"></div>'
        else:
            uptime_dots += '<div class="uptime-dot up"></div>'

    chart_activity_title = "Üretim Aktivitesi (14 Gün)" if st.session_state.lang == "tr" else "Production Activity (14 Days)"
    chart_uptime_title = "Sistem Durumu (30 Gün)" if st.session_state.lang == "tr" else "System Uptime (30 Days)"
    uptime_text = "Çalışma Süresi" if st.session_state.lang == "tr" else "Uptime"

    st.markdown(f"""
    <div class="charts-row">
        <div class="chart-card">
            <div class="chart-title">{chart_activity_title}</div>
            <div class="mini-bars">{bars_html}</div>
            <div class="bar-labels">{labels_html}</div>
        </div>
        <div class="chart-card">
            <div class="chart-title">{chart_uptime_title}</div>
            <div class="uptime-grid">{uptime_dots}</div>
            <div class="uptime-legend">
                <span>30 gün önce</span>
                <span>Bugün</span>
            </div>
            <div class="uptime-stat">
                <span class="uptime-pct">{uptime_pct:.0f}%</span>
                <span class="uptime-label">{uptime_text}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Active providers badges
    st.markdown(f'<div class="section-label">{t("active_providers")}</div>', unsafe_allow_html=True)
    prov_html = f"""
    <div class="provider-badges">
        <span class="provider-badge">{get_provider_display_name(providers['script_ai'])}</span>
        <span class="provider-badge green">{get_provider_display_name(providers['image'])}</span>
        <span class="provider-badge muted">{get_provider_display_name(providers['tts'])}</span>
    </div>
    """
    st.markdown(prov_html, unsafe_allow_html=True)

    # ── Live Channel Stats (Tier 2 #11) ───────────────────────
    try:
        from pipeline import channel_stats as _cstats
        _connected_channels = [c for c in get_channels() if c.get("connected")]
        if _connected_channels:
            _stats_title = {"tr": "📊 Kanal İstatistikleri (canlı)",
                            "en": "📊 Channel Stats (live)"}[st.session_state.lang]
            st.markdown(f'<div class="section-label" style="margin-top:2rem;">{_stats_title}</div>',
                        unsafe_allow_html=True)

            # Channel picker
            _stat_ch_labels = [c["name"] for c in _connected_channels]
            stat_ch_idx = 0
            if len(_connected_channels) > 1:
                stat_ch_idx = _stat_ch_labels.index(
                    st.selectbox(
                        {"tr": "Kanal seç", "en": "Select channel"}[st.session_state.lang],
                        _stat_ch_labels, index=0, key="stats_ch_sel",
                    )
                )
            stat_ch = _connected_channels[stat_ch_idx]
            ref_col = st.columns([6, 1])
            with ref_col[1]:
                force_refresh = st.button(
                    {"tr": "🔄 Yenile", "en": "🔄 Refresh"}[st.session_state.lang],
                    key="stats_refresh", use_container_width=True,
                )

            snap = _cstats.fetch_stats(stat_ch["token_path"], force_refresh=force_refresh)
            if snap.get("error"):
                st.warning(f"⚠ {snap['error']}")
            elif snap.get("channel"):
                ch_data = snap["channel"]
                sc1, sc2, sc3, sc4 = st.columns(4)
                sc1.metric({"tr": "Abone", "en": "Subs"}[st.session_state.lang],
                           _cstats.format_count(ch_data["subscribers"]))
                sc2.metric({"tr": "Toplam İzlenme", "en": "Total Views"}[st.session_state.lang],
                           _cstats.format_count(ch_data["views"]))
                sc3.metric({"tr": "Video Sayısı", "en": "Video Count"}[st.session_state.lang],
                           ch_data["videos"])
                # Derived: avg views per video
                avg_v = int(ch_data["views"] / max(1, ch_data["videos"]))
                sc4.metric({"tr": "Ort. İzlenme/Video", "en": "Avg Views/Video"}[st.session_state.lang],
                           _cstats.format_count(avg_v))

                # Recent videos preview
                if snap.get("recent"):
                    recent_title = {"tr": "Son Yüklenenler (10)",
                                    "en": "Latest Uploads (10)"}[st.session_state.lang]
                    st.markdown(f"<div class='section-label' style='margin-top:1rem;font-size:0.82rem'>{recent_title}</div>",
                                unsafe_allow_html=True)

                    cards = ['<div class="yt-cards">']
                    for v in snap["recent"][:10]:
                        pub_short = v["published_at"][:10] if v["published_at"] else ""
                        thumb = v["thumbnail"] or ""
                        cards.append(
                            f'<a class="yt-card" href="{v["url"]}" target="_blank">'
                            f'<div class="yt-thumb" style="background-image:url({thumb})"></div>'
                            f'<div class="yt-meta">'
                            f'<div class="yt-title">{v["title"][:55]}</div>'
                            f'<div class="yt-stats">'
                            f'  <span>👁 {_cstats.format_count(v["views"])}</span>'
                            f'  <span>👍 {_cstats.format_count(v["likes"])}</span>'
                            f'  <span>💬 {_cstats.format_count(v["comments"])}</span>'
                            f'  <span class="yt-date">{pub_short}</span>'
                            f'</div></div>'
                            f'</a>'
                        )
                    cards.append('</div>')
                    if hasattr(st, "html"):
                        st.html("".join(cards))
                    else:
                        st.markdown("".join(cards), unsafe_allow_html=True)
    except Exception as _cs_err:
        st.caption(f"(channel_stats: {_cs_err})")

    # ── Cost Dashboard (Tier 1 #5) ─────────────────────────────
    try:
        from pipeline import cost as _cost_mod
        _cost_summary = _cost_mod.summary(days=30)
        _cost_today = _cost_mod.today_usd()
        _cost_mtd = _cost_mod.month_to_date_usd()

        st.markdown(f'<div class="section-label" style="margin-top:2rem;">{{"tr":"💰 Harcama","en":"💰 Spend"}}[{repr(st.session_state.lang)}]</div>' if False else
                    f'<div class="section-label" style="margin-top:2rem;">{"💰 Harcama" if st.session_state.lang == "tr" else "💰 Spend"}</div>',
                    unsafe_allow_html=True)
        cc1, cc2, cc3, cc4 = st.columns(4)
        cc1.metric({"tr": "Bugün", "en": "Today"}[st.session_state.lang],
                   f"${_cost_today:.2f}")
        cc2.metric({"tr": "Bu Ay", "en": "Month-to-date"}[st.session_state.lang],
                   f"${_cost_mtd:.2f}")
        cc3.metric({"tr": "Son 30 Gün", "en": "Last 30d"}[st.session_state.lang],
                   f"${_cost_summary['total_usd']:.2f}")
        cc4.metric({"tr": "Üretim (30g)", "en": "Jobs (30d)"}[st.session_state.lang],
                   _cost_summary["job_count"])

        # Daily spend chart
        if _cost_summary["daily_series"]:
            try:
                import pandas as pd
                df = pd.DataFrame(_cost_summary["daily_series"])
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date")
                st.bar_chart(df, height=180, use_container_width=True, color="#C9A96E")
            except Exception:
                # Fallback: Streamlit native line_chart without pandas
                import altair as alt  # comes with Streamlit
                # altair fallback omitted for brevity — raw data fallback
                st.line_chart({d["date"]: d["usd"] for d in _cost_summary["daily_series"]},
                              height=180, use_container_width=True)

        # Provider breakdown
        if _cost_summary["by_provider"]:
            _top_providers = list(_cost_summary["by_provider"].items())[:8]
            breakdown_html = '<div class="cost-breakdown">'
            total_for_bars = max(v for _, v in _top_providers) if _top_providers else 1
            for prov_key, amt in _top_providers:
                pct = int((amt / total_for_bars) * 100) if total_for_bars > 0 else 0
                name = get_provider_display_name(prov_key)
                breakdown_html += (
                    f'<div class="cost-row">'
                    f'<div class="cost-name">{name}</div>'
                    f'<div class="cost-bar-wrap"><div class="cost-bar" style="width:{pct}%"></div></div>'
                    f'<div class="cost-amount">${amt:.2f}</div>'
                    f'</div>'
                )
            breakdown_html += '</div>'
            if hasattr(st, "html"):
                st.html(breakdown_html)
            else:
                st.markdown(breakdown_html, unsafe_allow_html=True)
    except Exception as _e:
        st.caption(f"(cost module: {_e})")

    # Recent productions table
    st.markdown(f"""
    <div class="table-header">
        <div>
            <h3>{t("recent_prod")}</h3>
            <p>{t("recent_prod_sub")}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if drafts:
        # Premium card list — rendered via st.html to bypass markdown's code-block heuristic
        cards_html = ['<div class="prod-cards">']
        for d in drafts[:10]:
            title = (d.get("youtube_title") or d.get("news") or "Untitled")
            title_short = title[:72] + ("…" if len(title) > 72 else "")
            job_id = str(d.get("job_id", "?"))
            prd_id = f"PRD-{job_id[-4:]}"
            state = d.get("_pipeline_state", {})
            done = sum(1 for v in state.values() if isinstance(v, dict) and v.get("status") == "done")
            total_stages = 9
            pct = int(done * 100 / total_stages) if total_stages else 0

            # Status derivation
            any_failed = any(isinstance(v, dict) and v.get("status") == "failed" for v in state.values())
            upload_done = isinstance(state.get("upload"), dict) and state["upload"].get("status") == "done"
            if upload_done:
                status_cls, status_lbl, accent = "done", t("success_label"), "#6BBD7B"
            elif any_failed:
                status_cls, status_lbl, accent = "failed", t("error_label"), "#E06B6B"
            elif done > 0:
                status_cls, status_lbl, accent = "progress", t("processing_label"), "#6B9FC4"
            else:
                status_cls, status_lbl, accent = "pending", t("draft_label"), "#C9A96E"

            lang = d.get("lang", "").upper() or "EN"
            fmt = d.get("format", "shorts")
            dur = d.get("duration", "short")
            ago = time_ago(job_id)
            # Language flag emoji
            flag = {"TR": "🇹🇷", "EN": "🇬🇧", "DE": "🇩🇪", "HI": "🇮🇳", "ES": "🇪🇸", "FR": "🇫🇷", "PT": "🇵🇹"}.get(lang, "🌐")
            fmt_icon = "📱" if fmt == "shorts" else "🖥️"

            # Escape quotes and < / > in title
            safe_title = title_short.replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

            card = (
                f'<div class="prod-card" data-status="{status_cls}">'
                  f'<div class="prod-card-accent" style="background:{accent}"></div>'
                  f'<div class="prod-card-main">'
                    f'<div class="prod-card-head">'
                      f'<span class="prod-card-title">{safe_title}</span>'
                      f'<span class="prod-card-id">{prd_id}</span>'
                    f'</div>'
                    f'<div class="prod-card-meta">'
                      f'<span class="meta-chip">{flag} {lang}</span>'
                      f'<span class="meta-chip">{fmt_icon} {fmt}</span>'
                      f'<span class="meta-chip">⏱ {dur}</span>'
                      f'<span class="meta-chip meta-ago">🕘 {ago}</span>'
                    f'</div>'
                    f'<div class="prod-card-progress">'
                      f'<div class="prod-progress-track"><div class="prod-progress-fill" style="width:{pct}%;background:{accent}"></div></div>'
                      f'<span class="prod-progress-text">{done}/{total_stages} · {pct}%</span>'
                    f'</div>'
                  f'</div>'
                  f'<div class="prod-card-side">'
                    f'<span class="prod-status-chip prod-status-{status_cls}">'
                      f'<span class="prod-status-dot"></span>{status_lbl}'
                    f'</span>'
                  f'</div>'
                f'</div>'
            )
            cards_html.append(card)
        cards_html.append('</div>')

        # st.html ships in Streamlit >=1.33; safe fallback to markdown with stripped whitespace
        _html_blob = "".join(cards_html)
        if hasattr(st, "html"):
            st.html(_html_blob)
        else:
            st.markdown(_html_blob, unsafe_allow_html=True)
    else:
        _empty = f'<div class="prod-empty">{t("no_prod")}</div>'
        if hasattr(st, "html"):
            st.html(_empty)
        else:
            st.markdown(_empty, unsafe_allow_html=True)

    # Last produced video preview
    if videos:
        st.markdown(f'<div class="section-label" style="margin-top:2rem;">{t("last_video")}</div>', unsafe_allow_html=True)
        st.video(str(videos[0]))


# =====================================================================
# PIPELINE PAGE
# =====================================================================
elif page == "Pipeline":
    st.markdown(f"""
    <div class="topbar">
        <div class="topbar-title">{t("new_production")}</div>
    </div>
    """, unsafe_allow_html=True)

    # Selected providers info
    st.markdown(f'<div class="section-label">{t("selected_providers")}</div>', unsafe_allow_html=True)
    prov_info_html = f"""
    <div class="provider-badges">
        <span class="provider-badge">{get_provider_display_name(providers['script_ai'])}</span>
        <span class="provider-badge green">{get_provider_display_name(providers['image'])}</span>
        <span class="provider-badge muted">{get_provider_display_name(providers['tts'])}</span>
    </div>
    """
    st.markdown(prov_info_html, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        topic = st.text_area(
            t("topic_label"),
            placeholder=t("topic_placeholder"),
            height=100, key="topic_input",
        )
        channel_ctx = st.text_input(
            t("channel_ctx_label"),
            placeholder=t("channel_ctx_placeholder"),
            key="channel_ctx",
        )

        # Viral potential score (Tier 4 #18)
        if topic and len(topic.strip()) >= 10:
            _vs_key = f"vs_{hash(topic)}"
            if st.checkbox(
                {"tr": "🔥 Viral Potansiyel Skoru (AI)",
                 "en": "🔥 Viral Potential Score (AI)"}[st.session_state.lang],
                value=False, key="show_viral_score",
                help={"tr": "Claude + heuristikle 0-100 puan. AI çağrısı yapar, yavaş olabilir.",
                      "en": "Claude + heuristic composite 0-100. Makes an AI call — may be slow."}[st.session_state.lang],
            ):
                if _vs_key not in st.session_state:
                    with st.spinner({"tr": "Skor hesaplanıyor...", "en": "Scoring..."}[st.session_state.lang]):
                        try:
                            from pipeline import viral_score as _vs
                            st.session_state[_vs_key] = _vs.score(topic=topic, use_llm=True)
                        except Exception as e:
                            st.session_state[_vs_key] = {"error": str(e)}
                vs_res = st.session_state.get(_vs_key, {})
                if "error" in vs_res:
                    st.warning(f"Skor hatası: {vs_res['error']}")
                elif "score" in vs_res:
                    s = vs_res["score"]
                    tier = vs_res["tier"]
                    tier_color = {"viral": "#E74C3C", "high": "#2ECC71",
                                  "medium": "#F39C12", "low": "#95A5A6"}[tier]
                    tier_label_tr = {"viral": "🚀 VİRAL", "high": "📈 YÜKSEK",
                                     "medium": "➡️ ORTA", "low": "📉 DÜŞÜK"}[tier]
                    tier_label_en = {"viral": "🚀 VIRAL", "high": "📈 HIGH",
                                     "medium": "➡️ MEDIUM", "low": "📉 LOW"}[tier]
                    tier_label = tier_label_tr if st.session_state.lang == "tr" else tier_label_en

                    st.markdown(
                        f'<div style="padding:14px;background:rgba(0,0,0,0.2);'
                        f'border-left:4px solid {tier_color};border-radius:8px;margin:8px 0">'
                        f'<div style="display:flex;justify-content:space-between;align-items:center">'
                        f'<span style="font-size:2.2rem;font-weight:700;color:{tier_color}">{s}</span>'
                        f'<span style="font-size:0.9rem;color:{tier_color};font-weight:600">{tier_label}</span>'
                        f'</div>'
                        f'<div style="color:var(--text-dim);font-size:0.8rem;margin-top:6px">'
                        f'{vs_res.get("reasoning", "")[:200]}'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
                    if vs_res.get("recommendations"):
                        with st.expander(
                            {"tr": "💡 İyileştirme Önerileri",
                             "en": "💡 Improvement Suggestions"}[st.session_state.lang],
                        ):
                            for r in vs_res["recommendations"]:
                                st.markdown(f"- {r}")
                    if st.button({"tr": "🔄 Yeniden Skorla",
                                  "en": "🔄 Rescore"}[st.session_state.lang],
                                 key=f"rescore_{_vs_key}"):
                        del st.session_state[_vs_key]
                        st.rerun()

        # Topic memory — warn if we've already produced a very similar topic recently
        if topic and len(topic.strip()) >= 8:
            try:
                from pipeline import topic_memory as _tm
                _similar = _tm.find_similar(topic, threshold=0.5, limit=3, days=90)
                if _similar:
                    with st.expander(
                        {"tr": f"⚠️ {len(_similar)} benzer konu daha önce üretilmiş — detay",
                         "en": f"⚠️ {len(_similar)} similar topic(s) previously produced — details"}[st.session_state.lang],
                        expanded=True,
                    ):
                        for s in _similar:
                            age_days = "?"
                            try:
                                from datetime import datetime as _dt, timezone as _tz
                                ca = _dt.fromisoformat(s["created_at"].replace("Z", "+00:00"))
                                age_days = str((_dt.now(_tz.utc) - ca).days)
                            except Exception:
                                pass
                            link = f" · [📺]({s['youtube_url']})" if s.get("youtube_url") else ""
                            st.markdown(
                                f"- **{int(s['similarity']*100)}%** benzer · "
                                f"{age_days} gün önce · `{s['topic'][:70]}`{link}"
                            )
                        st.caption({
                            "tr": "Tekrarlanan konu YouTube algoritmasında olumsuz etkileyebilir. Yine de devam etmek istersen aşağıdaki butonu kullan.",
                            "en": "Duplicate topics can hurt YouTube's algorithm. Proceed anyway if you're sure.",
                        }[st.session_state.lang])
            except Exception:
                pass

    with col2:
        mode_options = [
            t("mode_full"),
            t("mode_video"),
            t("mode_draft"),
        ]
        mode = st.selectbox(t("pipeline_mode"), mode_options)
        lang = st.selectbox(
            t("language"), ["en", "de", "tr", "hi"],
            format_func=lambda x: {"en": "English", "de": "Deutsch", "tr": "Türkçe", "hi": "Hindi"}[x],
        )

        # Format & Duration selection
        fmt_col1, fmt_col2 = st.columns(2)
        with fmt_col1:
            video_format = st.selectbox(
                t("video_format"),
                ["shorts", "video"],
                format_func=lambda x: t("format_shorts") if x == "shorts" else t("format_video"),
            )
        with fmt_col2:
            duration_options = ["short", "3min", "5min", "10min"]
            duration_labels = {
                "short": t("dur_short"),
                "3min": t("dur_3min"),
                "5min": t("dur_5min"),
                "10min": t("dur_10min"),
            }
            video_duration = st.selectbox(
                t("video_duration"),
                duration_options,
                format_func=lambda x: duration_labels[x],
            )

        force = st.checkbox(t("force_redo"))

        # Channel selection
        channels = get_channels()
        if len(channels) > 1:
            selected_channel = st.selectbox(
                t("select_channel"),
                channels,
                format_func=lambda x: x["name"],
                key="pipeline_channel",
            )
        elif channels:
            selected_channel = channels[0]
        else:
            selected_channel = None

    # Channel preset hint — show user what defaults will apply
    channel_preset = {}
    if selected_channel:
        from pipeline.channel_preset import load_preset as _load_preset
        channel_preset = _load_preset(selected_channel["id"])
        if channel_preset:
            _hints = []
            for k, v in channel_preset.items():
                if v and k in ("lang", "format", "duration", "tone"):
                    _hints.append(f"{k}={v}")
                elif v and k in ("script_ai", "image", "tts", "music"):
                    _hints.append(f"{k}={v}")
                elif v and k == "playlist_id":
                    _hints.append(f"playlist ✓")
            if _hints:
                st.caption({
                    "tr": f"🎨 Kanal preset aktif — {' · '.join(_hints[:6])}",
                    "en": f"🎨 Channel preset active — {' · '.join(_hints[:6])}",
                }[st.session_state.lang])

    # Pipeline stages visualization
    stages = ["Research", "Draft", "B-Roll", "Voice", "Captions", "Music", "Assemble", "Thumb", "Upload"]
    pills = "".join(f'<span class="stage-pill">{s}</span>' for s in stages)
    st.markdown(f'<div class="pipeline-stages">{pills}</div>', unsafe_allow_html=True)

    # ── Scheduled publish picker ───────────────────────────────
    from datetime import datetime, timedelta, timezone as _tz
    _sched_title = {"tr": "📅 Yayın Zamanı", "en": "📅 Publish Schedule"}[st.session_state.lang]
    _sched_opts = {
        "now_private":   {"tr": "Yüklendikten hemen sonra (private)",   "en": "Immediately after upload (private)"},
        "now_unlisted":  {"tr": "Yüklendikten hemen sonra (unlisted)",  "en": "Immediately after upload (unlisted)"},
        "now_public":    {"tr": "Yüklendikten hemen sonra (public)",    "en": "Immediately after upload (public)"},
        "scheduled":     {"tr": "Belirli bir tarih/saatte otomatik yayınla", "en": "Schedule at a specific date/time"},
    }
    schedule_choice = st.selectbox(
        _sched_title,
        options=list(_sched_opts.keys()),
        format_func=lambda k: _sched_opts[k][st.session_state.lang],
        index=0,
        key="schedule_choice",
        help={"tr": "Zamanlanmış yayınlarda video önce private yüklenir, belirtilen saatte YouTube otomatik public yapar.",
              "en": "For scheduled publishing, video is uploaded as private and YouTube auto-publishes at the given time."}[st.session_state.lang],
    )

    publish_at_iso: str | None = None
    privacy_default: str = "private"
    if schedule_choice == "now_public":
        privacy_default = "public"
    elif schedule_choice == "now_unlisted":
        privacy_default = "unlisted"
    elif schedule_choice == "scheduled":
        sc1, sc2, sc3 = st.columns(3)
        tomorrow_9 = datetime.now() + timedelta(days=1)
        tomorrow_9 = tomorrow_9.replace(hour=9, minute=0, second=0, microsecond=0)
        with sc1:
            d = st.date_input({"tr": "Tarih", "en": "Date"}[st.session_state.lang],
                              value=tomorrow_9.date(), min_value=datetime.now().date(), key="sched_date")
        with sc2:
            t_str = st.text_input({"tr": "Saat (HH:MM)", "en": "Time (HH:MM)"}[st.session_state.lang],
                                   value=tomorrow_9.strftime("%H:%M"), key="sched_time")
        with sc3:
            tz_offset = st.selectbox(
                {"tr": "Zaman dilimi", "en": "Time zone"}[st.session_state.lang],
                ["UTC", "Europe/Istanbul (+03:00)", "Europe/London", "America/New_York", "America/Los_Angeles"],
                index=1, key="sched_tz",
            )
        try:
            hh, mm = [int(x) for x in t_str.split(":")]
            # Convert local time to UTC by subtracting offset
            offsets = {"UTC": 0, "Europe/Istanbul (+03:00)": 3, "Europe/London": 0,
                       "America/New_York": -5, "America/Los_Angeles": -8}
            off = offsets.get(tz_offset, 0)
            local_dt = datetime.combine(d, datetime.min.time()).replace(hour=hh, minute=mm)
            utc_dt = local_dt - timedelta(hours=off)
            utc_dt = utc_dt.replace(tzinfo=_tz.utc)
            if utc_dt <= datetime.now(_tz.utc) + timedelta(minutes=5):
                st.warning({"tr": "⚠️ Zamanlama en az 5 dakika ilerde olmalı.",
                            "en": "⚠️ Schedule must be at least 5 minutes in the future."}[st.session_state.lang])
                publish_at_iso = None
            else:
                publish_at_iso = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                st.caption({
                    "tr": f"🕒 YouTube'a gönderilecek zaman (UTC): `{publish_at_iso}`",
                    "en": f"🕒 UTC time to send to YouTube: `{publish_at_iso}`",
                }[st.session_state.lang])
        except Exception:
            st.error({"tr": "Saat biçimi geçersiz (HH:MM olmalı)",
                      "en": "Invalid time format (HH:MM expected)"}[st.session_state.lang])
            publish_at_iso = None

    # Queue-first mode: add to queue, return instantly, continue in background
    _lbl_queue = {"tr": "Kuyruğa Ekle (Arka Planda Üret)", "en": "Add to Queue (Background)"}[st.session_state.lang]
    _lbl_live  = {"tr": "Canlı İlerleme (Bekle)", "en": "Live Progress (Blocking)"}[st.session_state.lang]

    btn_col1, btn_col2 = st.columns([2, 1])
    queue_clicked = btn_col1.button(_lbl_queue, use_container_width=True, disabled=not topic, type="primary")
    live_clicked  = btn_col2.button(_lbl_live, use_container_width=True, disabled=not topic)

    if queue_clicked and topic:
        if not has_claude and providers["script_ai"] in ("claude_cli", "claude_api"):
            st.error(t("claude_required"))
        else:
            mode_full_label = t("mode_full")
            mode_video_label = t("mode_video")
            pipeline_mode = "full" if mode == mode_full_label else ("video" if mode == mode_video_label else "draft")
            channel_id = selected_channel.get("id") if selected_channel else None
            job = enqueue_job(
                topic=topic,
                context=channel_ctx or "",
                lang=lang,
                mode=pipeline_mode,
                video_format=video_format,
                duration=video_duration,
                channel=channel_id,
                force=bool(force),
                publish_at=publish_at_iso,
                privacy_status=privacy_default,
            )
            sched_msg = ""
            if publish_at_iso:
                sched_msg = {"tr": f" · 🕒 {publish_at_iso} UTC'de yayınlanacak",
                             "en": f" · 🕒 will publish at {publish_at_iso} UTC"}[st.session_state.lang]
            elif privacy_default != "private":
                sched_msg = {"tr": f" · 👁 {privacy_default}",
                             "en": f" · 👁 {privacy_default}"}[st.session_state.lang]
            st.success({
                "tr": f"Kuyruğa eklendi: {job['id']}{sched_msg} — arkaplanda üretim başladı.",
                "en": f"Queued: {job['id']}{sched_msg} — production running in background.",
            }[st.session_state.lang])
            st.info({
                "tr": "Kuyruk sayfasından ilerlemeyi takip edebilirsin.",
                "en": "Track progress from the Queue page.",
            }[st.session_state.lang])

    if live_clicked and topic and not queue_clicked:
        if not has_claude and providers["script_ai"] in ("claude_cli", "claude_api"):
            st.error(t("claude_required"))
        else:
            mode_full_label = t("mode_full")
            mode_video_label = t("mode_video")

            if mode == mode_full_label:
                cmd = ["run", "--news", topic, "--lang", lang,
                       "--format", video_format, "--duration", video_duration]
            elif mode == mode_video_label:
                cmd = ["run", "--news", topic, "--lang", lang, "--dry-run",
                       "--format", video_format, "--duration", video_duration]
            else:
                cmd = ["draft", "--news", topic, "--lang", lang,
                       "--format", video_format, "--duration", video_duration]

            if channel_ctx:
                cmd += ["--context", channel_ctx]

            # Add channel token path for upload
            if selected_channel and selected_channel.get("token_path"):
                cmd += ["--token-path", selected_channel["token_path"]]

            # Progress bar
            st.markdown("---")
            progress_bar = st.progress(0, text={"tr": "Başlatılıyor...", "en": "Starting..."}[st.session_state.lang])
            status_text = st.empty()

            stdout, stderr, code = run_pipeline_with_progress(
                cmd, progress_bar, status_text, st.session_state.lang,
            )

            if code == 0:
                st.success(t("prod_complete"))

                # If draft+video mode, run produce with progress too
                if mode == mode_video_label:
                    new_drafts = get_drafts()
                    if new_drafts:
                        produce_cmd = ["produce", "--draft", new_drafts[0]["_file"], "--lang", lang]
                        if force:
                            produce_cmd.append("--force")

                        progress_bar2 = st.progress(0, text={"tr": "Video üretimi başlıyor...", "en": "Video production starting..."}[st.session_state.lang])
                        status_text2 = st.empty()

                        stdout2, stderr2, code2 = run_pipeline_with_progress(
                            produce_cmd, progress_bar2, status_text2, st.session_state.lang,
                        )
                        if code2 == 0:
                            st.success(t("done"))
                        else:
                            st.error(t("pipeline_error"))
                            if stdout2:
                                st.code(stdout2, language="text")
            else:
                st.error(t("pipeline_error"))
                if stdout:
                    with st.expander("Log", expanded=True):
                        st.code(stdout, language="text")

    # ─────────────────────────────────────────────────────────
    # Batch CSV upload — Tier 1 #2
    # ─────────────────────────────────────────────────────────
    st.markdown("---")
    _batch_title = {"tr": "📦 Toplu Üretim (CSV)", "en": "📦 Batch Production (CSV)"}[st.session_state.lang]
    with st.expander(_batch_title, expanded=False):
        st.caption({
            "tr": "Bir CSV / TXT / Excel dosyasından birden fazla konuyu tek seferde kuyruğa ekle. Her satır bir video olur. Worker sırayla üretir ve sırayla yükler.",
            "en": "Add multiple topics from a CSV / TXT / Excel file at once. Each row becomes a video. Worker produces and uploads them sequentially.",
        }[st.session_state.lang])

        # Sample CSV explanation
        st.code(
            "topic,context,lang,format,duration,mode\n"
            "NASA yeni Ay görevini başlattı,Teknoloji haber kanalı,tr,shorts,short,full\n"
            "AI regülasyonu Avrupa'da imzalandı,,tr,shorts,short,full\n"
            "Tesla robotaxi lansmanı,,tr,video,3min,video",
            language="csv",
        )
        st.caption({
            "tr": "Minimum kolon: `topic`. Diğerleri atlanırsa üstteki form seçimleri kullanılır.",
            "en": "Minimum column: `topic`. Others fall back to the form selections above.",
        }[st.session_state.lang])

        batch_file = st.file_uploader(
            {"tr": "CSV / TXT / Excel dosyası", "en": "CSV / TXT / Excel file"}[st.session_state.lang],
            type=["csv", "txt", "xlsx", "xls"],
            key="batch_file",
        )

        # Manual paste alternative
        pasted = st.text_area(
            {"tr": "...veya buraya yapıştır (her satır bir konu veya CSV)",
             "en": "...or paste here (one topic per line, or CSV)"}[st.session_state.lang],
            height=120,
            key="batch_paste",
            placeholder="NASA yeni Ay görevini başlattı\nAI regülasyonu imzalandı\n...",
        )

        batch_rows: list[dict] = []
        parse_error = None

        def _parse_csv_rows(text: str) -> list[dict]:
            """Return list of dicts. Accepts full CSV header or raw lines."""
            import csv, io
            text = text.strip()
            if not text:
                return []
            # Detect if first line looks like a header
            first = text.splitlines()[0].lower()
            has_header = "topic" in first and "," in first
            if has_header:
                reader = csv.DictReader(io.StringIO(text))
                return [{k.strip(): (v or "").strip() for k, v in row.items() if k} for row in reader if any(row.values())]
            # Fallback: each non-empty line is a topic
            out = []
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Allow "topic,context" compact form
                parts = [p.strip() for p in line.split(",", 1)]
                out.append({"topic": parts[0], "context": parts[1] if len(parts) > 1 else ""})
            return out

        try:
            if batch_file is not None:
                name = batch_file.name.lower()
                if name.endswith((".csv", ".txt")):
                    raw = batch_file.read().decode("utf-8", errors="replace")
                    batch_rows = _parse_csv_rows(raw)
                elif name.endswith((".xlsx", ".xls")):
                    try:
                        import pandas as pd
                        df = pd.read_excel(batch_file)
                        batch_rows = df.to_dict("records")
                    except Exception as e:
                        parse_error = f"Excel okunamadı ({e}). pandas + openpyxl gerekli: pip install pandas openpyxl"
            elif pasted.strip():
                batch_rows = _parse_csv_rows(pasted)
        except Exception as e:
            parse_error = str(e)

        if parse_error:
            st.error(parse_error)

        if batch_rows:
            st.success({
                "tr": f"{len(batch_rows)} konu bulundu",
                "en": f"{len(batch_rows)} topics found",
            }[st.session_state.lang])

            # Preview table
            preview = []
            for i, row in enumerate(batch_rows[:20], 1):
                preview.append({
                    "#": i,
                    "Topic": str(row.get("topic", ""))[:80],
                    "Lang": (row.get("lang") or lang).lower(),
                    "Format": row.get("format") or video_format,
                    "Duration": row.get("duration") or video_duration,
                    "Mode": row.get("mode") or ("full" if mode == t("mode_full") else ("video" if mode == t("mode_video") else "draft")),
                })
            st.dataframe(preview, use_container_width=True, hide_index=True)
            if len(batch_rows) > 20:
                st.caption(f"... +{len(batch_rows) - 20} satır daha")

            batch_col1, batch_col2 = st.columns([2, 1])
            with batch_col1:
                batch_default_mode = st.selectbox(
                    {"tr": "Varsayılan Pipeline Modu (CSV'de belirtilmemişse)",
                     "en": "Default Pipeline Mode (if CSV row lacks it)"}[st.session_state.lang],
                    options=["full", "video", "draft"],
                    index=0,
                    key="batch_default_mode",
                )
            with batch_col2:
                batch_interval = st.number_input(
                    {"tr": "Her N saniyede 1 iş (0 = hemen hepsini)",
                     "en": "Stagger every N seconds (0 = all now)"}[st.session_state.lang],
                    min_value=0, max_value=3600, value=0, step=30,
                    key="batch_interval",
                    help={"tr": "API rate-limit yemeden sıralı ekleme için.",
                          "en": "Stagger enqueue to avoid rate limits."}[st.session_state.lang],
                )

            if st.button(
                {"tr": f"🚀 {len(batch_rows)} Videoyu Kuyruğa Ekle",
                 "en": f"🚀 Add {len(batch_rows)} Videos to Queue"}[st.session_state.lang],
                use_container_width=True, type="primary", key="batch_submit",
            ):
                import time as _t
                added = 0
                errors = 0
                progress_text = st.empty()
                bar = st.progress(0)
                channel_id = selected_channel.get("id") if selected_channel else None
                for i, row in enumerate(batch_rows, 1):
                    topic_i = str(row.get("topic", "")).strip()
                    if not topic_i:
                        continue
                    try:
                        enqueue_job(
                            topic=topic_i,
                            context=str(row.get("context") or channel_ctx or "").strip(),
                            lang=(row.get("lang") or lang).lower(),
                            mode=(row.get("mode") or batch_default_mode).lower(),
                            video_format=(row.get("format") or video_format).lower(),
                            duration=(row.get("duration") or video_duration).lower(),
                            channel=channel_id,
                        )
                        added += 1
                    except Exception as e:
                        errors += 1
                        progress_text.error(f"[{i}] {topic_i[:50]} — {e}")
                    bar.progress(i / len(batch_rows), text=f"{i}/{len(batch_rows)}")
                    if batch_interval > 0 and i < len(batch_rows):
                        _t.sleep(float(batch_interval))
                st.success({
                    "tr": f"✅ {added} iş kuyruğa eklendi. Hata: {errors}. Worker arkaplanda çalışıyor — Kuyruk sayfasından takip edebilirsin.",
                    "en": f"✅ {added} jobs queued. Errors: {errors}. Worker running in background — see the Queue page.",
                }[st.session_state.lang])


# =====================================================================
# QUEUE PAGE
# =====================================================================
elif page == "Queue":
    from pipeline import queue as qmod

    _title = {"tr": "Üretim Kuyruğu", "en": "Production Queue"}[st.session_state.lang]
    st.markdown(f"""
    <div class="topbar">
        <div class="topbar-title">{_title}</div>
    </div>
    """, unsafe_allow_html=True)

    # Worker status bar
    worker_up = qmod.worker_running()
    counts = qmod.counts()
    active = counts.get("pending", 0) + counts.get("producing", 0) + counts.get("produced", 0) + counts.get("uploading", 0)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric({"tr": "Bekleyen", "en": "Pending"}[st.session_state.lang], counts.get("pending", 0))
    c2.metric({"tr": "Üretim", "en": "Producing"}[st.session_state.lang], counts.get("producing", 0))
    c3.metric({"tr": "Yükleme", "en": "Uploading"}[st.session_state.lang], counts.get("uploading", 0))
    c4.metric({"tr": "Tamamlanan", "en": "Done"}[st.session_state.lang], counts.get("done", 0))
    c5.metric({"tr": "Hata", "en": "Failed"}[st.session_state.lang], counts.get("failed", 0))

    # Stuck-job warning: in-flight status but no live worker = crashed previously
    stuck_count = counts.get("producing", 0) + counts.get("uploading", 0)
    if stuck_count > 0 and not worker_up:
        sc1, sc2 = st.columns([4, 1])
        with sc1:
            st.warning({
                "tr": f"⚠️ {stuck_count} iş 'üretim/yükleme' durumunda ama worker kapalı. Önceki çalışmadan takılı kalmış olabilir.",
                "en": f"⚠️ {stuck_count} job(s) marked 'producing/uploading' but worker is OFF. Likely stuck from previous crash.",
            }[st.session_state.lang])
        with sc2:
            if st.button({"tr": "🔄 Kuyruğa Geri Al", "en": "🔄 Requeue"}[st.session_state.lang],
                         use_container_width=True, key="recover_stuck"):
                from pipeline.worker import recover_stuck_jobs
                n = recover_stuck_jobs()
                ensure_worker_running()
                st.success({
                    "tr": f"{n} iş yeniden kuyruğa alındı, kaldığı yerden devam edecek.",
                    "en": f"{n} job(s) recovered — will resume from last completed stage.",
                }[st.session_state.lang])
                st.rerun()

    wc1, wc2, wc3 = st.columns([2, 1, 1])
    with wc1:
        _label = {"tr": "Worker durumu", "en": "Worker status"}[st.session_state.lang]
        _state = ("● ON", "var(--status-success)") if worker_up else ("○ OFF", "var(--status-error)")
        st.markdown(
            f'<div style="padding:0.75rem;background:var(--bg-card);border-radius:8px;">'
            f'<b>{_label}:</b> <span style="color:{_state[1]}">{_state[0]}</span></div>',
            unsafe_allow_html=True,
        )
    with wc2:
        if st.button({"tr": "Worker Başlat", "en": "Start Worker"}[st.session_state.lang],
                     use_container_width=True, disabled=worker_up):
            if ensure_worker_running():
                st.success({"tr": "Worker başladı", "en": "Worker started"}[st.session_state.lang])
                st.rerun()
    with wc3:
        if st.button({"tr": "Yenile", "en": "Refresh"}[st.session_state.lang], use_container_width=True):
            st.rerun()

    st.divider()

    # Job list
    jobs = qmod.list_jobs()
    if not jobs:
        st.info({"tr": "Kuyruk boş. Pipeline sayfasından yeni üretim ekleyebilirsin.",
                 "en": "Queue is empty. Add a production from the Pipeline page."}[st.session_state.lang])
    else:
        # Show active jobs first, then recent finished
        active_jobs   = [j for j in jobs if j["status"] in ("pending", "producing", "produced", "uploading")]
        finished_jobs = [j for j in jobs if j["status"] in ("done", "failed", "cancelled")]
        finished_jobs = sorted(finished_jobs, key=lambda j: j.get("updated_at", ""), reverse=True)[:20]

        status_colors = {
            "pending":   "var(--status-warning)",
            "producing": "var(--status-info)",
            "produced":  "var(--status-info)",
            "uploading": "var(--status-info)",
            "done":      "var(--status-success)",
            "failed":    "var(--status-error)",
            "cancelled": "var(--text-dim)",
        }
        status_labels_tr = {"pending": "Bekliyor", "producing": "Üretiliyor", "produced": "Üretildi",
                            "uploading": "Yükleniyor", "done": "Tamamlandı", "failed": "Hata", "cancelled": "İptal"}

        if active_jobs:
            st.markdown(f"### {'Aktif' if st.session_state.lang == 'tr' else 'Active'}")
            for j in active_jobs:
                with st.container(border=True):
                    top1, top2, top3 = st.columns([4, 2, 1])
                    with top1:
                        st.markdown(f"**{j['topic']}**")
                        st.caption(f"`{j['id']}` · {j['lang'].upper()} · {j['format']} · {j['duration']} · {j['mode']}")
                    with top2:
                        col = status_colors.get(j["status"], "var(--text-dim)")
                        lbl = status_labels_tr.get(j["status"], j["status"]) if st.session_state.lang == "tr" else j["status"]
                        st.markdown(f'<div style="color:{col};font-weight:600">{lbl}</div>',
                                    unsafe_allow_html=True)
                        st.caption(j.get("stage") or "")
                    with top3:
                        if st.button("⛔", key=f"cancel_{j['id']}", help="Iptal et / Cancel"):
                            qmod.cancel_job(j["id"])
                            st.rerun()
                    pct = int(j.get("progress_pct", 0))
                    st.progress(max(pct, 0) / 100.0, text=f"{pct}%")
                    if j.get("log_tail"):
                        with st.expander({"tr": "Log", "en": "Log"}[st.session_state.lang]):
                            st.code("\n".join(j["log_tail"][-20:]), language="text")

        if finished_jobs:
            st.markdown(f"### {'Geçmiş' if st.session_state.lang == 'tr' else 'Recent'}")

            # Retry from stage labels
            _retry_stages_tr = {
                "upload":     "Sadece yüklemeyi tekrar dene",
                "thumbnail":  "Thumbnail'dan itibaren tekrar",
                "assemble":   "Videoyu birleştirmeden itibaren",
                "music":      "Müzikten itibaren",
                "captions":   "Altyazıdan itibaren",
                "voiceover":  "Seslendirmeden itibaren",
                "broll":      "Görsellerden itibaren (pahalı)",
                "draft":      "Script'ten itibaren (her şey)",
            }
            _retry_stages_en = {
                "upload":     "Retry upload only",
                "thumbnail":  "From thumbnail onward",
                "assemble":   "From assembly onward",
                "music":      "From music onward",
                "captions":   "From captions onward",
                "voiceover":  "From voiceover onward",
                "broll":      "From visuals (costly)",
                "draft":      "From script (full rerun)",
            }
            _retry_labels = _retry_stages_tr if st.session_state.lang == "tr" else _retry_stages_en

            for j in finished_jobs:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([4, 2, 1])
                    col1.markdown(f"**{j['topic'][:80]}**")
                    col1.caption(f"`{j['id']}` · {j['lang'].upper()} · {j['format']} · {j.get('updated_at','')[:19].replace('T',' ')}")
                    clr = status_colors.get(j["status"], "var(--text-dim)")
                    lbl = status_labels_tr.get(j["status"], j["status"]) if st.session_state.lang == "tr" else j["status"]
                    col2.markdown(f'<span style="color:{clr};font-weight:600">{lbl}</span>',
                                  unsafe_allow_html=True)
                    if j.get("error"):
                        col2.caption(f"⚠ {str(j['error'])[:80]}")
                    if col3.button("🗑", key=f"del_{j['id']}", use_container_width=True,
                                   help="Delete / Sil"):
                        qmod.delete_job(j["id"])
                        st.rerun()

                    # Retry controls — only show for failed/cancelled or when draft exists
                    can_retry = j["status"] in ("failed", "cancelled") or (
                        j["status"] == "done" and j.get("draft_path")
                    )
                    if can_retry:
                        rc1, rc2 = st.columns([3, 1])
                        with rc1:
                            stage_choice = st.selectbox(
                                {"tr": "Tekrar deneme noktası:",
                                 "en": "Retry from stage:"}[st.session_state.lang],
                                options=list(_retry_labels.keys()),
                                format_func=lambda k: _retry_labels[k],
                                index=0,
                                key=f"retry_stage_{j['id']}",
                                label_visibility="collapsed",
                            )
                        with rc2:
                            if st.button({"tr": "🔁 Tekrar Dene", "en": "🔁 Retry"}[st.session_state.lang],
                                         key=f"retry_{j['id']}", use_container_width=True):
                                qmod.retry_job(j["id"], from_stage=stage_choice)
                                ensure_worker_running()
                                st.success({"tr": "Kuyruğa geri alındı", "en": "Requeued"}[st.session_state.lang])
                                st.rerun()

            if st.button({"tr": "Geçmişi Temizle", "en": "Clear History"}[st.session_state.lang]):
                for j in finished_jobs:
                    qmod.delete_job(j["id"])
                st.rerun()


# =====================================================================
# DRAFTS PAGE — Script Editor (Tier 2 #12)
# =====================================================================
elif page == "Drafts":
    import json as _json
    from pipeline.config import DRAFTS_DIR

    _title = {"tr": "✏️ Draftlar · Script Editörü", "en": "✏️ Drafts · Script Editor"}[st.session_state.lang]
    st.markdown(f'<div class="topbar"><div class="topbar-title">{_title}</div></div>', unsafe_allow_html=True)
    st.caption({
        "tr": "Claude'un ürettiği draftları düzenle, manuel güncelle veya AI ile yeniden üret. Değişiklikler kaydedilince sonraki üretimde kullanılır.",
        "en": "Edit Claude-generated drafts manually or regenerate with AI. Changes are applied on next production run.",
    }[st.session_state.lang])

    all_drafts = sorted(DRAFTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True) if DRAFTS_DIR.exists() else []

    if not all_drafts:
        st.info({"tr": "Henüz draft yok. Pipeline sayfasından bir üretim başlat.",
                 "en": "No drafts yet. Start a production from the Pipeline page."}[st.session_state.lang])
    else:
        # Build draft selector — show title + job_id + status
        draft_options = []
        draft_data = {}
        for p in all_drafts[:50]:
            try:
                d = _json.loads(p.read_text(encoding="utf-8"))
                if not d.get("script"):
                    continue
                job_id = str(d.get("job_id", p.stem))
                title = (d.get("youtube_title") or d.get("news") or "Untitled")[:60]
                state = d.get("_pipeline_state", {})
                done = sum(1 for v in state.values() if isinstance(v, dict) and v.get("status") == "done")
                upload_done = isinstance(state.get("upload"), dict) and state["upload"].get("status") == "done"
                status_icon = "✅" if upload_done else ("🎬" if done >= 7 else ("📝" if done >= 2 else "⭕"))
                label = f"{status_icon}  {title}  ·  PRD-{job_id[-4:]}  ({done}/9)"
                draft_options.append(label)
                draft_data[label] = (p, d)
            except Exception:
                continue

        if not draft_options:
            st.info({"tr": "Okunabilir draft bulunamadı.", "en": "No readable drafts."}[st.session_state.lang])
        else:
            sel = st.selectbox(
                {"tr": "Düzenlenecek Draft", "en": "Select draft to edit"}[st.session_state.lang],
                options=draft_options,
                key="draft_editor_sel",
            )
            draft_path, draft = draft_data[sel]

            st.divider()

            # Meta row
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric({"tr": "Job ID", "en": "Job ID"}[st.session_state.lang], f"PRD-{str(draft.get('job_id',''))[-4:]}")
            mc2.metric({"tr": "Dil", "en": "Lang"}[st.session_state.lang], (draft.get("lang") or "?").upper())
            mc3.metric({"tr": "Format", "en": "Format"}[st.session_state.lang], draft.get("format", "?"))
            mc4.metric({"tr": "Süre", "en": "Duration"}[st.session_state.lang], draft.get("duration", "?"))

            # Form
            with st.form(f"script_edit_{draft_path.stem}"):
                new_title = st.text_input(
                    {"tr": "📺 YouTube Başlığı", "en": "📺 YouTube Title"}[st.session_state.lang],
                    value=draft.get("youtube_title", ""),
                    max_chars=100,
                )
                new_script = st.text_area(
                    {"tr": "🎙️ Script (Seslendirme Metni)", "en": "🎙️ Script (Voiceover Text)"}[st.session_state.lang],
                    value=draft.get("script", ""),
                    height=280,
                    help={"tr": "Kelime sayısı: gerçek süreyi belirler (~2.5 kelime/sn).",
                          "en": "Word count drives duration (~2.5 words/s)."}[st.session_state.lang],
                )
                word_count = len(new_script.split())
                est_sec = word_count / 2.5
                st.caption(f"📊 {word_count} kelime · ~{est_sec:.0f} saniye")

                new_desc = st.text_area(
                    {"tr": "📝 Açıklama", "en": "📝 Description"}[st.session_state.lang],
                    value=draft.get("youtube_description", ""),
                    height=100,
                )
                new_tags = st.text_input(
                    {"tr": "🏷️ Etiketler (virgülle)", "en": "🏷️ Tags (comma-separated)"}[st.session_state.lang],
                    value=draft.get("youtube_tags", ""),
                )

                # B-roll prompts — one per line
                existing_brolls = draft.get("broll_prompts", [])
                broll_text = "\n".join(existing_brolls) if isinstance(existing_brolls, list) else str(existing_brolls)
                new_broll = st.text_area(
                    {"tr": "🎨 B-roll Görsel Prompt'ları (her satır bir görsel)",
                     "en": "🎨 B-roll Image Prompts (one per line)"}[st.session_state.lang],
                    value=broll_text,
                    height=160,
                )

                new_thumb_prompt = st.text_area(
                    {"tr": "🖼️ Thumbnail Prompt", "en": "🖼️ Thumbnail Prompt"}[st.session_state.lang],
                    value=draft.get("thumbnail_prompt", ""),
                    height=70,
                )

                fc1, fc2, fc3 = st.columns(3)
                save_clicked = fc1.form_submit_button(
                    {"tr": "💾 Değişiklikleri Kaydet", "en": "💾 Save Changes"}[st.session_state.lang],
                    use_container_width=True, type="primary",
                )
                regen_script_clicked = fc2.form_submit_button(
                    {"tr": "🤖 Script'i Yeniden Üret (AI)", "en": "🤖 Regenerate Script (AI)"}[st.session_state.lang],
                    use_container_width=True,
                )
                requeue_clicked = fc3.form_submit_button(
                    {"tr": "🚀 Bu Draft'la Video Üret", "en": "🚀 Produce Video From This Draft"}[st.session_state.lang],
                    use_container_width=True,
                )

            # Actions
            if save_clicked:
                # Update in-memory draft
                draft["youtube_title"] = new_title
                draft["script"] = new_script
                draft["youtube_description"] = new_desc
                draft["youtube_tags"] = new_tags
                draft["thumbnail_prompt"] = new_thumb_prompt
                draft["broll_prompts"] = [line.strip() for line in new_broll.splitlines() if line.strip()]

                # Invalidate downstream state — they need regeneration if script changed
                ps = draft.setdefault("_pipeline_state", {})
                script_changed = new_script != draft_data[sel][1].get("script", "")
                if script_changed:
                    for stg in ("voiceover", "whisper", "captions", "music", "assemble", "upload"):
                        ps.pop(stg, None)
                broll_changed = draft["broll_prompts"] != draft_data[sel][1].get("broll_prompts", [])
                if broll_changed:
                    for stg in ("broll", "assemble", "upload"):
                        ps.pop(stg, None)

                draft_path.write_text(_json.dumps(draft, indent=2, ensure_ascii=False), encoding="utf-8")
                st.success({
                    "tr": f"✅ Kaydedildi. {'Script değiştiği için sonraki üretimde voice/caption/assemble yeniden yapılacak.' if script_changed else ''}",
                    "en": f"✅ Saved. {'Script changed → voice/caption/assemble will regenerate on next produce.' if script_changed else ''}",
                }[st.session_state.lang])
                st.rerun()

            if regen_script_clicked:
                with st.spinner({"tr": "AI ile yeniden üretiliyor...", "en": "Regenerating with AI..."}[st.session_state.lang]):
                    try:
                        from pipeline.draft import _call_script_ai as _ai_call
                        news = draft.get("news") or new_title
                        lang_code = draft.get("lang", "en")
                        # Build a lighter regeneration prompt — keep structure, rewrite body
                        regen_prompt = f"""Rewrite this YouTube video script while keeping the topic, tone and format.
Topic: {news}
Language: {lang_code}
Target duration: {draft.get('duration', 'short')}

Current script to improve:
---
{new_script}
---

Provide a new version of the script only (no JSON, no markdown fences, no preamble)."""
                        new_draft_script = _ai_call(regen_prompt).strip()
                        # Strip markdown fences if the model added them
                        if new_draft_script.startswith("```"):
                            new_draft_script = new_draft_script.split("```", 2)[1]
                            if new_draft_script.startswith("text\n"):
                                new_draft_script = new_draft_script[5:]
                        draft["script"] = new_draft_script.strip()
                        # Invalidate downstream
                        ps = draft.setdefault("_pipeline_state", {})
                        for stg in ("voiceover", "whisper", "captions", "music", "assemble", "upload"):
                            ps.pop(stg, None)
                        draft_path.write_text(_json.dumps(draft, indent=2, ensure_ascii=False), encoding="utf-8")
                        st.success({
                            "tr": "🤖 Script yeniden üretildi. Aşağıdaki formda gör.",
                            "en": "🤖 Script regenerated. See above.",
                        }[st.session_state.lang])
                        st.rerun()
                    except Exception as e:
                        st.error(f"AI regenerate failed: {e}")

            if requeue_clicked:
                # Create a new queue job pointing at this draft (skips draft stage)
                job = enqueue_job(
                    topic=draft.get("news") or new_title,
                    context=draft.get("context") or "",
                    lang=draft.get("lang", "tr"),
                    mode="video",
                    video_format=draft.get("format", "shorts"),
                    duration=draft.get("duration", "short"),
                    draft_path=str(draft_path),
                )
                st.success({
                    "tr": f"🚀 Kuyruğa eklendi: {job['id']} — bu draft kullanılarak video üretilecek.",
                    "en": f"🚀 Queued: {job['id']} — producing video from this draft.",
                }[st.session_state.lang])


# =====================================================================
# COMMENTS MODERATOR PAGE (Tier 2 #10)
# =====================================================================
elif page == "Comments":
    from pipeline import comment_moderator as cm

    _ctitle = {"tr": "💬 Yorum Moderatörü", "en": "💬 Comment Moderator"}[st.session_state.lang]
    st.markdown(f'<div class="topbar"><div class="topbar-title">{_ctitle}</div></div>',
                unsafe_allow_html=True)
    st.caption({
        "tr": "Son yüklenen videolardaki yorumları AI ile sınıflandır, spamı gizle, soruları panelde topla.",
        "en": "Classify recent video comments with AI — hide spam, collect questions in the inbox.",
    }[st.session_state.lang])

    _connected = [c for c in get_channels() if c.get("connected")]
    if not _connected:
        st.info({"tr": "Bağlı kanal yok. Önce Ayarlar'dan kanal OAuth'u yap.",
                 "en": "No connected channels. Set up channel OAuth in Settings first."}[st.session_state.lang])
    else:
        # Channel picker + refresh
        cpc1, cpc2, cpc3 = st.columns([3, 1, 1])
        with cpc1:
            ch_idx = 0
            if len(_connected) > 1:
                ch_idx = [c["name"] for c in _connected].index(
                    st.selectbox({"tr": "Kanal", "en": "Channel"}[st.session_state.lang],
                                 [c["name"] for c in _connected], key="mod_ch_sel")
                )
            sel_ch = _connected[ch_idx]
        with cpc2:
            use_llm = st.checkbox(
                {"tr": "AI sınıflandırma", "en": "LLM classify"}[st.session_state.lang],
                value=True, help={"tr": "Kapalıysa regex kurallarıyla hızlı sınıflandırma.",
                                    "en": "If off, falls back to regex heuristics."}[st.session_state.lang],
            )
        with cpc3:
            fetch_clicked = st.button(
                {"tr": "🔄 Yorumları Çek", "en": "🔄 Fetch Comments"}[st.session_state.lang],
                use_container_width=True, type="primary", key="mod_fetch_btn",
            )

        if fetch_clicked:
            with st.spinner({"tr": "Yorumlar çekiliyor ve sınıflandırılıyor...",
                             "en": "Fetching + classifying comments..."}[st.session_state.lang]):
                try:
                    res = cm.process_new(
                        token_path=sel_ch["token_path"],
                        channel=sel_ch["id"],
                        use_llm=use_llm,
                    )
                    st.success(
                        {"tr": f"✅ {res['new']} yeni · {res['skipped']} zaten vardı · {res.get('total_fetched', 0)} toplam",
                         "en": f"✅ {res['new']} new · {res['skipped']} already seen · {res.get('total_fetched', 0)} total"}[st.session_state.lang]
                    )
                except Exception as e:
                    st.error(f"Fetch failed: {e}")

        # Category tabs
        st.divider()
        ch_counts = cm.counts(days=14, channel=sel_ch["id"])
        total = sum(ch_counts.values())

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric({"tr": "Sorular", "en": "Questions"}[st.session_state.lang], ch_counts.get("question", 0))
        mc2.metric({"tr": "Teşekkürler", "en": "Thanks"}[st.session_state.lang], ch_counts.get("thanks", 0))
        mc3.metric({"tr": "Spam", "en": "Spam"}[st.session_state.lang], ch_counts.get("spam", 0))
        mc4.metric({"tr": "Tartışma", "en": "Discussion"}[st.session_state.lang], ch_counts.get("discussion", 0))

        tab_titles_tr = ["❓ Sorular", "🙏 Teşekkürler", "🚫 Spam", "💬 Tartışma"]
        tab_titles_en = ["❓ Questions", "🙏 Thanks", "🚫 Spam", "💬 Discussion"]
        tab_titles = tab_titles_tr if st.session_state.lang == "tr" else tab_titles_en
        tabs = st.tabs(tab_titles)

        for tab, cat in zip(tabs, ["question", "thanks", "spam", "discussion"]):
            with tab:
                items = [c for c in cm.inbox(category=cat, channel=sel_ch["id"], limit=50)
                         if c.get("action") != "handled"]
                if not items:
                    st.caption({"tr": "Bu kategoride yorum yok.",
                                "en": "No comments in this category."}[st.session_state.lang])
                    continue
                for it in items:
                    with st.container(border=True):
                        hc1, hc2 = st.columns([5, 1])
                        hc1.markdown(f"**{it['author']}** · `{it['published_at'][:10]}`")
                        hc1.write(it["text"])
                        confidence_pct = int((it.get("confidence") or 0) * 100)
                        hc1.caption(f"📊 {confidence_pct}% güven · 📺 [video](https://youtu.be/{it['video_id']})")
                        # Actions
                        ac1, ac2, ac3 = hc2.columns(3) if False else (hc2, hc2, hc2)
                        if cat == "spam":
                            if hc2.button("🚫", key=f"hide_{it['id']}", help="Gizle",
                                          use_container_width=True):
                                if cm.hide_comment(it["id"], sel_ch["token_path"]):
                                    st.success("Gizlendi")
                                    st.rerun()
                                else:
                                    st.error("Gizleme başarısız")
                        if hc2.button("✅", key=f"mark_{it['id']}",
                                      help={"tr": "Halledildi", "en": "Handled"}[st.session_state.lang],
                                      use_container_width=True):
                            cm.mark_handled(it["id"])
                            st.rerun()


# =====================================================================
# TOOLS PAGE — Tier 4 feature hub
# =====================================================================
elif page == "Tools":
    _title = {"tr": "🧰 Araçlar · Enterprise Özellikler",
              "en": "🧰 Tools · Enterprise Features"}[st.session_state.lang]
    st.markdown(f'<div class="topbar"><div class="topbar-title">{_title}</div></div>',
                unsafe_allow_html=True)

    tab_names_tr = ["📰 Haber Watcher", "🎯 Rakip Takibi", "🎙️ Ses Klonu",
                    "🎨 LoRA Eğitim", "🌐 Çoklu Dil", "🛡️ Watermark",
                    "🎬 Demo", "⏰ Zamanlayıcı", "💰 Gelir",
                    "📱 QR Mobil", "🤖 Telegram Bot"]
    tab_names_en = ["📰 News Watcher", "🎯 Competitors", "🎙️ Voice Clone",
                    "🎨 LoRA Training", "🌐 Translate", "🛡️ Watermark",
                    "🎬 Demo", "⏰ Scheduler", "💰 Revenue",
                    "📱 QR Mobile", "🤖 Telegram Bot"]
    tabs = st.tabs(tab_names_tr if st.session_state.lang == "tr" else tab_names_en)

    # ─── Tab 1: News Watcher ─────────────────────────────────
    with tabs[0]:
        try:
            from pipeline import news_watcher as nw
            st.caption({
                "tr": "RSS feed'leri izle, anahtar kelime eşleşince otomatik kuyruğa at.",
                "en": "Monitor RSS feeds; auto-queue jobs when keywords match.",
            }[st.session_state.lang])

            # Add new feed
            with st.form("nw_add_feed", clear_on_submit=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    new_url = st.text_input(
                        "RSS URL", placeholder="https://hnrss.org/frontpage",
                    )
                    new_kws = st.text_input(
                        {"tr": "Anahtar kelimeler (virgülle, boş=hepsi)",
                         "en": "Keywords (comma, empty=all)"}[st.session_state.lang],
                    )
                with c2:
                    new_name = st.text_input(
                        {"tr": "İsim", "en": "Name"}[st.session_state.lang],
                    )
                    new_auto = st.checkbox(
                        {"tr": "Auto-queue", "en": "Auto-queue"}[st.session_state.lang],
                        value=False,
                    )
                if st.form_submit_button(
                    {"tr": "+ Feed Ekle", "en": "+ Add Feed"}[st.session_state.lang],
                    type="primary", use_container_width=True,
                ) and new_url.strip():
                    nw.add_feed(new_url.strip(), name=new_name.strip(),
                                keywords=new_kws.strip(), auto_queue=new_auto)
                    st.success({"tr": "Eklendi", "en": "Added"}[st.session_state.lang])
                    st.rerun()

            # Feed list
            feeds = nw.list_feeds()
            if feeds:
                st.markdown(f"**{'Kayıtlı Feedler' if st.session_state.lang == 'tr' else 'Registered Feeds'}**")
                for f in feeds:
                    with st.container(border=True):
                        fc1, fc2, fc3, fc4 = st.columns([3, 2, 1, 1])
                        fc1.markdown(f"**{f['name']}**  ")
                        fc1.caption(f"🔗 {f['url'][:60]}")
                        fc2.caption(f"🔑 {f['keywords'] or '(hepsi)'}")
                        fc2.caption(f"🤖 auto-queue: {'✓' if f['auto_queue'] else '✗'}")
                        if fc3.button("🔄", key=f"scan_{f['id']}", help="Tara"):
                            with st.spinner("..."):
                                r = nw.scan_feed(f["id"])
                            st.success(f"{r.get('new_matches', 0)} yeni match")
                            st.rerun()
                        if fc4.button("🗑", key=f"rm_{f['id']}"):
                            nw.remove_feed(f["id"])
                            st.rerun()

                # Inbox
                inbox = nw.inbox(matched_only=True, limit=20)
                if inbox:
                    st.markdown(f"**{'Son Eşleşmeler' if st.session_state.lang == 'tr' else 'Recent Matches'}**")
                    for e in inbox:
                        em_col1, em_col2 = st.columns([5, 1])
                        em_col1.markdown(f"📌 **{e['title'][:90]}**")
                        em_col1.caption(f"`{e['feed_name']}` · {e['published_at'][:10]}")
                        if e.get("queued_job_id"):
                            em_col2.caption(f"✅ {e['queued_job_id'][-6:]}")
                        elif em_col2.button("🚀", key=f"enq_{e['id']}", help="Kuyruğa at"):
                            from pipeline import queue as qmod
                            job = qmod.enqueue(topic=e["title"], lang="tr", mode="full")
                            st.success(f"Queued: {job['id']}")
                            st.rerun()

            # Telegram config
            with st.expander({"tr": "🔔 Telegram/Webhook Bildirimleri",
                              "en": "🔔 Telegram/Webhook Notifications"}[st.session_state.lang]):
                cfg = nw._load_notify_config()
                with st.form("nw_notify"):
                    tg_token = st.text_input("Telegram Bot Token",
                                              value=cfg.get("telegram_bot_token", ""),
                                              type="password")
                    tg_chat = st.text_input("Telegram Chat ID",
                                             value=cfg.get("telegram_chat_id", ""))
                    webhook = st.text_input("Webhook URL",
                                             value=cfg.get("webhook_url", ""))
                    bc1, bc2 = st.columns(2)
                    save_notify = bc1.form_submit_button(
                        "💾 Kaydet", use_container_width=True, type="primary",
                    )
                    test_tg = bc2.form_submit_button(
                        "📤 Telegram Test", use_container_width=True,
                    )
                if save_notify:
                    nw.save_notify_config({
                        "telegram_bot_token": tg_token.strip(),
                        "telegram_chat_id": tg_chat.strip(),
                        "webhook_url": webhook.strip(),
                    })
                    st.success("Kaydedildi")
                if test_tg and tg_token and tg_chat:
                    res = nw.send_telegram_test(tg_token.strip(), tg_chat.strip())
                    if res.get("ok"):
                        st.success("✅ Telegram'a mesaj gitti")
                    else:
                        st.error(f"Hata: {res}")
        except Exception as e:
            st.error(f"News watcher error: {e}")

    # ─── Tab 2: Competitor Tracker ────────────────────────────
    with tabs[1]:
        try:
            from pipeline import competitor_tracker as ct
            st.caption({
                "tr": "Rakip kanalları izle, topic gap analizi ile yapmadığın konuları bul.",
                "en": "Track competitor channels, find topic gaps from their top performers.",
            }[st.session_state.lang])

            with st.form("ct_add_channel", clear_on_submit=True):
                cc1, cc2, cc3 = st.columns([3, 2, 1])
                new_cid = cc1.text_input("YouTube Channel ID (UC...)",
                                          placeholder="UC_AAAAAAAAAAAAAAAAAAAAAAAAA")
                new_cname = cc2.text_input({"tr": "İsim", "en": "Name"}[st.session_state.lang])
                cc3.markdown("&nbsp;", unsafe_allow_html=True)
                if cc3.form_submit_button(
                    "+ Ekle", use_container_width=True, type="primary",
                ) and new_cid.strip().startswith("UC"):
                    ct.add_channel(new_cid.strip(), name=new_cname.strip())
                    st.success("Eklendi")
                    st.rerun()

            # Scan button (requires API key)
            api_key = config.get("GEMINI_API_KEY") or config.get("YOUTUBE_DATA_API_KEY", "")
            channels = ct.list_channels()
            if channels:
                sc1, sc2 = st.columns([3, 1])
                sc1.markdown(f"**{len(channels)} rakip kanal kayıtlı**")
                if sc2.button({"tr": "🔄 Hepsini Tara", "en": "🔄 Scan All"}[st.session_state.lang],
                              use_container_width=True,
                              disabled=not api_key):
                    with st.spinner("Taranıyor..."):
                        results = ct.scan_all(api_key)
                    ok = sum(1 for r in results if "error" not in r)
                    st.success(f"{ok}/{len(results)} kanal tarandı")
                    st.rerun()

                if not api_key:
                    st.info({
                        "tr": "YouTube Data API key (Gemini API key de kullanılabilir) gerekli. Ayarlar'dan ekle.",
                        "en": "Needs YouTube Data API key (Gemini key works too). Set it in Settings.",
                    }[st.session_state.lang])

                # Top performers
                top = ct.top_performers(days=30, limit=10)
                if top:
                    st.markdown(f"**{'Son 30g Top 10' if st.session_state.lang == 'tr' else 'Last 30d Top 10'}**")
                    import pandas as pd
                    df_top = pd.DataFrame([{
                        "Başlık" if st.session_state.lang == "tr" else "Title": v["title"][:60],
                        "İzlenme" if st.session_state.lang == "tr" else "Views": f"{v['views']:,}",
                        "Beğeni" if st.session_state.lang == "tr" else "Likes": f"{v['likes']:,}",
                        "Yorum" if st.session_state.lang == "tr" else "Comments": f"{v['comments']:,}",
                    } for v in top])
                    st.dataframe(df_top, use_container_width=True, hide_index=True)

                # Topic gaps
                gaps = ct.topic_gaps(days=30, similarity_threshold=0.4, limit=10)
                if gaps:
                    st.markdown(f"**🎯 {'Topic Fırsatları' if st.session_state.lang == 'tr' else 'Topic Opportunities'}**")
                    st.caption({
                        "tr": "Rakiplerin yaptığı ama senin yapmadığın konular — AI buraya bakmanı öneriyor.",
                        "en": "Topics competitors cover but you haven't — AI flagged these.",
                    }[st.session_state.lang])
                    for g in gaps:
                        gc1, gc2 = st.columns([5, 1])
                        gc1.markdown(f"💡 **{g['competitor_title'][:80]}** — {g['views']:,} izlenme")
                        if gc2.button("🚀", key=f"gap_enq_{g['video_id']}", help="Kuyruğa at"):
                            from pipeline import queue as qmod
                            job = qmod.enqueue(topic=g["competitor_title"], lang="tr", mode="full")
                            st.success(f"Queued: {job['id']}")
                            st.rerun()

                # Channel list + remove
                with st.expander({"tr": "Kanalları Yönet",
                                  "en": "Manage Channels"}[st.session_state.lang]):
                    for c in channels:
                        mc1, mc2, mc3 = st.columns([3, 2, 1])
                        mc1.markdown(f"**{c['name']}**")
                        mc1.caption(c["channel_id"])
                        stats = ct.channel_stats(c["channel_id"], days=30)
                        mc2.caption(f"🎬 {stats['video_count']} video · Ø {stats['avg_views']:,}")
                        if mc3.button("🗑", key=f"ct_rm_{c['channel_id']}"):
                            ct.remove_channel(c["channel_id"])
                            st.rerun()
        except Exception as e:
            st.error(f"Competitor tracker error: {e}")

    # ─── Tab 3: Voice Clone ───────────────────────────────────
    with tabs[2]:
        try:
            from pipeline import voice_clone as vc
            st.caption({
                "tr": "ElevenLabs Instant Voice Cloning: 30-90 saniyelik sesle kendi kopyasını üret.",
                "en": "ElevenLabs Instant Voice Cloning: 30-90s sample → your cloned voice.",
            }[st.session_state.lang])

            # Account info
            acc_info = vc.account_info()
            if "error" not in acc_info:
                ac1, ac2, ac3 = st.columns(3)
                ac1.metric({"tr": "Plan", "en": "Tier"}[st.session_state.lang],
                           acc_info.get("tier", "?"))
                limit = acc_info.get("character_limit") or 0
                used = acc_info.get("character_count") or 0
                ac2.metric({"tr": "Karakter Kullanımı", "en": "Chars Used"}[st.session_state.lang],
                           f"{used:,} / {limit:,}")
                ac3.metric({"tr": "Cloning", "en": "Cloning"}[st.session_state.lang],
                           "✅" if acc_info.get("can_use_instant_voice_cloning") else "❌")

            # Upload form
            with st.form("vc_clone", clear_on_submit=True):
                vname = st.text_input({"tr": "Ses Adı", "en": "Voice Name"}[st.session_state.lang])
                vdesc = st.text_area({"tr": "Açıklama", "en": "Description"}[st.session_state.lang],
                                      height=70)
                vchannels = get_channels()
                vch_id = None
                if vchannels:
                    picked = st.selectbox(
                        {"tr": "İlişkili Kanal (ops.)", "en": "Link to channel (opt.)"}[st.session_state.lang],
                        ["(none)"] + [c["id"] for c in vchannels],
                        format_func=lambda x: x if x == "(none)" else
                            next((c["name"] for c in vchannels if c["id"] == x), x),
                    )
                    vch_id = None if picked == "(none)" else picked
                vsample = st.file_uploader(
                    {"tr": "Ses Örneği (30-90 sn, mp3/wav)",
                     "en": "Voice Sample (30-90s, mp3/wav)"}[st.session_state.lang],
                    type=["mp3", "wav", "m4a", "ogg"],
                )
                if st.form_submit_button(
                    {"tr": "🎤 Sesi Klonla", "en": "🎤 Clone Voice"}[st.session_state.lang],
                    type="primary", use_container_width=True,
                ) and vname and vsample:
                    with st.spinner("ElevenLabs'e gönderiliyor..."):
                        r = vc.clone_instant(
                            name=vname, sample_bytes=vsample.read(),
                            sample_filename=vsample.name,
                            description=vdesc, channel_id=vch_id,
                        )
                    if r.get("voice_id"):
                        st.success(f"✅ Voice ID: `{r['voice_id']}` — TTS sağlayıcısında kullanabilirsin")
                    else:
                        st.error(f"Hata: {r.get('error')}")

            # Existing voices
            voices = vc.list_cloned_voices()
            if voices:
                st.markdown(f"**{'Kayıtlı Klonlar' if st.session_state.lang == 'tr' else 'Registered Clones'}**")
                for v in voices:
                    with st.container(border=True):
                        vc1, vc2, vc3 = st.columns([4, 2, 1])
                        vc1.markdown(f"**{v['name']}**")
                        vc1.caption(f"`{v['voice_id']}`")
                        vc2.caption(f"Kanal: {v.get('channel_id') or '-'} · {v.get('mode', 'instant')}")
                        vc2.caption(f"Örnek: {v.get('sample_size_bytes', 0) // 1024} KB")
                        if vc3.button("🗑", key=f"vc_rm_{v['voice_id']}"):
                            vc.delete_voice(v["voice_id"], delete_remote=True)
                            st.rerun()
        except Exception as e:
            st.error(f"Voice clone error: {e}")

    # ─── Tab 4: LoRA Training ─────────────────────────────────
    with tabs[3]:
        try:
            from pipeline import lora_training as lt
            st.caption({
                "tr": "10-20 karakter/stil görseli yükle → Replicate eğitir → tutarlı görsel üretimi için LoRA.",
                "en": "Upload 10-20 character/style images → Replicate trains → LoRA for consistent visuals.",
            }[st.session_state.lang])

            with st.form("lt_start", clear_on_submit=True):
                lc1, lc2 = st.columns(2)
                with lc1:
                    lname = st.text_input(
                        {"tr": "İsim (ör. 'Mascot V1')",
                         "en": "Name (e.g. 'Mascot V1')"}[st.session_state.lang],
                    )
                    ltrigger = st.text_input(
                        {"tr": "Trigger kelime (prompt'ta geçecek)",
                         "en": "Trigger word (used in prompts)"}[st.session_state.lang],
                        placeholder="MYCHAR_V1",
                    )
                with lc2:
                    lbase = st.selectbox(
                        {"tr": "Temel Model", "en": "Base Model"}[st.session_state.lang],
                        list(lt.SUPPORTED_BASE_MODELS.keys()),
                        format_func=lambda k: lt.SUPPORTED_BASE_MODELS[k]["desc"],
                    )
                    lsteps = st.slider(
                        {"tr": "Training Step", "en": "Training Steps"}[st.session_state.lang],
                        min_value=500, max_value=3000,
                        value=lt.SUPPORTED_BASE_MODELS[lbase]["steps_default"],
                        step=100,
                    )
                limages = st.file_uploader(
                    {"tr": "Görseller (10-20 adet, png/jpg)",
                     "en": "Images (10-20 files, png/jpg)"}[st.session_state.lang],
                    type=["png", "jpg", "jpeg"],
                    accept_multiple_files=True,
                )
                cost_est = lt.SUPPORTED_BASE_MODELS[lbase]["typical_cost_usd"]
                st.caption(f"💰 Tahmini maliyet: ${cost_est:.2f} (Replicate faturalandırır)")
                if st.form_submit_button(
                    {"tr": "🚀 Eğitimi Başlat", "en": "🚀 Start Training"}[st.session_state.lang],
                    type="primary", use_container_width=True,
                ):
                    if not limages or len(limages) < 5:
                        st.error("En az 5 görsel gerekli (10-20 ideal)")
                    elif not lname or not ltrigger:
                        st.error("İsim ve trigger kelime zorunlu")
                    else:
                        img_bytes = [f.read() for f in limages]
                        r = lt.start_training(
                            name=lname, trigger_word=ltrigger,
                            images=img_bytes, base_model=lbase, steps=lsteps,
                        )
                        if r.get("job_id"):
                            st.success(f"🎨 Training başlatıldı · ID={r['job_id']}")
                            st.info("20-60 dakika sürebilir · worker arka planda poll ediyor")
                        else:
                            st.error(f"Hata: {r.get('error')}")

            # Running / completed jobs
            trainings = lt.list_trainings(limit=20)
            if trainings:
                st.markdown(f"**{'Eğitim Geçmişi' if st.session_state.lang == 'tr' else 'Training History'}**")
                for tr in trainings:
                    icon = {"running": "⏳", "succeeded": "✅",
                            "failed": "❌", "canceled": "🚫", "pending": "⏸"}.get(tr["status"], "?")
                    with st.container(border=True):
                        tc1, tc2, tc3 = st.columns([4, 2, 1])
                        tc1.markdown(f"{icon} **{tr['name']}** · `{tr['trigger_word']}`")
                        tc1.caption(f"Model: {tr['base_model']} · Steps: {tr['steps']} · Görsel: {tr['image_count']}")
                        tc2.caption(f"Durum: `{tr['status']}`")
                        if tr["lora_url"]:
                            tc2.caption(f"💾 [weights]({tr['lora_url']})")
                        if tr["cost_usd"]:
                            tc2.caption(f"💰 ${tr['cost_usd']:.2f}")
                        if tr["status"] == "running":
                            if tc3.button("🔄", key=f"poll_{tr['id']}", help="Poll"):
                                lt.poll_training(tr["id"])
                                st.rerun()
        except Exception as e:
            st.error(f"LoRA training error: {e}")

    # ─── Tab 5: Auto-translation ──────────────────────────────
    with tabs[4]:
        try:
            from pipeline import auto_translate as at
            from pipeline.config import DRAFTS_DIR
            import json as _json
            st.caption({
                "tr": "1 video → N dil → N kanal fan-out. Claude ile çevirir, produce'a gönderir.",
                "en": "One video → N languages → N channels. Claude translates, re-produces.",
            }[st.session_state.lang])

            # Source draft picker — only produced drafts
            all_drafts = sorted(DRAFTS_DIR.glob("*.json"),
                                key=lambda p: p.stat().st_mtime, reverse=True) if DRAFTS_DIR.exists() else []
            valid_drafts = []
            for p in all_drafts[:30]:
                try:
                    d = _json.loads(p.read_text(encoding="utf-8"))
                    if d.get("script") and d.get("_pipeline_state", {}).get("broll", {}).get("status") == "done":
                        valid_drafts.append((p, d))
                except Exception:
                    continue

            if not valid_drafts:
                st.info({"tr": "Çevirmek için önce en az 1 üretim yapılmış draft olmalı.",
                         "en": "You need at least one produced draft to translate."}[st.session_state.lang])
            else:
                with st.form("at_fan_out"):
                    sel_idx = st.selectbox(
                        {"tr": "Kaynak Draft",
                         "en": "Source Draft"}[st.session_state.lang],
                        range(len(valid_drafts)),
                        format_func=lambda i: f"{valid_drafts[i][1].get('youtube_title', '')[:50]} · {valid_drafts[i][1].get('lang', '?')}",
                    )
                    src_path, src_draft = valid_drafts[sel_idx]
                    src_lang = src_draft.get("lang", "?")
                    st.caption(f"Kaynak dil: **{src_lang}**")

                    # Target langs — multiselect
                    all_langs = list(at.SUPPORTED_LANGS.keys())
                    if src_lang in all_langs:
                        all_langs.remove(src_lang)
                    targets = st.multiselect(
                        {"tr": "Hedef Diller", "en": "Target Languages"}[st.session_state.lang],
                        options=all_langs,
                        format_func=lambda x: f"{x.upper()} · {at.SUPPORTED_LANGS[x]}",
                    )

                    # Channel mapping — optional
                    st.markdown(f"**{'Dil → Kanal eşlemesi (opsiyonel)' if st.session_state.lang == 'tr' else 'Language → Channel mapping (optional)'}**")
                    lang_channel_map = {}
                    chans = get_channels()
                    chan_ids = [""] + [c["id"] for c in chans]
                    for lang in targets:
                        picked = st.selectbox(
                            f"{lang.upper()}",
                            chan_ids,
                            format_func=lambda x: x or "(none)",
                            key=f"at_ch_{lang}",
                        )
                        if picked:
                            lang_channel_map[lang] = picked

                    if st.form_submit_button(
                        {"tr": "🌐 Fan-out Başlat", "en": "🌐 Start Fan-out"}[st.session_state.lang],
                        type="primary", use_container_width=True,
                        disabled=not targets,
                    ):
                        with st.spinner("Çeviriliyor..."):
                            r = at.fan_out(
                                source_draft_path=str(src_path),
                                target_langs=targets,
                                lang_channel_map=lang_channel_map or None,
                                video_format=src_draft.get("format", "shorts"),
                                duration=src_draft.get("duration", "short"),
                            )
                        if r.get("queued_jobs"):
                            st.success(f"✅ {len(r['queued_jobs'])} yeni üretim kuyruğa eklendi")
                            if r.get("errors"):
                                st.warning(f"Hatalar: {r['errors']}")
                        else:
                            st.error(f"Fan-out başarısız: {r.get('errors', r.get('error'))}")

                # History
                history = at.history(limit=10)
                if history:
                    with st.expander({"tr": "🕒 Geçmiş Fan-out'lar",
                                      "en": "🕒 Past Fan-outs"}[st.session_state.lang]):
                        for h in history:
                            st.caption(
                                f"{h['ts'][:19].replace('T', ' ')} · "
                                f"{h['source_lang']} → {' '.join(h['target_langs'])} · "
                                f"{len(h['queued_jobs'])} job"
                            )
        except Exception as e:
            st.error(f"Auto-translate error: {e}")

    # ─── Tab 6: Watermark / Reupload detection ────────────────
    with tabs[5]:
        try:
            from pipeline import watermark as wm
            st.caption({
                "tr": "Ürettiğin videoların audio parmak izini kaydet, başka kanallarda re-upload edilip edilmediğini kontrol et.",
                "en": "Register your videos' audio fingerprints; check if re-uploaded elsewhere.",
            }[st.session_state.lang])

            # Register from existing produced videos
            with st.expander({"tr": "📼 Üretilen Videoyu Kaydet",
                              "en": "📼 Register Produced Video"}[st.session_state.lang]):
                from pipeline.config import MEDIA_DIR
                video_files = sorted(MEDIA_DIR.glob("*.mp4"),
                                     key=lambda p: p.stat().st_mtime, reverse=True)[:20] if MEDIA_DIR.exists() else []
                if not video_files:
                    st.caption({"tr": "Üretilmiş video yok", "en": "No produced videos"}[st.session_state.lang])
                else:
                    picked = st.selectbox(
                        {"tr": "Video seç", "en": "Pick video"}[st.session_state.lang],
                        video_files, format_func=lambda p: p.name,
                    )
                    reg_label = st.text_input(
                        {"tr": "Etiket (ops.)", "en": "Label (opt.)"}[st.session_state.lang],
                    )
                    if st.button({"tr": "📌 Parmak İzi Al + Kaydet",
                                  "en": "📌 Fingerprint + Register"}[st.session_state.lang],
                                 type="primary", use_container_width=True):
                        with st.spinner("ffmpeg ile parmak izi hesaplanıyor..."):
                            vid = picked.stem
                            r = wm.register(vid, str(picked), label=reg_label or picked.stem)
                        if r.get("ok"):
                            st.success(f"✅ Kaydedildi: {vid} ({r['method']})")
                        else:
                            st.error(f"Hata: {r.get('error')}")

            # Check suspect
            with st.expander({"tr": "🔍 Şüpheli Videoyu Kontrol Et",
                              "en": "🔍 Check Suspect Video"}[st.session_state.lang]):
                suspect = st.file_uploader(
                    {"tr": "Kontrol edilecek video", "en": "Video to check"}[st.session_state.lang],
                    type=["mp4", "mov", "webm"],
                )
                threshold = st.slider(
                    {"tr": "Benzerlik eşiği (%)", "en": "Similarity threshold (%)"}[st.session_state.lang],
                    min_value=50, max_value=99, value=85, step=5,
                )
                if suspect and st.button(
                    {"tr": "🛡️ Kontrol Et", "en": "🛡️ Check"}[st.session_state.lang],
                    type="primary", use_container_width=True,
                ):
                    # Save upload temporarily
                    import tempfile as _tf
                    with _tf.NamedTemporaryFile(delete=False, suffix=Path(suspect.name).suffix) as tf:
                        tf.write(suspect.read())
                        tmp_path = tf.name
                    with st.spinner("Parmak izi hesaplanıyor + karşılaştırılıyor..."):
                        r = wm.check_against_registry(
                            tmp_path, threshold=threshold / 100.0,
                            source_url=suspect.name,
                        )
                    best = r.get("best_match")
                    if best and r.get("above_threshold"):
                        st.error(f"⚠️ KOPYAL ŞÜPHESİ: **{best['video_id']}** ile %{best['similarity']*100:.0f} eşleşme")
                    elif best:
                        st.success(f"✅ Eşleşme yok (en yüksek {best['video_id']} ile %{best['similarity']*100:.0f})")
                    else:
                        st.info({"tr": "Kayıtlı parmak izi yok — önce video kaydet.",
                                 "en": "No registered fingerprints yet."}[st.session_state.lang])

            # Recent checks
            matches = wm.recent_matches(limit=10)
            if matches:
                st.markdown(f"**{'Son Kontroller' if st.session_state.lang == 'tr' else 'Recent Checks'}**")
                import pandas as pd
                df = pd.DataFrame([{
                    "Zaman": m["checked_at"][:19].replace("T", " "),
                    "URL/Dosya": (m["checked_url"] or m["checked_file"])[:40],
                    "Eşleşti": m["matched_video_id"],
                    "%": f"{m['similarity']*100:.0f}%",
                } for m in matches])
                st.dataframe(df, use_container_width=True, hide_index=True)

            st.caption({
                "tr": "💡 Parmak izi ffmpeg'in chromaprint filtresi veya audio digest ile alınır.",
                "en": "💡 Fingerprints via ffmpeg chromaprint or audio digest.",
            }[st.session_state.lang])
        except Exception as e:
            st.error(f"Watermark error: {e}")

    # ─── Tab 7: Demo Mode (Closing #25) ───────────────────────
    with tabs[6]:
        try:
            from pipeline import demo_mode
            st.caption({
                "tr": "Sunum için tek tıkla demo üretim — ucuz sağlayıcılar, hızlı çıkış.",
                "en": "One-click demo production for sales calls — cheap providers, quick output.",
            }[st.session_state.lang])

            safe = demo_mode.is_demo_preset_safe()
            if not safe["safe"]:
                st.warning(f"Demo preset uyarı: {safe['issues']}")

            dc1, dc2 = st.columns([3, 1])
            demo_lang = dc1.selectbox(
                {"tr": "Dil", "en": "Language"}[st.session_state.lang],
                ["tr", "en"],
                format_func=lambda x: {"tr": "Türkçe", "en": "English"}[x],
            )
            dc2.markdown("&nbsp;", unsafe_allow_html=True)

            preview_topic = demo_mode.pick_random_topic(demo_lang)
            st.info(f"🎲 Rastgele konu önizleme: **{preview_topic}**")

            custom_topic = st.text_input(
                {"tr": "Veya kendi konunu yaz",
                 "en": "Or write your own topic"}[st.session_state.lang],
            )
            if st.button(
                {"tr": "🎬 DEMO BAŞLAT (30 saniye)",
                 "en": "🎬 START DEMO (30 seconds)"}[st.session_state.lang],
                type="primary", use_container_width=True,
            ):
                r = demo_mode.start_demo(
                    topic=custom_topic.strip() or None, lang=demo_lang,
                )
                ensure_worker_running()
                st.success(f"🚀 Demo iş kuyrukta: `{r['job_id']}` — `{r['topic'][:60]}`")
                st.info("💡 Kuyruk sayfasına geç ve ilerlemeyi göster")
        except Exception as e:
            st.error(f"Demo error: {e}")

    # ─── Tab 8: Scheduler (Closing #27 gece modu) ─────────────
    with tabs[7]:
        try:
            from pipeline import scheduler as sch
            st.caption({
                "tr": "Cron benzeri zamanlayıcı — sabah 09'da, 12'de, 18'de otomatik üretim.",
                "en": "Cron-like scheduler — auto-produce at 09:00, 12:00, 18:00.",
            }[st.session_state.lang])

            # Add new schedule
            with st.form("sch_add", clear_on_submit=True):
                sc1, sc2 = st.columns(2)
                with sc1:
                    s_name = st.text_input({"tr": "İsim", "en": "Name"}[st.session_state.lang])
                    s_kind = st.selectbox(
                        {"tr": "Tip", "en": "Type"}[st.session_state.lang],
                        ["cron", "burst", "daily_topic_pool"],
                        format_func=lambda k: {
                            "cron": "Cron (belirli saatlerde)",
                            "burst": "Burst (anlık N video)",
                            "daily_topic_pool": "Günlük havuz rotasyonu",
                        }[k],
                    )
                    s_hours = st.text_input(
                        {"tr": "Saatler (virgülle, UTC, ör. 09:00,12:00,18:00)",
                         "en": "Hours (comma-sep, UTC)"}[st.session_state.lang],
                    )
                with sc2:
                    s_lang = st.selectbox("Lang", ["tr", "en", "de", "hi"])
                    s_mode = st.selectbox("Mode", ["full", "video", "draft"])
                    s_count = st.number_input(
                        {"tr": "Burst sayısı", "en": "Burst count"}[st.session_state.lang],
                        min_value=1, max_value=20, value=3,
                    )
                s_topics = st.text_area(
                    {"tr": "Konular (her satırda bir)",
                     "en": "Topics (one per line)"}[st.session_state.lang],
                    height=120,
                )
                if st.form_submit_button(
                    {"tr": "+ Zamanlayıcı Ekle", "en": "+ Add Schedule"}[st.session_state.lang],
                    type="primary", use_container_width=True,
                ):
                    topics = [t.strip() for t in s_topics.splitlines() if t.strip()]
                    hours = [h.strip() for h in s_hours.split(",") if h.strip()]
                    if topics and (s_kind != "cron" or hours):
                        sch.create_schedule(
                            name=s_name or "Unnamed", kind=s_kind, topics=topics,
                            hours_utc=hours, count_per_burst=int(s_count),
                            lang=s_lang, mode=s_mode,
                        )
                        st.success("Eklendi")
                        st.rerun()

            # List + run buttons
            schs = sch.list_schedules()
            if schs:
                st.markdown(f"**{'Aktif Zamanlayıcılar' if st.session_state.lang == 'tr' else 'Active Schedules'}**")
                for s in schs:
                    with st.container(border=True):
                        rc1, rc2, rc3, rc4 = st.columns([3, 2, 1, 1])
                        on_icon = "🟢" if s["enabled"] else "⚪"
                        rc1.markdown(f"{on_icon} **{s['name']}** · `{s['kind']}`")
                        if s["kind"] == "cron":
                            rc1.caption(f"⏰ UTC {', '.join(s.get('hours_utc', []))}")
                        rc1.caption(f"📝 {len(s['topics'])} konu · fired: {s.get('fired_count', 0)}")
                        rc2.caption(f"Son: {(s.get('last_fired_at') or '-')[:19]}")
                        if s["kind"] in ("burst", "daily_topic_pool"):
                            if rc3.button("▶", key=f"fire_{s['id']}", help="Şimdi çalıştır"):
                                r = sch.run_burst(s["id"])
                                st.success(f"{len(r.get('queued', []))} iş kuyrukta")
                                ensure_worker_running()
                                st.rerun()
                        toggle_label = "⏸" if s["enabled"] else "▶"
                        if rc3.button(toggle_label, key=f"toggle_{s['id']}"):
                            sch.toggle_schedule(s["id"], not s["enabled"])
                            st.rerun()
                        if rc4.button("🗑", key=f"sch_rm_{s['id']}"):
                            sch.delete_schedule(s["id"])
                            st.rerun()
        except Exception as e:
            st.error(f"Scheduler error: {e}")

    # ─── Tab 9: Revenue estimate (Closing #29) ────────────────
    with tabs[8]:
        try:
            from pipeline import revenue_estimate as rev
            st.caption({
                "tr": "YouTube AdSense gelir tahmini — niche + audience country CPM bazlı.",
                "en": "YouTube AdSense revenue estimation — niche + audience country CPM.",
            }[st.session_state.lang])

            rc1, rc2 = st.columns(2)
            with rc1:
                niche = st.selectbox(
                    {"tr": "Niche (video kategorisi)",
                     "en": "Niche (video category)"}[st.session_state.lang],
                    list(rev.CPM_BY_NICHE.keys()),
                )
                country = st.selectbox(
                    {"tr": "Audience ülke", "en": "Audience country"}[st.session_state.lang],
                    list(rev.COUNTRY_MULTIPLIER.keys()),
                )
            with rc2:
                views = st.number_input(
                    {"tr": "Video başı izlenme",
                     "en": "Views per video"}[st.session_state.lang],
                    min_value=100, max_value=100_000_000,
                    value=50_000, step=1000,
                )
                dur = st.slider(
                    {"tr": "Süre (saniye)", "en": "Duration (sec)"}[st.session_state.lang],
                    min_value=15, max_value=1800, value=180,
                )

            est = rev.estimate(views=views, niche=niche, country=country,
                                duration_sec=dur)
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric(
                {"tr": "Efektif CPM", "en": "Effective CPM"}[st.session_state.lang],
                f"${est['cpm_usd']}",
            )
            mc2.metric(
                {"tr": "Monetize İzlenme", "en": "Monetized Views"}[st.session_state.lang],
                f"{est['monetized_views']:,}",
            )
            mc3.metric(
                {"tr": "Tahmini Gelir",
                 "en": "Estimated Earnings"}[st.session_state.lang],
                f"${est['earnings_usd']}",
            )
            if est["is_short"]:
                st.warning({
                    "tr": "⚠️ Shorts (60 sn altı) — pre-roll ad yok, Shorts Fund/rev-share daha düşük.",
                    "en": "⚠️ Shorts (<60s) — no pre-roll, Shorts Fund/rev-share is lower.",
                }[st.session_state.lang])

            st.divider()
            # Monthly forecast
            st.markdown(f"**{'Aylık Projeksiyon' if st.session_state.lang == 'tr' else 'Monthly Forecast'}**")
            fc1, fc2 = st.columns(2)
            vids_per_month = fc1.number_input(
                {"tr": "Ay başına video", "en": "Videos per month"}[st.session_state.lang],
                min_value=1, max_value=500, value=30,
            )
            fc2.markdown("&nbsp;", unsafe_allow_html=True)
            forecast = rev.forecast_monthly(
                videos_per_month=vids_per_month,
                avg_views_per_video=views,
                niche=niche, country=country, duration_sec=dur,
            )
            pc1, pc2, pc3 = st.columns(3)
            pc1.metric("Video/ay", vids_per_month)
            pc2.metric(
                {"tr": "Aylık Gelir", "en": "Monthly Revenue"}[st.session_state.lang],
                f"${forecast['monthly_earnings_usd']}",
            )
            pc3.metric(
                {"tr": "Yıllık Gelir", "en": "Annual Revenue"}[st.session_state.lang],
                f"${forecast['annual_earnings_usd']}",
            )
        except Exception as e:
            st.error(f"Revenue error: {e}")

    # ─── Tab 10: QR Mobile Preview (Closing #26) ──────────────
    with tabs[9]:
        try:
            from pipeline import qr_preview
            st.caption({
                "tr": "Mobil önizleme ve paylaşım için QR kod — tara, telefonunda aç.",
                "en": "QR codes for mobile preview + sharing — scan and open on phone.",
            }[st.session_state.lang])

            if not qr_preview.has_qrcode_lib():
                st.warning({
                    "tr": "QR kütüphanesi yok: `pip install qrcode[pil]`",
                    "en": "QR library not installed: `pip install qrcode[pil]`",
                }[st.session_state.lang])

            qr_mode = st.radio(
                {"tr": "Ne için QR?", "en": "QR for what?"}[st.session_state.lang],
                ["job", "video", "custom_url"],
                format_func=lambda x: {"job": "Belirli bir iş (panel üzerinden)",
                                         "video": "YouTube video",
                                         "custom_url": "Özel URL"}[x],
                horizontal=True,
            )

            if qr_mode == "job":
                from pipeline import queue as qmod
                recent_jobs = qmod.list_jobs()[-10:] if qmod.list_jobs() else []
                if not recent_jobs:
                    st.info("İş yok")
                else:
                    picked = st.selectbox(
                        {"tr": "İş", "en": "Job"}[st.session_state.lang],
                        recent_jobs, format_func=lambda j: f"{j['id'][-10:]} · {j['topic'][:40]}",
                    )
                    base = st.text_input("Base URL", value="https://retube.rewmarket.com")
                    if picked:
                        r = qr_preview.qr_for_job(picked["id"], base)
                        st.code(r["target_url"])
                        if r["data_uri"]:
                            st.markdown(f'<img src="{r["data_uri"]}" width="200"/>',
                                        unsafe_allow_html=True)

            elif qr_mode == "video":
                url = st.text_input("YouTube URL", placeholder="https://youtu.be/...")
                if url:
                    r = qr_preview.qr_for_video(url)
                    if r["data_uri"]:
                        st.markdown(f'<img src="{r["data_uri"]}" width="200"/>',
                                    unsafe_allow_html=True)

            else:
                url = st.text_input("URL")
                if url:
                    png = qr_preview.generate_qr_png(url)
                    if png:
                        uri = qr_preview.as_data_uri(png)
                        st.markdown(f'<img src="{uri}" width="200"/>',
                                    unsafe_allow_html=True)
        except Exception as e:
            st.error(f"QR error: {e}")

    # ─── Tab 11: Telegram Bot (Closing #28) ───────────────────
    with tabs[10]:
        try:
            from pipeline import telegram_bot
            st.caption({
                "tr": "Telegram üzerinden bot ile iş oluştur, durum takip et.",
                "en": "Create jobs + check status via Telegram bot.",
            }[st.session_state.lang])

            st.markdown(f"**{'Bot Kurulumu' if st.session_state.lang == 'tr' else 'Bot Setup'}**")
            st.markdown("""
1. Telegram'da `@BotFather` ile yeni bot oluştur → token al
2. Botuna `/start` yaz, `@userinfobot` üzerinden user ID'ni bul
3. Aşağıya token ve izinli user ID'leri gir
4. "Botu Başlat" ile bağlan
""")

            bot_token = st.text_input(
                "Bot Token", type="password",
                value=config.get("TELEGRAM_BOT_TOKEN", ""),
            )
            allowed_ids_str = st.text_input(
                {"tr": "İzinli User ID'ler (virgülle)",
                 "en": "Allowed User IDs (comma)"}[st.session_state.lang],
                value=config.get("TELEGRAM_ALLOWED_USERS", ""),
            )

            bc1, bc2 = st.columns(2)
            if bc1.button({"tr": "💾 Token Kaydet",
                           "en": "💾 Save Token"}[st.session_state.lang],
                          use_container_width=True):
                config["TELEGRAM_BOT_TOKEN"] = bot_token.strip()
                config["TELEGRAM_ALLOWED_USERS"] = allowed_ids_str.strip()
                save_config(config)
                st.success("Kaydedildi")
            if bc2.button({"tr": "▶ Botu Başlat (bu session)",
                           "en": "▶ Start Bot (this session)"}[st.session_state.lang],
                          use_container_width=True, type="primary",
                          disabled=not bot_token):
                allowed = []
                if allowed_ids_str:
                    try:
                        allowed = [int(x.strip()) for x in allowed_ids_str.split(",") if x.strip()]
                    except Exception:
                        st.error("User ID'ler integer olmalı")
                        allowed = None
                if allowed is not None:
                    th, stop = telegram_bot.start_background(bot_token.strip(), allowed or None)
                    st.session_state["tg_bot_stop"] = stop
                    st.success(f"🤖 Bot başladı · izinli: {len(allowed)} user")

            st.divider()
            st.markdown(f"**{'Komutlar' if st.session_state.lang == 'tr' else 'Commands'}**")
            st.code("""/start     — karşılama + yardım
/yap <konu> — yeni video üret (örn: /yap NASA Artemis)
/durum [id] — kuyruk durumu veya tek iş
/iptal <id> — işi iptal et
/kuyruk     — son 10 iş listesi
/stat       — bugün + ay harcama özeti""", language="text")
        except Exception as e:
            st.error(f"Telegram bot error: {e}")


# =====================================================================
# MANUAL PRODUCTION PAGE
# =====================================================================
elif page == "Manual":
    st.markdown(f"""
    <div class="topbar">
        <div class="topbar-title">{t("manual_prod")}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"<p style='color: var(--text-dim); margin-bottom: 1.5rem;'>{t('manual_desc')}</p>",
                unsafe_allow_html=True)

    mcol1, mcol2 = st.columns([2, 1])

    with mcol1:
        manual_script = st.text_area(
            t("script_input"),
            placeholder=t("script_placeholder"),
            height=250,
            key="manual_script",
        )

        # YouTube metadata
        manual_title = st.text_input("YouTube Title", placeholder="Video başlığı", key="manual_title")
        manual_desc = st.text_input("YouTube Description", placeholder="Video açıklaması", key="manual_desc_input")
        manual_tags = st.text_input("Tags", placeholder="tag1,tag2,tag3", key="manual_tags")

    with mcol2:
        # Format & Duration
        m_format = st.selectbox(
            t("video_format"),
            ["shorts", "video"],
            format_func=lambda x: t("format_shorts") if x == "shorts" else t("format_video"),
            key="manual_format",
        )
        m_lang = st.selectbox(
            t("language"), ["en", "de", "tr", "hi"],
            format_func=lambda x: {"en": "English", "de": "Deutsch", "tr": "Türkçe", "hi": "Hindi"}[x],
            key="manual_lang",
        )

        # Number of visual prompts
        num_prompts = st.number_input(t("num_visuals"), min_value=1, max_value=25, value=6, key="num_prompts")

    # Visual prompts
    st.markdown(f"### {t('broll_prompts_label')}")
    st.caption("Her görsel için İngilizce prompt girin. AI bu prompt'lara göre görsel/video üretecek.")

    if "manual_prompts" not in st.session_state:
        st.session_state.manual_prompts = [""] * 6

    # Adjust prompt list to match num_prompts
    while len(st.session_state.manual_prompts) < num_prompts:
        st.session_state.manual_prompts.append("")
    st.session_state.manual_prompts = st.session_state.manual_prompts[:num_prompts]

    prompt_cols = st.columns(2)
    for i in range(num_prompts):
        with prompt_cols[i % 2]:
            st.session_state.manual_prompts[i] = st.text_input(
                f"Prompt {i+1}",
                value=st.session_state.manual_prompts[i],
                placeholder=t("broll_prompt_ph"),
                key=f"mprompt_{i}",
            )

    st.markdown("---")

    if st.button(t("manual_start"), use_container_width=True, disabled=not manual_script):
        if not manual_script.strip():
            st.error(t("no_script"))
        else:
            import json as _json

            # Build draft JSON manually
            fmt_cfg = {"shorts": {"width": 1080, "height": 1920}, "video": {"width": 1920, "height": 1080}}
            job_id = str(int(time.time()))

            # Filter empty prompts, fill with defaults
            broll_prompts = [p.strip() for p in st.session_state.manual_prompts if p.strip()]
            if not broll_prompts:
                broll_prompts = ["Cinematic landscape"] * num_prompts

            draft = {
                "job_id": job_id,
                "news": manual_title or "Manual Production",
                "script": manual_script.strip(),
                "broll_prompts": broll_prompts,
                "youtube_title": manual_title or "Untitled",
                "youtube_description": manual_desc or "",
                "youtube_tags": manual_tags or "",
                "instagram_caption": "",
                "thumbnail_prompt": broll_prompts[0] if broll_prompts else "",
                "research": "",
                "format": m_format,
                "duration": "short",
                "_pipeline_state": {
                    "research": {"status": "done", "timestamp": "manual"},
                    "draft": {"status": "done", "timestamp": "manual"},
                },
            }

            # Save draft
            DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
            draft_path = DRAFTS_DIR / f"{job_id}.json"
            draft_path.write_text(_json.dumps(draft, indent=2, ensure_ascii=False), encoding="utf-8")
            st.success(f"Taslak kaydedildi: PRD-{job_id[-4:]}")

            # Run produce with progress
            produce_cmd = ["produce", "--draft", str(draft_path), "--lang", m_lang]

            st.markdown("---")
            progress_bar = st.progress(0, text={"tr": "Üretim başlıyor...", "en": "Starting production..."}[st.session_state.lang])
            status_text = st.empty()

            stdout, stderr, code = run_pipeline_with_progress(
                produce_cmd, progress_bar, status_text, st.session_state.lang,
            )

            if code == 0:
                st.success(t("prod_complete"))

                # Ask about upload
                if st.button(t("upload"), key="manual_upload"):
                    upload_cmd = ["upload", "--draft", str(draft_path), "--lang", m_lang]
                    with st.spinner(t("uploading")):
                        out, err, ucode = run_pipeline_command(upload_cmd)
                        if ucode == 0:
                            st.success(out)
                        else:
                            st.error(err[:300])
            else:
                st.error(t("pipeline_error"))
                if stdout:
                    with st.expander("Log", expanded=True):
                        st.code(stdout, language="text")


# =====================================================================
# TRENDS PAGE
# =====================================================================
elif page == "Trends":
    st.markdown(f"""
    <div class="topbar">
        <div class="topbar-title">{t("trending_topics")}</div>
    </div>
    """, unsafe_allow_html=True)

    # Country selection
    countries = {
        "TR": "Türkiye",
        "DE": "Almanya / Deutschland",
        "GB": "İngiltere / United Kingdom",
        "US": "Amerika / United States",
        "ES": "İspanya / España",
        "IT": "İtalya / Italia",
    }

    tcol1, tcol2 = st.columns([2, 1])
    with tcol1:
        selected_country = st.selectbox(
            "Ülke / Country",
            list(countries.keys()),
            format_func=lambda x: f"{'🇹🇷' if x=='TR' else '🇩🇪' if x=='DE' else '🇬🇧' if x=='GB' else '🇺🇸' if x=='US' else '🇪🇸' if x=='ES' else '🇮🇹'} {countries[x]}",
            key="trend_country",
        )
    with tcol2:
        limit = st.slider(t("results_limit"), 5, 30, 15, key="trend_limit")

    if st.button(t("discover"), use_container_width=True):
        with st.spinner(t("searching")):
            cmd = ["topics", "--limit", str(limit), "--region", selected_country]
            stdout, stderr, code = run_pipeline_command(cmd)
            if code == 0 and stdout:
                # Parse and display nicely
                lines = stdout.strip().split("\n")
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("Trending") or line.startswith("No"):
                        st.markdown(f"**{line}**")
                    elif line[0:1].isdigit():
                        # Extract topic info
                        st.markdown(f"""
                        <div style="background: var(--bg-card); border: 1px solid var(--border-subtle);
                                    border-radius: 10px; padding: 0.8rem 1rem; margin-bottom: 0.5rem;
                                    transition: border-color 0.2s ease;">
                            <span style="color: var(--text-bright); font-weight: 500;">{line}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    elif line.startswith("  "):
                        st.caption(line.strip())
            elif stderr:
                st.warning(stderr[:300])


# =====================================================================
# VIDEOS PAGE
# =====================================================================
elif page == "Videos":
    st.markdown(f"""
    <div class="topbar">
        <div class="topbar-title">{t("produced_videos")}</div>
    </div>
    """, unsafe_allow_html=True)

    if not videos:
        st.info(t("no_videos"))
    else:
        for v in videos:
            with st.expander(v.name):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.video(str(v))
                with c2:
                    mb = v.stat().st_size / (1024 * 1024)
                    st.metric(t("size"), f"{mb:.1f} MB")


# =====================================================================
# HISTORY PAGE
# =====================================================================
elif page == "History":
    st.markdown(f"""
    <div class="topbar">
        <div class="topbar-title">{t("prod_history")}</div>
    </div>
    """, unsafe_allow_html=True)

    for d in drafts:
        job_id = d.get("job_id", "?")
        title = d.get("youtube_title", d.get("news", "Untitled"))
        state = d.get("_pipeline_state", {})

        with st.expander(f"{title} (PRD-{str(job_id)[-4:]})"):
            col1, col2 = st.columns([2, 1])

            with col1:
                script = d.get("script", "")
                if script:
                    st.text_area("Script", value=script[:500], height=120, key=f"s_{job_id}", disabled=True)
                broll = d.get("broll_prompts", [])
                if broll:
                    for i, p in enumerate(broll, 1):
                        st.caption(f"B-Roll {i}: {p}")

            with col2:
                stage_names = ["research", "draft", "broll", "voiceover", "captions", "music", "assemble", "thumbnail", "upload"]
                for sn in stage_names:
                    entry = state.get(sn, {})
                    s = entry.get("status", "pending")
                    ic = {"done": "●", "failed": "●", "pending": "○"}.get(s, "○")
                    cl = {"done": "var(--status-success)", "failed": "var(--status-error)", "pending": "var(--text-ghost)"}.get(s, "var(--text-ghost)")
                    st.markdown(f'<span style="color:{cl}">{ic}</span> {sn.capitalize()}', unsafe_allow_html=True)

            # Actions
            bc1, bc2, bc3, bc4 = st.columns(4)
            with bc1:
                if st.button(t("produce"), key=f"p_{job_id}", use_container_width=True):
                    with st.spinner(t("producing")):
                        out, err, code = run_pipeline_command(["produce", "--draft", d["_file"], "--lang", "en"])
                        st.success(t("done")) if code == 0 else st.error(err[:200])
            with bc2:
                if st.button(t("upload"), key=f"u_{job_id}", use_container_width=True):
                    with st.spinner(t("uploading")):
                        out, err, code = run_pipeline_command(["upload", "--draft", d["_file"], "--lang", "en"])
                        st.success(out) if code == 0 else st.error(err[:200])
            with bc3:
                if st.button(t("force_redo_btn"), key=f"f_{job_id}", use_container_width=True):
                    with st.spinner(t("redoing")):
                        out, err, code = run_pipeline_command(["produce", "--draft", d["_file"], "--lang", "en", "--force"])
                        st.success(t("done")) if code == 0 else st.error(err[:200])
            with bc4:
                if st.button(t("delete"), key=f"del_{job_id}", use_container_width=True):
                    try:
                        Path(d["_file"]).unlink()
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))


# =====================================================================
# SETTINGS PAGE
# =====================================================================
elif page == "Settings":
    st.markdown(f"""
    <div class="topbar">
        <div class="topbar-title">{t("settings_title")}</div>
    </div>
    """, unsafe_allow_html=True)

    # --- Provider Selection ---
    from pipeline.config import PROVIDERS

    st.markdown(f"### {t('provider_selection')}")

    tier_labels = {
        "free": t("tier_free"),
        "cheapest": t("tier_cheapest"),
        "budget": t("tier_budget"),
        "mid": t("tier_mid"),
        "premium": t("tier_premium"),
    }

    def format_provider(key, category):
        p = PROVIDERS[category][key]
        cost = f"${p['cost_60s']:.3f}" if p['cost_60s'] > 0 else t("tier_free")
        tier = tier_labels.get(p["tier"], p["tier"])
        return f"{p['name']} — {cost} [{tier}]"

    # Script AI
    script_ai_keys = list(PROVIDERS["script_ai"].keys())
    current_script_ai = providers["script_ai"]
    script_ai_idx = script_ai_keys.index(current_script_ai) if current_script_ai in script_ai_keys else 0

    new_script = st.selectbox(
        t("script_ai"),
        script_ai_keys,
        index=script_ai_idx,
        format_func=lambda x: format_provider(x, "script_ai"),
        key="prov_script_ai",
    )

    # Image provider
    image_keys = list(PROVIDERS["image"].keys())
    current_image = providers["image"]
    image_idx = image_keys.index(current_image) if current_image in image_keys else 0

    new_image = st.selectbox(
        t("image_provider"),
        image_keys,
        index=image_idx,
        format_func=lambda x: format_provider(x, "image"),
        key="prov_image",
    )

    # Video provider
    video_keys = list(PROVIDERS["video"].keys())
    current_video = providers.get("video", "none")
    video_idx = video_keys.index(current_video) if current_video in video_keys else 0

    new_video = st.selectbox(
        t("video_provider"),
        video_keys,
        index=video_idx,
        format_func=lambda x: format_provider(x, "video"),
        key="prov_video",
    )

    # TTS provider
    tts_keys = list(PROVIDERS["tts"].keys())
    current_tts = providers["tts"]
    tts_idx = tts_keys.index(current_tts) if current_tts in tts_keys else 0

    new_tts = st.selectbox(
        t("tts_provider"),
        tts_keys,
        index=tts_idx,
        format_func=lambda x: format_provider(x, "tts"),
        key="prov_tts",
    )

    st.divider()

    # --- Cost Calculator ---
    script_cost = PROVIDERS["script_ai"][new_script]["cost_60s"]
    image_cost = PROVIDERS["image"][new_image]["cost_60s"]
    video_cost = PROVIDERS["video"][new_video]["cost_60s"]
    tts_cost = PROVIDERS["tts"][new_tts]["cost_60s"]
    total = script_cost + image_cost + video_cost + tts_cost

    st.markdown(f"### {t('cost_calculator')}")
    st.markdown(f"""
<div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 14px; padding: 1.5rem;">
    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
        <span style="color: var(--text-dim);">Script AI</span>
        <span style="color: var(--text-normal);">${script_cost:.4f}</span>
    </div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
        <span style="color: var(--text-dim);">Görsel (6x)</span>
        <span style="color: var(--text-normal);">${image_cost:.2f}</span>
    </div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
        <span style="color: var(--text-dim);">Video</span>
        <span style="color: var(--text-normal);">${video_cost:.2f}</span>
    </div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
        <span style="color: var(--text-dim);">TTS</span>
        <span style="color: var(--text-normal);">${tts_cost:.4f}</span>
    </div>
    <hr style="border-color: var(--border-subtle); margin: 0.8rem 0;">
    <div style="display: flex; justify-content: space-between;">
        <span style="color: var(--accent-primary); font-weight: 600;">{t('total_cost')}</span>
        <span style="color: var(--accent-primary); font-weight: 600; font-size: 1.2rem;">${total:.2f}</span>
    </div>
</div>
""", unsafe_allow_html=True)

    # Batch calculator
    batch_count = st.slider(t("batch_count"), 1, 100, 10)
    batch_total = total * batch_count
    st.markdown(f"**{t('batch_cost')}:** {batch_count} video = **${batch_total:.2f}**")

    st.divider()

    # --- API Keys ---
    st.markdown(f"### {t('api_keys')}")

    # Core keys (kept at top for quick access)
    new_anthropic = st.text_input("Anthropic API Key", value=config.get("ANTHROPIC_API_KEY", ""), type="password")
    new_gemini = st.text_input("Gemini API Key", value=config.get("GEMINI_API_KEY", ""), type="password")
    new_openai = st.text_input(t("openai_key"), value=config.get("OPENAI_API_KEY", ""), type="password")
    new_pexels = st.text_input("Pexels API Key", value=config.get("PEXELS_API_KEY", ""), type="password")
    new_elevenlabs = st.text_input("ElevenLabs API Key", value=config.get("ELEVENLABS_API_KEY", ""), type="password")
    new_voixor = st.text_input("Voixor API Key", value=config.get("VOIXOR_API_KEY", ""), type="password",
                               help="https://voixor.com/api.php · TR-friendly TTS, ElevenLabs-compatible voice IDs")
    new_google_tts = st.text_input(t("google_tts_key"), value=config.get("GOOGLE_TTS_KEY", ""), type="password")

    # Extended provider keys — collapsed by default
    with st.expander("Ek Sağlayıcılar · LLM / Image / Video / TTS (müşteri kendi key'ini girer)", expanded=False):
        st.caption("Bu alanlar boş bırakılabilir — müşteri ilgili sağlayıcıyı seçerse key girmesi istenir.")

        # Group: LLM / script_ai
        st.markdown("**LLM & Script**")
        c1, c2, c3 = st.columns(3)
        with c1:
            new_groq      = st.text_input("Groq", value=config.get("GROQ_API_KEY", ""), type="password", key="k_groq")
            new_deepseek  = st.text_input("DeepSeek", value=config.get("DEEPSEEK_API_KEY", ""), type="password", key="k_deepseek")
            new_mistral   = st.text_input("Mistral", value=config.get("MISTRAL_API_KEY", ""), type="password", key="k_mistral")
        with c2:
            new_xai       = st.text_input("xAI Grok", value=config.get("XAI_API_KEY", ""), type="password", key="k_xai")
            new_perplexity= st.text_input("Perplexity", value=config.get("PERPLEXITY_API_KEY", ""), type="password", key="k_ppx")
            new_openrouter= st.text_input("OpenRouter", value=config.get("OPENROUTER_API_KEY", ""), type="password", key="k_or")
        with c3:
            new_together  = st.text_input("Together AI", value=config.get("TOGETHER_API_KEY", ""), type="password", key="k_tog")
            new_fireworks = st.text_input("Fireworks", value=config.get("FIREWORKS_API_KEY", ""), type="password", key="k_fw")
            new_qwen      = st.text_input("Qwen (Alibaba)", value=config.get("QWEN_API_KEY", ""), type="password", key="k_qw")

        st.markdown("**Image / Video**")
        c1, c2, c3 = st.columns(3)
        with c1:
            new_stability = st.text_input("Stability AI", value=config.get("STABILITY_API_KEY", ""), type="password", key="k_st")
            new_bfl       = st.text_input("Black Forest (Flux)", value=config.get("BFL_API_KEY", ""), type="password", key="k_bfl")
            new_fal       = st.text_input("fal.ai", value=config.get("FAL_API_KEY", ""), type="password", key="k_fal")
            new_replicate = st.text_input("Replicate", value=config.get("REPLICATE_API_KEY", ""), type="password", key="k_rep")
        with c2:
            new_ideogram  = st.text_input("Ideogram", value=config.get("IDEOGRAM_API_KEY", ""), type="password", key="k_id")
            new_recraft   = st.text_input("Recraft", value=config.get("RECRAFT_API_KEY", ""), type="password", key="k_rc")
            new_leonardo  = st.text_input("Leonardo", value=config.get("LEONARDO_API_KEY", ""), type="password", key="k_leo")
            new_pixabay   = st.text_input("Pixabay", value=config.get("PIXABAY_API_KEY", ""), type="password", key="k_pix")
        with c3:
            new_runway    = st.text_input("Runway", value=config.get("RUNWAY_API_KEY", ""), type="password", key="k_rw")
            new_luma      = st.text_input("Luma Dream Machine", value=config.get("LUMA_API_KEY", ""), type="password", key="k_lu")
            new_kling     = st.text_input("Kling", value=config.get("KLING_API_KEY", ""), type="password", key="k_kl")
            new_minimax   = st.text_input("Minimax / Hailuo", value=config.get("MINIMAX_API_KEY", ""), type="password", key="k_mm")
            new_pika      = st.text_input("Pika", value=config.get("PIKA_API_KEY", ""), type="password", key="k_pk")
            new_unsplash  = st.text_input("Unsplash", value=config.get("UNSPLASH_API_KEY", ""), type="password", key="k_un")

        st.markdown("**TTS / Ses**")
        c1, c2, c3 = st.columns(3)
        with c1:
            new_playht    = st.text_input("PlayHT", value=config.get("PLAYHT_API_KEY", ""), type="password", key="k_pht")
            new_cartesia  = st.text_input("Cartesia", value=config.get("CARTESIA_API_KEY", ""), type="password", key="k_ca")
            new_deepgram  = st.text_input("Deepgram", value=config.get("DEEPGRAM_API_KEY", ""), type="password", key="k_dg")
        with c2:
            new_azure_tts = st.text_input("Azure TTS", value=config.get("AZURE_TTS_KEY", ""), type="password", key="k_az")
            new_murf      = st.text_input("Murf", value=config.get("MURF_API_KEY", ""), type="password", key="k_mrf")
            new_resemble  = st.text_input("Resemble", value=config.get("RESEMBLE_API_KEY", ""), type="password", key="k_rs")
        with c3:
            new_speechify = st.text_input("Speechify", value=config.get("SPEECHIFY_API_KEY", ""), type="password", key="k_sp")
            new_fishaudio = st.text_input("Fish Audio", value=config.get("FISHAUDIO_API_KEY", ""), type="password", key="k_fa")
            new_assemblyai= st.text_input("AssemblyAI", value=config.get("ASSEMBLYAI_API_KEY", ""), type="password", key="k_asm")
            new_speechmatics=st.text_input("Speechmatics", value=config.get("SPEECHMATICS_KEY", ""), type="password", key="k_sm")

        st.markdown("**Müzik**")
        c1, c2, c3 = st.columns(3)
        with c1:
            new_suno      = st.text_input("Suno", value=config.get("SUNO_API_KEY", ""), type="password", key="k_sn")
        with c2:
            new_udio      = st.text_input("Udio", value=config.get("UDIO_API_KEY", ""), type="password", key="k_ud")
            new_mubert    = st.text_input("Mubert", value=config.get("MUBERT_API_KEY", ""), type="password", key="k_mu")
        with c3:
            new_soundraw  = st.text_input("Soundraw", value=config.get("SOUNDRAW_API_KEY", ""), type="password", key="k_sd")

    if st.button(t("save_config"), use_container_width=True):
        # Core
        config["ANTHROPIC_API_KEY"] = new_anthropic
        config["GEMINI_API_KEY"]    = new_gemini
        config["PEXELS_API_KEY"]    = new_pexels
        config["ELEVENLABS_API_KEY"] = new_elevenlabs
        config["VOIXOR_API_KEY"]    = new_voixor
        if new_openai:     config["OPENAI_API_KEY"] = new_openai
        if new_google_tts: config["GOOGLE_TTS_KEY"] = new_google_tts
        # Extended — only write when not empty to keep config.json tidy
        _ext = {
            "GROQ_API_KEY": new_groq, "DEEPSEEK_API_KEY": new_deepseek, "MISTRAL_API_KEY": new_mistral,
            "XAI_API_KEY": new_xai, "PERPLEXITY_API_KEY": new_perplexity, "OPENROUTER_API_KEY": new_openrouter,
            "TOGETHER_API_KEY": new_together, "FIREWORKS_API_KEY": new_fireworks, "QWEN_API_KEY": new_qwen,
            "STABILITY_API_KEY": new_stability, "BFL_API_KEY": new_bfl, "FAL_API_KEY": new_fal,
            "REPLICATE_API_KEY": new_replicate, "IDEOGRAM_API_KEY": new_ideogram, "RECRAFT_API_KEY": new_recraft,
            "LEONARDO_API_KEY": new_leonardo, "PIXABAY_API_KEY": new_pixabay, "UNSPLASH_API_KEY": new_unsplash,
            "RUNWAY_API_KEY": new_runway, "LUMA_API_KEY": new_luma, "KLING_API_KEY": new_kling,
            "MINIMAX_API_KEY": new_minimax, "PIKA_API_KEY": new_pika,
            "PLAYHT_API_KEY": new_playht, "CARTESIA_API_KEY": new_cartesia, "DEEPGRAM_API_KEY": new_deepgram,
            "AZURE_TTS_KEY": new_azure_tts, "MURF_API_KEY": new_murf, "RESEMBLE_API_KEY": new_resemble,
            "SPEECHIFY_API_KEY": new_speechify, "FISHAUDIO_API_KEY": new_fishaudio,
            "ASSEMBLYAI_API_KEY": new_assemblyai, "SPEECHMATICS_KEY": new_speechmatics,
            "SUNO_API_KEY": new_suno, "UDIO_API_KEY": new_udio, "MUBERT_API_KEY": new_mubert,
            "SOUNDRAW_API_KEY": new_soundraw,
        }
        for k, v in _ext.items():
            if v:
                config[k] = v
        config["providers"] = {
            "script_ai": new_script,
            "image": new_image,
            "video": new_video,
            "tts": new_tts,
        }
        save_config(config)
        st.success(t("config_saved"))
        st.rerun()

    st.divider()

    # --- YouTube Channels ---
    st.markdown(f"### {t('channels')}")

    channels = get_channels()

    if channels:
        from pipeline import channel_preset as _cp
        from pipeline.config import PROVIDERS as _PROV
        for ch in channels:
            ch_col1, ch_col2 = st.columns([3, 1])
            with ch_col1:
                status_icon = "●" if ch.get("connected") else "○"
                status_color = "var(--status-success)" if ch.get("connected") else "var(--status-error)"
                status_text = "Bağlı" if ch.get("connected") else "OAuth gerekli"
                st.markdown(
                    f'<span style="color:{status_color}">{status_icon}</span> '
                    f'**{ch["name"]}** — <span style="color:var(--text-dim)">{status_text}</span>',
                    unsafe_allow_html=True,
                )
                if not ch.get("connected"):
                    st.caption(f'`python scripts/setup_youtube_oauth.py --channel "{ch["id"]}"`')
            with ch_col2:
                if st.button(t("remove_channel"), key=f"rm_ch_{ch['id']}", use_container_width=True):
                    remove_channel(ch["id"])
                    st.success(t("channel_removed"))
                    st.rerun()

            # Per-channel preset editor
            _preset_label = {"tr": "🎨 Kanal Preset'i (marka tutarlılığı)",
                             "en": "🎨 Channel Preset (brand consistency)"}[st.session_state.lang]
            with st.expander(_preset_label, expanded=False):
                current = _cp.load_preset(ch["id"])
                st.caption({
                    "tr": f"Bu kanalı seçince aşağıdaki varsayılanlar otomatik uygulanır. Boş alanlar global ayarlardan çekilir.",
                    "en": f"When this channel is selected, these defaults are applied. Empty fields fall back to global settings.",
                }[st.session_state.lang])

                # Build form
                with st.form(f"preset_form_{ch['id']}"):
                    new_preset = {}
                    for key, lbl_tr, lbl_en, ftype, opts in _cp.PRESET_FIELDS:
                        lbl = lbl_tr if st.session_state.lang == "tr" else lbl_en
                        existing = current.get(key, "")
                        if ftype == "select":
                            options = [""] + list(opts)
                            try:
                                idx = options.index(existing) if existing in options else 0
                            except Exception:
                                idx = 0
                            v = st.selectbox(lbl, options=options, index=idx,
                                             format_func=lambda x: x or "(global)",
                                             key=f"pre_{ch['id']}_{key}")
                            new_preset[key] = v
                        elif ftype == "provider":
                            cat = opts
                            cat_keys = [""] + list(_PROV.get(cat, {}).keys())
                            try:
                                idx = cat_keys.index(existing) if existing in cat_keys else 0
                            except Exception:
                                idx = 0
                            def _fmt(k, _cat=cat):
                                if not k:
                                    return "(global)"
                                info = _PROV.get(_cat, {}).get(k, {})
                                return info.get("name", k)
                            v = st.selectbox(lbl, options=cat_keys, index=idx,
                                             format_func=_fmt,
                                             key=f"pre_{ch['id']}_{key}")
                            new_preset[key] = v
                        elif ftype == "textarea":
                            v = st.text_area(lbl, value=existing or "", height=80,
                                             key=f"pre_{ch['id']}_{key}")
                            new_preset[key] = v
                        else:
                            v = st.text_input(lbl, value=existing or "",
                                              key=f"pre_{ch['id']}_{key}")
                            new_preset[key] = v

                    save_col1, save_col2 = st.columns(2)
                    save_clicked = save_col1.form_submit_button(
                        {"tr": "💾 Preset'i Kaydet", "en": "💾 Save Preset"}[st.session_state.lang],
                        use_container_width=True,
                    )
                    reset_clicked = save_col2.form_submit_button(
                        {"tr": "🗑 Preset'i Sil", "en": "🗑 Delete Preset"}[st.session_state.lang],
                        use_container_width=True,
                    )

                if save_clicked:
                    # Only keep non-empty fields (empty means "use global")
                    cleaned = {k: v for k, v in new_preset.items() if v not in ("", None)}
                    _cp.save_preset(ch["id"], cleaned)
                    st.success({"tr": f"{ch['name']} preset kaydedildi",
                                "en": f"{ch['name']} preset saved"}[st.session_state.lang])
                    st.rerun()
                if reset_clicked:
                    from pipeline.channel_preset import _preset_path
                    p = _preset_path(ch["id"])
                    if p.exists():
                        p.unlink()
                    st.success({"tr": "Preset silindi", "en": "Preset deleted"}[st.session_state.lang])
                    st.rerun()
    else:
        st.info(t("no_channels"))

    # Add new channel
    st.markdown("---")
    with st.form("add_channel_form", clear_on_submit=True):
        add_col1, add_col2 = st.columns([3, 1])
        with add_col1:
            new_channel_name = st.text_input(
                t("channel_name"),
                placeholder=t("channel_name_ph"),
            )
        with add_col2:
            st.markdown("")
            st.markdown("")
            submitted = st.form_submit_button(t("add_channel"), use_container_width=True)

        if submitted and new_channel_name.strip():
            ch_dir = add_channel(new_channel_name.strip())
            if ch_dir:
                st.success(f"{t('channel_added')} — {new_channel_name.strip()}")
                st.info(f"{t('channel_auth_info')}\n```\npython scripts/setup_youtube_oauth.py --channel \"{new_channel_name.strip()}\"\n```")
                st.rerun()

    st.divider()

    # --- Multi-Tenant (Tier 3 #13) ---
    st.divider()
    _mt_title = {"tr": "🏢 Çoklu Müşteri Modu (Multi-Tenant)",
                 "en": "🏢 Multi-Tenant Mode"}[st.session_state.lang]
    with st.expander(_mt_title, expanded=False):
        try:
            from pipeline import tenant as _tn
            mt_on = _tn.is_multi_tenant_enabled()

            # Status + toggle
            mtc1, mtc2 = st.columns([3, 1])
            with mtc1:
                state_label = "● AÇIK" if mt_on else "○ KAPALI"
                color = "var(--status-success)" if mt_on else "var(--text-dim)"
                st.markdown(
                    f'<div style="padding:0.75rem;background:var(--bg-card);border-radius:8px;">'
                    f'<b>Durum:</b> <span style="color:{color}">{state_label}</span></div>',
                    unsafe_allow_html=True,
                )
            with mtc2:
                if not mt_on:
                    if st.button({"tr": "▶ Aç", "en": "▶ Enable"}[st.session_state.lang],
                                 use_container_width=True, type="primary", key="mt_enable"):
                        st.session_state["_mt_enable_confirming"] = True
                        st.rerun()
                else:
                    if st.button({"tr": "■ Kapat", "en": "■ Disable"}[st.session_state.lang],
                                 use_container_width=True, key="mt_disable"):
                        st.session_state["_mt_disable_confirming"] = True
                        st.rerun()

            # Confirmation dialog for enabling
            if st.session_state.get("_mt_enable_confirming"):
                st.warning({
                    "tr": "⚠️ **Dikkat — Multi-tenant modu açıyorsun.**\n\n"
                          "Bu işlem drafts/, media/, channels/, config.json ve YouTube token'larını "
                          "`tenants/default/` altına **taşıyacak**. İşlem başlamadan önce otomatik bir "
                          "YEDEK alınır (`.backup.<timestamp>/`). Hata olursa yedekten geri alabilirsin.\n\n"
                          "YouTube OAuth token'ları korunur — **yeniden giriş yapmana gerek yok**.",
                    "en": "⚠️ **Caution — Enabling multi-tenant.**\n\n"
                          "This will MOVE drafts/, media/, channels/, config.json and YouTube tokens "
                          "into `tenants/default/`. A full backup to `.backup.<timestamp>/` is created "
                          "automatically before any file is moved. You can restore from backup if anything "
                          "goes wrong.\n\nYouTube OAuth tokens are preserved — **no re-auth needed**.",
                }[st.session_state.lang])
                confirm_col1, confirm_col2 = st.columns(2)
                if confirm_col1.button({"tr": "✅ Anladım, Aç", "en": "✅ Got it, Enable"}[st.session_state.lang],
                                        type="primary", use_container_width=True, key="mt_confirm_enable"):
                    with st.spinner("Backup + migrate..."):
                        res = _tn.enable_multi_tenant()
                    del st.session_state["_mt_enable_confirming"]
                    if "error" in res:
                        st.error(f"❌ {res.get('reason', res['error'])}")
                    else:
                        st.success({
                            "tr": f"✅ Açıldı — {len(res.get('migrated', []))} öğe taşındı.\n\n"
                                  f"📦 Yedek: `{res.get('backup_path', '-')}`",
                            "en": f"✅ Enabled — {len(res.get('migrated', []))} items migrated.\n\n"
                                  f"📦 Backup: `{res.get('backup_path', '-')}`",
                        }[st.session_state.lang])
                    st.rerun()
                if confirm_col2.button({"tr": "❌ Vazgeç", "en": "❌ Cancel"}[st.session_state.lang],
                                        use_container_width=True, key="mt_cancel_enable"):
                    del st.session_state["_mt_enable_confirming"]
                    st.rerun()

            if st.session_state.get("_mt_disable_confirming"):
                st.warning({
                    "tr": "⚠️ **Multi-tenant kapatılıyor.**\n\n"
                          "`default` tenant'ın datası geri SKILL_DIR'a taşınacak. Diğer tenant'lar "
                          "(varsa) `tenants/` altında kalacak — silinmez. Backup otomatik alınır.",
                    "en": "⚠️ **Disabling multi-tenant.**\n\n"
                          "Default tenant data moves back to SKILL_DIR. Non-default tenants stay "
                          "in `tenants/` — not deleted. Automatic backup before any move.",
                }[st.session_state.lang])
                cc1, cc2 = st.columns(2)
                if cc1.button({"tr": "✅ Anladım, Kapat", "en": "✅ Got it, Disable"}[st.session_state.lang],
                               type="primary", use_container_width=True, key="mt_confirm_disable"):
                    with st.spinner("Backup + restore..."):
                        res = _tn.disable_multi_tenant()
                    del st.session_state["_mt_disable_confirming"]
                    if "error" in res:
                        st.error(f"❌ {res.get('reason', res['error'])}")
                    else:
                        st.success({
                            "tr": f"✅ Kapatıldı · 📦 Yedek: `{res.get('backup_path', '-')}`",
                            "en": f"✅ Disabled · 📦 Backup: `{res.get('backup_path', '-')}`",
                        }[st.session_state.lang])
                    st.rerun()
                if cc2.button({"tr": "❌ Vazgeç", "en": "❌ Cancel"}[st.session_state.lang],
                               use_container_width=True, key="mt_cancel_disable"):
                    del st.session_state["_mt_disable_confirming"]
                    st.rerun()

            st.caption({
                "tr": "Multi-tenant açılınca: verilerin `tenants/default/` altına taşınır, "
                      "yeni müşteri hesapları oluşturabilirsin. YouTube OAuth token'larına dokunulmaz, "
                      "mevcut kanallar çalışmaya devam eder.",
                "en": "When enabled: your data moves into `tenants/default/`, and you can create "
                      "additional customer accounts. YouTube OAuth tokens are preserved.",
            }[st.session_state.lang])

            if mt_on:
                st.markdown(f"**{'Müşteri Hesapları' if st.session_state.lang == 'tr' else 'Customer Tenants'}**")
                tenants = _tn.list_tenants()
                if tenants:
                    import pandas as pd
                    df = pd.DataFrame([{
                        "ID": x["id"],
                        ("İsim" if st.session_state.lang == "tr" else "Name"): x["name"],
                        ("Oluşturma" if st.session_state.lang == "tr" else "Created"): (x.get("created_at") or "")[:10],
                        ("Varsayılan" if st.session_state.lang == "tr" else "Default"): "✓" if x.get("is_default") else "",
                    } for x in tenants])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                # Add new tenant
                with st.form("new_tenant_form", clear_on_submit=True):
                    tc1, tc2, tc3 = st.columns([2, 2, 1])
                    new_tid = tc1.text_input({"tr": "ID (a-z, 0-9, _)", "en": "ID (a-z, 0-9, _)"}[st.session_state.lang])
                    new_tname = tc2.text_input({"tr": "Görünen İsim", "en": "Display Name"}[st.session_state.lang])
                    tc3.markdown("&nbsp;", unsafe_allow_html=True)
                    add_tenant = tc3.form_submit_button(
                        {"tr": "+ Ekle", "en": "+ Add"}[st.session_state.lang],
                        use_container_width=True, type="primary",
                    )
                    if add_tenant and new_tid.strip():
                        r = _tn.create_tenant(new_tid.strip(), name=new_tname.strip() or None)
                        st.success({"tr": f"Eklendi: {r.get('id')}",
                                    "en": f"Created: {r.get('id')}"}[st.session_state.lang])
                        st.rerun()
        except Exception as e:
            st.caption(f"(multi-tenant: {e})")

    # --- API Access (Tier 3 #16) ---
    st.divider()
    _api_title = {"tr": "🔌 API Erişimi ve Webhook'lar",
                  "en": "🔌 API Access & Webhooks"}[st.session_state.lang]
    with st.expander(_api_title, expanded=False):
        try:
            from pipeline import api_server as _api
            st.caption({
                "tr": "Müşterinin kendi sistemi panel üzerinden iş oluşturabilsin, webhook ile durum güncellemesi alsın.",
                "en": "Let customers create jobs programmatically and receive status updates via webhook.",
            }[st.session_state.lang])

            # Server controls
            api_running = _api.is_running()
            api_port = _api.port() or _api.DEFAULT_PORT
            sc1, sc2, sc3 = st.columns([3, 1, 1])
            with sc1:
                state_label = "● ÇALIŞIYOR" if api_running else "○ KAPALI"
                state_color = "var(--status-success)" if api_running else "var(--text-dim)"
                st.markdown(
                    f'<div style="padding:0.75rem;background:var(--bg-card);border-radius:8px;">'
                    f'<b>API:</b> <span style="color:{state_color}">{state_label}</span>'
                    f' · Port: <code>{api_port}</code></div>',
                    unsafe_allow_html=True,
                )
            with sc2:
                if not api_running and st.button(
                    {"tr": "▶ Başlat", "en": "▶ Start"}[st.session_state.lang],
                    use_container_width=True, key="api_start",
                ):
                    res = _api.start(port=api_port)
                    st.success(f"API :{res['port']}")
                    st.rerun()
            with sc3:
                if api_running and st.button(
                    {"tr": "■ Durdur", "en": "■ Stop"}[st.session_state.lang],
                    use_container_width=True, key="api_stop",
                ):
                    _api.stop()
                    st.rerun()

            st.markdown(f"**{'API Tokenları' if st.session_state.lang == 'tr' else 'API Tokens'}**")

            tokens_meta = _api.list_tokens()
            if tokens_meta:
                import pandas as pd
                df = pd.DataFrame([
                    {
                        "Token": m["token_preview"],
                        ("İsim" if st.session_state.lang == "tr" else "Name"): m["name"],
                        ("Oluşturma" if st.session_state.lang == "tr" else "Created"): (m["created_at"] or "")[:19],
                        "Scopes": ", ".join(m["scopes"]),
                        ("İptal" if st.session_state.lang == "tr" else "Revoked"): "✓" if m["revoked"] else "",
                    }
                    for m in tokens_meta
                ])
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.caption({"tr": "Henüz token yok.", "en": "No tokens issued."}[st.session_state.lang])

            # Issue new token
            with st.form("api_token_form", clear_on_submit=True):
                tn_col1, tn_col2 = st.columns([3, 1])
                with tn_col1:
                    new_token_name = st.text_input(
                        {"tr": "Token ismi (ör. 'Müşteri A')",
                         "en": "Token name (e.g. 'Customer A')"}[st.session_state.lang],
                    )
                with tn_col2:
                    st.markdown("&nbsp;", unsafe_allow_html=True)
                    issue_clicked = st.form_submit_button(
                        {"tr": "+ Token Oluştur", "en": "+ Issue Token"}[st.session_state.lang],
                        use_container_width=True, type="primary",
                    )
                if issue_clicked and new_token_name.strip():
                    new_tok = _api.issue_token(new_token_name.strip())
                    st.success({"tr": "Token oluşturuldu — BİR KEZ gösteriliyor, kopyala:",
                                "en": "Token issued — shown ONCE, copy it:"}[st.session_state.lang])
                    st.code(new_tok, language="text")

            # API docs
            st.markdown(f"**{'Örnek Kullanım' if st.session_state.lang == 'tr' else 'Example Usage'}**")
            external_host = "http://retube.rewmarket.com" if api_port == 80 else f"http://<sunucu>:{api_port}"
            st.code(f'''# İş oluştur
curl -X POST {external_host}/v1/jobs \\
  -H "Authorization: Bearer rt_xxx..." \\
  -H "Content-Type: application/json" \\
  -d '{{"topic":"Tesla yeni model","lang":"tr","mode":"full","webhook_url":"https://senin-servis.com/hook"}}'

# Durum çek
curl -H "Authorization: Bearer rt_xxx..." {external_host}/v1/jobs/<job_id>

# İstatistikler
curl -H "Authorization: Bearer rt_xxx..." {external_host}/v1/stats''',
                    language="bash")
        except Exception as e:
            st.caption(f"(api: {e})")

    # --- White-Label Branding (Tier 3 #14) ---
    st.divider()
    _wl_title = {"tr": "🎨 Marka Özelleştirme (White-Label)",
                 "en": "🎨 White-Label Branding"}[st.session_state.lang]
    with st.expander(_wl_title, expanded=False):
        try:
            from pipeline import branding as _br
            current_brand = _br.load()
            st.caption({
                "tr": "Panel'i kendi markan olarak sat: logo, renk, isim. Her müşteri için farklı görünüm oluştur.",
                "en": "Rebrand the panel: logo, accent color, product name. Ship it as your own.",
            }[st.session_state.lang])

            with st.form("branding_form"):
                b_col1, b_col2 = st.columns(2)
                with b_col1:
                    new_name = st.text_input(
                        {"tr": "Ürün Adı", "en": "Product Name"}[st.session_state.lang],
                        value=current_brand.get("product_name", "RE-Tube"),
                    )
                    new_short = st.text_input(
                        {"tr": "Kısa Ad (tab'da görünür)", "en": "Short Name (tab title)"}[st.session_state.lang],
                        value=current_brand.get("short_name", "RT"),
                        max_chars=6,
                    )
                    new_tagline = st.text_input(
                        {"tr": "Slogan", "en": "Tagline"}[st.session_state.lang],
                        value=current_brand.get("tagline", ""),
                    )
                    new_accent = st.color_picker(
                        {"tr": "Vurgu Rengi", "en": "Accent Color"}[st.session_state.lang],
                        value=current_brand.get("accent", "#C9A96E"),
                    )
                    new_bg = st.color_picker(
                        {"tr": "Arkaplan", "en": "Background"}[st.session_state.lang],
                        value=current_brand.get("bg_deep", "#0F0D0A"),
                    )
                with b_col2:
                    new_logo = st.file_uploader(
                        {"tr": "Logo (PNG/SVG, tercihen kare)",
                         "en": "Logo (PNG/SVG, square preferred)"}[st.session_state.lang],
                        type=["png", "jpg", "jpeg", "svg"],
                        key="brand_logo_upload",
                    )
                    if current_brand.get("logo_path"):
                        st.caption(f"Mevcut logo: {current_brand['logo_path']}")
                    new_hide_credit = st.checkbox(
                        {"tr": "RE-Tube atıflarını gizle",
                         "en": "Hide RE-Tube credits"}[st.session_state.lang],
                        value=current_brand.get("hide_retube_credit", False),
                    )
                    new_support_email = st.text_input(
                        {"tr": "Destek E-posta", "en": "Support Email"}[st.session_state.lang],
                        value=current_brand.get("support_email", ""),
                    )
                    new_support_url = st.text_input(
                        {"tr": "Destek URL", "en": "Support URL"}[st.session_state.lang],
                        value=current_brand.get("support_url", ""),
                    )

                sc1, sc2 = st.columns(2)
                save_brand = sc1.form_submit_button(
                    {"tr": "💾 Kaydet", "en": "💾 Save"}[st.session_state.lang],
                    use_container_width=True, type="primary",
                )
                reset_brand = sc2.form_submit_button(
                    {"tr": "🔄 Varsayılana Dön", "en": "🔄 Reset to Default"}[st.session_state.lang],
                    use_container_width=True,
                )

            if save_brand:
                brand_update = {
                    "product_name": new_name,
                    "short_name": new_short,
                    "tagline": new_tagline,
                    "accent": new_accent,
                    "bg_deep": new_bg,
                    "hide_retube_credit": new_hide_credit,
                    "support_email": new_support_email,
                    "support_url": new_support_url,
                }
                # Persist uploaded logo to disk
                if new_logo is not None:
                    from pipeline.config import SKILL_DIR as _sd
                    brand_dir = _sd / "branding"
                    brand_dir.mkdir(parents=True, exist_ok=True)
                    ext = Path(new_logo.name).suffix.lower() or ".png"
                    logo_dest = brand_dir / f"logo{ext}"
                    logo_dest.write_bytes(new_logo.read())
                    brand_update["logo_path"] = str(logo_dest)
                _br.save(brand_update)
                try:
                    from pipeline import audit as _audit
                    _audit.log("provider_changed", target="branding",
                               details={"product_name": new_name})
                except Exception:
                    pass
                st.success({"tr": "✅ Kaydedildi — sayfayı yenile.",
                            "en": "✅ Saved — refresh the page."}[st.session_state.lang])
                st.rerun()

            if reset_brand:
                _br.reset()
                st.success({"tr": "Varsayılana döndü", "en": "Reset to default"}[st.session_state.lang])
                st.rerun()

            # Preview
            st.divider()
            st.markdown(f"**{'Önizleme' if st.session_state.lang == 'tr' else 'Preview'}:**")
            preview = _br.load()
            st.markdown(
                f'<div style="padding:14px;background:{preview["bg_deep"]};'
                f'border:1px solid {preview["accent"]};border-radius:10px;'
                f'display:flex;gap:12px;align-items:center;">'
                f'<div style="width:36px;height:36px;background:{preview["accent"]};border-radius:8px;"></div>'
                f'<div><div style="font-size:1.1rem;font-weight:600;color:{preview["accent"]}">{preview["product_name"]}</div>'
                f'<div style="font-size:0.8rem;color:#999">{preview["tagline"]}</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        except Exception as e:
            st.caption(f"(branding: {e})")

    # --- Audit Log (Tier 3 #17) ---
    st.divider()
    _audit_title = {"tr": "📋 Denetim Günlüğü (Audit Log)",
                    "en": "📋 Audit Log"}[st.session_state.lang]
    with st.expander(_audit_title, expanded=False):
        try:
            from pipeline import audit as _audit
            st.caption({
                "tr": "Sistemdeki her kritik aksiyonun kaydı. Compliance ve hata ayıklama için.",
                "en": "Record of every meaningful system action — for compliance and debugging.",
            }[st.session_state.lang])

            # Leaderboard of recent actions
            counts_7d = _audit.counts_by_action(days=7)
            if counts_7d:
                st.markdown(f"**{'Son 7 Gün Aktivite' if st.session_state.lang == 'tr' else 'Last 7 Days Activity'}**")
                for action, n in list(counts_7d.items())[:8]:
                    pct = int(min(100, (n / max(1, max(counts_7d.values()))) * 100))
                    st.markdown(
                        f'<div class="cost-row">'
                        f'<div class="cost-name">{action}</div>'
                        f'<div class="cost-bar-wrap"><div class="cost-bar" style="width:{pct}%"></div></div>'
                        f'<div class="cost-amount">{n}</div>'
                        f'</div>', unsafe_allow_html=True,
                    )

            st.divider()

            # Filtered recent entries
            flt_col1, flt_col2, flt_col3 = st.columns(3)
            with flt_col1:
                flt_action = st.selectbox(
                    {"tr": "Aksiyon filtresi", "en": "Filter by action"}[st.session_state.lang],
                    options=["(tümü)"] + sorted(_audit.ACTIONS),
                    key="audit_flt_action",
                )
            with flt_col2:
                flt_days = st.selectbox(
                    {"tr": "Zaman aralığı", "en": "Time range"}[st.session_state.lang],
                    options=[1, 7, 30, 90, 365],
                    format_func=lambda d: f"{d}g" if st.session_state.lang == "tr" else f"{d}d",
                    index=1, key="audit_flt_days",
                )
            with flt_col3:
                flt_result = st.selectbox(
                    {"tr": "Sonuç", "en": "Result"}[st.session_state.lang],
                    options=["(tümü)", "ok", "fail", "denied"],
                    key="audit_flt_result",
                )

            entries = _audit.query(
                action=None if flt_action == "(tümü)" else flt_action,
                result=None if flt_result == "(tümü)" else flt_result,
                days=flt_days, limit=200,
            )

            if not entries:
                st.info({"tr": "Bu filtreyle kayıt yok.",
                         "en": "No records match this filter."}[st.session_state.lang])
            else:
                import pandas as pd
                df = pd.DataFrame([{
                    "Zaman" if st.session_state.lang == "tr" else "Time":
                        e["ts"][:19].replace("T", " "),
                    "Aksiyon" if st.session_state.lang == "tr" else "Action": e["action"],
                    "Hedef" if st.session_state.lang == "tr" else "Target": (e.get("target") or "")[:40],
                    "Aktör" if st.session_state.lang == "tr" else "Actor": e.get("actor", ""),
                    "Sonuç" if st.session_state.lang == "tr" else "Result": e.get("result", ""),
                } for e in entries[:100]])
                st.dataframe(df, use_container_width=True, hide_index=True, height=320)

            # Export button
            exp_col1, exp_col2 = st.columns([3, 1])
            with exp_col1:
                st.caption({
                    "tr": f"📊 Toplam {len(entries)} kayıt (ilk 100 gösterildi)",
                    "en": f"📊 {len(entries)} total records (first 100 shown)",
                }[st.session_state.lang])
            with exp_col2:
                if st.button({"tr": "📥 CSV İndir", "en": "📥 Export CSV"}[st.session_state.lang],
                             use_container_width=True, key="audit_export"):
                    from pipeline.config import SKILL_DIR
                    out_path = SKILL_DIR / f"audit_export_{flt_days}d.csv"
                    _audit.export_csv(out_path, days=flt_days)
                    with open(out_path, "rb") as f:
                        st.download_button(
                            {"tr": "⬇ İndir", "en": "⬇ Download"}[st.session_state.lang],
                            data=f.read(),
                            file_name=out_path.name, mime="text/csv",
                        )
        except Exception as e:
            st.caption(f"(audit: {e})")

    # --- Updates ---
    st.divider()
    st.markdown(f"### {t('updates')}")

    from updater import load_version_info, save_version_info, check_for_updates, apply_update, init_repo, has_git, get_update_changelog

    ver_info = load_version_info()
    st.markdown(f"**{t('version_label')}:** v{ver_info.get('current_version', '1.0.0')}")

    repo_url_input = st.text_input(
        t("repo_url"),
        value=ver_info.get("repo_url", ""),
        placeholder="https://github.com/username/re-tube-private.git",
        key="repo_url_input",
    )

    if repo_url_input != ver_info.get("repo_url", ""):
        ver_info["repo_url"] = repo_url_input
        save_version_info(ver_info)

    ucol1, ucol2 = st.columns(2)
    with ucol1:
        if st.button(t("check_updates"), use_container_width=True):
            if not repo_url_input:
                st.warning(t("no_repo"))
            elif not has_git():
                st.error("Git bulunamadı. Git yükleyin: https://git-scm.com/downloads")
            else:
                with st.spinner(t("searching")):
                    init_repo(repo_url_input, ver_info.get("branch", "main"))
                    has_upd, local_h, remote_h = check_for_updates(
                        repo_url_input, ver_info.get("branch", "main")
                    )
                    if has_upd:
                        changelog = get_update_changelog(ver_info.get("branch", "main"))
                        st.warning(f"{t('update_available')} ({local_h} → {remote_h})")
                        if changelog:
                            st.code(changelog, language="text")
                    else:
                        st.success(f"{t('up_to_date')} ({local_h})")

    with ucol2:
        if st.button(t("apply_update"), use_container_width=True):
            if not repo_url_input:
                st.warning(t("no_repo"))
            else:
                with st.spinner(t("manual_producing")):
                    init_repo(repo_url_input, ver_info.get("branch", "main"))
                    ok, msg = apply_update(ver_info.get("branch", "main"))
                    if ok:
                        st.success(t("update_success"))
                    else:
                        st.error(f"{t('update_failed')}: {msg}")

    # --- System Info ---
    st.divider()
    st.markdown(f"### {t('system_info')}")
    info_rows = [
        ("Claude AI", t("connected") if has_claude else t("not_connected")),
        ("FFmpeg", t("installed") if has_ffmpeg else t("not_found")),
        ("YouTube OAuth", t("configured") if has_yt_token else t("missing")),
        (t("version_label"), f"v{ver_info.get('current_version', '1.0.0')}"),
        ("Config Path", f"`{CONFIG_FILE}`"),
        ("Drafts Path", f"`{DRAFTS_DIR}`"),
        ("Media Path", f"`{MEDIA_DIR}`"),
    ]
    table_md = f"| {t('component')} | {t('status_col')} |\n|-----------|--------|\n"
    for comp, stat in info_rows:
        table_md += f"| {comp} | {stat} |\n"
    st.markdown(table_md)
