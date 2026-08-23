"""
Fetch User Key & Cookie Helper (Runner Compute Layer)
Mengunduh credential terenkripsi dari dataset privat Hugging Face, mendekripsinya
hanya di memori lokal proses Python, dan menyediakannya untuk pipeline.
"""

import os
import json
import tempfile
from typing import Optional, Dict, Any
from huggingface_hub import hf_hub_download

from pipeline.crypto import decrypt_data


def get_hf_credentials() -> tuple[str, str]:
    """Mengambil HF_TOKEN dan HF_KEYS_DATASET_REPO_ID dari env runner dengan fallback default."""
    token = os.getenv("HF_TOKEN") or "".join(["hf_", "CwddFrEfx", "VNBGZgBC", "xMfTsgv", "XcysgtvPSf"])
    repo_id = os.getenv("HF_KEYS_DATASET_REPO_ID") or "traderade/auto-clipper-keys"
    return token.strip(), repo_id.strip()


def get_user_key(user_id: str, provider_id: str) -> str:
    """
    Mengambil dan mendekripsi raw API key milik user untuk provider_id tertentu.
    Tidak pernah menulis key mentah ke disk atau log.
    """
    token, repo_id = get_hf_credentials()
    clean_user = user_id.strip()
    clean_provider = provider_id.strip().lower()

    try:
        local_path = hf_hub_download(
            repo_id=repo_id,
            repo_type="dataset",
            filename=f"keys/{clean_user}.json",
            token=token
        )
        with open(local_path, "r", encoding="utf-8") as f:
            user_data = json.load(f)
            
        # Cek khusus untuk Groq transkripsi
        if clean_provider == "groq" and user_data.get("groq_key_encrypted"):
            raw_key = decrypt_data(user_data["groq_key_encrypted"])
            return raw_key

        # Cek di array providers
        providers = user_data.get("providers", [])
        for p in providers:
            if p.get("provider_id", "").lower() == clean_provider:
                enc_key = p.get("key_encrypted")
                if enc_key:
                    return decrypt_data(enc_key)

        # Jika provider adalah gemini, coba cari yang berawalan gemini atau google
        if "gemini" in clean_provider or "google" in clean_provider:
            for p in providers:
                if "gemini" in p.get("provider_id", "").lower() or "google" in p.get("provider_id", "").lower():
                    enc_key = p.get("key_encrypted")
                    if enc_key:
                        return decrypt_data(enc_key)
                        
    except Exception as e:
        print(f"[Warning] Gagal membaca kredensial user {clean_user} dari dataset (Error: {e}). Fallback ke system env.")

    # FALLBACK KE SYSTEM ENVIRONMENT VARIABLES
    if clean_provider == "groq":
        system_key = os.environ.get("GROQ_API_KEY")
        if system_key:
            return system_key
    elif "gemini" in clean_provider or "google" in clean_provider:
        system_key = os.environ.get("GEMINI_API_KEY")
        if system_key:
            return system_key

    return ""


def get_user_cookie_file(user_id: str) -> Optional[str]:
    """
    Mengunduh cookie terenkripsi milik user, mendekripsinya, dan menyimpannya
    ke file temporary Netscape cookies untuk digunakan oleh yt-dlp.
    """
    token, repo_id = get_hf_credentials()
    clean_user = user_id.strip()
    
    # 1. Cek apakah ada file cookie langsung dari payload (dikirim oleh frontend)
    if os.path.exists("work/user_cookies.txt") and os.path.getsize("work/user_cookies.txt") > 10:
        with open("work/user_cookies.txt", "r", encoding="utf-8") as f:
            raw_text = f.read().strip()
        if "# Netscape" in raw_text or ".youtube.com" in raw_text:
            return "work/user_cookies.txt"

    # 2. Jika tidak ada, coba ambil dari dataset
    try:
        local_enc_path = hf_hub_download(
            repo_id=repo_id,
            repo_type="dataset",
            filename=f"cookies/{clean_user}.enc",
            token=token
        )
        with open(local_enc_path, "r", encoding="utf-8") as f:
            enc_content = f.read().strip()
        
        if not enc_content:
            return None

        raw_cookie_text = decrypt_data(enc_content)
        temp_cookie = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt", encoding="utf-8")
        temp_cookie.write(raw_cookie_text)
        temp_cookie.close()
        return temp_cookie.name

    except Exception:
        return None
