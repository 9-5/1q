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
            os_name = "Linux (Distribution info unavailable)"
        context_parts.append(f"OS: {os_name}")
    else:
        context_parts.append(f"OS: {system}")

    shell = os.environ.get("SHELL", "Unknown Shell")
    context_parts.append(f"Shell: {shell}")

    return ", ".join(context_parts)


def generate_command(prompt: str, api_key: str) -> Dict[str, Any]:
    """
    Generates a shell command and explanation using the Gemini API.

    Args:
        prompt: The natural language query.
        api_key: The Gemini API key.

    Returns:
        A dictionary containing the generated command and explanation.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)

    platform_context = _get_platform_context()

    enriched_prompt = f"""
    You are an expert command-line tool that translates natural language into executable commands.
    Your goal is to understand the user's intent and provide the single best command that fulfills their request.
    Consider the user's platform to provide compatible commands. Current platform context: {platform_context}.
    Output the command in a single line, without any additional formatting or comments.

    User query: {prompt}
    """

    try:
        response = model.generate_content(enriched_prompt)
        response.resolve()

        if response.prompt_feedback and response.prompt_feedback.block_reason:
            raise GeminiApiError(f"The Gemini API blocked the request due to: {response.prompt_feedback.block_reason}")

        command = response.text.strip()
        explanation = "This command was generated based on your query. Review it carefully before execution." # For now, a static explanation

        return {"command": command, "explanation": explanation}

    except google_exceptions.QuotaExceeded as e:
         raise GeminiApiError(
             f"Gemini API Quota Exceeded: You have exceeded your API quota. ({e})") from e
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