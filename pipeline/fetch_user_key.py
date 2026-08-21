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
    """Mengambil HF_TOKEN dan HF_KEYS_DATASET_REPO_ID dari env runner."""
    token = os.getenv("HF_TOKEN")
    repo_id = os.getenv("HF_KEYS_DATASET_REPO_ID")
    if not token or not repo_id:
        raise ValueError("HF_TOKEN atau HF_KEYS_DATASET_REPO_ID belum disetel di runner!")
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
    except Exception as e:
        raise RuntimeError(f"User '{clean_user}' belum memiliki kredensial di dataset privat (Error: {e}). Harap sambungkan API Key di Tab Pengaturan.")

    # Cek khusus untuk Groq transkripsi
    if clean_provider == "groq" and user_data.get("groq_key_encrypted"):
        raw_key = decrypt_data(user_data["groq_key_encrypted"])
        return raw_key

    # Cek di array providers
    providers = user_data.get("providers", [])
    for p in providers:
        if p.get("provider_id", "").lower() == clean_provider:
            enc_key = p.get("key_encrypted")
            if not enc_key:
                break
            raw_key = decrypt_data(enc_key)
            return raw_key

    raise RuntimeError(f"Kunci API untuk provider '{clean_provider}' belum disambungkan oleh user '{clean_user}'.")


def get_user_cookie_file(user_id: str) -> Optional[str]:
    """
    Mengunduh cookie terenkripsi milik user, mendekripsinya, dan menyimpannya
    ke file temporary Netscape cookies untuk digunakan oleh yt-dlp.
    Mengembalikan path file temporary, atau None jika user belum menyetel cookie.
    """
    token, repo_id = get_hf_credentials()
    clean_user = user_id.strip()

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
        
        # Buat temporary file untuk cookie Netscape
        temp_cookie = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt", encoding="utf-8")
        temp_cookie.write(raw_cookie_text)
        temp_cookie.close()
        return temp_cookie.name

    except Exception:
        return None
