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
        except Exception:
            pass  # Unable to determine the specific distribution.
        context_parts.append(os_name)

    shell = os.environ.get("SHELL")
    if shell:
        shell_name = os.path.basename(shell)
        context_parts.append(f"Shell: {shell_name}")

    return ", ".join(context_parts)


def generate_command(query: str, api_key: str) -> str:
    """Generates a shell command from a natural language query using the Gemini API."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)

    platform_context = _get_platform_context()
    prompt = f"""
    You are a helpful AI assistant that translates user requests into shell commands.
    Your responses should be concise and executable in a terminal.

    Here's the user's request: {query}

    Platform Context: {platform_context}

    Return ONLY the shell command. Do not include any explanation or other text.
    """

    try:
        response = model.generate_content(prompt)
        response.resolve() # Raise an exception if the response is blocked
        return response.text.strip()
    except google_exceptions.QuotaExceeded as e:
        raise GeminiApiError(f"Gemini API Quota Exceeded: You have exceeded your API quota. ({e})") from e
    except google_exceptions.ServiceUnavailable as e:
        raise GeminiApiError("Gemini API Service Unavailable: The service is currently unavailable. Please try again later.") from e
    except google_exceptions.APIError as e:
        raise GeminiApiError(
            f"Gemini API Error: There was an API error. Status code: {e.code}, message: {e.message}"
        ) from e
    except google_exceptions.InternalServerError as e:
        raise GeminiApiError("Gemini API Internal Server Error: An internal server error occurred. Please try again later.") from e
    except google_exceptions.BadGateway as e:
        raise GeminiApiError("Gemini API Bad Gateway: There was a bad gateway error. Please try again later.") from e
    except google_exceptions.DeadlineExceeded as e:
        raise GeminiApiError("Gemini API Deadline Exceeded: The request timed out. Please try again later.") from e
    except google_exceptions.NotFound as e:
        raise GeminiApiError(f"Gemini API Resource Not Found: The requested resource was not found. ({e})") from e
    except google_exceptions.PermissionDenied as e:
        raise GeminiApiError(f"Gemini API Permission Denied: You do not have permission to access this resource. ({e})") from e
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