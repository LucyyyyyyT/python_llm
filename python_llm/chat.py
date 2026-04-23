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

_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}


def _eval_node(node):
    """
    Recursively evaluate a single AST node.

    Raises ValueError for unsafe expressions.

    >>> _eval_node(ast.parse('2 + 2', mode='eval').body)
    4
    >>> _eval_node(ast.parse('3 * 7', mode='eval').body)
    21
    """
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError('invalid expression')
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPS:
            raise ValueError('invalid expression')
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return _ALLOWED_OPS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPS:
            raise ValueError('invalid expression')
        operand = _eval_node(node.operand)
        return _ALLOWED_OPS[op_type](operand)
    else:
        raise ValueError('invalid expression')


def is_path_safe(path):
    """
    Returns True if a path is safe to read.

    Checks for absolute paths or directory traversal.

    >>> is_path_safe('README.md')
    True
    >>> is_path_safe('chat.py')
    True
    >>> is_path_safe('/etc/passwd')
    False
    >>> is_path_safe('../secret.txt')
    False
    >>> is_path_safe('some/../file.txt')
    False
    >>> is_path_safe('.')
    True
    >>> is_path_safe('')
    True
    """
    if path.startswith('/'):
        return False
    parts = path.replace('\\', '/').split('/')
    if '..' in parts:
        return False
    return True


def calculate(expression):
    """
    Evaluate a simple arithmetic expression and return the result as a string.

    Integer results are returned without a decimal point. Division that
    produces a whole number keeps the '.0' to signal it came from division.
    Repeating or non-whole floats are returned as-is.

    >>> calculate('2 + 2')
    '4'
    >>> calculate('10 - 3')
    '7'
    >>> calculate('6 * 7')
    '42'
    >>> calculate('100 / 4')       # whole-number true division keeps '.0'
    '25.0'
    >>> calculate('5 * 5.0')       # whole-number non-division drops '.0'
    '25'
    >>> calculate('10 / 3')        # repeating decimal returned as-is
    '3.3333333333333335'
    >>> calculate('1 / 0')
    'Error: division by zero'
    >>> calculate('1 + (2 *')
    'Error: invalid expression'
    >>> calculate('__import__("os")')
    'Error: invalid expression'
    >>> calculate('None + 1')
    'Error: invalid expression'
    """
    try:
        tree = ast.parse(expression, mode='eval')
        result = _eval_node(tree.body)
        if isinstance(result, float) and result.is_integer():
            if '/' in expression and '//' not in expression:
                return str(result)
            return str(int(result))
        return str(result)
    except ZeroDivisionError:
        return 'Error: division by zero'
    except (ValueError, TypeError):
        return 'Error: invalid expression'
    except SyntaxError:
        return 'Error: invalid expression'


def ls(folder='.'):
    """
    List files/folders in a directory, asciibetically, one per line.

    Each entry is just the base name (not the full path). Unsafe paths
    (absolute or containing '..') return an error string instead.

    >>> result = ls('.')
    >>> 'chat.py' in result        # chat.py lives in the current directory
    True
    >>> result.split('\\n') == sorted(result.split('\\n'))   # asciibetical order
    True
    >>> ls('/etc')
    'Error: unsafe path'
    >>> ls('../other')
    'Error: unsafe path'
    >>> ls('nonexistent_folder_xyz')
    ''
    """
    if not is_path_safe(folder):
        return 'Error: unsafe path'
    files = sorted(glob.glob(f'{folder}/*'))
    names = [os.path.basename(f) for f in files]
    return '\n'.join(names)


def cat(path):
    """
    Open a file and return its contents as a string.

    >>> contents = cat('chat.py')
    >>> contents.startswith('\"\"\"AI-powered')   # first line of this file
    True
    >>> 'def cat(' in contents                     # this function is in the file
    True
    >>> cat('nonexistent_file_xyz.txt')
    'Error: file not found'
    >>> cat('/etc/passwd')
    'Error: unsafe path'
    >>> cat('../secret.txt')
    'Error: unsafe path'
    """
    if not is_path_safe(path):
        return 'Error: unsafe path'
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return 'Error: file not found'
    except UnicodeDecodeError:
        try:
            with open(path, 'r', encoding='utf-16') as f:
                return f.read()
        except Exception:
            return 'Error: cannot decode file'
    except Exception as e:
        return f'Error: {e}'


def grep(pattern, path='.'):
    """
    Search for lines matching a regex pattern (recursive).

    Each matching line is returned in 'filename:line' format, one per line.
    Returns an empty string when there are no matches, or an error string
    for unsafe paths or invalid patterns.

    >>> result = grep('def is_path_safe', 'chat.py')
    >>> result                              # shows 'filename:line' format
    'chat.py:def is_path_safe(path):'
    >>> result.startswith('chat.py:')      # filename comes before the colon
    True
    >>> 'def is_path_safe' in result       # matched text appears after colon
    True
    >>> grep('def ', '/etc')
    'Error: unsafe path'
    >>> grep('def ', '../other')
    'Error: unsafe path'
    >>> grep('zzz_nomatch_xyz', 'chat.py')
    ''
    >>> grep('[invalid', 'chat.py')
    'Error: invalid pattern: unterminated character set at position 0'
    """
    if not is_path_safe(path):
        return 'Error: unsafe path'
    try:
        compiled = re.compile(pattern)
    except re.error as e:
        return f'Error: invalid pattern: {e}'

    results = []
    if os.path.isfile(path):
        files = [path]
    else:
        files = []
        for root, dirs, filenames in os.walk(path):
            dirs[:] = sorted([d for d in dirs if not d.startswith('.')])
            for fname in sorted(filenames):
                files.append(os.path.join(root, fname))

    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if compiled.search(line):
                        results.append(f'{filepath}:{line.rstrip()}')
        except Exception:
            continue

    return '\n'.join(results)


# Maps tool names (as the LLM sends them) to the standalone functions above.
TOOL_DISPATCH = {
    'calculate': calculate,
    'ls': ls,
    'cat': cat,
    'grep': grep,
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
        self.client = Groq()
        self.messages = []

    def run_tool(self, name, args):
        """
        Dispatch a tool call by name and return its string result.

        >>> c = Chat()
        >>> c.run_tool('calculate', {'expression': '3 + 4'})
        '7'
        >>> c.run_tool('ls', {'folder': '/etc'})
        'Error: unsafe path'
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
        >>> 'WORLD' in reply_x   # x has no knowledge of y's conversation
        False
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
    """Run a terminal loop letting users chat with the agent."""
    chat = Chat()
    try:
        while True:
            user_input = input('chat> ')
            response = chat.send_message(user_input, temperature=0.0)
            print(response)
    except (KeyboardInterrupt, EOFError):
        print()


if __name__ == '__main__':
    repl()