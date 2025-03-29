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
            # Handle potential errors with platform.freedesktop_os_release()
            pass
        context_parts.append(os_name)
    elif system == "Windows":
        context_parts.append("Windows")
    elif system == "Darwin":
        context_parts.append("macOS")
    else:
        context_parts.append(system)

    shell = os.environ.get("SHELL") or os.environ.get("COMSPEC") or "Unknown Shell"
    context_parts.append(f"Shell: {shell}")

    return ", ".join(context_parts)


def init_gemini(api_key: str) -> None:
    """Initializes the Gemini API with the provided API key."""
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        raise GeminiApiError(f"Failed to configure Gemini API: {e}") from e


def generate_command(user_query: str) -> Dict[str, Any]:
    """Generates a command using the Gemini API based on the user query.

    Returns:
        A dictionary containing the generated command, explanation, and any relevant notes.
    """
    model = genai.GenerativeModel(MODEL_NAME)

    platform_context = _get_platform_context()

    prompt = f"""
    You are an expert command-line assistant.  A user will provide a description of a task, and you will generate a single command that performs that task.
    The command should be as concise as possible.
    Consider the user's platform when generating the command.
    The user's platform is: {platform_context}.
    If the user asks for code, provide a complete code snippet, including necessary imports.  Assume the user is using the latest version of Python unless otherwise specified.
    Do not include any introductory or explanatory text before the command or code.
    If the request is ambiguous, ask clarifying questions.
    If you are unable to generate a command, explain why.
    Provide a brief explanation of the command.
    Also provide any important notes or warnings about the command's usage.

    User Query: {user_query}
    """

    try:
        response = model.generate_content(prompt)
        response.resolve()  # Force the API call to check for errors eagerly

        if response.prompt_feedback and response.prompt_feedback.block_reason:
            raise GeminiApiError(f"The Gemini API blocked the request due to: {response.prompt_feedback.block_reason}")

        command = response.text.strip()

        # Basic filtering (can be expanded)
        command = command.replace("`", "") #Remove backticks

        return {
            "command": command,
            "explanation": "Explanation of the command.", #TODO: Get explanation from model
            "notes": "Important notes about the command." #TODO: Get notes from model
        }

    except google_exceptions.QuotaExceeded as e:
        raise GeminiApiError(f"Gemini API Quota Exceeded: Have you exceeded your API usage limits? ({e})") from e
    except google_exceptions.PermissionDenied as e:
        raise GeminiApiError(f"Gemini API Permission Denied: Check your API key and permissions. ({e})") from e
    except google_exceptions.ServiceUnavailable as e:
        raise GeminiApiError(f"Gemini API Service Unavailable: The service is currently unavailable. ({e})") from e
    except google_exceptions.APIError as e:
        raise GeminiApiError(f"Gemini API Error: A general API error occurred. ({e})") from e
    except google_exceptions.InvalidArgument as e:
        raise GeminiApiError(f"Gemini API Invalid Argument: Check your request parameters. ({e})") from e
    except google_exceptions.NotFound as e:
        raise GeminiApiError(f"Gemini API Not Found: The requested resource was not found. ({e})") from e
    except google_exceptions.InternalServerError as e:
        raise GeminiApiError(
            "Gemini API Internal Server Error: An unexpected error occurred on the server. ({e})") from e
    except google_exceptions.DeadlineExceeded as e:
        raise GeminiApiError(
            "Gemini API Deadline Exceeded: The request timed out. Consider simplifying your query. ({e})") from e
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