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
            pass  # Ignore errors getting distro info
        context_parts.append(os_name)
    else:
        context_parts.append(system)

    shell = os.environ.get("SHELL")
    if shell:
        shell_name = os.path.basename(shell)
        context_parts.append(f"Shell: {shell_name}")

    python_version = platform.python_version()
    context_parts.append(f"Python {python_version}")

    return ", ".join(context_parts)


def generate_command(api_key: str, query: str) -> Optional[str]:
    """
    Generates a shell command or code snippet using the Gemini API.

    Args:
        api_key: The Gemini API key.
        query: The natural language query.

    Returns:
        The generated command as a string, or None if an error occurred.
    """
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(MODEL_NAME)

    platform_context = _get_platform_context()

    prompt = f"""
    You are a helpful AI assistant that translates natural language into shell commands, command chains, and code snippets.
    You should generate commands that are most likely to work and are the most efficient.
    Consider the user's platform when generating commands. Current platform context: {platform_context}

    User Query: {query}
    """

    try:
        response = model.generate_content(prompt)
        if response and hasattr(response, "text"):
            return response.text.strip()
        else:
            console.print(f"Unexpected response structure: {response}", style="red")
            return None
    except google_exceptions.InvalidArgument as e:
        raise GeminiApiError(f"Gemini API Invalid Argument: Check your prompt or API key. ({e})") from e
    except google_exceptions.PermissionDenied as e:
        raise GeminiApiError(
            "Gemini API Permission Denied: Ensure the API is enabled and you have the correct permissions.") from e
    except google_exceptions.QuotaExceeded as e:
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