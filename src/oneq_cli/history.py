import json
import os
from pathlib import Path
from typing import List, Dict, Any

from platformdirs import user_data_dir

APP_NAME = "1q"
HISTORY_DIR_NAME = "1q"
HISTORY_FILE_NAME = "history.json"

def get_history_dir_path() -> Path:
    """Returns the path to the application's history directory."""
    return Path(user_data_dir(APP_NAME, appauthor=False))

def get_history_file_path() -> Path:
    """Returns the path to the history file."""
    return get_history_dir_path() / HISTORY_FILE_NAME

def load_history() -> List[Dict[str, str]]:
    """Loads the interaction history from the history file."""
    history_file = get_history_file_path()
    if not history_file.exists():
        return []

    try:
        with open(history_file, "r") as f:
            history = json.load(f)
        return history
    except FileNotFoundError:
        return [] # Handle case where file doesn't exist.
    except json.JSONDecodeError:
        print("Error decoding history file.  Returning empty history.") # Using print here as console might not be available.
        return []
    except OSError as e:
        print(f"OS error reading history file: {e}") # Using print here as console might not be available.
        return []
    except Exception as e:
        print(f"Unexpected error reading history file: {e}")
        return []

def save_history(query: str, command: str) -> None:
  """Saves a query and its corresponding command to the history file."""
    history = load_history()
    history.append({"query": query, "command": command})

    # Limit history size (e.g., to the last 100 entries)
    history = history[-100:]

    history_file = get_history_file_path()
    try:
        # Ensure the history directory exists
        history_dir = get_history_dir_path()
        history_dir.mkdir(parents=True, exist_ok=True)

        with open(history_file, "w") as f:
            json.dump(history, f, indent=4)
    except OSError as e:
        print(f"Error writing history file: {e}") # Using print here as console might not be available.
    except Exception as e:
         print(f"Unexpected error writing history file: {e}")