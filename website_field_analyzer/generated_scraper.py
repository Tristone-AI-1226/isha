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
        
        match_found = False
        
        # 1. Direct String Match
        if attribute.lower() in combined_text.lower() and target_value.lower() in combined_text.lower():
            match_found = True
            
        # 2. Smart Date Match (Fall back if string fail)
        if not match_found and attribute.lower() in combined_text.lower():
            try:
                from dateutil import parser
                # Try to parse the target value (e.g. 2000-11-22)
                target_dt = parser.parse(target_value)
                
                # Extract text potentially containing the date (after the attribute)
                # We lowercase for search
                lower_text = combined_text.lower()
                attr_idx = lower_text.find(attribute.lower())
                if attr_idx != -1:
                    # Look at the next 100 chars
                    snippet = combined_text[attr_idx + len(attribute): attr_idx + len(attribute) + 100]
                    # fuzzy=True extracts the date from the string
                    found_dt = parser.parse(snippet, fuzzy=True)
                    
                    if found_dt.date() == target_dt.date():
                        match_found = True
                        print(f"POD: Fuzzy Date Match! Expected {target_dt.date()} found {found_dt.date()}")
            except:
                # Not a date or parse failure - ignore
                pass

        if match_found:
            print(f"POD Match Found in Row {i}...")
            await row.scroll_into_view_if_needed()
            # Ensure it stays expanded
            await row.click(force=True)
            return row
    print("POD: No match found.")
    return None

async def scrape_company(page, company_name, pod_attr, pod_value):
    print(f"Scraping Company: {company_name} | POD: {pod_attr}={pod_value}")
    
    # 1. Search for Company
    await page.goto('https://sosnc.gov/online_services/search/by_title/search_Business_Registration')
    await page.get_by_label('Organizational name', exact=False).first.fill(company_name)
    await page.keyboard.press('Enter')
    await page.wait_for_load_state('networkidle')
    await asyncio.sleep(3.0) # Wait for results
    
    matched_row = None
    
    # Check for "Skip POD" condition
    if "########" in str(pod_value):
        print("Flag '########' detected. Skipping POD search, selecting first result...")
        # Find the first button that looks like a result (has aria-controls)
        try:
            buttons = await page.locator('button').all()
            for btn in buttons:
                attr = await btn.get_attribute('aria-controls')
                if attr:
                    matched_row = btn
                    print("Found first result row.")
                    break
        except Exception as e:
            print(f"Error matching first row: {e}")
    else:
        # Normal POD Search
        matched_row = await pod(page, 'button', pod_attr, pod_value)

    # If we have a row (either from POD or First Result)
    if matched_row:
        # 1. Get Panel ID
        panel_id = await matched_row.get_attribute('aria-controls')
        # 2. Expand Row (Try clicking search term or just row to be safe)
        try:
             # Try to click the company name if we know it, or just the button
             # Using generic expansion since 'Rely' is hardcoded in original
             await matched_row.click()
        except:
             pass
        await asyncio.sleep(1)
        
        # 3. Click inside Panel
        if panel_id:
            await page.locator(f'#{panel_id}').get_by_text('More information', exact=False).first.click()
        else:
            await matched_row.locator('xpath=./../following-sibling::*[1]').get_by_text('More information', exact=False).first.click()
            
        # Wait for Details Page
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)
        
        # Extract Full Text
        data = await page.evaluate("document.body.innerText")
        return parse_details(data) # Return parsed dict
    else:
        print("Error: No matching row found.")
        return False

import pandas as pd
import os
import re

# ... existing imports ...

def parse_details(text):
    data = {}
    
    # Helper for single line fields
    def extract(label, content):
        # Match "Label: value" until newline
        pattern = f"{re.escape(label)}[:\s]+(.*?)(?:\n|$)"
        match = re.search(pattern, content, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    data['Legal Name'] = extract("Legal name", text)
    # Handle both full and short label for SOSID
    sosid = extract("Secretary of State Identification Number (SOSID)", text)
    if not sosid:
        sosid = extract("Sosid", text)
    data['SOSID'] = sosid
    
    data['Status'] = extract("Status", text)
    data['Date Formed'] = extract("Date formed", text)
    data['Citizenship'] = extract("Citizenship", text)
    data['Fiscal Month'] = extract("Fiscal month", text)
    data['Registered Agent'] = extract("Registered agent", text)
    
    # Helper for multi-line blocks (Addresses)
    # They generally end with another Header (Capitalized Word) or double newline
    def extract_block(header, content):
        # Look for Header + "address"
        # Capture everything until we hit a known next section or double newline
        # Heuristic: Stop at "\n\n" or "\n[Word] [Word]:"
        pattern = f"{re.escape(header)}\s+address\s*\n(.*?)(?:\n\n|\n[A-Z][a-z]+)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            # Replace newlines with comma for clean CSV/Excel
            return match.group(1).strip().replace('\n', ', ')
        return ""

    data['Principal Office Address'] = extract_block("Principal Office", text)
    data['Mailing Address'] = extract_block("Mailing", text)
    data['Registered Office Address'] = extract_block("Registered Office", text)
    data['Registered Mailing Address'] = extract_block("Registered Mailing", text)

    # Officers Block
    match = re.search(r"Officers\s*\n(.*?)(?:\n\nStock:|Stock:)", text, re.DOTALL | re.IGNORECASE)
    if match:
        data['Officers'] = match.group(1).strip().replace('\n', ', ')
    else:
        data['Officers'] = ""

    # Stock Block
    match = re.search(r"Stock:\s*\n(.*?)(?:\n\nReturn to top|Return to top)", text, re.DOTALL | re.IGNORECASE)
    if match:
        data['Stock'] = match.group(1).strip().replace('\n', ', ')
    else:
        data['Stock'] = ""

    return data


# ... existing imports ...
# (We will rely on existing imports being there or add them if missing. 
# The file already has asyncio, sys, pathlib, async_playwright, get_cf_cookies, dateutil)

async def setup_browser():
    url = 'https://sosnc.gov/online_services/search/by_title/search_Business_Registration'
    print('Solving Cloudflare challenge (this may take a moment)...')
    cookies, user_agent = await get_cf_cookies(url, headless=False)

    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False)
    context = await browser.new_context(user_agent=user_agent)
    
    # STEALTH: Webdriver removal
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    
    if cookies:
        clean_cookies = []
        for c in cookies:
             # Basic cleaning or pass through
             clean_cookies.append(c)
        await context.add_cookies(clean_cookies)

    page = await context.new_page()
    return p, browser, context, page

async def run():
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
        row_data = {}
        
        for attempt in range(max_retries + 1):
            try:
                # Attempt Scrape
                data = await scrape_company(page, company_name, pod_attribute, pod_value)
                if data:
                    outcome = "Found"
                    row_data = data
                    break # Success
                else:
                    outcome = "Not Found"
                    break # Logic handled but not found
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

        # Flatten Results
        row_result = {
            "Company": company_name,
            "Result": outcome
        }
        if row_data:
            row_result.update(row_data)
        
        results.append(row_result)
        
        # Save check
        pd.DataFrame(results).to_json("scraped_results.json", orient='records', indent=4)
        
        await asyncio.sleep(2)

    # Cleanup
    await browser.close()
    await playwright_instance.stop()
    print("\nDone! Results saved to scraped_results.json")

if __name__ == '__main__':
    asyncio.run(run())