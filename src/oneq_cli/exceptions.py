class OneQError(Exception):
    """Base class for 1Q specific errors."""
    pass

class ApiKeyNotFound(OneQError):
    """Raised when the Gemini API key cannot be found."""
    pass

class ConfigurationError(OneQError):
    """Raised for general configuration issues."""
    pass

class ApiKeySetupCancelled(OneQError):
    """Raised when the user cancels the API key setup TUI."""
    pass

class GeminiApiError(OneQError):
    """Raised when there's an error communicating with the Gemini API."""
    pass