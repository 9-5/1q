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
            pass  # Unable to determine distro.

        context_parts.append(os_name)
    else:
        context_parts.append(system)

    shell = os.environ.get("SHELL")
    if shell:
        shell_name = os.path.basename(shell)
        context_parts.append(f"Shell: {shell_name}")

    return ", ".join(context_parts)


def generate_command(prompt: str, api_key: str) -> str:
    """
    Generates a shell command using the Gemini API.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)

    platform_context = _get_platform_context()
    augmented_prompt = f"""
    Generate a shell command (or chain of commands using &&) that satisfies the user's request.
    The user's operating system and shell is: {platform_context}.
    If the request cannot be satisfied with a single command or chain of commands, respond with an error message.
    If the request is ambiguous, ask for clarification.
    The user's request is: {prompt}
    """

    try:
        response = model.generate_content(augmented_prompt)
        return response.text.strip()
    except google_exceptions.PermissionDenied as e:
        raise GeminiApiError("Gemini API Permission Denied: Ensure the API is enabled and the API key is valid.") from e
    except google_exceptions.QuotaExceeded as e:
         raise GeminiApiError(f"Gemini API Resource Exhausted: Quota limit reached? ({e})") from e
    except google_exceptions.FailedPrecondition as e:
         raise GeminiApiError(f"Gemini API Failed Precondition: API not enabled or billing issue? ({e})") from e
    except google_exceptions.GoogleAPIError as e:
        raise GeminiApiError(f"An unexpected Gemini API error occurred: {e}") from e
    except AttributeError as e:
        response_info = str(response) if 'response' in locals() else "Response object not available"
        raise GeminiApiError(f"Error parsing Gemini API response structure: {e}. Response info: {response_info}") from e
    except Exception as e:
        raise GeminiApiError(f"An unexpected error occurred during Gemini interaction: {e}") from e