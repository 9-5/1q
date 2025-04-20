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
        except AttributeError:  # Handle systems where freedesktop_os_release is not available
            os_name = "Linux (Distribution info not available)"
        context_parts.append(os_name)
    else:
        context_parts.append(system)

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

    prompt = f"""You are a command-line assistant. Your task is to convert a natural language query into a shell command.
    The user's operating system is: {platform_context}.
    Only respond with the shell command, and nothing else.  Do not include any explanations or context.
    If the query is ambiguous, make your best guess. If you cannot generate a command, return an empty string.

    Query: {query}
    """

    try:
        response = model.generate_content(prompt)
        response.resolve() #  Explicitly resolve the response (if needed)
        command = response.text.strip()

        # Basic cleaning to remove any surrounding quotes or backticks
        command = re.sub(r"^`|`$", "", command)
        command = re.sub(r"^\"|\"$", "", command)
        command = re.sub(r"^'|'$", "", command)

        return command

    except google_exceptions.ServiceUnavailable as e:
        raise GeminiApiError(f"Gemini API Service Unavailable: {e}") from e
    except google_exceptions.APIError as e:
        raise GeminiApiError(f"Generic Gemini API Error: {e}") from e
    except google_exceptions.PermissionDenied as e:
        raise GeminiApiError(f"Gemini API Permission Denied: Check your API key permissions. ({e})") from e
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