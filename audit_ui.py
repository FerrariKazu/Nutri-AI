import asyncio
from playwright.async_api import async_playwright
import os

async def audit_ui():
    async with async_playwright() as p:
        print("🌐 Launching browser for audit...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        try:
            print("🔗 Navigating to http://localhost:5173...")
            await page.goto("http://localhost:5173", timeout=10000, wait_until="networkidle")
            
            # 1. Type query
            print("⌨️ Typing query 'Why is coffee bitter?'")
            # Wait for specific input by id or placeholder
            await page.wait_for_selector('textarea', state='visible')
            await page.fill('textarea', "Why is coffee bitter?")
            await page.keyboard.press("Enter")
            
            # 2. Wait for response and panel
            print("⏳ Waiting for Intelligence Panel...")
            # Adjust selector based on component names - usually a 'button' or 'header' for the panel
            # Let's look for "Nutri Intelligence" text
            await page.wait_for_selector('text="Nutri Intelligence"', timeout=30000)
            
            # 3. Open Panel if collapsed
            # Usually clickable
            await page.click('text="Nutri Intelligence"')
            await asyncio.sleep(2) # Animation
            
            # 4. Check for Perception UI
            print("🧐 Checking for 'Biological Perception' text...")
            perception_text = await page.query_selector('text="Biological Perception"')
            if perception_text:
                print("✅ Found 'Biological Perception' UI element!")
            else:
                print("❌ 'Biological Perception' UI NOT FOUND in DOM.")
                
            # 5. Capture Screenshot
            screenshot_path = "/home/ferrarikazu/nutri-ai/ui_audit.png"
            await page.screenshot(path=screenshot_path)
            print(f"📸 Screenshot saved to {screenshot_path}")
            
            # 6. Dump basic HTML of the panel for debugging
            panel_html = await page.evaluate("() => document.querySelector('.space-y-10')?.innerHTML")
            if panel_html:
                 with open("/home/ferrarikazu/nutri-ai/panel_dump.html", "w") as f:
                     f.write(panel_html)
                 print("📄 Panel HTML dumped to panel_dump.html")
            
        except Exception as e:
            print(f"⚠️ Audit Failed: {e}")
            # Take emergency screenshot
            await page.screenshot(path="/home/ferrarikazu/nutri-ai/error_audit.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(audit_ui())
