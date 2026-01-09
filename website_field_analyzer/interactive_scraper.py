
import asyncio
import argparse
import sys
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from browser.browser_manager import BrowserManager
from browser.page_loader import PageLoader
from analyzer.dom_analyzer import DOMAnalyzer
from analyzer.form_detector import FormDetector
from analyzer.field_classifier import FieldClassifier
from browser.cf_solver import get_cf_cookies
from models.field import Field
from models.form import Form
from utils.logger import logger
from config.settings import Settings

class InteractiveScraper:
    """
    Scraper that enters fields in the web page by taking inputs from the user
    and scrapes the detail from the page.
    """
    
    def __init__(self, url: str, input_data: Dict[str, str], headless: bool = True):
        self.url = url
        self.input_data = input_data
        self.headless = headless
        
    async def run(self) -> Dict[str, Any]:
        """
        Run the scraper logic.
        """
        logger.info(f"Starting Interactive Scraper for: {self.url}")
        logger.info(f"Input Data: {self.input_data}")
        logger.info(f"Headless Mode: {self.headless}")
        
        try:
            # 1. Launch & Load
            async with BrowserManager(headless=self.headless) as browser_manager:
                page = await browser_manager.new_page()
                
                logger.info("Loading page...")
                await PageLoader.load(page, self.url)
                
                # 2. Analyze Page
                fields = await DOMAnalyzer.analyze(page)
                forms = await FormDetector.detect(fields, page)
                FieldClassifier.classify(forms)
                
                logger.info(f"Found {len(forms)} forms.")
                
                if not forms:
                    logger.warning("No forms found. Suspecting bot protection. Attempting Cloudflare Bypass...")
                    
                    # Close current browser session
                    await browser_manager.close()
                    
                    # Get CF Cookies
                    try:
                        # For CF bypass, we often need visible browser to solve challenges
                        # If user requested headless=True, we might need to temporarily override it for solving?
                        # But cf_solver usually handles its own headless state.
                        
                        logger.info("Launching Cloudflare Solver...")
                        cookies, user_agent = await get_cf_cookies(self.url, headless=self.headless)
                        logger.success("Cloudflare cookies retrieved")
                        
                        # Retry with cookies
                        async with BrowserManager(headless=self.headless, cookies=cookies, user_agent=user_agent) as browser_manager_cf:
                            page = await browser_manager_cf.new_page()
                            await PageLoader.load(page, self.url)
                            
                            fields = await DOMAnalyzer.analyze(page)
                            forms = await FormDetector.detect(fields, page)
                            FieldClassifier.classify(forms)
                            
                            logger.info(f"Found {len(forms)} forms with Cloudflare bypass.")
                            
                            if not forms:
                                return {"error": "No forms found even after Cloudflare bypass"}
                                
                            # Proceed with the found forms
                            return await self._process_forms(page, forms)
                            
                    except Exception as e:
                        logger.error(f"Cloudflare bypass failed: {e}")
                        return {"error": f"Cloudflare bypass failed: {e}"}

                # If we found forms initially, process them
                return await self._process_forms(page, forms)
                
        except Exception as e:
            logger.error(f"Scraper failed: {e}")
            raise

    async def _process_forms(self, page, forms) -> Dict[str, Any]:
        """Process the forms: match, fill, submit, scrape."""
        # 3. Match Inputs to Fields
        target_form, field_mapping = self._match_inputs_to_form(forms, self.input_data)
        
        if not target_form:
            logger.error("Could not match input data to any form on the page.")
            return {"error": "No matching form found"}
        
        # Identified target form
        form_identifier = target_form.form_id or "Unknown Form"
        logger.info(f"Targeting Form: {form_identifier}")
        logger.info(f"Field Mapping: {field_mapping}")
        
        # 4. Fill and Submit
        await self._fill_and_submit(page, field_mapping)
        
        
        # 5. Follow Result (Org -> More Info)
        final_page_content = await self._follow_results_and_scrape(page, self.input_data)
        
        # 6. Final Scrape
        result_data = {
            "url": page.url,
            "text_content_preview": final_page_content[:500] + "...",
            "full_text": final_page_content,
            "html_length": len(final_page_content)
        }
        
        logger.success("Scraping complete.")
        return result_data

    async def _follow_results_and_scrape(self, page, input_data: Dict[str, str]) -> str:
        """
        Follow the result link (organization) and optionally 'More Info'.
        Returns the final page text content.
        """
        # 1. Identify search term to find the right link
        search_term = ""
        for key, val in input_data.items():
            if "search" in key.lower() or "criteria" in key.lower() or "name" in key.lower():
                search_term = val
                break
        if not search_term and input_data:
            search_term = list(input_data.values())[0]

        logger.info(f"Looking for result link matching: '{search_term}'")
        
        try:
            # Wait for results to stabilize
            await asyncio.sleep(2)
            
            # Find closest matching link
            # Prioritize links inside the main results grid/table if it exists
            # SOS NC uses a grid often.
            
            target_link = None
            
            # Try to find a link that starts with the search term (more specific)
            xpath_start = f"//a[starts-with(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{search_term.lower()}')]"
            start_elements = await page.locator(xpath_start).all()
            
            if start_elements:
                 target_link = start_elements[0]
            else:
                # Fallback to contains
                xpath_contains = f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{search_term.lower()}')]"
                elements = await page.locator(xpath_contains).all()
                if elements:
                    target_link = elements[0]
            
            if target_link:
                text = await target_link.text_content()
                logger.success(f"Clicking result link: '{text.strip()}'")
                await target_link.click()
                
                # Wait for potential expansion or navigation
                await asyncio.sleep(2)
                await page.wait_for_load_state("networkidle")
            else:
                logger.warning(f"No result link found matching '{search_term}'.")

            # 2. 'More Info' Step
            # Now look for "More information" or "View filings" etc.
            # Based on user screenshot, it says "More information"
            
            logger.info("Looking for 'More information' link...")
            
            # Specific text match for "More information"
            more_info_selector = "parsed_css_fallback" # placeholder
            
            # Try finding by text
            more_info = page.get_by_text("More information", exact=False)
            
            if await more_info.count() > 0 and await more_info.first.is_visible():
                logger.success("Found 'More information' link. Clicking...")
                await more_info.first.click()
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2) # Extra wait for load
            else:
                logger.warning("'More information' link not found or not visible.")
            
        except Exception as e:
            logger.error(f"Navigation error during result follow: {e}")
            
        # Return final content
        return await page.evaluate("document.body.innerText")

    def _match_inputs_to_form(self, forms: List[Form], input_data: Dict[str, str]) -> tuple[Optional[Form], Dict[str, Field]]:
        """
        Find the best matching form and map inputs to its fields.
        Returns (Form, {input_key: Field})
        """
        best_form = None
        best_mapping = {}
        max_matches = 0
        
        for form in forms:
            mapping = {}
            matches = 0
            
            # Create a copy of fields to avoid double-mapping
            available_fields = list(form.fields)
            
            for key, value in input_data.items():
                # Find best matching field for this key
                score, field = self._find_best_field_match(key, available_fields)
                if field and score > 0.5: # Threshold
                    mapping[key] = field
                    matches += 1
                    available_fields.remove(field)
            
            if matches > max_matches:
                max_matches = matches
                best_form = form
                best_mapping = mapping
            elif matches == max_matches and matches > 0:
                 # Tie-breaker: Prefer form with 'search' purpose or more fields
                 if form.form_purpose == 'search' and (not best_form or best_form.form_purpose != 'search'):
                     best_form = form
                     best_mapping = mapping
                 elif not best_form:
                     best_form = form
                     best_mapping = mapping
        
        return best_form, best_mapping

    def _find_best_field_match(self, key: str, fields: List[Field]) -> tuple[float, Optional[Field]]:
        """
        Simple heuristic implementation to match keys to fields.
        """
        best_score = 0.0
        best_field = None
        
        key_lower = key.lower()
        
        for field in fields:
            if field.input_type in ['hidden', 'submit', 'button', 'image', 'reset']:
                continue
                
            score = 0.0
            
            # Get label text
            label = field.get_label().lower()
            name = (field.name or "").lower()
            fid = (field.id or "").lower()
            placeholder = (field.placeholder or "").lower()
            
            # Exact match
            if key_lower == name or key_lower == fid or key_lower == label:
                score = 1.0
            # Partial match
            elif key_lower in label or key_lower in name or key_lower in placeholder:
                score = 0.8
            elif label in key_lower: # e.g. input="Company Name", label="Company"
                score = 0.7
            
            if score > best_score:
                best_score = score
                best_field = field
                
        return best_score, best_field

    async def _fill_and_submit(self, page, field_mapping: Dict[str, Field]):
        """Fill mapped fields and submit the form."""
        
        # Fill fields
        for key, field in field_mapping.items():
            value = self.input_data[key]
            logger.info(f"Filling field '{field.get_label()}' with '{value}'")
            
            selector = field.selector
            if not selector:
                logger.warning(f"No selector for field {field}, skipping.")
                continue
                
            try:
                # Handle Select (Dropdown)
                if field.tag_name == 'select':
                    # Select by value first, then label/text
                    try:
                        await page.select_option(selector, value=value)
                    except Exception:
                        try:
                            await page.select_option(selector, label=value)
                        except Exception:
                             logger.warning(f"Could not select option '{value}' for field '{field.get_label()}'")
                
                # Handle Checkbox/Radio
                elif field.input_type in ['checkbox', 'radio']:
                    if str(value).lower() in ['true', '1', 'yes', 'on', 'checked']:
                        await page.check(selector)
                    else:
                        await page.uncheck(selector)
                        
                # Handle Standard Input (Text, Email, Password, etc.)
                else:
                    await page.fill(selector, str(value))
                    
            except Exception as e:
                 logger.error(f"Error filling field '{field.get_label()}': {e}")
            
        # Submit
        # Strategy: Press Enter in the last filled text input or click submit button
        logger.info("Submitting form...")
        
        # Try to find an explicit submit button in the form if we have the form object context
        # Since we don't pass the full form object easily here without refactoring, 
        # let's fallback to the Enter key strategy on the last text-like field.
        
        if field_mapping:
            last_field = list(field_mapping.values())[-1]
            if last_field.tag_name == 'input' and last_field.input_type in ['text', 'password', 'email', 'search']:
                await page.press(last_field.selector, "Enter")
            else:
                # If last field is a select or something else, pressing Enter might not work.
                # Try to find a submit button in the page? or just press Enter on body?
                await page.keyboard.press("Enter")
            
        await asyncio.sleep(2)


