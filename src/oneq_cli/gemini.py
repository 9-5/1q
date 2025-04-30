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
            # Handle cases where platform.freedesktop_os_release() is not available
            pass
        except Exception as e:
            console.print(f"Error getting Linux distribution info: {e}", style="yellow")
    else:
        os_name = system

    shell_name = os.environ.get("SHELL")
    if shell_name:
        shell_name = os.path.basename(shell_name)  # Just get the shell's name, not the full path
        context_parts.append(f"Shell: {shell_name}")
    else:
        context_parts.append("Shell: Unknown")

    context_parts.append(f"OS: {os_name}")
    return ", ".join(context_parts)


def generate_command(query: str, api_key: str) -> Dict[str, Any]:
    """Generates a shell command using the Gemini API.

    Args:
        query: The natural language query.
        api_key: The Gemini API key.

    Returns:
        A dictionary containing the generated command and other information.  The "command" key holds the generated shell command.

    Raises:
        GeminiApiError: If there is an error communicating with the Gemini API.
    """

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)
    platform_context = _get_platform_context()

    prompt = f"""
    You are a helpful AI assistant that translates natural language queries into shell commands.
    Your responses must be executable commands, and nothing else. Do not add any prose or descriptive text.
    The user's operating system and shell is: {platform_context}.
    If a command requires confirmation (e.g., prompts 'Are you sure?'), assume the default is yes.
    If the user asks to create a file or directory, use absolute paths (e.g. /Users/john/documents/newfile.txt)

    User Query: {query}
    """
    try:
        response = model.generate_content(prompt)
        response.resolve()  # Force the API call to happen immediately

        if response.prompt_feedback and response.prompt_feedback.block_reason:
            raise GeminiApiError(f"Gemini API Safety Filter blocked the request: {response.prompt_feedback.block_reason}")

        command = response.text.strip()
        return {"command": command, "query": query}  # Return the query as well for history

    except google_exceptions.ServiceUnavailable as e:
        raise GeminiApiError(
            "Gemini API Service Unavailable: Could not connect to the service. Check your network connection.") from e
    except google_exceptions.PermissionDenied as e:
        raise GeminiApiError(
            "Gemini API Permission Denied: Check your API key and permissions.") from e
    except google_exceptions.BadRequest as e:
        raise GeminiApiError(f"Gemini API Bad Request: {e}") from e
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