"""
LLM Router (Engine Compute Layer)
Pintu masuk tunggal pemanggilan LLM untuk detect_highlights, generate_content,
build_schedule, dan summarize_performance.
Membungkus call_with_rotation() dengan automatic key fetching dan pembersihan JSON.
"""

import os
import json
import re
from typing import List, Dict, Any, Tuple

from pipeline.model_pool import call_with_rotation
from pipeline.fetch_user_key import get_user_key


def clean_json_markdown(text: str) -> str:
    """
    Membersihkan markdown code blocks (```json ... ```) dari output respons LLM.
    """
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```[a-zA-Z]*\n?", "", clean)
        clean = re.sub(r"\n?```$", "", clean)
    return clean.strip()


def call_llm(
    user_id: str,
    messages: List[Dict[str, str]],
    capability: str = "chat",
    temperature: float = 0.7,
    max_tokens: int = 2048,
    json_mode: bool = False
) -> Tuple[str, Dict[str, str]]:
    """
    Memanggil LLM dengan rotasi otomatis menggunakan key milik user.
    """
    public_repo_id = os.getenv("HF_DATASET_REPO_ID", "")
    hf_token = os.getenv("HF_TOKEN", "")

    raw_text, llm_used = call_with_rotation(
        user_id=user_id,
        messages=messages,
        get_raw_key_fn=lambda p_id: get_user_key(user_id, p_id),
        public_repo_id=public_repo_id,
        hf_token=hf_token,
        capability=capability,
        temperature=temperature,
        max_tokens=max_tokens,
        json_mode=json_mode
    )
    return raw_text, llm_used


def call_llm_json(
    user_id: str,
    messages: List[Dict[str, str]],
    capability: str = "chat",
    temperature: float = 0.5,
    max_tokens: int = 2048
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Memanggil LLM dan mem-parsing output menjadi Python Dictionary JSON yang valid.
    Dilengkapi 1x retry jika parsing JSON pertama kali gagal.
    """
    raw_text, llm_used = call_llm(
        user_id=user_id,
        messages=messages,
        capability=capability,
        temperature=temperature,
        max_tokens=max_tokens,
        json_mode=True
    )

    cleaned = clean_json_markdown(raw_text)
    try:
        parsed = json.loads(cleaned)
        return parsed, llm_used
    except json.JSONDecodeError:
        # Percobaan retry dengan instruksi perbaikan format
        repair_messages = list(messages) + [
            {"role": "assistant", "content": raw_text},
            {"role": "user", "content": "Format JSON Anda sebelumnya tidak valid. Kembalikan HANYA string JSON murni tanpa pembuka/penutup teks markdown apapun."}
        ]
        retry_raw, retry_llm_used = call_llm(
            user_id=user_id,
            messages=repair_messages,
            capability=capability,
            temperature=0.2,
            max_tokens=max_tokens,
            json_mode=True
        )
        retry_cleaned = clean_json_markdown(retry_raw)
        try:
            parsed_retry = json.loads(retry_cleaned)
            return parsed_retry, retry_llm_used
        except Exception as e:
            raise ValueError(f"Gagal mem-parsing JSON dari respons LLM ({llm_used}): {e}\nRaw output: {raw_text[:200]}")
