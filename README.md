# Python LLM Chat Agent

An AI-powered document chat agent that lets users query files using natural language and shell-like commands.

![doctests](https://github.com/LucyyyyyyT/python_llm/actions/workflows/doctests.yml/badge.svg)
![flake8](https://github.com/LucyyyyyyT/python_llm/actions/workflows/flake8.yml/badge.svg)
![tests](https://github.com/LucyyyyyyT/python_llm/actions/workflows/test.yml/badge.svg)
[![PyPI](https://img.shields.io/pypi/v/python-llm-lucy)](https://pypi.org/project/python-llm-lucy/)
[![coverage](https://codecov.io/gh/LucyyyyyyT/python_llm/branch/main/graph/badge.svg)](https://codecov.io/gh/LucyyyyyyT/python_llm)

A chat agent that depends on command line and uses Groq's LLM API. It is able to hold conversations and answer questions. It can also call built-in tools: (`calculate`, `cat`, `grep`, `ls`). 

Here is a working example of my code:
![Demo](demo.gif)

## Usage

### docsum

This example shows how the agent can explore a project's file structure.

$ cd docsum
$ chat
chat> what files are in this project
Here's the directory tree of the current project:

python_llm/
├── chat.py
└── tools/
    ├── calculator.py
    ├── filesystem.py
    └── search.py

chat> what does chat.py do
chat.py defines a Chat class that connects to the Groq LLM API,
maintains conversation history, and supports tool calling for
ls, cat, grep, and calculate.