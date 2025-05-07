# 1Q - The right one-liner is just one query away.
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/oneq.svg)](https://badge.fury.io/py/oneq)
<p align="center">
    <img src="assets/icons/1Q.svg" alt="1Q Icon" height=25% width=25%>
</p>

`1q`, short for 1Query, is a cross-platform command-line utility that lets you use natural language to generate shell commands, command chains, and code snippets right in your terminal. Get the command you need instantly, review it, modify it, and even execute it directly!

https://github.com/user-attachments/assets/b3bb7b79-a9f3-4d23-96f6-788cecd5dfa4

## Table of Contents

*   [Features](#features)
*   [Installation](#installation)
*   [Getting Started](#getting-started)
*   [Configuration](#configuration)
    *   [API Key](#api-key)
    *   [Output Style](#output-style)
*   [Interactive Features & Usage](#️-interactive-features--usage)
    *   [Inline Mode (stderr prompt)](#inline-mode-stderr-prompt)
    *   [TUI Mode (Textual Interface)](#tui-mode-textual-interface)
*   [Command-Line Options](#command-line-options)
*   [Contributing](#contributing)
*   [License](#license)

## Features

*   **Natural Language Input:** Simply type what you want to do (e.g., `1q find all files larger than 50MB in my home dir`).
*   **Gemini Powered:** Leverages Google's powerful Gemini model (specifically `gemini-2.0-flash`) for accurate and relevant command/code generation.
*   **Context-Aware Refinement:** Didn't get the perfect command on the first try? Refine your request in a conversation! `1q` remembers the context.
*   **Intelligent Output:**
    *   **Inline Mode:** For simple queries, get just the raw command printed directly to standard output, perfect for piping (`|`) or immediate use.
    *   **TUI Mode:** For more complex commands, or when explanations/install steps are needed, `1q` automatically launches a Textual User Interface (TUI) for a clear, structured view.
    *   **Configurable Default:** Choose whether you prefer `inline`, `tui`, or `auto` (default) detection as your standard output method.
*   **Interactive Workflow:**
    *   **Execute:** Run the generated command directly from the TUI or the inline prompt (`x` key or `execute` action).
    *   **Modify:** Tweak the command in your editor (`m` key or `modify` action) before execution.
    *   **Copy:** Easily copy the generated command to your clipboard (`c` key or `copy` action).
*   **Structured Responses:** The AI provides not just the `COMMAND:`, but often includes `EXPLANATION:` and `INSTALL:` steps when necessary, clearly presented in the TUI.
*   **Configuration:**
    *   Securely store your Gemini API key via environment variable (`GEMINI_API_KEY`) or a configuration file.
    *   Set your preferred default output style (`--set-default-output`).
*   **Cross-Platform:** Built with Python and Textual, runs on Linux, macOS, and Windows.

## Installation

`1Q` requires **Python 3.8 or higher**.

You can install `1Q` directly from PyPI using pip:

```bash
pip install oneq
```

It's often recommended to install Python CLI tools in isolated environments using tools like `pipx`:

```bash
pipx install oneq
```

*(Optional)* For the inline `copy` action to work reliably, ensure you have a clipboard utility installed (`pyperclip` is used internally):
*   **Linux:** `sudo apt-get install xclip` or `sudo apt-get install xsel` (for X11), or `wl-copy` (for Wayland).
*   **macOS:** `pbcopy` is usually built-in.
*   **Windows:** Should work out of the box.

## Getting Started

1.  **Configure API Key:**
    `1Q` needs a Google Gemini API key. Get one from [Google AI Studio](https://aistudio.google.com/app/apikey). You can configure it in one of two ways:

    *   **(Recommended) Environment Variable:** Set the `GEMINI_API_KEY` environment variable:
        ```bash
        export GEMINI_API_KEY='YOUR_API_KEY_HERE'
        # Add this line to your shell profile (~/.bashrc, ~/.zshrc, etc.) for persistence
        ```

    *   **Configuration File:** Run `1q` once without arguments and without the environment variable set. It will launch an interactive setup TUI to securely save your key to a configuration file.
        ```bash
        1q
        ```
        (Follow the prompts to enter your key and choose a default output style).

2.  **Make your First Query:**
    Ask `1q` to generate a command:
    ```bash
    1q list all python files modified in the last 2 days
    ```

3.  **Interact with the Result:**
    *   If the command is simple, it might print directly to your console (inline mode).
    *   If it's complex or includes details, the TUI will launch.

    *   **Inline Mode:** You'll be prompted for the next action (execute, modify, refine, copy, quit).
    *   **TUI Mode:** Use keyboard shortcuts (see below) to interact.

    Example TUI:
    ```
    ┌────────────────────────── 1Q Response ───────────────────────────┐
    │ ### COMMAND                                                      │
    │ find . -name "*.py" -type f -mtime -2                            │
    │                                                                  │
    │ ### EXPLANATION                                                  │
    │                                                                  │
    │ - `find .`: Search in the current directory (`.`) and subdirs.   │
    │ - `-name "*.py"`: Find files matching the pattern '*.py'.        │
    │ - `-type f`: Only consider regular files.                        │
    │ - `-mtime -2`: Find files modified within the last 2 days (less  │
    │   than 2*24 hours ago).                                          │
    └──────────────────────────────────────────────────────────────────┘
    [c] Copy Cmd [x] Execute [m] Modify [r] Refine [q] Quit
    ```

4.  **Refine (If Needed):**
    If the first command wasn't quite right, choose the `refine` action (or press `r` in the TUI) and enter a follow-up request, like:
    ```
    Refine your request (or press Enter to quit): also exclude the venv directory
    ```
    `1q` will use the previous conversation context to generate an updated command.

---

## Configuration

### API Key

As mentioned in *Getting Started*, the API key is loaded in this order:

1.  `GEMINI_API_KEY` environment variable.
2.  `config.ini` file located in the user's configuration directory.

You can find the configuration file path using:
```bash
1q --show-config-path
```

### Output Style

Control how `1q` presents results:

*   `auto` (Default): Shows TUI for complex results (with explanation/install) or if markers are present; otherwise, shows inline command.
*   `tui`: Always uses the Textual User Interface.
*   `inline`: Always attempts to print the raw command to stdout and details/prompts to stderr.

**Set the default style permanently:**
```bash
# Set TUI as the default
1q --set-default-output=tui

# Set inline as the default
1q --set-default-output=inline

# Set auto as the default
1q --set-default-output=auto
```
This modifies the `output_style` key under the `[Settings]` section in your `config.ini`.

**Override the default for a single run:**
```bash
# Force TUI for this query
1q find unused docker images -o tui

# Force inline output for this query
1q make a directory called temp and cd into it -o inline
```

## ⌨️ Interactive Features & Usage

### Inline Mode (stderr prompt)

When `1q` runs in `inline` mode (or `auto` for simple commands):

1.  The generated command is printed to **stdout**.
2.  Explanation/Install steps (if any) are printed to **stderr**.
3.  A prompt appears on **stderr** asking for your next action:
    *   `execute`: Run the command immediately.
    *   `modify`: Open the command in an interactive prompt for editing.
    *   `refine`: Provide a follow-up natural language instruction.
    *   `copy`: (If `pyperclip` is available) Copy the command to the clipboard.
    *   `quit`: Exit `1q`.

### TUI Mode (Textual Interface)

When `1q` runs in `tui` mode (or `auto` for complex commands):

*   The response is displayed visually, separating Command, Installation, and Explanation.
*   Use these keybindings:
    *   `c`: **Copy** the command to the clipboard.
    *   `x`: **Execute** the command (exits TUI first).
    *   `m`: **Modify** the command (exits TUI first, then opens inline editor).
    *   `r`: **Refine** the query (exits TUI first, then prompts for refinement).
    *   `q` / `Ctrl+C`: **Quit** the TUI and `1q`.

## Command-Line Options

```bash
usage: 1q [-h] [-o {auto,tui,inline}] [--show-config-path] [--clear-config]
          [--set-default-output STYLE] [-v]
          [query ...]

1Q: Your instant command-line and code snippet generator.

positional arguments:
  query                 Your natural language query. If omitted, runs setup (if needed) or shows help.

options:
  -h, --help            show this help message and exit
  -o {auto,tui,inline}, --output {auto,tui,inline}
                        Specify output style for this run: 'auto', 'tui', 'inline'. Overrides config default.
  -v, --version         show program's version number and exit

Configuration and Info Actions:
  --show-config-path    Print the path to the configuration file and exit.
  --clear-config        Remove the configuration file (prompts for confirmation).
  --set-default-output STYLE
                        Set and save the default output style in the config file (auto, tui, inline).

Example: 1q list files in Documents ending with .pdf
```

## Contributing

Contributions are welcome! If you find a bug or have a feature request, please open an issue on the GitHub repository (link to be added).

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details (or check `pyproject.toml`).
