"""
Model Pool & Rotation Engine (LLM Router)
Mengelola status ketersediaan, ranking kecepatan, self-healing cooldown,
dan failover otomatis lintas provider multi-LLM.
"""

import json
import os
import datetime
import time
import requests
from typing import List, Dict, Any, Optional, Tuple, Callable
from huggingface_hub import HfApi, hf_hub_download

from pipeline.registry import get_provider_spec


def parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime.datetime]:
    """Mengonversi ISO 8601 string menjadi datetime UTC object."""
    if not dt_str:
        return None
    try:
        clean_str = dt_str.replace("Z", "+00:00")
        return datetime.datetime.fromisoformat(clean_str)
    except Exception:
        return None


def format_countdown(cooldown_until_str: Optional[str]) -> str:
    """
    Format sisa waktu cooldown menjadi string terbaca (misal: '⏳ 01m 30s').
    """
    if not cooldown_until_str:
        return "-"
    cooldown_dt = parse_iso_datetime(cooldown_until_str)
    if not cooldown_dt:
        return "-"
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    diff_sec = (cooldown_dt - now_dt).total_seconds()
    if diff_sec <= 0:
        return "⚡ Siap (Pulih)"
    mins, secs = divmod(int(diff_sec), 60)
    if mins > 60:
        hours, mins = divmod(mins, 60)
        return f"⏳ {hours}j {mins}m"
    return f"⏳ {mins:02d}m {secs:02d}s"


