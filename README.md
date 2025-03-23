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

*   **Natural Language to Command:** Converts your natural language queries into executable shell commands.
*   **Cross-Platform Compatibility:** Works seamlessly on Linux, macOS, and Windows.
*   **Interactive Mode:** Supports interactive command review, modification, and execution.
*   **Configurable:** Allows you to set default output styles and manage your Gemini API key.

## Introduction

`1q` bridges the gap between human language and machine commands. Simply ask `1q` what you want to do, and it will generate the appropriate command for you. Whether you're a seasoned developer or new to the command line, `1q` helps you save time and effort.

## Installation

```bash
pip install oneq
```

## Usage

```bash
1q <your_query>
```

For example: 1q list files in Documents ending with .pdf
```

Here's the complete help printout.
```text
usage: 1q [-h] [--show-config-path] [--clear-config] [--set-default-output {auto,tui,inline}] [-v] [query]

1Q - The right one-liner is just one query away.

Positional Arguments:
  query                 The natural language query for generating commands.

Optional Arguments:
  -h, --help            show this help message and exit

Display and Configuration:
  These actions configure 1q or display useful information. Requires arguments like --set-default-output STYLE, STYLE being a valid option (auto, tui, inline).
  Missing arguments or invalid options result in no change to the config default.
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