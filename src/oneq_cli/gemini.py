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
            os_name = f"{os_name} ({distro})"
        except FileNotFoundError:
            pass  # Unable to determine distro.

        try:
            shell = os.environ.get("SHELL")
            if shell:
                shell_name = os.path.basename(shell)
                context_parts.append(f"Shell: {shell_name}")
        except Exception:
            pass

    context_parts.insert(0, f"OS: {system}")
    return ", ".join(context_parts)

def generate_command(query: str, api_key: str) -> Dict[str, Any]:
    """Generates a shell command based on the given query using the Gemini API."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)

    platform_context = _get_platform_context()

    prompt = f"""You are a command-line tool expert. Generate a single, valid shell command (or a short chain of commands using &&) that satisfies the user's request.
The command should be executable directly in a terminal. Only output the command(s).
If the request is ambiguous, make reasonable assumptions to provide a useful command.

Here is some context about the user's environment: {platform_context}

User Query: {query}
"""
    try:
        response = model.generate_content(prompt)
        command = response.text.strip()
        # Basic cleaning: Remove any leading/trailing quotes or backticks.
        command = command.strip('"`')
        return {"command": command}
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