"""AI-powered document chat agent.

Lets users query files using natural language and shell-like commands.
"""
import json
import os
<<<<<<< HEAD
import re
import subprocess
=======
>>>>>>> origin/main
import sys
from groq import Groq

from python_llm.tools.calculator import calculate
from python_llm.tools.filesystem import ls, cat, doctests, write_file, write_files, rm
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

DOCTESTS_SCHEMA = {
    'type': 'function',
    'function': {
        'name': 'doctests',
        'description': 'Run doctests on a Python file and return the output.',
        'parameters': {
            'type': 'object',
            'properties': {
                'path': {
                    'type': 'string',
                    'description': 'The path to the Python file to test.',
                },
            },
            'required': ['path'],
        },
    },
}

WRITE_FILE_SCHEMA = {
    'type': 'function',
    'function': {
        'name': 'write_file',
        'description': (
            'Write contents to a file and commit the change to git. '
            'If the file is a Python file, doctests are run after writing.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {
                'path': {
                    'type': 'string',
                    'description': 'The path to the file to write.',
                },
                'contents': {
                    'type': 'string',
                    'description': 'The contents to write to the file.',
                },
                'commit_message': {
                    'type': 'string',
                    'description': 'The git commit message.',
                },
            },
            'required': ['path', 'contents', 'commit_message'],
        },
    },
}

WRITE_FILES_SCHEMA = {
    'type': 'function',
    'function': {
        'name': 'write_files',
        'description': (
            'Write multiple files and commit all changes to git in one commit.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {
                'files': {
                    'type': 'array',
                    'description': (
                        'A list of files to write, each with a path and '
                        'contents key.'
                    ),
                    'items': {
                        'type': 'object',
                        'properties': {
                            'path': {'type': 'string'},
                            'contents': {'type': 'string'},
                        },
                        'required': ['path', 'contents'],
                    },
                },
                'commit_message': {
                    'type': 'string',
                    'description': 'The git commit message for all files.',
                },
            },
            'required': ['files', 'commit_message'],
        },
    },
}

RM_SCHEMA = {
    'type': 'function',
    'function': {
        'name': 'rm',
        'description': (
            'Delete a file (supports globs) and commit the removal to git.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {
                'path': {
                    'type': 'string',
                    'description': 'The path (or glob) of the file to delete.',
                },
            },
            'required': ['path'],
        },
    },
}

ALL_TOOL_SCHEMAS = [
    CALCULATE_SCHEMA,
    LS_SCHEMA,
    CAT_SCHEMA,
    GREP_SCHEMA,
    DOCTESTS_SCHEMA,
    WRITE_FILE_SCHEMA,
    WRITE_FILES_SCHEMA,
    RM_SCHEMA,
]


# Maps tool names (as the LLM sends them) to the standalone functions above.
TOOL_DISPATCH = {
    'calculate': calculate,
    'ls': ls,
    'cat': cat,
    'grep': grep,
    'doctests': doctests,
    'write_file': write_file,
    'write_files': write_files,
    'rm': rm,
}


class Chat:
    """
    A chat agent that talks with an LLM and supports tool usage.

    Stores conversation history so that follow-up questions work correctly.
    Each Chat instance is fully independent — two instances never share history.

    >>> a = Chat()
    >>> b = Chat()
    >>> _ = a.send_message('My name is Alice. Just say OK.', temperature=0.0)
    >>> _ = b.send_message('My name is Bob. Just say OK.', temperature=0.0)
    >>> 'Alice' in a.send_message('What is my name? Say only my name.', temperature=0.0)
    True
    >>> 'Bob' in b.send_message('What is my name? Say only my name.', temperature=0.0)
    True
    >>> 'Alice' not in b.send_message('What is my name? Say only my name.', temperature=0.0)
    True
    """

    def __init__(self):
        """Initialize a new, empty conversation with the LLM."""
<<<<<<< HEAD
        """
        Initialize a new, empty conversation with the LLM.

        # Setup: Mock the Groq class to avoid requiring a real API key during tests
        >>> from unittest.mock import MagicMock
        >>> original_groq = globals().get('Groq')  # Save original import if it exists
        >>> globals()['Groq'] = MagicMock()        # Inject the mock

        # 1. Test instantiation
        >>> chat = YourClassName()
        
        # 2. Verify the messages array starts empty
        >>> chat.messages
        []
        
        # 3. Verify the Groq client was successfully instantiated (as our mock)
        >>> isinstance(chat.client, MagicMock)
        True

        # Cleanup: Restore the original Groq class so other code isn't affected
        >>> if original_groq:
        ...     globals()['Groq'] = original_groq
        >>> else:
        ...     del globals()['Groq']
        """
