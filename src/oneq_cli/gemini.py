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
        context_parts.append(f"OS: {os_name}")

    shell = os.environ.get('SHELL')
    if shell:
        shell_name = os.path.basename(shell)
        context_parts.append(f"Shell: {shell_name}")

    return ", ".join(context_parts)

def generate_command(query: str, api_key: str) -> Dict[str, Any]:
    """
    Generates a shell command using the Gemini API based on the given query.

    Args:
        query (str): The natural language query for generating the command.
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
    You are a command-line AI assistant.  Your job is to translate user requests into shell commands.
    The user is on {platform_context}.
    Always respond with a valid command that can be executed in a terminal, unless the request is impossible.
    If a TUI is needed, or the request is ambiguous, ask the user. Do not offer code unless asked for.
    Be concise, and do not provide any additional explanation or context.
    If the user asks a question that is not related to generating shell commands, respond politely that you are designed only to provide shell commands.
    If the user asks for code, provide a code block with the correct language tag.

    User Query: {query}
    """

    try:
        response = model.generate_content(prompt)
        response.resolve() # Force the future to resolve immediately, catching exceptions

        # Extract command (crude, but works for now). Look for the first line that doesn't start with a comment.
        command = ""
        for line in response.text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                command = line
                break

        return {"command": command.strip(), "explanation": "Generated command from Gemini"}
    except google_exceptions.QuotaExceeded as e:
        raise GeminiApiError("Gemini API Quota Exceeded: You have exceeded your quota for the Gemini API.") from e
    except google_exceptions.ServiceUnavailable as e:
        raise GeminiApiError("Gemini API Service Unavailable: The Gemini API service is currently unavailable.") from e
    except google_exceptions.APIError as e:
        raise GeminiApiError(f"Gemini API Error: An API error occurred: {e}") from e
    except google_exceptions.RateLimitExceeded as e:
        raise GeminiApiError("Gemini API Rate Limit Exceeded: You are sending requests too quickly.") from e
    except google_exceptions.InternalServerError as e:
        raise GeminiApiError("Gemini API Internal Server Error: An internal error occurred on the Gemini API server.") from e
    except google_exceptions.InvalidArgument as e:
        raise GeminiApiError(f"Gemini API Invalid Argument: The request to the Gemini API was invalid. ({e})") from e
    except google_exceptions.PermissionDenied as e:
        raise GeminiApiError("Gemini API Permission Denied: You do not have permission to access the Gemini API.") from e
    except google_exceptions.NotFound as e:
        raise GeminiApiError("Gemini API Not Found: The requested resource was not found.") from e
    except google_exceptions.Cancelled as e:
        raise GeminiApiError("Gemini API Request Cancelled: The request to the Gemini API was cancelled.") from e
    except google_exceptions.DeadlineExceeded as e:
        raise GeminiApiError("Gemini API Deadline Exceeded: The request to the Gemini API took too long to respond.") from e
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