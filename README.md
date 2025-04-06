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

*   **Natural Language to Code**: Describe what you want to do, and `1q` will generate the corresponding shell command.
*   **Cross-Platform**: Works on Windows, macOS, and Linux.
*   **Interactive TUI**: Review, modify, and execute commands in a user-friendly terminal interface.
*   **Configuration**: Customize the output style and manage your API key.
*   **History**: Access a history of your previous queries and generated commands.

## Installation

### Prerequisites

*   Python 3.8 or higher
*   A Google AI Studio API key (required for accessing the Gemini API). Get one [here](https://makersuite.google.com/app/apikey).

### Installing from PyPI

```bash
pip install oneq
```

### Installing from Source

Clone the repository:

```bash
git clone https://github.com/9-5/1q.git
cd 1q
```

Install with `pip`:

```bash
pip install .
```

Alternatively, use `setuptools`:

```bash
python setup.py install
```

## Usage

To run `1q`, simply type `1q` followed by your query:

```bash
1q <your_query>
```

For example:

```bash
1q list files in Documents ending with .pdf
```

### Setting the API Key

The first time you run `1q`, it will prompt you for your Gemini API key. You can also set it manually using the `ONEQ_GEMINI_API_KEY` environment variable or via the config file (see Configuration).

### Command-Line Options

```
usage: 1q [-h] [-c] [-s STYLE] [-v] [query]

1Q - The right one-liner is just one query away.

positional arguments:
  query                 The query to convert to a command.

options:
  -h, --help            show this help message and exit
  -c, --clear-history   Clear the history of queries and commands.
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