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
            pass  # Just use 'Linux' if distro info fails
        context_parts.append(f"OS: {os_name}")

    shell = os.environ.get('SHELL')
    if shell:
        shell_name = os.path.basename(shell)
        context_parts.append(f"Shell: {shell_name}")

    return ", ".join(context_parts)

def init_gemini(api_key: str) -> None:
    """Initializes the Gemini API with the provided API key."""
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        raise GeminiApiError(f"Failed to configure Gemini API: {e}") from e


def generate_command(query: str) -> Dict[str, Any]:
    """
    Generates a shell command based on the user's query using the Gemini API.

    Returns:
        A dictionary containing the generated command and its explanation.
        Example: {"command": "ls -l", "explanation": "Lists all files in long format."}

    Raises:
        GeminiApiError: If there is an error communicating with the Gemini API.
    """
    model = genai.GenerativeModel(MODEL_NAME)

    platform_context = _get_platform_context()
    prompt = f"""
    You are an expert in generating shell commands.  The user will provide a natural language query,
    and you should generate a shell command that fulfills the query.  Provide a short explanation
    of what the command does.

    Here is some context about the user's environment: {platform_context}

    Respond with a JSON object containing the command and explanation.  The JSON object should have
    the following format:
    {{
        "command": "the generated shell command",
        "explanation": "a short explanation of what the command does"
    }}

    Do not include any other text in your response.  Do not include any code fences or other formatting.
    Just the JSON object.

    Here is the user's query:
    {query}
    """

    try:
        response = model.generate_content(prompt)
        response.resolve() # Force the response to be available immediately
        response_text = response.text
        # Basic JSON extraction using regex
        match =  re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            json_string = match.group(0)
            import json
            try:
                data = json.loads(json_string)
                return data
            except json.JSONDecodeError as e:
                raise GeminiApiError(f"Could not decode JSON from Gemini API response: {e}.  Raw response: {response_text}") from e
        else:
            raise GeminiApiError(f"Could not find JSON in Gemini API response. Raw response: {response_text}")

    except google_exceptions.ServiceUnavailable as e:
        raise GeminiApiError(f"Gemini API Service Unavailable: The service is currently unavailable. ({e})") from e
    except google_exceptions.APIError as e:
        raise GeminiApiError(f"Generic Gemini API Error: {e}") from e
    except google_exceptions.QuotaFailure as e:
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