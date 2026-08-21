"""
Kriptografi Helper (Fernet AES-128)
Digunakan untuk mendekripsi credential di memori runner saat job berjalan.
"""

import os
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken


def get_master_key() -> bytes:
    """Mengambil master encryption key dari environment variable."""
    key = os.getenv("MASTER_ENCRYPTION_KEY")
    if not key:
        raise ValueError("Environment variable MASTER_ENCRYPTION_KEY belum disetel!")
    return key.strip().encode()


def encrypt_data(raw_text: str, master_key: Optional[bytes] = None) -> str:
    """
    Mengenkripsi string plaintext menjadi ciphertext terenkripsi (Fernet).
    """
    if not raw_text:
        return ""
    key = master_key or get_master_key()
    fernet = Fernet(key)
    encrypted_bytes = fernet.encrypt(raw_text.strip().encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_data(encrypted_text: str, master_key: Optional[bytes] = None) -> str:
    """
    Mendekripsi ciphertext Fernet kembali menjadi plaintext.
    """
    if not encrypted_text:
        return ""
    key = master_key or get_master_key()
    fernet = Fernet(key)
    try:
        decrypted_bytes = fernet.decrypt(encrypted_text.strip().encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except InvalidToken:
        raise ValueError("Gagal mendekripsi credential: MASTER_ENCRYPTION_KEY tidak cocok atau data rusak!")


def mask_key_preview(raw_key: str) -> str:
    """
    Mengambil 4 karakter terakhir untuk preview aman di UI (misal: '•••• a1B2').
    """
    if not raw_key:
        return "•••• ----"
    clean = raw_key.strip()
    last4 = clean[-4:] if len(clean) >= 4 else clean
    return f"•••• {last4}"