def get_user_pool_file(user_id: str, public_repo_id: str, hf_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Mengambil file metadata pool_state/{user_id}.json dari dataset publik (tanpa secret).
    """
    default_structure = {
        "user_id": user_id,
        "models": [],
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    if not public_repo_id:
        return default_structure

    try:
        local_path = hf_hub_download(
            repo_id=public_repo_id,
            repo_type="dataset",
            filename=f"pool_state/{user_id}.json",
            token=hf_token
        )
        with open(local_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_structure


def save_user_pool_file(user_id: str, data: Dict[str, Any], public_repo_id: str, hf_token: str) -> bool:
    """
    Menyimpan metadata pool_state/{user_id}.json ke dataset publik.
    """
    if not public_repo_id or not hf_token:
        return False
    try:
        api = HfApi(token=hf_token)
        data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        json_bytes = json.dumps(data, indent=2).encode("utf-8")
        api.upload_file(
            path_or_fileobj=json_bytes,
            path_in_repo=f"pool_state/{user_id}.json",
            repo_id=public_repo_id,
            repo_type="dataset",
            commit_message=f"Update pool_state for user {user_id}"
        )
        return True
    except Exception as e:
        print(f"[Warning] Gagal upload pool_state: {e}")
        return False


def refresh_provider_models_in_pool(
    user_id: str,
    provider_id: str,
    discovered_models: List[str],
    hf_token: str,
    public_repo_id: str
):
    """
    Memperbarui daftar model milik provider tertentu di pool tanpa menghapus provider lain.
    """
    pool_data = get_user_pool_file(user_id, public_repo_id, hf_token)
    existing_models = pool_data.get("models", [])
    
    # Hapus model lama untuk provider ini
    filtered_models = [m for m in existing_models if m.get("provider_id") != provider_id]
    
    spec = get_provider_spec(provider_id)
    speed = spec.speed_tier if spec else "medium"
    caps = spec.capabilities if spec else ["chat"]
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Tambahkan model-model baru
    for model_id in discovered_models:
        filtered_models.append({
            "provider_id": provider_id,
            "model_id": model_id,
            "capabilities": caps,
            "speed_tier": speed,
            "status": "available",
            "cooldown_until": None,
            "last_result": "discovered",
            "updated_at": now_iso
        })

    pool_data["models"] = filtered_models
    save_user_pool_file(user_id, pool_data, public_repo_id, hf_token)


def remove_provider_models_from_pool(
    user_id: str,
    provider_id: str,
    hf_token: str,
    public_repo_id: str
):
    """
    Menghapus semua model milik provider tertentu dari pool.
    """
    pool_data = get_user_pool_file(user_id, public_repo_id, hf_token)
    existing_models = pool_data.get("models", [])
    filtered_models = [m for m in existing_models if m.get("provider_id") != provider_id]
    pool_data["models"] = filtered_models
    save_user_pool_file(user_id, pool_data, public_repo_id, hf_token)


def get_ranked_pool(
    user_id: str,
    public_repo_id: str = "",
    hf_token: Optional[str] = None,
    capability: str = "chat",
    local_pool_data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Algoritma Ranking Rotasi (Section 12.4):
    1. Self-healing: Cooldown yang waktunya sudah lewat otomatis pulih jadi 'available'.
    2. Pisahkan: available vs cooldown (buang yang 'disabled').
    3. available[] diurutkan: Kecepatan tertinggi dulu (fast > medium > slow).
    4. cooldown[] diurutkan: Waktu pulih paling dekat ditaruh paling depan.
    5. Return available + cooldown (cooldown selalu di belakang available).
    """
    data = local_pool_data or get_user_pool_file(user_id, public_repo_id, hf_token)
    models = data.get("models", [])
    now_dt = datetime.datetime.now(datetime.timezone.utc)

    available_list = []
    cooldown_list = []
    speed_order = {"fast": 0, "medium": 1, "slow": 2}

    for item in models:
        # Filter kapabilitas
        if capability not in item.get("capabilities", ["chat"]):
            continue

        status = item.get("status", "available")
        cooldown_until_str = item.get("cooldown_until")

        # 1. Self-healing
        if status == "cooldown" and cooldown_until_str:
            cd_dt = parse_iso_datetime(cooldown_until_str)
            if cd_dt and cd_dt <= now_dt:
                item["status"] = "available"
                item["cooldown_until"] = None
                status = "available"

        # 2. Pengelompokan
        if status == "available":
            available_list.append(item)
        elif status == "cooldown":
            cooldown_list.append(item)
        # Status 'disabled' sengaja dilewati

    # 3. Urutkan available berdasarkan kecepatan
    available_list.sort(key=lambda x: speed_order.get(x.get("speed_tier", "medium"), 1))

    # 4. Urutkan cooldown berdasarkan sisa waktu paling cepat pulih
    def get_cd_timestamp(x):
        dt = parse_iso_datetime(x.get("cooldown_until"))
        return dt.timestamp() if dt else float("inf")

    cooldown_list.sort(key=get_cd_timestamp)

    return available_list + cooldown_list


def mark_model_status(
    user_id: str,
    provider_id: str,
    model_id: str,
    status: str,
    cooldown_seconds: Optional[int] = None,
    last_result: str = "success",
    public_repo_id: str = "",
    hf_token: str = ""
):
    """
    Memperbarui status satu model di pool (available / cooldown / disabled).
    """
    pool_data = get_user_pool_file(user_id, public_repo_id, hf_token)
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    updated = False

    cooldown_until_iso = None
    if status == "cooldown" and cooldown_seconds:
        cooldown_until_iso = (now_dt + datetime.timedelta(seconds=cooldown_seconds)).isoformat()

    for m in pool_data.get("models", []):
        if m.get("provider_id") == provider_id and m.get("model_id") == model_id:
            m["status"] = status
            m["cooldown_until"] = cooldown_until_iso
            m["last_result"] = last_result
            m["updated_at"] = now_dt.isoformat()
            updated = True
            break

    if updated and public_repo_id and hf_token:
        save_user_pool_file(user_id, pool_data, public_repo_id, hf_token)


def call_with_rotation(
    user_id: str,
    messages: List[Dict[str, str]],
    get_raw_key_fn: Callable[[str], str],
    public_repo_id: str = "",
    hf_token: str = "",
    capability: str = "chat",
    temperature: float = 0.7,
    max_tokens: int = 2048,
    json_mode: bool = False
) -> Tuple[str, Dict[str, str]]:
    """
    Eksekusi request ke pool model dengan failover otomatis.
    Jika model pertama gagal (429/401/error), otomatis mencoba model berikutnya di antrean.
    """
    pool = get_ranked_pool(user_id, public_repo_id, hf_token, capability=capability)
    if not pool:
        # Fallback: Auto-inject defaults if pool state is empty (e.g. serverless UI mode)
        groq_key = get_raw_key_fn("groq")
        if groq_key:
            pool.append({
                "provider_id": "groq",
                "model_id": "llama3-8b-8192",
                "status": "available",
                "speed_tier": "fast",
                "capabilities": ["chat", "vision"]
            })
            pool.append({
                "provider_id": "groq",
                "model_id": "llama-3.3-70b-versatile",
                "status": "available",
                "speed_tier": "medium",
                "capabilities": ["chat", "vision"]
            })
        gemini_key = get_raw_key_fn("gemini")
        if gemini_key:
            pool.append({
                "provider_id": "gemini",
                "model_id": "gemini-1.5-flash",
                "status": "available",
                "speed_tier": "fast",
                "capabilities": ["chat", "vision"]
            })

    if not pool:
        raise RuntimeError("Belum ada provider/model LLM yang tersambung di akun Anda. Silakan sambungkan key di Tab Pengaturan.")

    attempt_errors = []

    for entry in pool:
        provider_id = entry.get("provider_id")
        model_id = entry.get("model_id")
        status = entry.get("status")
        cooldown_until = entry.get("cooldown_until")

        # Jika sampai ke entry yang masih cooldown, artinya SEMUA model di pool sedang cooldown
        if status == "cooldown":
            remaining = format_countdown(cooldown_until)
            raise RuntimeError(f"Semua model LLM di pool Anda sedang cooldown. Model tercepat akan pulih dalam {remaining}. Silakan coba beberapa saat lagi atau tambah provider baru di Pengaturan.")

        spec = get_provider_spec(provider_id)
        if not spec or spec.adapter != "openai_compatible":
            continue

        raw_key = get_raw_key_fn(provider_id)
        if not raw_key:
            mark_model_status(user_id, provider_id, model_id, "disabled", last_result="missing_key", public_repo_id=public_repo_id, hf_token=hf_token)
            attempt_errors.append(f"{provider_id}/{model_id}: API key tidak ditemukan")
            continue

        url = f"{spec.base_url.rstrip('/')}{spec.chat_path}"
        headers = {
            "Authorization": f"Bearer {raw_key.strip()}",
            "Content-Type": "application/json",
            "User-Agent": "AutoClipper-Engine/2.1"
        }
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if json_mode and provider_id in ("groq", "openrouter", "gemini"):
            payload["response_format"] = {"type": "json_object"}

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=45)
            
            # Sukses
            if resp.status_code == 200:
                res_data = resp.json()
                content = res_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                mark_model_status(user_id, provider_id, model_id, "available", last_result="success", public_repo_id=public_repo_id, hf_token=hf_token)
                return content, {"provider_id": provider_id, "model_id": model_id}

            # Rate Limited (429)
            elif resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                cd_seconds = int(retry_after) if (retry_after and retry_after.isdigit()) else (60 if spec.default_rpm else 120)
                mark_model_status(user_id, provider_id, model_id, "cooldown", cooldown_seconds=cd_seconds, last_result="rate_limited", public_repo_id=public_repo_id, hf_token=hf_token)
                attempt_errors.append(f"{provider_id}/{model_id} (Rate Limited - Jeda {cd_seconds}s)")
                continue

            # Key Invalid (401 / 403)
            elif resp.status_code in (401, 403):
                mark_model_status(user_id, provider_id, model_id, "disabled", last_result="invalid_key", public_repo_id=public_repo_id, hf_token=hf_token)
                attempt_errors.append(f"{provider_id}/{model_id} (Key Ditolak / Invalid)")
                continue

            else:
                attempt_errors.append(f"{provider_id}/{model_id} (Error {resp.status_code}: {resp.text[:80]})")
                continue

        except requests.exceptions.Timeout:
            attempt_errors.append(f"{provider_id}/{model_id} (Timeout 45s)")
            continue
        except Exception as e:
            attempt_errors.append(f"{provider_id}/{model_id} ({str(e)[:80]})")
            continue

    # Jika semua model gagal
    err_summary = "; ".join(attempt_errors)
    raise RuntimeError(f"Semua provider di pool gagal dieksekusi: {err_summary}. Silakan periksa kunci di Tab Pengaturan.")
