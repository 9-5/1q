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
            os_name = f"Linux ({distro})"
        except (OSError, AttributeError):
             os_name = "Linux (Distro detection failed)"
        context_parts.append(f"OS: {os_name}")

        shell_path = os.environ.get("SHELL")
        shell_name = os.path.basename(shell_path) if shell_path else "Unknown"
        context_parts.append(f"Shell: {shell_name}")

    elif system == "Windows":
        context_parts.append("OS: Windows")
        context_parts.append("Shell: cmd/powershell") # Assume cmd or powershell

    elif system == "Darwin":
        context_parts.append("OS: macOS")
        shell_path = os.environ.get("SHELL")
        shell_name = os.path.basename(shell_path) if shell_path else "Unknown"
        context_parts.append(f"Shell: {shell_name}")

    else:
        context_parts.append(f"OS: {system}")
        context_parts.append("Shell: Unknown")

    return ", ".join(context_parts)


def get_system_instruction() -> str:
    """Generates the system instruction for the Gemini model, including platform context."""
    platform_context = _get_platform_context()

    # Note: The detailed instructions about formatting (COMMAND:, etc.) are crucial
    # for the model's behavior and should be kept clear.
    instruction = f"""You are an AI assistant providing command-line commands, unique one-line commands (that are efficiently chained to complete the task) or code snippets based on the user's request and their environment. Your goal is to be concise, accurate, and platform-aware.

**User's Environment:**
{platform_context}

Analyze the user's request below, considering their environment, to determine the appropriate level of detail required:

1.  **If the request is simple, direct, and likely requires only a single command/snippet** (e.g., 'list files', 'git commit', basic filtering):
    * Output ONLY the raw command/snippet itself, tailored for the user's environment if possible (e.g., `ls` for Linux/macOS bash/zsh, `dir` for Windows cmd).
    * DO NOT include any explanation, comments, or introductory text.
    * DO NOT use markers like COMMAND:, EXPLANATION:, or INSTALL:. Just the raw output.
    * DO NOT use codeblocks or in-line code markers -- just the raw command/snippet.

2.  **If the request seems more complex, involves non-trivial steps/flags, implies "how-to", requires a sequence of actions, or might benefit from clarification:**
    * Output the command or sequence of commands marked with `COMMAND:` on its own line. Ensure commands are suitable for the user's OS/Shell. This can be a single line containing multiple commands joined by operators like `;`, `&&`, `||`, or `|`.
    * Provide a concise explanation marked with `EXPLANATION:` on its own line, detailing what the command(s) do.
    * DO NOT include installation steps unless explicitly related to the core request.
    * DO NOT use Markdown codeblocks or in-line code markers -- just the raw command/snippet and steps/explanation as previously outlined in this case.

3.  **If the request explicitly mentions installation, setup, configuration, or involves tools/libraries known to require installation:**
    * Output the command or sequence of commands marked with `COMMAND:` on its own line, suitable for the user's environment. This can be a single line containing multiple commands joined by operators like `;`, `&&`, `||`, or `|`.
    * Provide necessary installation steps marked with `INSTALL:` on its own line (e.g., using platform-specific package managers like apt/yum/dnf for Linux, brew for macOS, winget/choco/scoop for Windows, pip for Python).
    * Provide a concise explanation marked with `EXPLANATION:` on its own line, detailing what the command(s) do.
    * DO NOT use codeblocks or in-line code markers -- just the raw command/snippet and steps/explanation as previously outlined in this case.

**Crucially:** Only use the markers (COMMAND:, EXPLANATION:, INSTALL:) when providing detail beyond the raw command/snippet itself (Cases 2 and 3). For Case 1, the output must be *only* the raw command/snippet. Ensure the text following `COMMAND:` is always the pure, executable command or usable code snippet suitable for the user's environment. DO NOT OUTPUT A MARKDOWN CODEBLOCK.

**Conversation Context:** If previous turns are provided, consider them when generating the response to the latest user request.
"""
    return instruction

def generate_command(
    api_key: str,
    user_query: str,
    history: Optional[List[Dict[str, Any]]] = None # Conversation history
    ) -> str:
    """
    Generates a command or code snippet using the Gemini API, handling context.

    Args:
        api_key: The Gemini API key.
        user_query: The user's natural language query.
        history: Optional list of previous user/model conversation turns.

    Returns:
        The potentially multi-line, structured (or raw) response string from Gemini.

    Raises:
        GeminiApiError: If there is an issue with the API call or response.
        ValueError: If inputs are invalid.
    """
    if not api_key:
        raise ValueError("API key must be provided.")
    if not user_query:
         raise ValueError("User query cannot be empty.")

    conversation_history = history or []

    try:
        genai.configure(api_key=api_key)

        safety_settings = [ # Standard safety settings
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        generation_config = genai.types.GenerationConfig(
             candidate_count=1,
             temperature=0.2, # Low temp for consistent commands
        )

        system_instruction_text = get_system_instruction() # Includes platform info

        model = genai.GenerativeModel(
            MODEL_NAME,
            safety_settings=safety_settings,
            generation_config=generation_config,
            system_instruction=system_instruction_text
        )

        # Combine history and new query for the API call
        content_to_send = conversation_history + [{'role': 'user', 'parts': [{'text': user_query.strip()}]}]

        response = model.generate_content(content_to_send)

        # --- Response Handling ---
        if not response.candidates:
            feedback = getattr(response, 'prompt_feedback', None)
            block_reason = getattr(feedback, 'block_reason', 'Unknown')
            raise GeminiApiError(f"Gemini API returned no candidates. Potential safety block or other issue (Reason: {block_reason}). Raw Feedback: {feedback}")

        candidate = response.candidates[0]
        finish_reason = getattr(candidate, 'finish_reason', None) # 1=STOP, 3=SAFETY, etc.

        if finish_reason == 3: # Safety block
            pass # Continue to attempt getting text, might be partial

        try:
             if not candidate.content or not candidate.content.parts:
                 # Check reason if content is empty
                 if finish_reason == 3: raise GeminiApiError("Gemini API response blocked due to safety settings. No content available.")
                 elif finish_reason == 2: raise GeminiApiError("Gemini API response stopped due to maximum token limit.")
                 else: raise GeminiApiError(f"Gemini API response has no text content. Finish Reason: {finish_reason}.")

             generated_text = candidate.content.parts[0].text
        except ValueError as e:
             if finish_reason == 3: raise GeminiApiError("Gemini API response blocked due to safety settings. No content available.") from e
             else: raise GeminiApiError(f"Gemini API response has no text content. Finish Reason: {finish_reason}. Error: {e}") from e
        except AttributeError:
              raise GeminiApiError("Error accessing Gemini API response structure (content/parts/text).")

        cleaned_text = generated_text.strip()

        # Raise error if model didn't stop normally but produced no text
        if not cleaned_text and finish_reason != 1: # 1 == STOP
              raise GeminiApiError(f"Gemini API returned an empty result. Finish Reason: {finish_reason}.")
        # Allow empty return if finish reason was normal stop (query might warrant no command)

        return cleaned_text

    # --- Error Handling ---
    except google_exceptions.PermissionDenied as e:
        raise GeminiApiError(f"Gemini API Permission Denied: Invalid API key or API/billing not enabled? ({e})") from e
    except google_exceptions.InvalidArgument as e:
         raise GeminiApiError(f"Gemini API Invalid Argument: Malformed request or history? ({e})") from e
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