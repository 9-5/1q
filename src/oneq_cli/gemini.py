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
            pass  # Ignore errors getting distro info
        context_parts.append(f"OS: {os_name}")

    shell = os.environ.get("SHELL")
    if shell:
        shell_name = os.path.basename(shell)
        context_parts.append(f"Shell: {shell_name}")

    return ", ".join(context_parts)


def resolve_query(query: str, api_key: str) -> Dict[str, Any]:
    """
    Resolves a natural language query into a shell command and explanation using the Gemini API.

    Args:
        query: The natural language query.
        api_key: The Gemini API key.

    Returns:
        A dictionary containing the generated command and explanation.
        Returns empty strings if the API call fails or the response is malformed.

    Raises:
        GeminiApiError: If there is an error communicating with the Gemini API.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)

    platform_context = _get_platform_context()

    prompt = f"""
    You are a helpful AI assistant that translates natural language queries into shell commands.
    Your responses should be concise and to the point.
    Consider the user's platform for command generation: {platform_context}.
    Provide the command, and a brief explanation of what the command does.

    Example:
    User Query: list files in Documents ending with .pdf
    Command: ls ~/Documents/*.pdf
    Explanation: Lists all files in the Documents directory that end with the .pdf extension.

    Now, respond to the following query:
    User Query: {query}
    """

    try:
        response = model.generate_content(prompt)
        response.raise_for_status()

        response_text = response.text

        # Simple parsing to extract command and explanation.  Handle missing parts gracefully.
        command_match = re.search(r"Command:\s*(.+)", response_text)
        explanation_match = re.search(r"Explanation:\s*(.+)", response_text)

        command = command_match.group(1).strip() if command_match else ""
        explanation = explanation_match.group(1).strip() if explanation_match else ""

        return {"command": command, "explanation": explanation}

    except google_exceptions.ServiceUnavailable as e:
        raise GeminiApiError(f"Gemini API Service Unavailable: The service is currently unavailable. ({e})") from e
    except google_exceptions.Timeout as e:
        raise GeminiApiError(f"Gemini API Timeout: The request timed out. ({e})") from e
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