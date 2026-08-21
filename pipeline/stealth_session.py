"""
Stealth Session Helper (Tier 3 YouTube Anti-Bot)
Menggunakan CloakBrowser / Playwright stealth Chromium untuk menghasilkan
session cookies dan PO-token segar saat yt-dlp diblokir oleh bot verification.
"""

import os
import tempfile
from typing import Optional


def get_stealth_cookies_file(output_path: Optional[str] = None) -> Optional[str]:
    """
    Menjalankan Playwright / CloakBrowser headless untuk handshake ke YouTube
    dan mengekstrak cookies dalam format Netscape.
    """
    target_file = output_path or tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".txt", encoding="utf-8"
    ).name

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[Warning] Playwright belum terinstall di runner, melewati Tier 3.")
        return None

    cloak_bin = os.getenv("CLOAKBROWSER_BIN", "/opt/cloakbrowser/chrome")
    executable_path = cloak_bin if os.path.exists(cloak_bin) else None

    try:
        with sync_playwright() as p:
            launch_args = [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars"
            ]
            browser = p.chromium.launch(
                executable_path=executable_path,
                headless=True,
                args=launch_args
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()
            
            # Kunjungi YouTube untuk memicu handshake botguard
            page.goto("https://www.youtube.com", wait_until="networkidle", timeout=25000)
            
            cookies = context.cookies()
            browser.close()

            # Format ke Netscape cookies
            lines = ["# Netscape HTTP Cookie File", "# https://curl.haxx.se/rfc/cookie_spec.html", ""]
            for c in cookies:
                domain = c.get("domain", "")
                flag = "TRUE" if domain.startswith(".") else "FALSE"
                path = c.get("path", "/")
                secure = "TRUE" if c.get("secure", False) else "FALSE"
                expires = int(c.get("expires", 0))
                if expires <= 0:
                    expires = 2147483647  # Far future
                name = c.get("name", "")
                value = c.get("value", "")
                lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}")

            with open(target_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

            return target_file

    except Exception as e:
        print(f"[Warning] Gagal menjalankan Stealth Session: {e}")
        return None
