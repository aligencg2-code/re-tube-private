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


# --- Page Config -------------------------------------------------
st.set_page_config(
    page_title="RE-Tube Dashboard",
    page_icon="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>▶</text></svg>",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Session State Defaults --------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "tr"

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
    # Brand
    st.markdown("""
    <div class="nav-brand">
        <div class="nav-brand-icon">▶</div>
        <div class="nav-brand-text">RE-Tube</div>
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

    # Navigation
    nav_labels = [
        t("dashboard"), t("pipeline"), t("manual_prod"), t("trends"),
        t("videos"), t("history"), t("settings"),
    ]
    nav_keys = ["Dashboard", "Pipeline", "Manual", "Trends", "Videos", "History", "Settings"]

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
        rows_html = ""
        for d in drafts[:10]:
            title = d.get("youtube_title", d.get("news", "Untitled"))[:50]
            job_id = d.get("job_id", "?")
            state = d.get("_pipeline_state", {})
            badge = draft_status_badge(state)
            done = sum(1 for v in state.values() if isinstance(v, dict) and v.get("status") == "done")
            ago = time_ago(job_id)

            rows_html += f"""
            <tr>
                <td>
                    <div class="prod-title">{title}</div>
                    <div class="prod-id">PRD-{str(job_id)[-4:]}</div>
                </td>
                <td>{badge}</td>
                <td><span style="color: var(--text-dim);">{done}/9 {t("stages_label")}</span></td>
                <td><span style="color: var(--text-ghost);">{ago}</span></td>
            </tr>
            """

        st.markdown(f"""
        <table class="prod-table">
            <thead>
                <tr>
                    <th>{t("production")}</th>
                    <th>{t("status")}</th>
                    <th>{t("progress")}</th>
                    <th>{t("created")}</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="text-align:center; padding:3rem; color: var(--text-ghost);">
            {t("no_prod")}
        </div>
        """, unsafe_allow_html=True)

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

    # Pipeline stages visualization
    stages = ["Research", "Draft", "B-Roll", "Voice", "Captions", "Music", "Assemble", "Thumb", "Upload"]
    pills = "".join(f'<span class="stage-pill">{s}</span>' for s in stages)
    st.markdown(f'<div class="pipeline-stages">{pills}</div>', unsafe_allow_html=True)

    if st.button(t("start_prod"), use_container_width=True, disabled=not topic):
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

    new_anthropic = st.text_input("Anthropic API Key", value=config.get("ANTHROPIC_API_KEY", ""), type="password")
    new_gemini = st.text_input("Gemini API Key", value=config.get("GEMINI_API_KEY", ""), type="password")
    new_openai = st.text_input(t("openai_key"), value=config.get("OPENAI_API_KEY", ""), type="password")
    new_pexels = st.text_input("Pexels API Key", value=config.get("PEXELS_API_KEY", ""), type="password")
    new_elevenlabs = st.text_input("ElevenLabs API Key", value=config.get("ELEVENLABS_API_KEY", ""), type="password")
    new_google_tts = st.text_input(t("google_tts_key"), value=config.get("GOOGLE_TTS_KEY", ""), type="password")

    if st.button(t("save_config"), use_container_width=True):
        config["ANTHROPIC_API_KEY"] = new_anthropic
        config["GEMINI_API_KEY"] = new_gemini
        config["PEXELS_API_KEY"] = new_pexels
        config["ELEVENLABS_API_KEY"] = new_elevenlabs
        if new_openai:
            config["OPENAI_API_KEY"] = new_openai
        if new_google_tts:
            config["GOOGLE_TTS_KEY"] = new_google_tts
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
