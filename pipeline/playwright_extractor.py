import asyncio
from playwright.async_api import async_playwright
import os
import re

async def extract_youtube_stream(url: str, cookies_file: str = None) -> str:
    """
    Membuka YouTube di browser asli (Playwright) untuk mengeksekusi BotGuard JS
    dan mencegat URL stream audio mentah (videoplayback).
    """
    async with async_playwright() as p:
        # Launch browser with stealth-like arguments
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--mute-audio"
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Inject cookies if provided
        if cookies_file and os.path.exists(cookies_file) and os.path.getsize(cookies_file) > 10:
            playwright_cookies = []
            with open(cookies_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.startswith('#') and line.strip():
                        parts = line.strip().split('\t')
                        if len(parts) >= 7:
                            domain = parts[0]
                            name = parts[5]
                            value = parts[6]
                            playwright_cookies.append({
                                'name': name,
                                'value': value,
                                'domain': domain.replace('#HttpOnly_', ''),
                                'path': '/'
                            })
            if playwright_cookies:
                await context.add_cookies(playwright_cookies)

        page = await context.new_page()
        
        # Intercept network requests
        stream_url = None
        
        async def handle_request(route, request):
            nonlocal stream_url
            # Cari URL videoplayback yang mengandung audio (mime=audio) atau itag m4a
            if "videoplayback" in request.url:
                if "mime=audio" in request.url or "itag=140" in request.url or "itag=251" in request.url:
                    if not stream_url:
                        stream_url = request.url
            await route.continue_()
            
        await page.route("**/*", handle_request)
        
        try:
            print(f"[PlaywrightExtractor] Membuka {url} ...")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Tunggu sebentar agar BotGuard selesai memvalidasi dan stream dimulai
            for _ in range(15):
                if stream_url:
                    break
                await asyncio.sleep(1)
                
            # Coba klik tombol play jika video tidak autoplay
            if not stream_url:
                try:
                    await page.click(".ytp-large-play-button", timeout=2000)
                    for _ in range(5):
                        if stream_url:
                            break
                        await asyncio.sleep(1)
                except:
                    pass
                    
        except Exception as e:
            print(f"[PlaywrightExtractor] Error saat memuat halaman: {e}")
            
        await browser.close()
        return stream_url

def get_stream_url_sync(url: str, cookies_file: str = None) -> str:
    return asyncio.run(extract_youtube_stream(url, cookies_file))
