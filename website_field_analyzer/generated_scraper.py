import asyncio
import sys
import os
import re
import pandas as pd
from pathlib import Path
from dateutil import parser
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))
from browser.cf_solver import get_cf_cookies

def scrape_all_fields(text):
    data = {}
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    block_headers = ['Registered Office address', 'Registered Mailing address', 'Mailing address', 'Principal Office address']
    current_key = None
    current_val_lines = []
    for line in lines:
        if ':' in line:
             parts = line.split(':', 1)
             potential_key = parts[0].strip()
             potential_val = parts[1].strip()
             if len(potential_key) < 60:
                 if current_key: data[current_key] = ' '.join(current_val_lines).strip()
                 current_key = potential_key
                 current_val_lines = [potential_val] if potential_val else []
                 continue
        is_header = False
        for h in block_headers:
            if h.lower() == line.lower():
                if current_key: data[current_key] = ' '.join(current_val_lines).strip()
                current_key = line
                current_val_lines = []
                is_header = True
                break
        if is_header: continue
        if current_key: current_val_lines.append(line)
    if current_key: data[current_key] = ' '.join(current_val_lines).strip()
    # Date Normalization
    for k, v in data.items():
        if re.search(r'\d+[/-]\d+[/-]\d+', v):
            try:
                dt = parser.parse(v)
                data[k] = dt.strftime('%m/%d/%Y')
            except: pass
    return data

async def pod(page, selector, attribute, target_value):
    print(f"Running POD: Finding row containing '{attribute}' and '{target_value}'...")
    rows = await page.locator(selector).all()
    for i, row in enumerate(rows):
        try:
            if await row.is_visible():
                await row.scroll_into_view_if_needed()
                panel_id = await row.get_attribute('aria-controls')
                try:
                    await row.click(timeout=1000)
                    await asyncio.sleep(0.5)
                except: pass
                
                text = await row.inner_text()
                panel_text = ''
                if panel_id:
                    panel = page.locator(f'#{panel_id}')
                    if await panel.count() > 0:
                        try: panel_text = await panel.inner_text()
                        except: pass
                combined_text = text + ' ' + panel_text
                
                # Normalize target if date
                target_str = str(target_value).strip()
                try:
                    target_dt = parser.parse(target_str)
                    target_norm = target_dt.strftime('%m/%d/%Y')
                except:
                    target_dt = None
                    target_norm = target_str
                
                # 1. Direct String Match (Original & Normalized)
                if attribute.lower() in combined_text.lower():
                    if target_str.lower() in combined_text.lower() or target_norm.lower() in combined_text.lower():
                         print(f"POD Match Found in Row {i}...")
                         return row
                    
                    # 2. Fuzzy Date Match
                    if target_dt:
                        # Regex find all date-like strings and compare
                        dates = re.findall(r'\d+[/-]\d+[/-]\d+', combined_text)
                        for d_str in dates:
                            try:
                                found_dt = parser.parse(d_str)
                                if found_dt.date() == target_dt.date():
                                     print(f"POD Match (Fuzzy Date) in Row {i}: {d_str}")
                                     return row
                            except: pass
        except Exception as e: 
            # print(f"Row check failed: {e}")
            pass
    print("POD: No match found.")
    return None

async def setup_browser():
    url = 'https://sosnc.gov/online_services/search/by_title/search_Business_Registration'
    print('Solving Cloudflare challenge...')
    cookies, user_agent = await get_cf_cookies(url, headless=False)
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False)
    context = await browser.new_context(user_agent=user_agent)
    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    if cookies:
        cl = [{k: v for k, v in c.items() if k in ['name', 'value', 'domain', 'path', 'expires', 'httpOnly', 'secure', 'sameSite']} for c in cookies]
        await context.add_cookies(cl)
    page = await context.new_page()
    return p, browser, context, page

async def scrape_company(page, company_name, pod_attr, pod_value):
    print(f"\nProcessing: {company_name} (POD: {pod_value})")
    await page.goto('https://sosnc.gov/online_services/search/by_title/search_Business_Registration')
    await page.get_by_label('Organizational name', exact=False).first.fill(company_name)
    await page.keyboard.press('Enter')
    await page.wait_for_load_state('networkidle')
    await asyncio.sleep(5.0)
    matched_row = await pod(page, 'button', pod_attr, pod_value)
    if matched_row:
        if matched_row:
            panel_id = await matched_row.get_attribute('aria-controls')
            should_expand = True
            if panel_id:
                panel = page.locator(f'#{panel_id}')
                if await panel.is_visible(): should_expand = False
            if should_expand:
                try: await matched_row.click(timeout=1000); await asyncio.sleep(1)
                except: pass
            if panel_id: await page.locator(f'#{panel_id}').get_by_text('More information', exact=False).first.click()
            else: await matched_row.locator('xpath=./following-sibling::*[1]').get_by_text('More information', exact=False).first.click()
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)
        raw_text = await page.evaluate('document.body.innerText')
        return scrape_all_fields(raw_text)
    else:
        print(f'No match found for {company_name}')
        return None

async def run():
    excel_path = 'Sample Companies - SoS.xlsx'
    if not os.path.exists(excel_path): return
    df = pd.read_excel(excel_path)
    pod_attribute = df.columns[1]
    playwright_instance, browser, context, page = await setup_browser()
    results = []
    for _, row in df.iterrows():
        company = str(row.iloc[0]).strip()
        val = str(row.iloc[1]).strip()
        if '00:00:00' in val: val = val.split(' ')[0]
        max_retries = 1
        for attempt in range(max_retries + 1):
            try:
                data = await scrape_company(page, company, pod_attribute, val)
                if data: data['Company'] = company; results.append(data); break
                else: break
            except Exception as e:
                print(f'Error: {e}')
                if attempt < max_retries:
                    print('Retrying with new session...')
                    try: await context.close(); await browser.close(); await playwright_instance.stop()
                    except: pass
                    playwright_instance, browser, context, page = await setup_browser()
        pd.DataFrame(results).to_json('scraped_results.json', orient='records', indent=4)
    await browser.close()
    await playwright_instance.stop()

if __name__ == '__main__':
    asyncio.run(run())