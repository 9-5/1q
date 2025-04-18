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
        except AttributeError:
            pass  # Handle cases where freedesktop_os_release is not available (older Python versions)
        context_parts.append(os_name)

    shell = os.environ.get("SHELL")
    if shell:
        shell_name = os.path.basename(shell)
        context_parts.append(f"Shell: {shell_name}")

    return ", ".join(context_parts)


def generate_command(api_key: str, query: str) -> Dict[str, str]:
    """
    Generates a shell command using the Gemini API based on the given query.

    Args:
        api_key (str): The Gemini API key.
        query (str): The query to generate a command for.

    Returns:
        Dict[str, str]: A dictionary containing the generated command (or an empty string if generation fails) and any relevant metadata.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)

    platform_context = _get_platform_context()

    prompt = f"""
    You are a command-line assistant.  The user will provide a plain text query, and you should respond with a single line containing a shell command that satisfies the query.
    Do not include any explanation or other text.  Only provide the command.
    The user's operating system and shell is: {platform_context}.
    If the query is unanswerable using command-line tools, respond with an empty string.

    Query: {query}
    """
    try:
        response = model.generate_content(prompt)
        response.resolve()  # Ensure the response is fully populated
        command = response.text.strip()
        return {"command": command}
    except google_exceptions.QuotaExceeded as e:
        raise GeminiApiError(
            "Gemini API Quota Exceeded: You have exceeded your quota for the Gemini API.  Please check your Google Cloud project for quota details.") from e
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