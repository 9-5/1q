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
        context_parts.append(f"Operating System: {os_name}")

    shell = os.environ.get("SHELL")
    if shell:
        shell_name = os.path.basename(shell)
        context_parts.append(f"Shell: {shell_name}")

    return ", ".join(context_parts)

def generate_command(api_key: str, query: str) -> Optional[Dict[str, Any]]:
    """Generates a shell command using the Gemini API.

    Returns:
        A dictionary containing the 'command' and 'explanation', or None on failure.
    Raises:
        GeminiApiError: If there's an error communicating with the Gemini API.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)
    platform_context = _get_platform_context()
    prompt = f"""
    You are a command-line expert.  A user will describe what they want to do, and you will generate a single command to do it.
    The command should be as short as possible.
    Include a brief explanation of what the command does.
    The response must be in JSON format, with the following keys: "command" and "explanation".
    Example:
    User: list files in Documents ending with .pdf
    Response: {{"command": "ls ~/Documents/*.pdf", "explanation": "Lists all files ending in .pdf in the Documents directory."}}
    User: {query}
    """

    try:
        response = model.generate_content(prompt)
        response.resolve()  # Ensure the response is fully populated
        response_text = response.text
        try:
            import json
            # Attempt to parse the response as JSON
            response_json = json.loads(response_text)
            return response_json
        except json.JSONDecodeError as e:
            console.print(f"[red]JSON Decode Error: {e}[/]", style="red")
            console.print(f"[red]Raw Response Text: {response_text}[/]", style="red")  # Print the raw response
            raise GeminiApiError(f"Could not decode Gemini API response as JSON: {e}. Raw response printed above.") from e
    except google_exceptions.InvalidArgument as e:
        raise GeminiApiError(f"Gemini API Invalid Argument: Check your prompt or API key. ({e})") from e
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