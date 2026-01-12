import asyncio
import pandas as pd
import sys
from playwright.async_api import async_playwright
# Import scraper logic
from generated_scraper import scrape_company
from browser.cf_solver import get_cf_cookies
import os

async def setup_browser():
    url = 'https://sosnc.gov/online_services/search/by_title/search_Business_Registration'
    print('Solving Cloudflare challenge (this may take a moment)...')
    cookies, user_agent = await get_cf_cookies(url, headless=False)

    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False)
    context = await browser.new_context(user_agent=user_agent)
    
    if cookies:
        clean_cookies = []
        for c in cookies:
             # Basic cleaning if needed, or just pass
             clean_cookies.append(c)
        await context.add_cookies(clean_cookies)

    page = await context.new_page()
    return p, browser, context, page

async def main():
    # 1. Load Excel
    input_file = r"C:\Users\TSPL159\OneDrive - Tristone Strategic Partners LLP\Documents\isha\website_field_analyzer\Sample Companies - SoS.xlsx"
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Please provide the file.")
        return

    print(f"Loading {input_file}...")
    try:
        df = pd.read_excel(input_file)
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return

    # Check columns
    if len(df.columns) < 2:
        print("Error: Excel file must have at least 2 columns (Company, Attribute).")
        return

    # Get POD Attribute from Column 2 Header
    pod_attribute = df.columns[1] 
    print(f"Detected POD Attribute from Header: '{pod_attribute}'")

    # Initial Browser Setup
    playwright_instance, browser, context, page = await setup_browser()

    # 3. Iterate Rows
    results = []
    
    for index, row in df.iterrows():
        company_name = str(row.iloc[0]).strip()
        pod_value = str(row.iloc[1]).strip()
        
        print(f"\n[{index+1}/{len(df)}] Processing: {company_name}")
        
        max_retries = 2
        outcome = "Error"
        
        for attempt in range(max_retries + 1):
            try:
                # Attempt Scrape
                success = await scrape_company(page, company_name, pod_attribute, pod_value)
                if success:
                    outcome = "Found"
                    break # Success, exit retry loop
                else:
                    outcome = "Not Found"
                    break # Logic handled, but result was 'not found'. No need to retry unless it was a session error?
                    # If it returned False, it means page loaded but row wasn't there.
                    # If it was a Timeout, it raises Exception.
            except Exception as e:
                print(f"Attempt {attempt+1} failed: {e}")
                if attempt < max_retries:
                    print("Possible Cloudflare block. Refreshing session...")
                    # Close old
                    try:
                        await context.close()
                        await browser.close()
                        await playwright_instance.stop()
                    except:
                        pass
                    
                    # Re-init
                    playwright_instance, browser, context, page = await setup_browser()
                else:
                    outcome = f"Error: {e}"

        results.append({
            "Company": company_name,
            "Result": outcome
        })
        
        # Save on every row to prevent data loss
        pd.DataFrame(results).to_excel("scraped_results.xlsx", index=False)
        
        await asyncio.sleep(2)

    # Cleanup
    await browser.close()
    await playwright_instance.stop()
    print("\nDone! Results saved to scraped_results.xlsx")

if __name__ == "__main__":
    asyncio.run(main())
