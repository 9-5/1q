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
*   [Introduction](#introduction)
*   [Installation](#installation)
*   [Usage](#usage)
*   [Configuration](#configuration)
*   [Contributing](#contributing)
*   [License](#license)

## Features

*   **Natural Language to Command**: Convert natural language queries into executable commands.
*   **Cross-Platform**: Works on Windows, macOS, and Linux.
*   **Customizable**: Configure the output style and other settings.
*   **Interactive TUI**: Review, modify, and execute commands in a terminal UI.
*   **History**: Stores command history and recently asked queries.

## Introduction

`1q` bridges the gap between thought and execution. Instead of wrangling with complex command syntax, describe what you want to achieve, and let `1q` handle the translation.  Whether you're a seasoned developer or just starting, `1q` streamlines your workflow and boosts productivity.

## Installation

### Prerequisites

*   Python 3.8 or higher.
*   A Google AI Studio API key.  You can obtain one from [makersuite.google.com](https://makersuite.google.com/).

### Installing 1Q

```bash
pip install oneq
```

### Setting up your API Key

`1q` requires a Google AI Studio API key to access the Gemini models. You can set this up in a few ways:

1.  **Using the TUI**: Run `1q` without an API key set. The TUI will guide you through the setup process.
2.  **Setting the Environment Variable**: Set the `GEMINI_API_KEY` environment variable.

    ```bash
    export GEMINI_API_KEY="YOUR_API_KEY"
    ```

3.  **Configuration File**: `1q` stores its configuration in a file located in your user config directory.  You can manually edit this file to set the API key (not recommended for security reasons).

## Usage

Simply run `1q` followed by your query:

```bash
1q list files in Documents ending with .pdf
```

### Command-Line Options

```
usage: 1q [-h] [-c] [-s STYLE] [-v] [--show-config-path] [--clear-config]
          [query]

1Q - The right one-liner is just one query away.

positional arguments:
  query                 The query to convert into a command.

options:
  -h, --help            show this help message and exit
  -c, --copy            Copy the generated command to the clipboard.
  -s STYLE, --set-default-output STYLE
                        Set and save the default output style in the config default.
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