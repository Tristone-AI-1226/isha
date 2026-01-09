"""
Website Field Analyzer - Main Entry Point
Orchestrates the complete 14-step analysis pipeline.
"""

import asyncio
import argparse
import sys
import time
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from browser.browser_manager import BrowserManager
from browser.page_loader import PageLoader
from analyzer.dom_analyzer import DOMAnalyzer
from analyzer.form_detector import FormDetector
from analyzer.field_classifier import FieldClassifier
from analyzer.page_classifier import PageClassifier
from models.page import PageAnalysis
from utils.logger import logger
from config.settings import Settings


from browser.cf_solver import get_cf_cookies


async def _run_analysis_pipeline(url: str, browser_manager: BrowserManager) -> PageAnalysis:
    """Run the analysis pipeline (Steps 3-13) with a running browser."""
    page = await browser_manager.new_page()
            
    # Step 3: Load URL and wait for stabilization
    await PageLoader.load(page, url)
    
    # Steps 4-7: DOM Analysis
    fields = await DOMAnalyzer.analyze(page)
    
    # Steps 8-9: Form Detection
    forms = await FormDetector.detect(fields, page)
    
    # Step 10: Field Classification
    FieldClassifier.classify(forms)
    
    # Steps 11-12: Page Classification
    analysis = PageClassifier.classify(url, forms)
    
    return analysis


async def analyze_website(
    url: str,
    headless: bool = True,
    output_file: str = None
) -> PageAnalysis:
    """
    Analyze a website and extract form/field information.
    
    This is the main orchestrator for the 14-step pipeline:
    1. Accept URL
    2. Launch browser
    3. Load & stabilize page
    4-7. DOM Analysis
    8-9. Form Detection
    10. Field Classification
    11-12. Page Classification
    13. Generate Output
    14. Cleanup
    
    Args:
        url: URL to analyze
        headless: Run browser in headless mode
        output_file: Optional output file path
        
    Returns:
        PageAnalysis object
    """
    start_time = time.time()
    
    logger.info("=" * 60)
    logger.info("Website Field Analyzer - Step 1 (Pure Analyzer)")
    logger.info("=" * 60)
    
    # [STEP 01] Input URL
    logger.step(1, f"Accepting URL: {url}")
    
    analysis = None
    
    try:
        # Attempt 1: Standard Analysis
        logger.info("Attempt 1: Standard Analysis")
        async with BrowserManager(headless=headless) as browser_manager:
            analysis = await _run_analysis_pipeline(url, browser_manager)
        
        # Attempt 2: Cloudflare Bypass (if needed)
        if analysis and analysis.total_fields == 0:
            logger.warning("[!] No fields found. Suspecting bot protection.")
            logger.info("[STEP 1.5] Attempting Cloudflare Bypass...")
            
            try:
                cookies, user_agent = await get_cf_cookies(url, headless=headless)
                logger.success("Cloudflare cookies retrieved")
                
                logger.info("Attempt 2: Analysis with Cloudflare Cookies")
                async with BrowserManager(headless=headless, cookies=cookies, user_agent=user_agent) as browser_manager:
                    analysis = await _run_analysis_pipeline(url, browser_manager)
                    analysis.notes.append("Analyzed with Cloudflare bypass")
                    
            except Exception as e:
                logger.error(f"Cloudflare bypass failed: {e}")
                if analysis:
                    analysis.notes.append(f"Cloudflare bypass failed: {e}")

        # Calculate analysis duration
        duration_ms = (time.time() - start_time) * 1000
        analysis.analysis_duration_ms = duration_ms
        
        # Step 13: Generate structured output
        logger.step(13, "Generating structured JSON output")
        
        # Print summary
        print("\n" + analysis.summary())
        
        # Save to file if specified
        if output_file:
            analysis.save_to_file(output_file)
            logger.success(f"Analysis saved to: {output_file}")
        
        # Print JSON output
        print("\nJSON Output:")
        print("-" * 60)
        print(analysis.to_json())
        print("-" * 60)
        
        logger.success(f"Analysis complete in {duration_ms:.2f}ms")
        
        return analysis
            
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Website Field Analyzer - Pure read-only form/field analyzer"
    )
    
    parser.add_argument(
        '--url',
        type=str,
        required=True,
        help='URL to analyze (e.g., https://example.com/login)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output JSON file path (optional)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        default=True,
        help='Run browser in headless mode (default: True)'
    )
    
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Run browser in visible mode'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Update settings
    if args.debug:
        Settings.LOG_LEVEL = "DEBUG"
        Settings.DEBUG_MODE = True
        logger.logger.setLevel("DEBUG")
    
    headless = not args.no_headless if args.no_headless else args.headless
    
    # Run analysis
    try:
        asyncio.run(analyze_website(
            url=args.url,
            headless=headless,
            output_file=args.output
        ))
    except KeyboardInterrupt:
        logger.warning("\nAnalysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nFatal error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
