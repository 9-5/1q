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
            # Handle cases where freedesktop_os_release() is not available.
            pass
        context_parts.append(os_name)

    shell = os.environ.get("SHELL")
    if shell:
        shell_name = os.path.basename(shell)
        context_parts.append(f"Shell: {shell_name}")

    return ", ".join(context_parts)


def init_gemini(api_key: str) -> None:
    """Initializes the Gemini API with the provided API key."""
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        raise GeminiApiError(f"Failed to initialize Gemini API: {e}") from e


def generate_command(query: str, platform_context: str) -> Dict[str, Any]:
    """Generates a command using the Gemini API based on the given query and platform context."""
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = f"""You are a command-line assistant. The user will provide a natural language query, and you will respond with a single command that satisfies the query.
    Consider the user's operating system and shell when generating the command.
    The user's platform context is: {platform_context}.
    If the query is ambiguous, ask clarifying questions. If you cannot generate a command, explain why.
    The command should be runnable directly in the user's shell. Do not include any explanation or other text.
    Here are some examples:
    User: list files in Documents ending with .pdf
    Command: find Documents -name "*.pdf" -print
    User: create a directory called 'test' in the current directory
    Command: mkdir test
    User: search for the string 'hello' in all files in the current directory
    Command: grep -r "hello" .
    User: show the first 10 lines of file test.txt
    Command: head -n 10 test.txt
    Now, generate the command for the following query:
    {query}
    """
    try:
        response = model.generate_content(prompt)

        # Extract the command from the response (assuming it's the first part of the text)
        command = response.text.strip()

        # Basic cleaning: remove any ```bash or ``` type markers from the response
        command = command.replace("```bash", "").replace("```", "").strip()

        return {"command": command, "response": response.text}
    except google_exceptions.ServiceUnavailable as e:
        raise GeminiApiError(
            "Gemini API Service Unavailable: Is the service down? "
            "Check Google Cloud Status page. ({e})") from e
    except google_exceptions.APIError as e:
         raise GeminiApiError(
            f"Gemini API Error: Check your API key and request parameters. ({e})") from e
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