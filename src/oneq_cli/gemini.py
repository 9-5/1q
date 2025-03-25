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
            # Handle cases where freedesktop_os_release is not available (older Python versions)
            try:
                import distro
                os_name += f" ({distro.name()})"
            except ImportError:
                pass  # Fallback to just "Linux"
        context_parts.append(f"Operating System: {os_name}")
    else:
        context_parts.append(f"Operating System: {system}")

    shell = os.environ.get("SHELL") or os.environ.get("COMSPEC") or "Unknown shell"
    context_parts.append(f"Shell: {shell}")
    return ", ".join(context_parts)

def generate_command(query: str, api_key: str) -> Dict[str, Any]:
    """
    Generates a shell command and explanation using the Gemini API.

    Args:
        query (str): The natural language query.
        api_key (str): The Gemini API key.

    Returns:
        Dict[str, Any]: A dictionary containing the generated command and explanation.

    Raises:
        GeminiApiError: If there's an error communicating with the Gemini API.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)

    platform_context = _get_platform_context()

    prompt = f"""
    You are a helpful assistant that translates natural language queries into shell commands.
    Your responses are structured as JSON, with a "command" key for the shell command and an "explanation" key
    for a brief explanation of what the command does.
    Here is platform context for more precise command generation: {platform_context}.
    If the query is ambiguous, ask for clarification.
    If you cannot generate a command, return a JSON object with an "error" key describing the problem.
    For example:
    {{
      "command": "ls -l",
      "explanation": "This command lists all files and directories in the current directory with detailed information."
    }}
    Now, respond to the following query: {query}
    """

    try:
        response = model.generate_content(prompt)
        response.resolve()
        response_text = response.text

        # Basic JSON validation (more robust validation might be needed)
        if not isinstance(response_text, str):
            raise GeminiApiError(f"Gemini API returned non-string response: {response_text}")

        # Attempt to extract JSON using regex (safer than naive eval)
        json_match = None
        try:
            import json
            json_match = json.loads(response_text)
        except json.JSONDecodeError as e:
             raise GeminiApiError(f"Failed to decode JSON from Gemini API response: {e}. Raw response: {response_text}") from e

        if json_match is None or not isinstance(json_match, dict):
            raise GeminiApiError(f"Could not parse JSON from the response. Raw response: {response_text}")

        return json_match

    except google_exceptions.APIError as e:
        raise GeminiApiError(
            f"Gemini API Error: {e}") from e # General API error (check inner exception for details)
    except google_exceptions.InvalidArgument as e:
        raise GeminiApiError(
            f"Gemini API Invalid Argument: Check your prompt or API key. ({e})") from e
    except google_exceptions.PermissionDenied as e:
        raise GeminiApiError(
            f"Gemini API Permission Denied: Insufficient permissions or API not enabled. ({e})") from e
    except google_exceptions.ResourceExhausted as e:
        raise GeminiApiError(
            f"Gemini API Resource Exhausted: Quota limit reached? ({e})") from e
    except google_exceptions.FailedPrecondition as e:
         raise GeminiApiError(f"Gemini API Failed Precondition: API not enabled or billing issue? ({e})") from e
    except google_exceptions.GoogleAPIError as e:
        raise GeminiApiError(f"An unexpected Gemini API error occurred: {e}") from e
    except AttributeError as e:
        response_info = str(response) if 'response' in locals() else "Response object not available"
        raise GeminiApiError(f"Error parsing Gemini API response structure: {e}. Response info: {response_info}") from e
    except Exception as e:
        raise GeminiApiError(f"An unexpected error occurred during Gemini interaction: {e}") from e