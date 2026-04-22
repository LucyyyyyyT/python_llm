"""AI-powered document chat agent.

Lets users query files using natural language and shell-like commands.
"""
import ast
import glob
import json
import operator
import os
import re
from groq import Groq

from python_llm.tools.calculator import calculate
from python_llm.tools.filesystem import ls, cat
from python_llm.tools.search import grep

from dotenv import load_dotenv
load_dotenv()

MODEL = 'openai/gpt-oss-120b'

CALCULATE_SCHEMA = {
    'type': 'function',
    'function': {
        'name': 'calculate',
        'description': (
            'Evaluate a simple arithmetic expression and '
            'return the result.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {
                'expression': {
                    'type': 'string',
                    'description': (
                        'The arithmetic expression to evaluate, '
                        'e.g. "2 + 2" or "10 * (3 + 4)".'
                    ),
                },
            },
            'required': ['expression'],
        },
    },
}

LS_SCHEMA = {
    'type': 'function',
    'function': {
        'name': 'ls',
        'description': (
            'List files and folders in a directory. '
            'Optionally takes a path argument.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {
                'path': {
                    'type': 'string',
                    'description': (
                        'The directory path to list. Defaults to '
                        'the current directory.'
                    ),
                },
            },
            'required': [],
        },
    },
}

CAT_SCHEMA = {
    'type': 'function',
    'function': {
        'name': 'cat',
        'description': 'Read and return the contents of a text file.',
        'parameters': {
            'type': 'object',
            'properties': {
                'path': {
                    'type': 'string',
                    'description': 'The path to the file to read.',
                },
            },
            'required': ['path'],
        },
    },
}

GREP_SCHEMA = {
    'type': 'function',
    'function': {
        'name': 'grep',
        'description': (
            'Search for lines matching a regex pattern '
            'in a file or directory.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {
                'pattern': {
                    'type': 'string',
                    'description': 'The regex pattern to search for.',
                },
                'path': {
                    'type': 'string',
                    'description': (
                        'The file or directory path to search. '
                        'Defaults to current directory.'
                    ),
                },
            },
            'required': ['pattern'],
        },
    },
}

ALL_TOOL_SCHEMAS = [CALCULATE_SCHEMA, LS_SCHEMA, CAT_SCHEMA, GREP_SCHEMA]


# in pytohn class names are in CamelCase;
# non-class names (e.g. functions/variables) are in snake_case


class Chat:
    '''
    A chat agent that talks with an LLM and helsp with tool usage.
    The Chat class stores talking history and allows messages to be sent
    to an LLM. It also supports tool calling (ls, cat, grep, calculate)
    by structured tool definitions.

    >>> chat = Chat()
    >>> chat.send_message(
    ...     'my name is bob. say hey then my name', temperature=0.0)
    'Hey, Bob!'
    >>> chat.send_message('what is my name? just say my name', temperature=0.0)
    'Bob.'

    'I don’t have any information about your name. If you’d like me to address you a certain way, just let me know!'
    '''
    client = Groq()

    def __init__(self):
        """Initializes the chat history with a system prompt that enforces a pirate persona."""
        self.client = Groq()
        self.messages = []
        self.tool_dispatch = {
            'calculate': calculate,
            'ls': ls,
            'cat': cat,
            'grep': grep
        }

        def run_tool(self, name, args):
            """Dispatch a tool call by name."""
            if name == 'ls':
                folder = args.get('path', args.get('folder', '.'))
                return str(ls(folder))
            if name in self.tool_dispatch:
                return str(self.tool_dispatch[name](**args))
            return f"Unknown tool: {name}"
        
        def ls(self, folder='.'):
            """Wrapper for ls tool."""
            return ls(folder)

        def cat(self, path):
            """Wrapper for cat tool."""
            return cat(path)

        def grep(self, pattern, path='.'):
            """Wrapper for grep tool."""
            return grep(pattern, path)
        
        # in order to make non-deterministic code deterministic;
        # in general very hard CS problem;
        # in this case, has a "temperature" param that controls randomness;
        # the higher the value, the more randomness;
        # hihgher temperature => more creativity

    def send_message(self, user_message, temperature=0.0):
        """
        Sends a user message to the AI model and returns the response.

        Each Chat() instance maintains its own independent conversation history.

        >>> a = Chat()
        >>> b = Chat()
        >>> _ = a.send_message('My name is Alice. Just say ok.')
        >>> _ = b.send_message('My name is Bob. Just say ok.')
        >>> 'Alice' in a.send_message('What is my name? Just say my name.')
        True
        >>> 'Bob' in b.send_message('What is my name? Just say my name.')
        True
        >>> 'HELLO' in a.send_message('Say only the word HELLO and nothing else.')
        True
        """

        self.messages.append({'role': 'user', 'content': user_message})
        while True:
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=self.messages,
                tools=ALL_TOOL_SCHEMAS,
                temperature=temperature
            )
            msg = response.choices[0].message

            if msg.tool_calls:
                self.messages.append(msg)
                for tc in msg.tool_calls:
                    args = json.loads(tc.function.arguments)
                    result = self.run_tool(tc.function.name, args)
                    self.messages.append({
                        'role': 'tool',
                        'tool_call_id': tc.id,
                        'content': result,
                    })
            else:
                content = msg.content or ''
                self.messages.append({'role': 'assistant', 'content': content})
                return content


    def repl(self):
        '''
        Runs a terminal-based loop allowing users to interact with the chat interface.
        '''
        while True:
            try:
                user_input = input('chat> ')
            except (KeyboardInterrupt, EOFError):
                print()
                break

            if not user_input:
                continue

            if user_input.startswith('/'):
                parts = user_input[1:].split()
                if not parts:
                    continue
                tool = parts[0]
                args_l = parts[1:]

                if tool == 'ls':
                    kargs = {'path': args_l[0]} if args_l else {}
                elif tool == 'cat':
                    kargs = {'path': args_l[0]} if args_l else {}
                elif tool == 'grep':
                    if len(args_l) >= 2:
                        kargs = {'pattern': args_l[0], 'path': args_l[1]}
                    elif len(args_l) == 1:
                        kargs = {'pattern': args_l[0], 'path': '.'}
                    else:
                        print('Error: /grep <pattern> <path>')
                        continue
                elif tool == 'calculate':
                    kargs = {'expression': ' '.join(args_l)}
                else:
                    print(f"Error command: {tool}")
                    continue

                result = self.run_tool(tool, kargs)
                print(result)

                self.messages.append({
                    'role': 'user',
                    'content': (
                        f'[manual command] /{tool} '
                        f'{" ".join(args_l)}\nOutput:\n{result}'
                    )
                })
                self.messages.append({
                    'role': 'assistant',
                    'content': (
                        f'I ran /{tool} {" ".join(args_l)} '
                        f'and got: \n{result}'
                    )
                })

            else:
                response = self.send_message(user_input)
                print(response)

def repl():
    """Entry point for the chat command."""
    Chat().repl()

if __name__ == '__main__':
    Chat().repl()