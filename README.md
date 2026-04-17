# Python LLM Chat Agent

An AI-powered document chat agent that lets users query files using natural language and shell-like commands.

![doctests](https://github.com/LucyyyyyyT/python_llm/actions/workflows/doctests.yml/badge.svg)
![flake8](https://github.com/LucyyyyyyT/python_llm/actions/workflows/flake8.yml/badge.svg)
![tests](https://github.com/LucyyyyyyT/python_llm/actions/workflows/test.yml/badge.svg)
[![PyPI](https://img.shields.io/pypi/v/python-llm-lucy)](https://pypi.org/project/python-llm-lucy/)
[![coverage](https://img.shields.io/badge/coverage-90%25-brightgreen)](#)

A chat agent that depends on command line and uses Groq's LLM API. It is able to hold conversations and answer questions. It can also call built-in tools: (`calculate`, `cat`, `grep`, `ls`). 

Here is a working example of my code:
![Demo](demo.gif)

## Usage

Any tool name that starts with '/' will run directly.

```
chat> /ls tools
tools/calculate.py tools/cat.py tools/grep.py tools/ls.py tools/screenshot.png tools/utils.py
chat> what files are in the tools folder?
The files in the tools folder are: calculate.py, cat.py, grep.py, ls.py, and utils.py. There is also a screenshot.png file.
```
```
chat> /calculate 2*6
12
```
The two examples above are good examples because they show two things. (1) The '/' works properly and (2) The functions are able to demonstrate a reasonable output.