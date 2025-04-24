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
        except AttributeError: # Handle cases where freedesktop_os_release might not be available
            pass

        context_parts.append(f"Operating System: {os_name}")
    else:
        context_parts.append(f"Operating System: {system}")

    shell = os.environ.get("SHELL")
    if shell:
        shell_name = os.path.basename(shell)
        context_parts.append(f"Shell: {shell_name}")

    return ", ".join(context_parts)


def generate_command(api_key: str, query: str) -> Dict[str, str]:
    """
    Generates a shell command based on the given query using the Gemini API.

    Args:
        api_key: The Gemini API key.
        query: The natural language query.

    Returns:
        A dictionary containing the generated command and its explanation, or None if an error occurs.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME) # was 'gemini-pro'

    platform_context = _get_platform_context()

    prompt = f"""
    You are an expert at generating shell commands and code snippets based on natural language queries.
    Your primary goal is to provide accurate, concise, and executable commands. Assume the user is an expert.
    Provide just the command unless an explanation is unavoidable. Assume the user is running the command in a {platform_context} environment.

    Example:
    User Query: list files in Documents ending with .pdf
    Generated Command: find ~/Documents -name "*.pdf"

    User Query: {query}
    Generated Command:
    """

    try:
        response = model.generate_content(prompt)

        # Extract the command from the response.  Look for a code block, otherwise take the first line.
        response_text = response.text
        command = ""
        explanation = ""

        # Regex to find markdown code blocks (```shell ... ``` or ```bash ... ``` or ``` ... ```)
        match = re.search(r"```(?:shell|bash)?\n(.*?)\n```", response_text, re.DOTALL)
        if match:
            command = match.group(1).strip()
            # If there's anything *before* the code block, consider it an explanation.
            pre_match = response_text[:match.start()].strip()
            if pre_match:
                explanation = pre_match
        else:
            # No code block found; just take the first line as the command.
            command = response_text.splitlines()[0].strip()
            if len(response_text.splitlines()) > 1:
                explanation = "\n".join(response_text.splitlines()[1:]).strip()


        return {"command": command, "explanation": explanation}

    except google_exceptions.ResourceExhausted as e:
        raise GeminiApiError("Gemini API Resource Exhausted: Quota limit reached? ({e})") from e
    except google_exceptions.FailedPrecondition as e:
         raise GeminiApiError(f"Gemini API Failed Precondition: API not enabled or billing issue? ({e})") from e
    except google_exceptions.GoogleAPIError as e:
        raise GeminiApiError(f"An unexpected Gemini API error occurred: {e}") from e
    except AttributeError as e:
        response_info = str(response) if 'response' in locals() else "Response object not available"
        raise GeminiApiError(f"Error parsing Gemini API response structure: {e}. Response info: {response_info}") from e
    except Exception as e:
        raise GeminiApiError(f"An unexpected error occurred during Gemini interaction: {e}") from e