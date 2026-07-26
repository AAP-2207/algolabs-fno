import asyncio
import os
import sys

# Ensure UTF-8 stdout on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright

async def main():
    artifacts_dir = r"C:\Users\armaa\.gemini\antigravity-ide\brain\0af790bf-0e4a-46a5-96af-659437c4a184"
    os.makedirs(artifacts_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 1000})
        
        print("Navigating to http://localhost:5173/greeks...")
        await page.goto("http://localhost:5173/greeks", wait_until="networkidle")
        
        await page.wait_for_selector("#simulated-data-banner", timeout=10000)
        await page.wait_for_timeout(3000)
        
        text = await page.inner_text("main")
        print("\n=== EXTRACTED MAIN CONTENT INNER TEXT FROM /greeks ===")
        print(text)
        print("====================================================\n")
        
        banner_text = await page.inner_text("#simulated-data-banner")
        print("=== VISIBLE BANNER TEXT ===")
        print(banner_text)
        print("===========================\n")
        
        desktop_img = os.path.join(artifacts_dir, "greeks_3d_surface_desktop.png")
        await page.screenshot(path=desktop_img, full_page=True)
        print(f"Desktop screenshot saved to: {desktop_img}")
        
        # Mobile viewport check (390px)
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.wait_for_timeout(1500)
        mobile_img = os.path.join(artifacts_dir, "greeks_3d_surface_mobile.png")
        await page.screenshot(path=mobile_img, full_page=True)
        print(f"Mobile screenshot saved to: {mobile_img}")
        
        # Option Chain page (/chain) regression check
        print("\nNavigating to http://localhost:5173/chain for regression check...")
        chain_page = await browser.new_page(viewport={"width": 1400, "height": 900})
        await chain_page.goto("http://localhost:5173/chain", wait_until="networkidle")
        await chain_page.wait_for_selector("table", timeout=10000)
        await chain_page.wait_for_timeout(1000)
        chain_text = await chain_page.inner_text("main")
        print("\n=== EXTRACTED OPTION CHAIN MAIN TEXT ===")
        print(chain_text[:600])
        print("========================================")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
