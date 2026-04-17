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

### markdown_compiler
This example shows how the agent can analyze code structure and answer questions about a project.
```
$ cd markdown_compiler
$ chat
chat> does this project use regular expressions?
No. I grepped all of the python files for any uses of the `re` library and did not find any.
```

### ebay_scraper
This example shows how the agent can summarize a project and answer questions about it.
```
$ cd ebay_scraper
$ chat
chat> tell me about this project
The README says this project is designed to scrape product information off of ebay.
chat> is this legal?
Yes. It is generally legal to scrape webpages, but ebay offers an API that would be more efficient to use.
```