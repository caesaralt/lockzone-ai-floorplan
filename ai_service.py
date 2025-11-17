"""
Centralized AI Service Manager
Handles all AI API calls with retry logic, error handling, and configuration management
"""
import time
import logging
from typing import Optional, Dict, Any, List
from functools import wraps

# Try importing AI libraries
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logging.warning("Anthropic library not available")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI library not available")

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    logging.warning("Tavily library not available")

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Base exception for AI service errors"""
    pass


class AIServiceUnavailable(AIServiceError):
    """Raised when AI service is not configured or unavailable"""
    pass


class AIServiceTimeout(AIServiceError):
    """Raised when AI service times out"""
    pass


def retry_on_failure(max_attempts=3, delay=2, backoff=2):
    """
    Decorator to retry function on failure with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay on each retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {str(e)}"
                    )

                    if attempt < max_attempts - 1:
                        logger.info(f"Retrying in {current_delay} seconds...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}")

            raise last_exception

        return wrapper
    return decorator


class AIService:
    """
    Centralized AI service manager with retry logic and error handling
    """

    def __init__(self, config):
        """
        Initialize AI service with configuration

        Args:
            config: Flask app configuration object
        """
        self.config = config
        self.anthropic_client = None
        self.openai_client = None
        self.tavily_client = None

        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize AI API clients"""
        # Anthropic Claude
        if ANTHROPIC_AVAILABLE and self.config.get('ANTHROPIC_API_KEY'):
            try:
                self.anthropic_client = anthropic.Anthropic(
                    api_key=self.config['ANTHROPIC_API_KEY']
                )
                logger.info("Anthropic Claude client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")

        # OpenAI GPT
        if OPENAI_AVAILABLE and self.config.get('OPENAI_API_KEY'):
            try:
                openai.api_key = self.config['OPENAI_API_KEY']
                self.openai_client = openai
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")

        # Tavily Web Search
        if TAVILY_AVAILABLE and self.config.get('TAVILY_API_KEY'):
            try:
                self.tavily_client = TavilyClient(
                    api_key=self.config['TAVILY_API_KEY']
                )
                logger.info("Tavily search client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Tavily client: {e}")

    @retry_on_failure(max_attempts=3, delay=2, backoff=2)
    def call_claude(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        thinking: Optional[Dict] = None,
        tools: Optional[List] = None,
        system: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Call Claude API with retry logic

        Args:
            messages: List of message dictionaries
            model: Model name (defaults to config)
            max_tokens: Maximum tokens (defaults to config)
            temperature: Temperature setting (defaults to config)
            thinking: Extended thinking configuration
            tools: Tool definitions for agentic mode
            system: System prompt

        Returns:
            API response dictionary

        Raises:
            AIServiceUnavailable: If Claude is not configured
            AIServiceError: On API errors
        """
        if not self.anthropic_client:
            raise AIServiceUnavailable("Anthropic Claude is not configured")

        # Use config defaults if not specified
        model_config = self.config['AI_MODELS']['claude']
        model = model or model_config['model']
        max_tokens = max_tokens or model_config['max_tokens']
        temperature = temperature or model_config['temperature']

        try:
            logger.info(f"Calling Claude API: model={model}, max_tokens={max_tokens}")

            # Build request parameters
            params = {
                'model': model,
                'max_tokens': max_tokens,
                'temperature': temperature,
                'messages': messages,
            }

            if thinking:
                params['thinking'] = thinking
            if tools:
                params['tools'] = tools
            if system:
                params['system'] = system

            response = self.anthropic_client.messages.create(**params)

            logger.info(f"Claude API call successful: stop_reason={response.stop_reason}")
            return response

        except anthropic.APITimeoutError as e:
            logger.error(f"Claude API timeout: {e}")
            raise AIServiceTimeout(f"Claude API timed out: {e}")
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise AIServiceError(f"Claude API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error calling Claude: {e}")
            raise AIServiceError(f"Unexpected error: {e}")

    @retry_on_failure(max_attempts=3, delay=2, backoff=2)
    def call_gpt4(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Call OpenAI GPT-4 API with retry logic

        Args:
            messages: List of message dictionaries
            model: Model name (defaults to config)
            max_tokens: Maximum tokens (defaults to config)
            temperature: Temperature setting (defaults to config)

        Returns:
            API response dictionary

        Raises:
            AIServiceUnavailable: If OpenAI is not configured
            AIServiceError: On API errors
        """
        if not self.openai_client:
            raise AIServiceUnavailable("OpenAI GPT-4 is not configured")

        # Use config defaults if not specified
        model_config = self.config['AI_MODELS']['gpt4']
        model = model or model_config['model']
        max_tokens = max_tokens or model_config['max_tokens']
        temperature = temperature or model_config['temperature']

        try:
            logger.info(f"Calling OpenAI API: model={model}, max_tokens={max_tokens}")

            response = self.openai_client.ChatCompletion.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )

            logger.info("OpenAI API call successful")
            return response

        except openai.error.Timeout as e:
            logger.error(f"OpenAI API timeout: {e}")
            raise AIServiceTimeout(f"OpenAI API timed out: {e}")
        except openai.error.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise AIServiceError(f"OpenAI API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error calling OpenAI: {e}")
            raise AIServiceError(f"Unexpected error: {e}")

    @retry_on_failure(max_attempts=2, delay=1, backoff=2)
    def web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Perform web search using Tavily API

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            Search results dictionary

        Raises:
            AIServiceUnavailable: If Tavily is not configured
            AIServiceError: On API errors
        """
        if not self.tavily_client:
            raise AIServiceUnavailable("Tavily search is not configured")

        try:
            logger.info(f"Performing web search: query='{query}'")

            results = self.tavily_client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced"
            )

            logger.info(f"Web search successful: {len(results.get('results', []))} results")
            return results

        except Exception as e:
            logger.error(f"Web search error: {e}")
            raise AIServiceError(f"Web search failed: {e}")

    def is_available(self, service: str) -> bool:
        """
        Check if a specific AI service is available

        Args:
            service: Service name ('claude', 'gpt4', 'search')

        Returns:
            True if service is available, False otherwise
        """
        if service == 'claude':
            return self.anthropic_client is not None
        elif service == 'gpt4':
            return self.openai_client is not None
        elif service == 'search':
            return self.tavily_client is not None
        else:
            return False
