"""
Multi-Provider LLM Registry
Definisi spesifikasi semua provider/router LLM yang didukung sistem.
File ini statis dan identik antara Repo A (Engine) dan Repo B (UI).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ProviderSpec:
    provider_id: str
    display_name: str
    base_url: str
    models_path: str = "/models"
    chat_path: str = "/chat/completions"
    adapter: str = "openai_compatible"  # "openai_compatible" | "custom_unsupported"
    free_filter: str = "all_free"       # "all_free" | "suffix_free" (:free) | "explicit_list"
    explicit_free_models: List[str] = field(default_factory=list)
    speed_tier: str = "fast"            # "fast" | "medium" | "slow"
    capabilities: List[str] = field(default_factory=lambda: ["chat"])
    default_rpm: int = 30
    default_rpd: int = 14400
    docs_url: str = ""
    icon: str = "⚡"
    notes: str = ""


# Katalog provider resmi
PROVIDER_REGISTRY: Dict[str, ProviderSpec] = {
    "groq": ProviderSpec(
        provider_id="groq",
        display_name="Groq (LPU Ultra-Fast)",
        base_url="https://api.groq.com/openai/v1",
        models_path="/models",
        chat_path="/chat/completions",
        adapter="openai_compatible",
        free_filter="all_free",
        speed_tier="fast",
        capabilities=["chat", "audio"],
        default_rpm=30,
        default_rpd=14400,
        docs_url="https://console.groq.com/keys",
        icon="⚡",
        notes="Sangat cepat, key yang sama dipakai untuk Groq Whisper transkripsi."
    ),
    "gemini": ProviderSpec(
        provider_id="gemini",
        display_name="Google Gemini (AI Studio)",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        models_path="/models",
        chat_path="/models/gemini-1.5-flash:generateContent",
        adapter="gemini_native",
        free_filter="all_free",
        speed_tier="fast",
        capabilities=["chat"],
        default_rpm=15,
        default_rpd=1500,
        docs_url="https://aistudio.google.com/app/apikey",
        icon="✨",
        notes="Kapasitas context window besar dan reasoning akurat (Gemini 1.5 Flash)."
    ),
    "openrouter": ProviderSpec(
        provider_id="openrouter",
        display_name="OpenRouter (Multi-Model Pool)",
        base_url="https://openrouter.ai/api/v1",
        models_path="/models",
        chat_path="/chat/completions",
        adapter="openai_compatible",
        free_filter="suffix_free",
        speed_tier="medium",
        capabilities=["chat"],
        default_rpm=20,
        default_rpd=50,
        docs_url="https://openrouter.ai/keys",
        icon="🌐",
        notes="Akses puluhan model gratis (:free) seperti Llama-3.3, Mistral, dan Qwen."
    ),
    "cerebras": ProviderSpec(
        provider_id="cerebras",
        display_name="Cerebras (Wafer-Scale Fast)",
        base_url="https://api.cerebras.ai/v1",
        models_path="/models",
        chat_path="/chat/completions",
        adapter="openai_compatible",
        free_filter="all_free",
        speed_tier="fast",
        capabilities=["chat"],
        default_rpm=30,
        default_rpd=14400,
        docs_url="https://cloud.cerebras.ai",
        icon="🧠",
        notes="Kecepatan generasi ultra tinggi berbasis hardware wafer-scale."
    ),
    "mistral": ProviderSpec(
        provider_id="mistral",
        display_name="Mistral AI (La Plateforme)",
        base_url="https://api.mistral.ai/v1",
        models_path="/models",
        chat_path="/chat/completions",
        adapter="openai_compatible",
        free_filter="all_free",
        speed_tier="medium",
        capabilities=["chat"],
        default_rpm=60,
        default_rpd=10000,
        docs_url="https://console.mistral.ai/api-keys",
        icon="🌪️",
        notes="Model open-weights berkualitas tinggi (Mistral Small / Nemo)."
    ),
    "github_models": ProviderSpec(
        provider_id="github_models",
        display_name="GitHub Models (Azure AI)",
        base_url="https://models.inference.ai.azure.com",
        models_path="/models",
        chat_path="/chat/completions",
        adapter="openai_compatible",
        free_filter="all_free",
        speed_tier="medium",
        capabilities=["chat"],
        default_rpm=15,
        default_rpd=150,
        docs_url="https://github.com/marketplace/models",
        icon="🐙",
        notes="Menggunakan GitHub Personal Access Token (PAT) gratis."
    ),
    "nvidia_nim": ProviderSpec(
        provider_id="nvidia_nim",
        display_name="NVIDIA NIM (Inference Microservice)",
        base_url="https://integrate.api.nvidia.com/v1",
        models_path="/models",
        chat_path="/chat/completions",
        adapter="openai_compatible",
        free_filter="all_free",
        speed_tier="medium",
        capabilities=["chat"],
        default_rpm=40,
        default_rpd=1000,
        docs_url="https://build.nvidia.com",
        icon="🟢",
        notes="Infrastruktur cloud NVIDIA dengan free trial credits."
    ),
    "huggingface": ProviderSpec(
        provider_id="huggingface",
        display_name="Hugging Face Inference Providers",
        base_url="https://api-inference.huggingface.co/v1",
        models_path="/models",
        chat_path="/chat/completions",
        adapter="openai_compatible",
        free_filter="all_free",
        speed_tier="slow",
        capabilities=["chat"],
        default_rpm=10,
        default_rpd=500,
        docs_url="https://huggingface.co/settings/tokens",
        icon="🤗",
        notes="Menggunakan HF User Access Token."
    ),
    "cohere": ProviderSpec(
        provider_id="cohere",
        display_name="Cohere API (Custom Adapter)",
        base_url="https://api.cohere.com/v2",
        models_path="/models",
        chat_path="/chat",
        adapter="custom_unsupported",
        free_filter="all_free",
        speed_tier="medium",
        capabilities=["chat"],
        default_rpm=20,
        default_rpd=1000,
        docs_url="https://dashboard.cohere.com/api-keys",
        icon="💠",
        notes="Disimpan untuk pengembangan adapter khusus (Fase lanjutan)."
    ),
    "cloudflare": ProviderSpec(
        provider_id="cloudflare",
        display_name="Cloudflare Workers AI",
        base_url="https://api.cloudflare.com/client/v4",
        models_path="/models",
        chat_path="/ai/run",
        adapter="custom_unsupported",
        free_filter="all_free",
        speed_tier="medium",
        capabilities=["chat"],
        default_rpm=60,
        default_rpd=10000,
        docs_url="https://dash.cloudflare.com/profile/api-tokens",
        icon="☁️",
        notes="10.000 neuron gratis per hari (membutuhkan account ID)."
    )
}


def get_provider_spec(provider_id: str) -> Optional[ProviderSpec]:
    """Mengambil spesifikasi provider dari registry berdasarkan ID."""
    return PROVIDER_REGISTRY.get(provider_id.lower().strip())


def list_rotatable_providers() -> List[ProviderSpec]:
    """Mengembalikan daftar provider yang sudah siap rotasi otomatis (OpenAI compatible)."""
    return [p for p in PROVIDER_REGISTRY.values() if p.adapter == "openai_compatible"]


def list_all_providers() -> List[ProviderSpec]:
    """Mengembalikan seluruh katalog provider."""
    return list(PROVIDER_REGISTRY.values())
