"""
Brand Voice Module
Membaca preferensi persona/gaya bahasa brand user dari dataset publik brand/{user_id}.json.
"""

import os
import json
from typing import Optional, Dict, Any
from huggingface_hub import hf_hub_download


def get_brand_voice(user_id: str, public_repo_id: str, hf_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Mengambil konfigurasi brand voice user dari brand/{user_id}.json.
    """
    if not public_repo_id:
        return None
    try:
        local_path = hf_hub_download(
            repo_id=public_repo_id,
            repo_type="dataset",
            filename=f"brand/{user_id}.json",
            token=hf_token
        )
        with open(local_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
