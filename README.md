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
*   [Usage](#usage)
*   [Configuration](#configuration)
*   [Contributing](#contributing)
*   [License](#license)

## Features

*   **Natural Language to Command:** Describe what you want to do, and 1q generates the command for you.
*   **Cross-Platform:** Works on Linux, macOS, and Windows.
*   **Interactive TUI:** Refine and execute commands through a Textual UI.
*   **Configuration:** Customize 1q with a configuration file.

## Installation

```bash
pip install oneq
```

## Usage

```bash
1q <your query>
```

Example: 1q list files in Documents ending with .pdf

```bash
1q --help
```

```
usage: 1q [-h] [-v] [--show-config-path] [--clear-config] [--set-default-output STYLE] [query]

1Q - The right one-liner is just one query away.

positional arguments:
  query                 The query to translate into a command.

options:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit

Configuration and Info Actions:
  --show-config-path    Print the path to the configuration file and exit.
  --clear-config        Remove the configuration file (prompts for confirmation).
  --set-default-output STYLE
                        Set and save the default output style in the config file (auto, tui, inline).

Example: 1q list files in Documents ending with .pdf
```

## Configuration

1q uses a configuration file to store settings such as the Gemini API key and default output style.

The configuration file is located in:

*   `~/.config/1q/config.ini` on Linux
*   `~/Library/Application Support/1q/config.ini` on macOS
*   `%APPDATA%\1q\config.ini` on Windows

You can also use the `--show-config-path` command-line option to display the configuration file path.

## Contributing

Contributions are welcome! If you find a bug or have a feature request, please open an issue on the GitHub repository (link to be added).

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details (or check `pyproject.toml`).