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

        try:
            shell = os.path.basename(os.environ.get('SHELL', 'Unknown'))
            context_parts.append(f"Shell: {shell}")
        except:
            pass

        context_parts.append(f"OS: {os_name}")
    elif system == "Darwin":
        os_name = "macOS"
        os_version = platform.mac_ver()[0]  # e.g., "10.15.7"
        context_parts.append(f"OS: {os_name} {os_version}")
        try:
            shell = os.path.basename(os.environ.get('SHELL', 'Unknown'))
            context_parts.append(f"Shell: {shell}")
        except:
            pass
    elif system == "Windows":
        os_name = "Windows"
        os_version = platform.version()  # e.g., "10.0.19041"
        context_parts.append(f"OS: {os_name} {os_version}")
        try:
            shell = os.environ.get('COMSPEC', 'cmd.exe')  # COMSPEC usually points to cmd.exe
            context_parts.append(f"Shell: {shell}")

        except:
            pass
    else:
        context_parts.append(f"OS: {system}")

    return ", ".join(context_parts)


def init_gemini_api(api_key: str):
    """Initializes the Gemini API with the provided API key."""
    try:
        genai.configure(api_key=api_key)
        return genai
    except Exception as e:
        raise GeminiApiError(f"Error initializing Gemini API: {e}") from e

def generate_command(genai: Any, query: str) -> Any:
    """Generates a shell command using the Gemini API."""
    model = genai.GenerativeModel(MODEL_NAME)
    platform_context = _get_platform_context()

    prompt = f"""You are a command-line assistant. Your goal is to translate a user's natural language query into a shell command.
    The user is operating in the following environment: {platform_context}. Only respond with the shell command, unless the user asks for an explanation.
    If the user asks a question that is not related to generating shell commands, respond politely that you are designed to generate shell commands.
    If you are unable to generate a command, explain why. Do not ask the user for clarification.
    Here are some examples:
    User Query: create a directory called "test"
    Generated Command: ```mkdir test```
    User Query: list all files in the current directory
    Generated Command: ```ls -l```
     User Query: show the first 10 lines of the file "my_file.txt"
    Generated Command: ```head -n 10 my_file.txt```
    User Query: search for the string "hello" in all files in the current directory
    Generated Command: ```grep -r "hello" .```
    Now generate the command for the following query: {query}
    """

    try:
        response = model.generate_content(prompt)
        return response
    except google_exceptions.ServiceUnavailable as e:
        raise GeminiApiError(f"Gemini API Service Unavailable: Is the service down? ({e})") from e
    except google_exceptions.APIError as e:
        raise GeminiApiError(f"Gemini API Error: Check your API key and request details. ({e})") from e
    except google_exceptions.PermissionDenied as e:
        raise GeminiApiError(f"Gemini API Permission Denied: Insufficient permissions to access the API. ({e})") from e
    except google_exceptions.ResourceExhausted as e:
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