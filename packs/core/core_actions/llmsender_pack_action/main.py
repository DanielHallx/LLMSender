#!/usr/bin/env python3
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
import re

from core.interfaces import Action

logger = logging.getLogger(__name__)


class FilterAction(Action):
    """Filter content based on various criteria."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.min_length = config.get('min_length', 0)
        self.max_length = config.get('max_length')
        self.keywords = config.get('keywords', [])
        self.exclude_keywords = config.get('exclude_keywords', [])
    
    def process(self, llm_output: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Filter content based on configured criteria."""
        # Check length constraints
        if len(llm_output) < self.min_length:
            return {
                'output': "Content too short after filtering",
                'should_continue': False,
                'metadata': {'filtered_reason': 'min_length'}
            }
        
        if self.max_length and len(llm_output) > self.max_length:
            llm_output = llm_output[:self.max_length] + "..."
        
        # Check for required keywords
        if self.keywords:
            content_lower = llm_output.lower()
            found_keywords = [kw for kw in self.keywords if kw.lower() in content_lower]
            if not found_keywords:
                return {
                    'output': "Content does not contain required keywords",
                    'should_continue': False,
                    'metadata': {'filtered_reason': 'missing_keywords', 'required': self.keywords}
                }
        
        # Check for excluded keywords
        if self.exclude_keywords:
            content_lower = llm_output.lower()
            found_excluded = [kw for kw in self.exclude_keywords if kw.lower() in content_lower]
            if found_excluded:
                return {
                    'output': "Content contains excluded keywords",
                    'should_continue': False,
                    'metadata': {'filtered_reason': 'excluded_keywords', 'found': found_excluded}
                }
        
        return {
            'output': llm_output,
            'should_continue': True,
            'metadata': {'filtered': True, 'passed': True}
        }
    
    def get_tool_spec(self) -> Optional[Dict[str, Any]]:
        """Not exposed as LLM tool."""
        return None


class FormatAction(Action):
    """Format content in various styles."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.format = config.get('format', 'plain')
        self.add_timestamp = config.get('add_timestamp', False)
    
    def process(self, llm_output: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Format the content according to specified format."""
        formatted_output = llm_output
        
        # Add timestamp if requested
        if self.add_timestamp:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            formatted_output = f"[{timestamp}] {formatted_output}"
        
        # Apply formatting
        if self.format == 'markdown':
            formatted_output = self._format_as_markdown(formatted_output)
        elif self.format == 'html':
            formatted_output = self._format_as_html(formatted_output)
        elif self.format == 'json':
            formatted_output = self._format_as_json(formatted_output, context)
        # 'plain' format needs no additional processing
        
        return {
            'output': formatted_output,
            'should_continue': True,
            'metadata': {'format': self.format, 'timestamp_added': self.add_timestamp}
        }
    
    def _format_as_markdown(self, content: str) -> str:
        """Format content as Markdown."""
        # Simple formatting - could be enhanced
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append('')
                continue
            
            # Make first line a header if it looks like a title
            if len(formatted_lines) == 0 and len(line) < 100:
                formatted_lines.append(f"# {line}")
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def _format_as_html(self, content: str) -> str:
        """Format content as HTML."""
        # Convert newlines to <br> tags and wrap in paragraph
        html_content = content.replace('\n', '<br>\n')
        return f"<div>\n{html_content}\n</div>"
    
    def _format_as_json(self, content: str, context: Dict[str, Any]) -> str:
        """Format content as JSON structure."""
        json_obj = {
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'task_name': context.get('task_name', 'unknown'),
            'metadata': {
                'content_length': len(content),
                'formatted_by': 'core.format'
            }
        }
        return json.dumps(json_obj, indent=2, ensure_ascii=False)
    
    def get_tool_spec(self) -> Optional[Dict[str, Any]]:
        """Not exposed as LLM tool."""
        return None


class WebSearchAction(Action):
    """Search the web for additional information (mock implementation)."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.query = config.get('query', '')
        self.max_results = config.get('max_results', 5)
    
    def process(self, llm_output: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform web search and append results."""
        # This is a mock implementation
        # In a real implementation, you'd use a search API like Google, Bing, etc.
        
        search_query = self.query or self._extract_search_terms(llm_output)
        
        # Mock search results
        mock_results = [
            f"Search result {i+1} for '{search_query}': Mock information about {search_query}"
            for i in range(min(self.max_results, 3))
        ]
        
        # Append search results to output
        enhanced_output = f"{llm_output}\n\n🔍 Additional Information:\n"
        for i, result in enumerate(mock_results, 1):
            enhanced_output += f"{i}. {result}\n"
        
        return {
            'output': enhanced_output,
            'should_continue': True,
            'metadata': {
                'search_query': search_query,
                'results_count': len(mock_results),
                'enhanced': True
            }
        }
    
    def _extract_search_terms(self, content: str) -> str:
        """Extract key terms from content for searching."""
        # Simple extraction - could use NLP libraries for better results
        words = re.findall(r'\b[A-Z][a-z]+\b', content)  # Find capitalized words
        return ' '.join(words[:3])  # Use first 3 capitalized words
    
    def get_tool_spec(self) -> Optional[Dict[str, Any]]:
        """This action can be used as an LLM tool."""
        return {
            'type': 'function',
            'function': {
                'name': 'web_search',
                'description': 'Search the web for additional information on a topic',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'query': {
                            'type': 'string',
                            'description': 'Search query or topic to research'
                        },
                        'max_results': {
                            'type': 'integer',
                            'description': 'Maximum number of search results to include',
                            'default': 5
                        }
                    },
                    'required': ['query']
                }
            }
        }


# Factory functions
def filter(config: Dict[str, Any]) -> FilterAction:
    """Factory for filter action."""
    return FilterAction(config)


def format(config: Dict[str, Any]) -> FormatAction:
    """Factory for format action."""
    return FormatAction(config)


def web_search(config: Dict[str, Any]) -> WebSearchAction:
    """Factory for web search action."""
    return WebSearchAction(config)