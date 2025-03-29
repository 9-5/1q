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
*   [Contributing](#contributing)
*   [License](#license)

## Features
*   **Natural Language to Code**: Describe what you want in plain English, and let 1Q generate the command for you.
*   **Cross-Platform**: Works on Windows, macOS, and Linux.
*   **Interactive TUI**: Review, modify, and execute commands in a user-friendly Textual interface.
*   **Configurable**: Set your preferred output style (auto, tui, inline).

## Installation

```bash
pip install oneq
```

## Usage

```bash
1q [flags] "your query here"
```

### Flags

```
usage: 1q [-h] [-k API_KEY] [--show-config-path] [--clear-config]
          [--set-default-output STYLE] [-v]
          [query]

positional arguments:
  query                 The query to convert into a command.

options:
  -h, --help            show this help message and exit
  -k API_KEY, --api-key API_KEY
                        Set the Gemini API key. Overrides config default.
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