=======
>>>>>>> origin/main
        self.client = Groq()
        self.messages = []

    def run_tool(self, name, args):
        """
        Dispatch a tool call by name and return its string result.

        >>> c = Chat()
        >>> c.run_tool('calculate', {'expression': '3 + 4'})
        '7'
        >>> c.run_tool('ls', {'path': '/etc'})
        'Error: unsafe path'
<<<<<<< HEAD

        # Test handling of an unregistered or hallucinated tool name
=======
>>>>>>> origin/main
        >>> c.run_tool('nonexistent_tool_xyz', {})
        "Error: unknown tool 'nonexistent_tool_xyz'"
        """
        func = TOOL_DISPATCH.get(name)
        if func is None:
            return f'Error: unknown tool {name!r}'
        return func(**args)

    def send_message(self, user_message, temperature=0.0):
        """
        Send a message and return the assistant's reply.

        Handles multi-turn conversation: history is preserved between calls,
        so the model can refer back to earlier messages.

        >>> a = Chat()
        >>> _ = a.send_message('Remember: the magic number is 42. Just say OK.')
        >>> reply = a.send_message('What is the magic number? Say only the number.')
        >>> '42' in reply
        True

        Two separate Chat instances are completely independent:

        >>> x = Chat()
        >>> y = Chat()
        >>> _ = x.send_message('Say only the word HELLO and nothing else.')
        >>> _ = y.send_message('Say only the word WORLD and nothing else.')
        >>> reply_x = x.send_message('Repeat the word you just said.')
        >>> reply_y = y.send_message('Repeat the word you just said.')
        >>> 'HELLO' in reply_x
        True
        >>> 'WORLD' in reply_y
        True
        >>> 'WORLD' in reply_x
        False

<<<<<<< HEAD
        # --- NEW TESTS ADDED BELOW ---

        # Setup: Mock the LLM client to test the tool-calling loop deterministically
=======
>>>>>>> origin/main
        >>> from unittest.mock import MagicMock
        >>> import json
        >>> c = Chat()
        >>> c.client = MagicMock()
<<<<<<< HEAD

        # 1. Test the tool calling while-loop
        # Create mock response A: The LLM decides to call a tool
=======
>>>>>>> origin/main
        >>> tc = MagicMock()
        >>> tc.id = 'call_abc123'
        >>> tc.function.name = 'calculate'
        >>> tc.function.arguments = '{"expression": "5 + 5"}'
        >>> msg_tool = MagicMock()
        >>> msg_tool.tool_calls = [tc]
        >>> msg_tool.content = None
        >>> resp1 = MagicMock()
        >>> resp1.choices = [MagicMock(message=msg_tool)]
<<<<<<< HEAD

        # Create mock response B: The LLM replies with the final text
=======
>>>>>>> origin/main
        >>> msg_text = MagicMock()
        >>> msg_text.tool_calls = None
        >>> msg_text.content = 'The answer is 10.'
        >>> resp2 = MagicMock()
        >>> resp2.choices = [MagicMock(message=msg_text)]
<<<<<<< HEAD

        # Assign the sequence of responses to the mock client
        >>> c.client.chat.completions.create.side_effect = [resp1, resp2]

        # Execute the method; it should run the tool and loop back for the final text
        >>> c.send_message('What is 5 + 5?')
        'The answer is 10.'
        
        # Verify the message history correctly recorded all 4 steps:
        # [User prompt, LLM tool request, Tool result, Final LLM reply]
=======
        >>> c.client.chat.completions.create.side_effect = [resp1, resp2]
        >>> c.send_message('What is 5 + 5?')
        'The answer is 10.'
>>>>>>> origin/main
        >>> len(c.messages)
        4
        >>> c.messages[2]['role']
        'tool'
        >>> c.messages[2]['content']
        '10'

<<<<<<< HEAD
        # 2. Test the empty content fallback logic (msg.content or '')
=======
>>>>>>> origin/main
        >>> msg_empty = MagicMock()
        >>> msg_empty.tool_calls = None
        >>> msg_empty.content = None
        >>> resp3 = MagicMock()
        >>> resp3.choices = [MagicMock(message=msg_empty)]
        >>> c.client.chat.completions.create.side_effect = [resp3]
<<<<<<< HEAD
        
=======
>>>>>>> origin/main
        >>> c.send_message('Say nothing.')
        ''
        """
        self.messages.append({'role': 'user', 'content': user_message})
        while True:
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=self.messages,
                tools=ALL_TOOL_SCHEMAS,
                temperature=temperature,
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


