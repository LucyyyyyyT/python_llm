# Python LLM Chat Agent

![doctests](https://github.com/LucyyyyyyT/python_llm/actions/workflows/doctests.yml/badge.svg)
![flake8](https://github.com/LucyyyyyyT/python_llm/actions/workflows/flake8.yml/badge.svg)
![tests](https://github.com/LucyyyyyyT/python_llm/actions/workflows/test.yml/badge.svg)
[![PyPI](https://img.shields.io/pypi/v/python-llm-lucy)](https://pypi.org/project/python-llm-lucy/)
<<<<<<< HEAD
[![coverage](https://codecov.io/gh/LucyyyyyyT/python_llm/branch/main/graph/badge.svg)](https://codecov.io/gh/LucyyyyyyT/python_llm)
=======
![coverage](https://github.com/LucyyyyyyT/python_llm/actions/workflows/test.yml/badge.svg)
>>>>>>> origin/main

A chat agent that depends on command line and uses Groq's LLM API. It is able to hold conversations and answer questions. It can also call built-in tools: (`calculate`, `cat`, `grep`, `ls`). 

![Demo](demo.gif)


## Usage

### docsum

This example shows how the agent can explore a project's file structure.

```
$ cd docsum
$ chat
<<<<<<< HEAD
chat> tell me about this project
The README says this project is designed to scrape product information off of ebay.
chat> is this legal?
Yes. It is generally legal to scrape webpages, but ebay offers an API that would be more efficient to use.
```

### Creating files with the agent
The session below demonstrates that the agent can create files and
automatically commit them to git.
```
$ ls -a
.git  README.md  python_llm/
$ git log --oneline
835b796 chat.py
$ python3 python_llm/chat.py
chat> create a file called hello.py that prints "hello world"
I've created hello.py with a simple print statement.
chat> ^C
$ ls -a
.git  README.md  hello.py  python_llm/
$ git log --oneline
f01358c (HEAD -> project4) [docchat] Add hello.py that prints hello world
835b796 chat.py
=======
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
>>>>>>> origin/main
```