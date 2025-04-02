# D:\1q\src\oneq_cli\gemini.py
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from rich.console import Console
from typing import List, Dict, Any, Optional
import platform
import os

from .exceptions import GeminiApiError

MODEL_NAME = "gemini-2.0-flash"
console = Console(stderr=True)


def _get_platform_context() -> str:
    """Gathers OS, distribution (Linux), and shell information for the LLM."""
    system = platform.system()
    context_parts = []

    if system == "Linux":
        os_name = "Linux"
        try:
            release_info = platform.freedesktop_os_release()
            distro = release_info.get('PRETTY_NAME') or release_info.get('NAME', 'Unknown Distro')
            os_name += f" ({distro})"
        except:
            pass # If lsb_release fails, just use "Linux"
        context_parts.append(f"OS: {os_name}")
    else:
        context_parts.append(f"OS: {system}")

    shell = os.environ.get("SHELL") or "Unknown"
    shell_name = os.path.basename(shell)
    context_parts.append(f"Shell: {shell_name}")

    return ", ".join(context_parts)


def generate_command(api_key: str, query: str) -> Optional[str]:
    """Generates a shell command based on the given query using the Gemini API.

    Args:
        api_key: The Gemini API key.
        query: The natural language query.

    Returns:
        The generated shell command, or None if an error occurred.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)

    platform_context = _get_platform_context()

    prompt = f"""
    You are a command-line assistant. Your goal is to translate a user's natural language query into a shell command that accomplishes their goal.
    Assume the user is working in a {platform_context}. Only respond with the single shell command that will fulfill the request.
    Do not include any explanation or conversation.

    User Query: {query}
    """

    try:
        response = model.generate_content(prompt)
        response.resolve() # Force the response to be evaluated immediately
        return response.text
    except google_exceptions.QuotaExceeded as e:
        raise GeminiApiError(
            "Gemini API Quota Exceeded: You have exceeded your quota for the Gemini API. Please check your Google Cloud project.") from e
    except google_exceptions.ServiceUnavailable as e:
        raise GeminiApiError(
            "Gemini API Service Unavailable: The Gemini API service is currently unavailable. Please try again later.") from e
    except google_exceptions.APIConnectionError as e:
        raise GeminiApiError(
            "Gemini API Connection Error: Could not connect to the Gemini API. Please check your network connection.") from e
    except google_exceptions.BadRequest as e:
        raise GeminiApiError(
            "Gemini API Bad Request: There was a problem with the request sent to the Gemini API. Please check your query.") from e
    except google_exceptions.NotFound as e:
        raise GeminiApiError(
            "Gemini API Not Found: The requested resource was not found. This could indicate an issue with the API or model name.") from e
    except google_exceptions.PermissionDenied as e:
        raise GeminiApiError(
            "Gemini API Permission Denied: You do not have permission to access the Gemini API. Please check your API key and project settings.") from e
    except google_exceptions.InternalServerError as e:
        raise GeminiApiError(
            "Gemini API Internal Server Error: An internal error occurred in the Gemini API. Please try again later.") from e
    except google_exceptions.Cancelled as e:
        raise GeminiApiError(
            "Gemini API Request Cancelled: The request to the Gemini API was cancelled.") from e
    except google_exceptions.ResourceExhausted as e:
        raise GeminiApiError(
"Gemini API Resource Exhausted: Quota limit reached? ({e})") from e
    except google_exceptions.FailedPrecondition as e:
         raise GeminiApiError(f"Gemini API Failed Precondition: API not enabled or billing issue? ({e})") from e
    except google_exceptions.GoogleAPIError as e:
        raise GeminiApiError(f"An unexpected Gemini API error occurred: {e}") from e
    except AttributeError as e:
        response_info = str(response) if 'response' in locals() else "Response object not available"
        raise GeminiApiError(f"Error parsing Gemini API response structure: {e}. Response info: {response_info}") from e
    except Exception as e:
        raise GeminiApiError(f"An unexpected error occurred during Gemini interaction: {e}") from e