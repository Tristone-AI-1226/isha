"""
Basic test for DOM analysis functionality.
"""

import asyncio
import pytest
from browser.browser_manager import BrowserManager
from browser.page_loader import PageLoader
from analyzer.dom_analyzer import DOMAnalyzer


@pytest.mark.asyncio
async def test_dom_analyzer_basic():
    """Test basic DOM analysis on a simple page."""
    
    # Create a simple HTML page for testing
    html_content = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title></head>
    <body>
        <form id="login-form">
            <input type="email" name="email" placeholder="Email" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
    </body>
    </html>
    """
    
    async with BrowserManager(headless=True) as browser_manager:
        page = await browser_manager.new_page()
        
        # Load HTML content
        await page.set_content(html_content)
        
        # Analyze DOM
        fields = await DOMAnalyzer.analyze(page)
        
        # Assertions
        assert len(fields) > 0, "Should extract at least one field"
        
        # Check for email field
        email_fields = [f for f in fields if f.input_type == 'email']
        assert len(email_fields) == 1, "Should find email field"
        
        # Check for password field
        password_fields = [f for f in fields if f.input_type == 'password']
        assert len(password_fields) == 1, "Should find password field"
        
        # Check for submit button
        submit_fields = [f for f in fields if f.is_submit()]
        assert len(submit_fields) == 1, "Should find submit button"


@pytest.mark.asyncio
async def test_field_normalization():
    """Test field normalization extracts correct properties."""
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <body>
        <input type="text" 
               id="username" 
               name="username" 
               placeholder="Enter username"
               aria-label="Username"
               required>
    </body>
    </html>
    """
    
    async with BrowserManager(headless=True) as browser_manager:
        page = await browser_manager.new_page()
        await page.set_content(html_content)
        
        fields = await DOMAnalyzer.analyze(page)
        
        assert len(fields) == 1
        field = fields[0]
        
        assert field.tag_name == 'input'
        assert field.input_type == 'text'
        assert field.name == 'username'
        assert field.id == 'username'
        assert field.placeholder == 'Enter username'
        assert field.aria_label == 'Username'
        assert field.required == True


if __name__ == '__main__':
    # Run tests
    asyncio.run(test_dom_analyzer_basic())
    asyncio.run(test_field_normalization())
    print("All tests passed!")
