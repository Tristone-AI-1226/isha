
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

        await self.command_loop()

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
        print("  finish                     : Save and exit")
        print("  quit                       : Exit without saving")
        print("="*50 + "\n")

        while True:
            try:
                # Use standard input (blocking) in a way that plays nice with asyncio?
                # Actually, input() blocks the event loop. In a simple script this might be okay 
                # if we don't need background events, but better to use run_in_executor usually.
                # For simplicity here, we'll just block.
                
                cmd_line = input("Trainer> ").strip()
                if not cmd_line:
                    continue

                parts = cmd_line.split(" ", 1) # simple split
                action = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""

                if action == "quit":
                    break
                
                elif action == "finish":
                    self.generate_script()
                    break

                elif action == "click":
                    await self.handle_click(args)

                elif action == "type":
                    # Simple heuristic split for type: "selector" "value"
                    # This is tricky with spaces. 
                    # Let's assume syntax: type "selector" "value" OR type selector value
                    # A better way might be to ask prompts.
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
                    # args is selector
                    selector = args.strip()
                    if not selector:
                        print("Usage: pod <selector>")
                        print("Example: pod .grid-item  (or whatever selector targets the rows)")
                    else:
                        await self.handle_pod(selector)

                elif action == "inspect":
                    # Save current HTML for debugging
                    content = await self.page.content()
                    with open("trainer_inspect.html", "w", encoding="utf-8") as f:
                        f.write(content)
                    print("Saved trainer_inspect.html")

                else:
                    print(f"Unknown command: {action}")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error executing command: {e}")

        # Cleanup
        await self.browser.close()
        await self.playwright.stop()

    async def handle_click(self, selector_or_text):
        # clean quotes if present
        target = selector_or_text.strip()
        if (target.startswith('"') and target.endswith('"')) or (target.startswith("'") and target.endswith("'")):
            target = target[1:-1]
            
        print(f"Attempting to click '{target}'...")
        
        # Strategy:
        # 1. Try generic selector/text locator
        # 2. Try strict selector
        
        # We need to find the specific Playwright locator that works
        loc = None
        method = "text"
        
        try:
            # Try finding by text first if it looks like text
            # Or use 'locator' with text= logic
            # Let's try to be smart.
            
            # Check if visual element exists
            element = self.page.get_by_text(target, exact=False).first
            if await element.count() > 0 and await element.is_visible():
                await element.click()
                method = "get_by_text"
                self.steps.append({"type": "click", "method": method, "target": target})
                print("Clicked by text.")
                return

            # Try selector
            element = self.page.locator(target).first
            if await element.count() > 0 and await element.is_visible():
                await element.click()
                method = "locator"
                self.steps.append({"type": "click", "method": method, "target": target})
                print("Clicked by locator.")
                return
                
            # If failed
            print(f"Could not find clickable element for '{target}'")

        except Exception as e:
            print(f"Click failed: {e}")


    async def handle_type(self, args_str):
        # We need 2 args: target and value
        # Basic parser for quotes
        import shlex
        try:
            parts = shlex.split(args_str)
            if len(parts) < 2:
                print("Usage: type <selector_or_label> <value>")
                return
            
            target = parts[0]
            value = parts[1]
            
            print(f"Type '{value}' into '{target}'...")
            
            # Strategy:
            # 1. get_by_label
            # 2. get_by_placeholder
            # 3. locator
            
            # Try label (exact=False to handle "Name *" vs "Name")
            element = self.page.get_by_label(target, exact=False).first
            if await element.count() > 0 and await element.is_visible():
                await element.fill(value)
                self.steps.append({"type": "type", "method": "get_by_label", "target": target, "value": value})
                print("Typed by label (exact=False).")
                return

            # Try by role (textbox) with name
            element = self.page.get_by_role("textbox", name=target, exact=False).first
            if await element.count() > 0 and await element.is_visible():
                await element.fill(value)
                self.steps.append({"type": "type", "method": "get_by_role", "target": target, "value": value})
                print("Typed by role (textbox).")
                return

            # Try placeholder
            element = self.page.get_by_placeholder(target, exact=False).first
            if await element.count() > 0 and await element.is_visible():
                await element.fill(value)
                self.steps.append({"type": "type", "method": "get_by_placeholder", "target": target, "value": value})
                print("Typed by placeholder.")
                return
                
            # Try locator (CSS/XPath)
            element = self.page.locator(target).first
            if await element.count() > 0 and await element.is_visible():
                await element.fill(value)
                self.steps.append({"type": "type", "method": "locator", "target": target, "value": value})
                print("Typed by locator.")
                return

            # Fallback: Try identifying by ID directly if target looks like a common ID word
            # Often user might type "SearchCriteria" which is the ID
            if not " " in target:
                 # Try ID
                 element = self.page.locator(f"#{target}").first
                 if await element.count() > 0 and await element.is_visible():
                    await element.fill(value)
                    self.steps.append({"type": "type", "method": "locator", "target": f"#{target}", "value": value})
                    print("Typed by ID inference.")
                    return
                 
                 # Try Name
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
        print(f"Scanning rows with selector '{selector}'...")
        rows = await self.page.locator(selector).all()
        
        if not rows:
            print(f"No elements found for selector '{selector}'")
            return

        print(f"Found {len(rows)} potential rows.")
        
        print("\n" + "="*50)
        print("SCENARIO: You want to select a specific row based on a criteria.")
        print("Example: If you want the row with 'Date formed: 1/1/2001',")
        print("Attribute = 'Date formed'")
        print("Value     = '1/1/2001'")
        print("This will find the row that contains BOTH strings.")
        print("="*50)
            
        attr = input("Enter identifying label/text (e.g. 'Date formed'): ").strip()
        val = input(f"Enter value for '{attr}' (e.g. '1/1/2001'): ").strip()
        
        print(f"Searching for row containing '{attr}' AND '{val}'...")
        print("Expanding and scanning each row (this may take a moment)...")
        
        matched_row = None
        for i, row in enumerate(rows):
            try:
                # SKIP OPTION: Check visibility first
                if not await row.is_visible():
                    continue

                # FORCE EXPAND
                try:
                    await row.click(timeout=1000)
                    await asyncio.sleep(0.5) 
                except Exception:
                    pass
                
                # Check row text, parent, AND grandparent text (for deep nesting)
                text = await row.inner_text()
                parent_text = ''
                grandparent_text = ''
                try:
                     parent_text = await row.locator('..').inner_text()
                     grandparent_text = await row.locator('../..').inner_text()
                except:
                     pass
                
                # Combine distinct texts to avoid massive duplication in output, but simple concat for checking
                combined_check_text = text + ' ' + parent_text + ' ' + grandparent_text
                
                # VISUAL FEEDBACK FOR USER
                preview = text.replace('\n', ' ')[:100]
                print(f"  [Row {i}] Text: {preview}...")
                # print(f"           Parent+: {parent_text[:50]}...")

                # Case insensitive check
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
        
        code = [
            "import asyncio",
            "import sys",
            "from pathlib import Path",
            "from playwright.async_api import async_playwright",
            "",
            "# Add current directory to path",
            "sys.path.insert(0, str(Path(__file__).parent))",
            "from browser.cf_solver import get_cf_cookies",
            "",
            "async def pod(page, selector, attribute, target_value):",
            "    print(f\"Running POD: Finding row containing '{attribute}' and '{target_value}'...\")",
            "    rows = await page.locator(selector).all()",
            "    for i, row in enumerate(rows):",
            "        try:",
            "            # Expand row",
            "            if await row.is_visible():",
            "                await row.click(timeout=1000)",
            "                await asyncio.sleep(0.5)",
            "        except Exception:",
            "            pass",
            "",
            "        # Check row text, parent, AND grandparent text (in case of accordion sibling)",
            "        text = await row.inner_text()",
            "        parent_text = ''",
            "        grandparent_text = ''",
            "        try:",
            "             parent_text = await row.locator('..').inner_text()",
            "             grandparent_text = await row.locator('../..').inner_text()",
            "        except:",
            "             pass",
            "        ",
            "        combined_text = text + ' ' + parent_text + ' ' + grandparent_text",
            "        if attribute.lower() in combined_text.lower() and target_value.lower() in combined_text.lower():",
            "            print(f\"POD Match Found in Row {i}...\")",
            "            await row.scroll_into_view_if_needed()",
            "            # Ensure it stays expanded",
            "            await row.click(force=True)",
            "            return row",
            "    print(\"POD: No match found.\")",
            "    return None",
            "",
            "async def run():",
            "    # Start URL",
            f"    url = '{self.start_url}'",
            "",
            "    print('Solving Cloudflare challenge...')",
            "    cookies, user_agent = await get_cf_cookies(url, headless=False)",
            "",
            "    async with async_playwright() as p:",
            "        browser = await p.chromium.launch(headless=False)",
            "        context = await browser.new_context(user_agent=user_agent)",
            "        ",
            "        if cookies:",
            "            clean_cookies = []",
            "            for c in cookies:",
            "                c_clean = {k: v for k, v in c.items() if k in ['name', 'value', 'domain', 'path', 'expires', 'httpOnly', 'secure', 'sameSite']}",
            "                clean_cookies.append(c_clean)",
            "            await context.add_cookies(clean_cookies)",
            "",
            "        page = await context.new_page()",
            ""
        ]
        
        code.append("    # Steps")
        
        pod_active = False
        
        for step in self.steps:
            stype = step["type"]
            line = ""
            
            if stype == "navigate":
                line = f"        await page.goto('{step['url']}')"
            
            elif stype == "click":
                target = step['target']
                # Determine method string
                if step['method'] == "get_by_text":
                    locator_str = f"get_by_text('{target}', exact=False).first"
                else:
                    locator_str = f"locator('{target}').first"
                
                # If POD is active, use matched_row ONLY but via ARIA panel
                if pod_active:
                    code.append(f"        if matched_row:")
                    code.append(f"            # 1. Get Panel ID")
                    code.append(f"            panel_id = await matched_row.get_attribute('aria-controls')")
                    code.append(f"            # 2. Expand Row (Try clicking search term or just row)")
                    code.append(f"            try:")
                    code.append(f"                 await matched_row.get_by_text('Rely', exact=False).click()")
                    code.append(f"            except:")
                    code.append(f"                 await matched_row.click()")
                    code.append(f"            await asyncio.sleep(1)")
                    code.append(f"            # 3. Click inside Panel")
                    code.append(f"            if panel_id:")
                    code.append(f"                await page.locator(f'#{{panel_id}}').{locator_str}.click()")
                    code.append(f"            else:")
                    code.append(f"                # Fallback: strict sibling")
                    code.append(f"                await matched_row.locator('xpath=./../following-sibling::*[1]').{locator_str}.click()")
                    line = "" # Handled above
                else:
                    line = f"        await page.{{locator_str}}.click()"
            
            elif stype == "type":
                target = step['target']
                val = step['value']
                method = step['method']
                if method == "get_by_label":
                    line = f"        await page.get_by_label('{target}', exact=False).first.fill('{val}')"
                elif method == "get_by_role":
                    line = f"        await page.get_by_role('textbox', name='{target}', exact=False).first.fill('{val}')"
                elif method == "get_by_placeholder":
                    line = f"        await page.get_by_placeholder('{target}', exact=False).first.fill('{val}')"
                else:
                    line = f"        await page.locator('{target}').first.fill('{val}')"

            elif stype == "press":
                line = f"        await page.keyboard.press('{step['key']}')"
                if step['key'].lower() == "enter":
                    code.append(line)
                    line = "        await page.wait_for_load_state('networkidle')"
                
            elif stype == "wait":
                line = f"        await asyncio.sleep({step['seconds']})"
            
            elif stype == "scroll":
                line = "        await page.evaluate('window.scrollBy(0, 500)')"
                
            elif stype == "pod":
                sel = step['selector']
                attr = step['attribute']
                val = step['value']
                # Assign result to matched_row and enable context
                code.append(f"        matched_row = await pod(page, '{sel}', '{attr}', '{val}')")
                pod_active = True
                line = "" 

            if line:
                code.append(line)
        
        # Add scrape step at end
        code.append("")
        code.append("        # Scrape Content")
        code.append("        print('Waiting for page to assume final state...')")
        code.append("        await page.wait_for_load_state('networkidle')")
        code.append("        await asyncio.sleep(2)")
        code.append("        content = await page.content()")
        code.append("        print(await page.evaluate('document.body.innerText'))")
        code.append("        await browser.close()")
        code.append("")
        code.append("if __name__ == '__main__':")
        code.append("    asyncio.run(run())")
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(code))
        
        print(f"Script generated: {filename}")


def main():
    parser = argparse.ArgumentParser(description="Scraper Trainer")
    parser.add_argument('--url', type=str, required=True, help='Start URL')
    args = parser.parse_args()
    
    trainer = ScraperTrainer(args.url)
    asyncio.run(trainer.start())

if __name__ == "__main__":
    main()
