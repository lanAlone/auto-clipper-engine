"""
Advanced Playwright YouTube Handshake
"""
import os
import tempfile
from typing import Optional

def generate_youtube_session_cookies(video_id: str, output_cookie_path: Optional[str] = None) -> Optional[str]:
    target_file = output_cookie_path or tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".txt", encoding="utf-8"
    ).name

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars"
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720}
            )
            page = context.new_page()
            
            # Kunjungi Embed Page YouTube untuk mendapatkan token otentikasi player
            embed_url = f"https://www.youtube.com/embed/{video_id}?autoplay=1"
            try:
                page.goto(embed_url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(3000)
            except Exception:
                pass
            
            cookies = context.cookies()
            browser.close()

            if not cookies:
                return None

            lines = ["# Netscape HTTP Cookie File", "# https://curl.haxx.se/rfc/cookie_spec.html", ""]
            for c in cookies:
                domain = c.get("domain", "")
                flag = "TRUE" if domain.startswith(".") else "FALSE"
                path = c.get("path", "/")
                secure = "TRUE" if c.get("secure", False) else "FALSE"
                expires = int(c.get("expires", 0))
                if expires <= 0:
                    expires = 2147483647
                name = c.get("name", "")
                value = c.get("value", "")
                lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}")

            with open(target_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

            return target_file
    except Exception as e:
        print(f"[Warning] Stealth handshake error: {e}")
        return None
