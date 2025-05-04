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
        except:  # Broad except, platform info is best effort.
            pass
        context_parts.append(f"OS: {os_name}")

    shell = os.environ.get('SHELL')
    if shell:
        shell_name = os.path.basename(shell)
        context_parts.append(f"Shell: {shell_name}")

    return ", ".join(context_parts)


def generate_command(api_key: str, query: str) -> Dict[str, str]:
    """
    Generates a shell command based on the user's query using the Gemini API.

    Args:
        api_key: The Gemini API key.
        query: The user's natural language query.

    Returns:
        A dictionary containing the generated command and its explanation.

    Raises:
        GeminiApiError: If there is an error communicating with the Gemini API.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)

    platform_context = _get_platform_context()

    prompt = f"""You are a command-line assistant. Given a user's query, you generate a shell command 
    that satisfies the query. Provide a short explanation of the command.
    The generated command should be executable in the current environment.
    Current Environment Details: {platform_context}
    Query: {query}
    Respond in JSON format with "command" and "explanation" keys.
    Example:
    {{"command": "ls -l", "explanation": "Lists all files in the current directory with detailed information."}}
    """

    try:
        response = model.generate_content(prompt)
        response.resolve()  # Force the API call to check for errors immediately
        return response.parts[0].text  # Directly return the JSON string, parsing is handled downstream
    except google_exceptions.QuotaExceeded as e:
        raise GeminiApiError(
            "Gemini API Quota Exceeded: You have exceeded your quota for the Gemini API.  Check usage and limits in Google AI Studio.") from e
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