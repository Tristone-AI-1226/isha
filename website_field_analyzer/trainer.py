
import asyncio
import argparse
import sys
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page

# specific imports from the project if needed, but keeping this standalone for portability is better
# We will generate a standalone script.


from browser.cf_solver import get_cf_cookies

class ScraperTrainer:
    def __init__(self, start_url: str):
        self.start_url = start_url
        self.steps: List[Dict[str, Any]] = []
        self.page: Page = None
        self.browser = None
        self.playwright = None
        self.context = None

    async def start(self):
        print(f"Starting Trainer...")
        await self.initialize_session()
        await self.command_loop()

    async def initialize_session(self):
        # 0. Solve Cloudflare (Visible)
        print("Solving Cloudflare challenge first...")
        try:
            cookies, user_agent = await get_cf_cookies(self.start_url, headless=False)
            print("Cloudflare cookies retrieved.")
        except Exception as e:
            print(f"Warning: Cloudflare bypass failed or timed out: {e}")
            print("Attempting to proceed without specific CF cookies...")
            cookies, user_agent = [], None

        # 1. Launch Playwright
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False, slow_mo=500)
        
        # Create context with CF bypass info
        self.context = await self.browser.new_context(
            user_agent=user_agent if user_agent else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        if cookies:
            # Playwright expects 'sameSite' to be valid or omitted, sometimes uc returns strict/lax etc.
            # Clean cookies if needed
            clean_cookies = []
            for c in cookies:
                # Basic cleaning
                c_clean = {k: v for k, v in c.items() if k in ['name', 'value', 'domain', 'path', 'expires', 'httpOnly', 'secure', 'sameSite']}
                clean_cookies.append(c_clean)
            await self.context.add_cookies(clean_cookies)

        self.page = await self.context.new_page()
        
        # Initial navigation
        print(f"Navigating to {self.start_url}...")
        try:
            await self.page.goto(self.start_url)
            self.steps.append({"type": "navigate", "url": self.start_url})
            print("Navigation successful.")
        except Exception as e:
            print(f"Error navigating: {e}")

    async def execute_command(self, action: str, args: str = "") -> str:
        """Execute a single command and return a status message."""
        if action == "quit":
            return "quit"
        
        elif action == "finish":
            self.generate_script()
            return "finished"

        elif action == "click":
            await self.handle_click(args)

        elif action == "type":
            await self.handle_type(args)

        elif action == "press":
            key = args.strip()
            await self.page.keyboard.press(key)
            self.steps.append({"type": "press", "key": key})
            print(f"Pressed '{key}'")

        elif action == "wait":
            try:
                secs = float(args.strip())
                await asyncio.sleep(secs)
                self.steps.append({"type": "wait", "seconds": secs})
                print(f"Waited {secs}s")
            except ValueError:
                print("Invalid seconds")

        elif action == "scroll":
            await self.page.evaluate("window.scrollBy(0, 500)")
            self.steps.append({"type": "scroll"})
            print("Scrolled down")

        elif action == "pod":
            selector = args.strip()
            if not selector:
                selector = "button" # Default if not provided
            await self.handle_pod(selector)

        elif action == "scrape":
            print("Scraping all content...")
            self.steps.append({"type": "scrape"})
            text = await self.page.inner_text("body")
            print(f"Captured {len(text)} characters.")
            return f"Captured {len(text)} characters."

        elif action == "inspect":
            content = await self.page.content()
            with open("trainer_inspect.html", "w", encoding="utf-8") as f:
                f.write(content)
            print("Saved trainer_inspect.html")

        else:
            print(f"Unknown command: {action}")
            return f"Unknown command: {action}"
            
        return "done"

    async def command_loop(self):
        print("\n" + "="*50)
        print("Interactive Trainer Ready")
        print("Available commands:")
        print("  click <selector_or_text>   : Click an element")
        print("  type <selector_or_text> <value> : Type text into a field")
        print("  press <key>                : Press a key (e.g., Enter)")
        print("  wait <seconds>             : Wait for X seconds")
        print("  scroll                     : Scroll down")
        print("  pod <selector>             : Scan rows, extract attrs, filter by user criteria")
        print("  scrape                     : Scrape all text content from the current page")
        print("  finish                     : Save and exit")
        print("  quit                       : Exit without saving")
        print("="*50 + "\n")

        while True:
            try:
                cmd_line = input("Trainer> ").strip()
                if not cmd_line:
                    continue

                parts = cmd_line.split(" ", 1) # simple split
                action = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""

                result = await self.execute_command(action, args)
                if result == "quit":
                    break
                elif result == "finished":
                    break


            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error executing command: {e}")

        # Cleanup
        await self.browser.close()
        await self.playwright.stop()

    async def handle_click(self, selector_or_text):
        target = selector_or_text.strip()
        if (target.startswith('"') and target.endswith('"')) or (target.startswith("'") and target.endswith("'")):
            target = target[1:-1]
            
        print(f"Attempting to click '{target}'...")
        
        try:
            element = self.page.get_by_text(target, exact=False).first
            if await element.count() > 0 and await element.is_visible():
                await element.click()
                self.steps.append({"type": "click", "method": "get_by_text", "target": target})
                print("Clicked by text (exact).")
                return

            element = self.page.get_by_text(target, exact=False).first
            if await element.count() > 0 and await element.is_visible():
                await element.click()
                self.steps.append({"type": "click", "method": "get_by_text_fuzzy", "target": target})
                print("Clicked by text (fuzzy).")
                return

            element = self.page.locator(target).first
            if await element.count() > 0 and await element.is_visible():
                await element.click()
                self.steps.append({"type": "click", "method": "locator", "target": target})
                print("Clicked by locator.")
                return
                
            print(f"Could not find clickable element for '{target}'")

        except Exception as e:
            print(f"Click failed: {e}")


    async def handle_type(self, args_str):
        import shlex
        try:
            parts = shlex.split(args_str)
            if len(parts) < 2:
                print("Usage: type <selector_or_label> <value>")
                return
            
            target = parts[0]
            value = parts[1]
            
            print(f"Type '{value}' into '{target}'...")
            
            element = self.page.get_by_label(target, exact=False).first
            if await element.count() > 0 and await element.is_visible():
                await element.fill(value)
                self.steps.append({"type": "type", "method": "get_by_label", "target": target, "value": value})
                print("Typed by label (exact=False).")
                return

            element = self.page.get_by_role("textbox", name=target, exact=False).first
            if await element.count() > 0 and await element.is_visible():
                await element.fill(value)
                self.steps.append({"type": "type", "method": "get_by_role", "target": target, "value": value})
                print("Typed by role (textbox).")
                return

            element = self.page.get_by_placeholder(target, exact=False).first
            if await element.count() > 0 and await element.is_visible():
                await element.fill(value)
                self.steps.append({"type": "type", "method": "get_by_placeholder", "target": target, "value": value})
                print("Typed by placeholder.")
                return
                
            element = self.page.locator(target).first
            if await element.count() > 0 and await element.is_visible():
                await element.fill(value)
                self.steps.append({"type": "type", "method": "locator", "target": target, "value": value})
                print("Typed by locator.")
                return

            if not " " in target:
                 element = self.page.locator(f"#{target}").first
                 if await element.count() > 0 and await element.is_visible():
                    await element.fill(value)
                    self.steps.append({"type": "type", "method": "locator", "target": f"#{target}", "value": value})
                    print("Typed by ID inference.")
                    return
                 
                 element = self.page.locator(f"[name='{target}']").first
                 if await element.count() > 0 and await element.is_visible():
                    await element.fill(value)
                    self.steps.append({"type": "type", "method": "locator", "target": f"[name='{target}']", "value": value})
                    print("Typed by Name inference.")
                    return
                
            print(f"Could not find input field for '{target}'")

        except ValueError:
            print("Error parsing arguments. Use quotes for strings with spaces.")
        except Exception as e:
            print(f"Type failed: {e}")

    async def handle_pod(self, selector):
        attr = "Date formed" # default
        val = "1/1/2001" # default
        
        if "|" in selector:
             parts = selector.split("|")
             selector = parts[0].strip()
             if len(parts) > 1: attr = parts[1].strip()
             if len(parts) > 2: val = parts[2].strip()

        print(f"Scanning rows with selector '{selector}'...")
        rows = await self.page.locator(selector).all()
        
        if not rows:
            print(f"No elements found for selector '{selector}'")
            return

        print(f"Found {len(rows)} potential rows.")

        print(f"Searching for row containing '{attr}' AND '{val}'...")
        print("Expanding and scanning each row (this may take a moment)...")
        
        matched_row = None
        for i, row in enumerate(rows):
            try:
                if not await row.is_visible():
                    continue

                try:
                    await row.click(timeout=1000)
                    await asyncio.sleep(0.5) 
                except Exception:
                    pass
                
                text = await row.inner_text()
                parent_text = ''
                grandparent_text = ''
                try:
                     parent_text = await row.locator('..').inner_text()
                     grandparent_text = await row.locator('../..').inner_text()
                except:
                     pass
                
                combined_check_text = text + ' ' + parent_text + ' ' + grandparent_text
                preview = text.replace('\n', ' ')[:100]
                print(f"  [Row {i}] Text: {preview}...")

                if attr.lower() in combined_check_text.lower() and val.lower() in combined_check_text.lower():
                    print(f"Match found in Row {i}!")
                    matched_row = row
                    break
            except Exception as e:
                pass
                
        if matched_row:
            self.steps.append({'type': 'pod', 'selector': selector, 'attribute': attr, 'value': val})
            print("POD Step Recorded.")
        else:
            print("No rows matched your criteria.")

    def generate_script(self):
        filename = "generated_scraper.py"
        print(f"Generating {filename}...")
        
        search_step_idx = -1
        pod_step_idx = -1
        for i, s in enumerate(self.steps):
            if s['type'] == 'type' and search_step_idx == -1: search_step_idx = i
            if s['type'] == 'pod' and pod_step_idx == -1: pod_step_idx = i

        code = [
            "import asyncio",
            "import sys",
            "import os",
            "import re",
            "import pandas as pd",
            "from pathlib import Path",
            "from dateutil import parser",
            "from playwright.async_api import async_playwright",
            "",
            "sys.path.insert(0, str(Path(__file__).parent))",
            "from browser.cf_solver import get_cf_cookies",
            "",
            "def scrape_all_fields(text):",
            "    data = {}",
            "    lines = [l.strip() for l in text.split('\\n') if l.strip()]",
            "    block_headers = ['Registered Office address', 'Registered Mailing address', 'Mailing address', 'Principal Office address']",
            "    current_key = None",
            "    current_val_lines = []",
            "    for line in lines:",
            "        if ':' in line:",
            "             parts = line.split(':', 1)",
            "             potential_key = parts[0].strip()",
            "             potential_val = parts[1].strip()",
            "             if len(potential_key) < 60:",
            "                 if current_key: data[current_key] = ' '.join(current_val_lines).strip()",
            "                 current_key = potential_key",
            "                 current_val_lines = [potential_val] if potential_val else []",
            "                 continue",
            "        is_header = False",
            "        for h in block_headers:",
            "            if h.lower() == line.lower():",
            "                if current_key: data[current_key] = ' '.join(current_val_lines).strip()",
            "                current_key = line",
            "                current_val_lines = []",
            "                is_header = True",
            "                break",
            "        if is_header: continue",
            "        if current_key: current_val_lines.append(line)",
            "    if current_key: data[current_key] = ' '.join(current_val_lines).strip()",
            "    # Date Normalization",
            "    for k, v in data.items():",
            "        if re.search(r'\\d+[/-]\\d+[/-]\\d+', v):",
            "            try:",
            "                dt = parser.parse(v)",
            "                data[k] = dt.strftime('%m/%d/%Y')",
            "            except: pass",
            "    return data",
            "",
            "async def pod(page, selector, attribute, target_value):",
            "    print(f\"Running POD: Finding row containing '{attribute}' and '{target_value}'...\")",
            "    rows = await page.locator(selector).all()",
            "    for i, row in enumerate(rows):",
            "        try:",
            "            if await row.is_visible():",
            "                await row.scroll_into_view_if_needed()",
            "                panel_id = await row.get_attribute('aria-controls')",
            "                try:",
            "                    await row.click(timeout=1000)",
            "                    await asyncio.sleep(0.5)",
            "                except: pass",
            "                ",
            "                text = await row.inner_text()",
            "                panel_text = ''",
            "                if panel_id:",
            "                    panel = page.locator(f'#{panel_id}')",
            "                    if await panel.count() > 0:",
            "                        try: panel_text = await panel.inner_text()",
            "                        except: pass",
            "                combined_text = text + ' ' + panel_text",
            "                ",
            "                # Normalize target if date",
            "                target_str = str(target_value).strip()",
            "                try:",
            "                    target_dt = parser.parse(target_str)",
            "                    target_norm = target_dt.strftime('%m/%d/%Y')",
            "                except:",
            "                    target_dt = None",
            "                    target_norm = target_str",
            "                ",
            "                # 1. Direct String Match (Original & Normalized)",
            "                if attribute.lower() in combined_text.lower():",
            "                    if target_str.lower() in combined_text.lower() or target_norm.lower() in combined_text.lower():",
            "                         print(f\"POD Match Found in Row {i}...\")",
            "                         return row",
            "                    ",
            "                    # 2. Fuzzy Date Match",
            "                    if target_dt:",
            "                        # Regex find all date-like strings and compare",
            "                        dates = re.findall(r'\\d+[/-]\\d+[/-]\\d+', combined_text)",
            "                        for d_str in dates:",
            "                            try:",
            "                                found_dt = parser.parse(d_str)",
            "                                if found_dt.date() == target_dt.date():",
            "                                     print(f\"POD Match (Fuzzy Date) in Row {i}: {d_str}\")",
            "                                     return row",
            "                            except: pass",
            "        except Exception as e: ",
            "            # print(f\"Row check failed: {e}\")",
            "            pass",
            "    print(\"POD: No match found.\")",
            "    return None",
            "",
            "async def setup_browser():",
            "    url = 'https://sosnc.gov/online_services/search/by_title/search_Business_Registration'",
            "    print('Solving Cloudflare challenge...')",
            "    cookies, user_agent = await get_cf_cookies(url, headless=False)",
            "    p = await async_playwright().start()",
            "    browser = await p.chromium.launch(headless=False)",
            "    context = await browser.new_context(user_agent=user_agent)",
            "    await context.add_init_script(\"Object.defineProperty(navigator, 'webdriver', {get: () => undefined})\")",
            "    if cookies:",
            "        cl = [{k: v for k, v in c.items() if k in ['name', 'value', 'domain', 'path', 'expires', 'httpOnly', 'secure', 'sameSite']} for c in cookies]",
            "        await context.add_cookies(cl)",
            "    page = await context.new_page()",
            "    return p, browser, context, page",
            "",
            "async def scrape_company(page, company_name, pod_attr, pod_value):",
            "    print(f\"\\nProcessing: {company_name} (POD: {pod_value})\")",
            f"    await page.goto('{self.start_url}')"
        ]

        # Generate steps
        pod_active = False
        indent = "    "
        for i, step in enumerate(self.steps):
            if step['type'] == 'navigate': continue 
            stype = step["type"]
            line = ""
            curr_indent = indent + ("    " if pod_active else "")
            
            if stype == "click":
                target = step['target']
                locator_str = f"get_by_text('{target}', exact=False).first" if step['method'] == "get_by_text" else f"locator('{target}').first"
                if pod_active:
                    code.append(f"{curr_indent}if matched_row:")
                    code.append(f"{curr_indent}    panel_id = await matched_row.get_attribute('aria-controls')")
                    code.append(f"{curr_indent}    should_expand = True")
                    code.append(f"{curr_indent}    if panel_id:")
                    code.append(f"{curr_indent}        panel = page.locator(f'#{{panel_id}}')")
                    code.append(f"{curr_indent}        if await panel.is_visible(): should_expand = False")
                    code.append(f"{curr_indent}    if should_expand:")
                    code.append(f"{curr_indent}        try: await matched_row.click(timeout=1000); await asyncio.sleep(1)")
                    code.append(f"{curr_indent}        except: pass")
                    code.append(f"{curr_indent}    if panel_id: await page.locator(f'#{{panel_id}}').{locator_str}.click()")
                    code.append(f"{curr_indent}    else: await matched_row.locator('xpath=./following-sibling::*[1]').{locator_str}.click()")
                else:
                    code.append(f"{curr_indent}await page.{locator_str}.click()")

            elif stype == "type":
                target = step['target']
                val = "company_name" if i == search_step_idx else f"'{step['value']}'"
                method = step['method']
                if method == "get_by_label": line = f"{curr_indent}await page.get_by_label('{target}', exact=False).first.fill({val})"
                else: line = f"{curr_indent}await page.locator('{target}').first.fill({val})"

            elif stype == "press":
                line = f"{curr_indent}await page.keyboard.press('{step['key']}')"
                if step['key'].lower() == "enter":
                    code.append(line)
                    line = f"{curr_indent}await page.wait_for_load_state('networkidle')"
                
            elif stype == "wait": line = f"{curr_indent}await asyncio.sleep({step['seconds']})"
            elif stype == "scroll": line = f"{curr_indent}await page.evaluate('window.scrollBy(0, 500)')"
            elif stype == "pod":
                sel = step['selector']
                attr = "pod_attr" if i == pod_step_idx else f"'{step['attribute']}'"
                val = "pod_value" if i == pod_step_idx else f"'{step['value']}'"
                code.append(f"{indent}matched_row = await pod(page, '{sel}', {attr}, {val})")
                code.append(f"{indent}if matched_row:")
                pod_active = True
                line = ""

            elif stype == "scrape":
                code.append(f"{curr_indent}await page.wait_for_load_state('networkidle')")
                code.append(f"{curr_indent}await asyncio.sleep(2)")
                code.append(f"{curr_indent}raw_text = await page.evaluate('document.body.innerText')")
                code.append(f"{curr_indent}return scrape_all_fields(raw_text)")

            if line: code.append(line)

        final_indent = indent + ("    " if pod_active else "")
        # Add fallback scrape if user forgot 'scrape' command, OR just indentation closure
        code.extend([
            f"{indent}else:",
            f"{indent}    print(f'No match found for {{company_name}}')",
            f"{indent}    return None",
            "",
            "async def run():",
            "    excel_path = 'Sample Companies - SoS.xlsx'",
            "    if not os.path.exists(excel_path): return",
            "    df = pd.read_excel(excel_path)",
            "    pod_attribute = df.columns[1]",
            "    playwright_instance, browser, context, page = await setup_browser()",
            "    results = []",
            "    for _, row in df.iterrows():",
            "        company = str(row.iloc[0]).strip()",
            "        val = str(row.iloc[1]).strip()",
            "        if '00:00:00' in val: val = val.split(' ')[0]",
            "        max_retries = 1",
            "        for attempt in range(max_retries + 1):",
            "            try:",
            "                data = await scrape_company(page, company, pod_attribute, val)",
            "                if data: data['Company'] = company; results.append(data); break",
            "                else: break",
            "            except Exception as e:",
            "                print(f'Error: {e}')",
            "                if attempt < max_retries:",
            "                    print('Retrying with new session...')",
            "                    try: await context.close(); await browser.close(); await playwright_instance.stop()",
            "                    except: pass",
            "                    playwright_instance, browser, context, page = await setup_browser()",
            "        pd.DataFrame(results).to_json('scraped_results.json', orient='records', indent=4)",
            "    await browser.close()",
            "    await playwright_instance.stop()",
            "",
            "if __name__ == '__main__':",
            "    asyncio.run(run())"
        ])
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(code))
        print(f"Batch Script generated: {filename}")


def main():
    parser = argparse.ArgumentParser(description="Scraper Trainer")
    parser.add_argument('--url', type=str, required=True, help='Start URL')
    args = parser.parse_args()
    
    trainer = ScraperTrainer(args.url)
    asyncio.run(trainer.start())

if __name__ == "__main__":
    main()
