import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))
from browser.cf_solver import get_cf_cookies

async def pod(page, selector, attribute, target_value):
    print(f"Running POD: Finding row containing '{attribute}' and '{target_value}'...")
    rows = await page.locator(selector).all()
    for i, row in enumerate(rows):
        try:
            # Expand row
            if await row.is_visible():
                await row.click(timeout=1000)
                await asyncio.sleep(0.5)
        except Exception:
            pass

        # Check row text, parent, AND grandparent text (in case of accordion sibling)
        text = await row.inner_text()
        parent_text = ''
        grandparent_text = ''
        try:
             parent_text = await row.locator('..').inner_text()
             grandparent_text = await row.locator('../..').inner_text()
        except:
             pass
        
        combined_text = text + ' ' + parent_text + ' ' + grandparent_text
        if attribute.lower() in combined_text.lower() and target_value.lower() in combined_text.lower():
            print(f"POD Match Found in Row {i}...")
            await row.scroll_into_view_if_needed()
            # Ensure it stays expanded
            await row.click(force=True)
            return row
    print("POD: No match found.")
    return None

async def run():
    # Start URL
    url = 'https://sosnc.gov/online_services/search/by_title/search_Business_Registration'

    print('Solving Cloudflare challenge...')
    cookies, user_agent = await get_cf_cookies(url, headless=False)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(user_agent=user_agent)
        
        if cookies:
            clean_cookies = []
            for c in cookies:
                c_clean = {k: v for k, v in c.items() if k in ['name', 'value', 'domain', 'path', 'expires', 'httpOnly', 'secure', 'sameSite']}
                clean_cookies.append(c_clean)
            await context.add_cookies(clean_cookies)

        page = await context.new_page()

    # Steps
        await page.goto('https://sosnc.gov/online_services/search/by_title/search_Business_Registration')
        await page.get_by_label('Organizational name', exact=False).first.fill('Rely')
        await page.keyboard.press('Enter')
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(5.0)
        matched_row = await pod(page, 'button', 'Date formed', '1/1/2001')
        if matched_row:
            # 1. Get Panel ID
            panel_id = await matched_row.get_attribute('aria-controls')
            # 2. Expand Row (Try clicking search term or just row)
            try:
                 await matched_row.get_by_text('Rely', exact=False).click()
            except:
                 await matched_row.click()
            await asyncio.sleep(1)
            # 3. Click inside Panel
            if panel_id:
                await page.locator(f'#{panel_id}').get_by_text('More information', exact=False).first.click()
            else:
                # Fallback: strict sibling
                await matched_row.locator('xpath=./../following-sibling::*[1]').get_by_text('More information', exact=False).first.click()
        await asyncio.sleep(5.0)

        # Scrape Content
        print('Waiting for page to assume final state...')
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)
        content = await page.content()
        print(await page.evaluate('document.body.innerText'))
        await browser.close()

if __name__ == '__main__':
    asyncio.run(run())