def repl():
    """
    Run a terminal loop letting users chat with the agent.

    >>> import os, sys, builtins
    >>> original_isdir = os.path.isdir
    >>> original_isfile = os.path.isfile
    >>> original_input = builtins.input
    >>> original_chat = globals().get('Chat')

    >>> os.path.isdir = lambda path: False
    >>> try:
    ...     repl()
    ... except SystemExit as e:
    ...     print(f'Exit code: {e.code}')
    Error: no .git folder found. Please run chat from a git repo.
    Exit code: 1

    >>> os.path.isdir = lambda path: True
    >>> os.path.isfile = lambda path: False
    >>> class StubChat:
    ...     def __init__(self):
    ...         self.messages = []
    ...     def send_message(self, text, temperature=0.0):
<<<<<<< HEAD
    ...         return "I hear you."
=======
    ...         return 'I hear you.'
>>>>>>> origin/main
    >>> globals()['Chat'] = StubChat
    >>> input_sequence = ['Hello agent!', EOFError()]
    >>> def fake_input(prompt):
    ...     val = input_sequence.pop(0)
    ...     if isinstance(val, Exception):
    ...         raise val
    ...     return val
    >>> builtins.input = fake_input
<<<<<<< HEAD
    >>> repl() 
    Hello! How can I assist you today?
=======
    >>> repl()  # doctest: +ELLIPSIS
    ...
>>>>>>> origin/main
    <BLANKLINE>

    >>> os.path.isdir = original_isdir
    >>> os.path.isfile = original_isfile
    >>> builtins.input = original_input
    >>> globals()['Chat'] = original_chat
<<<<<<< HEAD

    >>> input_sequence = ['/help', '/ls .', '/calculate 2+2', '/grep def chat.py', '/unknown', EOFError()]
    >>> def fake_input(prompt):
    ...     val = input_sequence.pop(0)
    ...     if isinstance(val, Exception):
    ...         raise val
    ...     return val
    >>> builtins.input = fake_input
    >>> repl()  # doctest: +ELLIPSIS
    Slash commands:
      /ls [path]
    ...
    <BLANKLINE>
    """
    # Check for .git folder in current directory
=======
    """
>>>>>>> origin/main
    if not os.path.isdir('.git'):
        print('Error: no .git folder found. Please run chat from a git repo.')
        sys.exit(1)

    chat = Chat()

<<<<<<< HEAD
    # Load AGENTS.md into the conversation if it exists
=======
>>>>>>> origin/main
    if os.path.isfile('AGENTS.md'):
        agents_contents = cat('AGENTS.md')
        chat.messages.append({
            'role': 'user',
            'content': f'Here are your instructions for this repo:\n{agents_contents}',
        })
        chat.messages.append({
            'role': 'assistant',
            'content': 'Understood. I have read the AGENTS.md instructions.',
        })

    try:
        while True:
            user_input = input('chat> ')

            if user_input.startswith('/'):
                parts = user_input[1:].split(None, 1)
                cmd = parts[0]
                arg = parts[1] if len(parts) > 1 else ''

                if cmd == 'ls':
                    print(ls(arg or '.'))
                elif cmd == 'cat':
                    print(cat(arg))
                elif cmd == 'grep':
                    s_parts = arg.split(None, 1)
                    if len(s_parts) < 1:
                        print('Error: /grep <pattern> [path]')
                    else:
                        pattern = s_parts[0]
                        path = s_parts[1] if len(s_parts) > 1 else '.'
                        print(grep(pattern, path))
                elif cmd == 'calculate':
                    print(calculate(arg))
                elif cmd == 'doctests':
                    print(doctests(arg))
                elif cmd == 'write_file':
<<<<<<< HEAD
                    subparts = arg.split(None, 1)  # use its own variable
                    if len(subparts) < 2:
                        print('Error: /write_file <path> <contents>')
                    else:
                        print(write_file(subparts[0], subparts[1], 'write via slash command'))
=======
                    subparts = arg.split(None, 1)
                    if len(subparts) < 2:
                        print('Error: /write_file <path> <contents>')
                    else:
                        print(write_file(
                            subparts[0], subparts[1], 'write via slash command'
                        ))
>>>>>>> origin/main
                elif cmd == 'rm':
                    print(rm(arg))
                elif cmd == 'help':
                    print(
                        'Slash commands:\n'
                        '  /ls [path]\n'
                        '  /cat <path>\n'
                        '  /grep <pattern> [path]\n'
                        '  /calculate <expression>\n'
                        '  /doctests <path>\n'
                        '  /write_file <path> <contents>\n'
                        '  /rm <path>\n'
                        '  /help'
                    )
                else:
                    print(f"Unknown command '/{cmd}.' Type /help for a list.")
                continue

<<<<<<< HEAD

=======
>>>>>>> origin/main
            response = chat.send_message(user_input, temperature=0.0)
            print(response)
    except (KeyboardInterrupt, EOFError):
        print()

if __name__ == "__main__":
    repl()