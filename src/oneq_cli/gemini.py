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
        except FileNotFoundError:
            pass  # Unable to determine distro
        context_parts.append(os_name)
    else:
        context_parts.append(system)

    shell = os.environ.get("SHELL")
    if shell:
        shell_name = os.path.basename(shell)
        context_parts.append(f"Shell: {shell_name}")

    return ", ".join(context_parts)


def generate_command(query: str, api_key: str) -> str:
    """Generates a shell command using the Gemini API."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)

    platform_context = _get_platform_context()
    prompt = f"""
    You are an expert in generating shell commands and code snippets.  A user will provide a natural language query, and you should respond with a single line containing ONLY the command or code snippet that satisfies the query. Do not include any additional text, explanation, or formatting.
    The user's operating system and shell is: {platform_context}.
    If asked to create a file, ensure the command does not include a confirmation prompt.
    If a command requires a specific tool that is unlikely to be installed by default (e.g., jq, awk), use a command that installs it.

    Example:
    User: list files in Documents ending with .pdf
    Response: find ~/Documents -name "*.pdf"

    User: {query}
    Response: 
    """

    try:
        response = model.generate_content(prompt)
        response.resolve()  # Force the future to resolve immediately
        return response.text.strip()
    except google_exceptions.QuotaExceeded as e:
        raise GeminiApiError(
            "Gemini API Quota Exceeded: You have exceeded your quota for the Gemini API. Please check your Google Cloud account and quota limits.") from e
    except google_exceptions.RateLimitExceeded as e:
        raise GeminiApiError(
            "Gemini API Rate Limit Exceeded: You are sending requests too quickly. Please reduce the rate at which you are sending requests.") from e
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