def main():
    parser = argparse.ArgumentParser(description="Interactive Website Scraper")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--data', type=str, help='JSON string of input data')
    group.add_argument('--data-file', type=str, help='Path to JSON file containing input data')
    
    parser.add_argument('--url', type=str, required=True, help='Target URL')
    parser.add_argument('--output', type=str, help='Path to save output JSON (e.g., results.json)')
    parser.add_argument('--headless', action='store_true', default=True, help='Run headless')
    parser.add_argument('--no-headless', action='store_true', help='Run visible (NOT headless)')
    
    args = parser.parse_args()
    
    try:
        if args.data_file:
            with open(args.data_file, 'r') as f:
                input_data = json.load(f)
        else:
            # Try to handle common Windows quoting issues where single quotes remain
            data_str = args.data
            if data_str.startswith("'") and data_str.endswith("'"):
                data_str = data_str[1:-1]
            input_data = json.loads(data_str)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON data. {e}")
        print("Tip: On Windows, use double quotes for the JSON string and escape inner quotes: --data \"{\\\"key\\\": \\\"value\\\"}\"")
        print("Or use --data-file input.json")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: Input file not found: {args.data_file}")
        sys.exit(1)
        
    # Check for no-headless
    headless = not args.no_headless if args.no_headless else args.headless
    
    # If using no-headless, user wants to see it, so we should allow it.
    
    scraper = InteractiveScraper(args.url, input_data, headless)
    
    try:
        result = asyncio.run(scraper.run())
        
        # Output to console
        print(json.dumps(result, indent=2))
        
        # Save to file if requested
        if args.output:
            try:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                logger.success(f"Results saved to: {args.output}")
            except Exception as e:
                logger.error(f"Failed to save output to file: {e}")
                
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
