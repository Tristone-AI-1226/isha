"""
Request Inspector - Observe network requests (optional).
For future enhancements to detect API endpoints and AJAX submissions.
"""

from typing import List, Dict, Any, Optional
from playwright.async_api import Page, Request, Response
from utils.logger import logger


class RequestInspector:
    """Observes network requests (read-only)."""
    
    def __init__(self):
        self.requests: List[Dict[str, Any]] = []
        self.responses: List[Dict[str, Any]] = []
        self.xhr_requests: List[Dict[str, Any]] = []
        self.api_endpoints: List[str] = []
    
    async def attach(self, page: Page):
        """
        Attach request/response listeners to page.
        
        Args:
            page: Playwright page object
        """
        logger.debug("Attaching network inspector")
        
        page.on("request", self._on_request)
        page.on("response", self._on_response)
    
    def _on_request(self, request: Request):
        """Handle request event."""
        try:
            resource_type = request.resource_type
            
            # Track XHR/Fetch requests
            if resource_type in ('xhr', 'fetch'):
                self.xhr_requests.append({
                    'url': request.url,
                    'method': request.method,
                    'resource_type': resource_type,
                    'headers': request.headers,
                })
                
                # Extract potential API endpoints
                if '/api/' in request.url or request.url.endswith('.json'):
                    self.api_endpoints.append(request.url)
            
            # Track all requests
            self.requests.append({
                'url': request.url,
                'method': request.method,
                'resource_type': resource_type,
            })
            
        except Exception as e:
            logger.debug(f"Request tracking error: {e}")
    
    def _on_response(self, response: Response):
        """Handle response event."""
        try:
            self.responses.append({
                'url': response.url,
                'status': response.status,
                'content_type': response.headers.get('content-type', ''),
            })
        except Exception as e:
            logger.debug(f"Response tracking error: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of network activity.
        
        Returns:
            Dictionary with network summary
        """
        return {
            'total_requests': len(self.requests),
            'total_responses': len(self.responses),
            'xhr_requests': len(self.xhr_requests),
            'api_endpoints': list(set(self.api_endpoints)),
        }
    
    def get_xhr_requests(self) -> List[Dict[str, Any]]:
        """Get all XHR/Fetch requests."""
        return self.xhr_requests
    
    def get_api_endpoints(self) -> List[str]:
        """Get detected API endpoints."""
        return list(set(self.api_endpoints))
