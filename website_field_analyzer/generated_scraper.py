import asyncio
from playwright.async_api import async_playwright
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))
from browser.cf_solver import get_cf_cookies

async def run():
    print("Solving Cloudflare challenge...")
    # NOTE: Update the URL to match your target
    url = "https://sosnc.gov/online_services/search/by_title/search_Business_Registration" 
    cookies, user_agent = await get_cf_cookies(url, headless=False)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(user_agent=user_agent)
        
        if cookies:
             # Clean cookies if needed
            clean_cookies = []
            for c in cookies:
                c_clean = {k: v for k, v in c.items() if k in ['name', 'value', 'domain', 'path', 'expires', 'httpOnly', 'secure', 'sameSite']}
                clean_cookies.append(c_clean)
            await context.add_cookies(clean_cookies)
            
        page = await context.new_page()

        await page.goto('https://sosnc.gov/online_services/search/by_title/search_Business_Registration')
        await page.locator('#SearchCriteria').first.fill('Rely')
        await page.keyboard.press('Enter')
        print("Waiting for results...")
        await page.wait_for_timeout(5000) # Wait for search to complete
        
        # await page.get_by_text('Rely', exact=False).first.click() # Removing potential duplicate/wrong click
        print("Clicking company...")
        await page.get_by_text('RELY, LLC', exact=False).first.click()
        
        print("Waiting for expansion...")
        await page.wait_for_timeout(2000) 
        
        print("Clicking More Info...")
        await page.get_by_text('More information', exact=False).first.click()
        await page.wait_for_timeout(3000) # Wait for page load

        # Scrape Content
        content = await page.content()
        print(await page.evaluate('document.body.innerText'))
        await browser.close()

if __name__ == '__main__':
    asyncio.run(run())