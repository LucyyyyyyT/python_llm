"""AI-powered document chat agent.

Lets users query files using natural language and shell-like commands.
"""
import ast
import glob
import json
import operator
import os
import re
import subprocess
import sys
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

    --- CONSTANT PATHS ---
    1. Valid integer Constant
    >>> _eval_node(ast.parse('42', mode='eval').body)
    42
    
    2. Valid float Constant
    >>> _eval_node(ast.parse('3.14', mode='eval').body)
    3.14
    
    3. Invalid Constant (e.g., string)
    >>> _eval_node(ast.parse('"hello"', mode='eval').body)
    Traceback (most recent call last):
        ...
    ValueError: invalid expression

    --- BINOP PATHS ---
    4. Valid BinOp (Addition)
    >>> _eval_node(ast.parse('10 + 5', mode='eval').body)
    15
    
    5. Invalid BinOp (Bitwise OR - not in _ALLOWED_OPS)
    >>> _eval_node(ast.parse('3 | 7', mode='eval').body)
    Traceback (most recent call last):
        ...
    ValueError: invalid expression

    --- UNARYOP PATHS ---
    6. Valid UnaryOp (Negation)
    >>> _eval_node(ast.parse('-5', mode='eval').body)
    -5
    
    7. Invalid UnaryOp (Bitwise Inversion - not in _ALLOWED_OPS)
    >>> _eval_node(ast.parse('~5', mode='eval').body)
    Traceback (most recent call last):
        ...
    ValueError: invalid expression

    --- CATCH-ALL ELSE PATH ---
    8. Unsupported Node Type (e.g., List)
    >>> _eval_node(ast.parse('[1, 2, 3]', mode='eval').body)
    Traceback (most recent call last):
        ...
    ValueError: invalid expression
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
    >>> calculate('100 / 4')
    '25.0'
    >>> calculate('5 * 5.0')
    '25'
    >>> calculate('10 / 3')
    '3.3333333333333335'
    >>> calculate('1 / 0')
    'Error: division by zero'
    >>> calculate('1 + (2 *')
    'Error: invalid expression'
    >>> calculate('__import__("os")')
    'Error: invalid expression'
    >>> calculate('None + 1')
    'Error: invalid expression'
    
    # Tests the floor division exclusion branch ('//' not in expression)
    # 10.0 // 2 evaluates to the float 5.0, but should be formatted as '5'
    >>> calculate('10.0 // 2')
    '5'
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


def ls(path='.'):
    """
    List files/folders in a directory, asciibetically, one per line.

    Each entry is just the base name (not the full path). Unsafe paths
    (absolute or containing '..') return an error string instead.

    >>> result = ls('.')
    >>> result.split('\\n') == sorted(result.split('\\n'))
    True
    >>> ls('/etc')
    'Error: unsafe path'
    >>> ls('../other')
    'Error: unsafe path'
    >>> ls('nonexistent_folder_xyz')
    ''
    
    # Tests the default argument fallback
    >>> ls() == ls('.')
    True
    
    >>> '/' not in ls()
    True
    """
    if not is_path_safe(path):
        return 'Error: unsafe path'
    files = sorted(glob.glob(f'{path}/*'))
    names = [os.path.basename(f) for f in files]
    return '\n'.join(names)


def cat(path):
    """
    Open a file and return its contents as a string.

    >>> cat('nonexistent_file_xyz.txt')
    'Error: file not found'
    >>> cat('/etc/passwd')
    'Error: unsafe path'
    >>> cat('../secret.txt')
    'Error: unsafe path'
    
    # 1. Test standard UTF-8 success
    >>> with open('test_cat_utf8.txt', 'w', encoding='utf-8') as f:
    ...     _ = f.write('hello world')
    >>> cat('test_cat_utf8.txt')
    'hello world'
    
    # 2. Test UnicodeDecodeError fallback to UTF-16 success
    >>> with open('test_cat_utf16.txt', 'w', encoding='utf-16') as f:
    ...     _ = f.write('hello utf16')
    >>> cat('test_cat_utf16.txt')
    'hello utf16'
    
    # 3. Test complete decode failure (invalid binary data)
    >>> with open('test_cat_binary.bin', 'wb') as f:
    ...     _ = f.write(b'\\x80\\x81\\xff') 
    >>> cat('test_cat_binary.bin')
    'Error: cannot decode file'

    # 4. Test general Exception catch (e.g., trying to read a directory)
    # This raises IsADirectoryError or PermissionError depending on the OS.
    >>> result = cat('.')
    >>> result.startswith('Error: [Errno')
    True

    # Cleanup the test files
    >>> os.remove('test_cat_utf8.txt')
    >>> os.remove('test_cat_utf16.txt')
    >>> os.remove('test_cat_binary.bin')
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

    >>> grep('def ', '/etc')
    'Error: unsafe path'
    >>> grep('def ', '../other')
    'Error: unsafe path'
    >>> grep('zzz_nomatch_xyz', 'chat.py')
    ''
    >>> grep('[invalid', 'chat.py')
    'Error: invalid pattern: unterminated character set at position 0'

    # --- NEW TESTS ADDED BELOW ---

    # Setup: Create a temporary directory structure for testing
    >>> os.mkdir('test_grep_dir')
    >>> with open('test_grep_dir/file1.txt', 'w', encoding='utf-8') as f:
    ...     _ = f.write('hello\\nsearch target\\nworld')
    >>> os.mkdir('test_grep_dir/subdir')
    >>> with open('test_grep_dir/subdir/file2.txt', 'w', encoding='utf-8') as f:
    ...     _ = f.write('another search target here')
    >>> os.mkdir('test_grep_dir/.hidden')
    >>> with open('test_grep_dir/.hidden/file3.txt', 'w', encoding='utf-8') as f:
    ...     _ = f.write('search target hidden')

    # 1. Test single file match and correct formatting
    # Note: We replace backslashes to ensure Windows/Linux cross-compatibility in the test
    >>> grep('target', 'test_grep_dir/file1.txt').replace('\\\\', '/')
    'test_grep_dir/file1.txt:search target'

    # 2. Test directory recursion and hidden directory filtering
    # Should find file1 and file2, but skip file3 because it is in a '.hidden' folder
    >>> result = grep('target', 'test_grep_dir').replace('\\\\', '/')
    >>> result.split('\\n') == ['test_grep_dir/file1.txt:search target', 'test_grep_dir/subdir/file2.txt:another search target here']
    True

    # 3. Test default path argument (searches current directory '.')
    # We check if it successfully finds the test file we just generated
    >>> 'test_grep_dir/file1.txt:search target' in grep('search target').replace('\\\\', '/')
    True

    # Cleanup: Remove the temporary files and directories
    >>> os.remove('test_grep_dir/file1.txt')
    >>> os.remove('test_grep_dir/subdir/file2.txt')
    >>> os.rmdir('test_grep_dir/subdir')
    >>> os.remove('test_grep_dir/.hidden/file3.txt')
    >>> os.rmdir('test_grep_dir/.hidden')
    >>> os.rmdir('test_grep_dir')
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


def doctests(path):
    """
    Run doctests (with --verbose flag) on a Python file and return output.

    >>> doctests('/etc/passwd')
    'Error: unsafe path'
    >>> doctests('../secret.py')
    'Error: unsafe path'
    >>> doctests('nonexistent_xyz.py')
    'Error: file not found'

    # --- NEW TESTS ADDED BELOW ---

    # Setup: Create a temporary Python file with a simple doctest
    >>> with open('test_dummy_doctest.py', 'w', encoding='utf-8') as f:
    ...     _ = f.write("def dummy():\\n    '''\\n    >>> 1 + 1\\n    2\\n    '''\\n    pass\\n")

    # 1. Test successful execution of the subprocess block
    # We check for strings generated by Python's 'doctest -v' command
    >>> output = doctests('test_dummy_doctest.py')
    >>> 'Trying:' in output
    True
    >>> '1 + 1' in output
    True
    >>> 'ok' in output or 'passed' in output.lower()
    True

    # Cleanup: Remove the temporary file
    >>> os.remove('test_dummy_doctest.py')
    """
    if not is_path_safe(path):
        return 'Error: unsafe path'
    if not os.path.isfile(path):
        return 'Error: file not found'
    result = subprocess.run(
        [sys.executable, '-m', 'doctest', '-v', path],
        capture_output=True,
        text=True,
    )
    return result.stdout + result.stderr


def write_files(files, commit_message):
    """
    Write multiple files and commit them all in one git commit.

    Each item in files must be a dict with 'path' and 'contents' keys.
    Returns an error string if any path is unsafe, otherwise returns
    a success message plus doctest output for any Python files written.

    >>> write_files([{'path': '/etc/foo', 'contents': 'x'}], 'msg')
    'Error: unsafe path: /etc/foo'
    >>> write_files([{'path': '../foo.py', 'contents': 'x'}], 'msg')
    'Error: unsafe path: ../foo.py'
    """
    for f in files:
        if not is_path_safe(f['path']):
            return f'Error: unsafe path: {f["path"]}'

    output_parts = []
    for f in files:
        os.makedirs(os.path.dirname(f['path']) or '.', exist_ok=True)
        with open(f['path'], 'w', encoding='utf-8') as fh:
            fh.write(f['contents'])
        output_parts.append(f'Written: {f["path"]}')

    try:
        repo = git.Repo('.')
        paths = [f['path'] for f in files]
        repo.index.add(paths)
        repo.index.commit(f'[docchat] {commit_message}')
    except Exception as e:
        output_parts.append(f'Git error: {e}')
        return '\n'.join(output_parts)

    for f in files:
        if f['path'].endswith('.py'):
            output_parts.append(f'Doctest output for {f["path"]}:')
            output_parts.append(doctests(f['path']))

    return '\n'.join(output_parts)


def write_file(path, contents, commit_message):
    """
    Write contents to a single file and commit the change to git.

    This is a thin wrapper around write_files. If the file is a Python
    file, doctests are run after writing and the output is returned.

    >>> write_file('/etc/foo', 'x', 'msg')
    'Error: unsafe path: /etc/foo'
    >>> write_file('../foo.py', 'x', 'msg')
    'Error: unsafe path: ../foo.py'

    # Setup: Mock the 'git' module to prevent actual commits during testing
    >>> from unittest.mock import MagicMock
    >>> import sys, os
    >>> sys.modules['git'] = MagicMock()

    # Test successful file writing and delegation to write_files
    >>> result = write_file('test_wrapper_file.txt', 'hello world', 'wrapper test commit')
    >>> 'Written: test_wrapper_file.txt' in result
    True

    # Cleanup: Remove the temporary file and mock
    >>> os.remove('test_wrapper_file.txt')
    >>> del sys.modules['git']
    """
    return write_files(
        [{'path': path, 'contents': contents}],
        commit_message,
    )


def rm(path):
    """
    Delete a file (supports globs) and commit the removal to git.

    >>> rm('/etc/passwd')
    'Error: unsafe path'
    >>> rm('../secret.txt')
    'Error: unsafe path'
    >>> rm('nonexistent_xyz.txt')
    'Error: no files matched: nonexistent_xyz.txt'

    >>> with open('test_rm_file.txt', 'w') as f:
    ...     _ = f.write('hello')
    >>> import os
    >>> os.path.isfile('test_rm_file.txt')
    True
    >>> from unittest.mock import MagicMock
    >>> import sys
    >>> sys.modules['git'] = MagicMock()
    >>> import git as git_module
    >>> result = rm('test_rm_file.txt')
    >>> os.path.isfile('test_rm_file.txt')
    False
    >>> del sys.modules['git']
    """
    if not is_path_safe(path):
        return 'Error: unsafe path'

    matched = glob.glob(path)
    if not matched:
        return f'Error: no files matched: {path}'

    removed = []
    for filepath in matched:
        try:
            os.remove(filepath)
            removed.append(filepath)
        except Exception as e:
            return f'Error deleting {filepath}: {e}'

    try:
        # If your code uses a local import, make sure to patch sys.modules 
        # instead, but based on your original snippet, git is global.
        repo = git.Repo('.')
        repo.index.remove(removed)
        repo.index.commit(f'[docchat] rm {path}')
    except Exception as e:
        return f'Files deleted but git error: {e}'

    return f'Deleted: {", ".join(removed)}'


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

        # Test handling of an unregistered or hallucinated tool name
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

        # --- NEW TESTS ADDED BELOW ---

        # Setup: Mock the LLM client to test the tool-calling loop deterministically
        >>> from unittest.mock import MagicMock
        >>> import json
        >>> c = Chat()
        >>> c.client = MagicMock()

        # 1. Test the tool calling while-loop
        # Create mock response A: The LLM decides to call a tool
        >>> tc = MagicMock()
        >>> tc.id = 'call_abc123'
        >>> tc.function.name = 'calculate'
        >>> tc.function.arguments = '{"expression": "5 + 5"}'
        >>> msg_tool = MagicMock()
        >>> msg_tool.tool_calls = [tc]
        >>> msg_tool.content = None
        >>> resp1 = MagicMock()
        >>> resp1.choices = [MagicMock(message=msg_tool)]

        # Create mock response B: The LLM replies with the final text
        >>> msg_text = MagicMock()
        >>> msg_text.tool_calls = None
        >>> msg_text.content = 'The answer is 10.'
        >>> resp2 = MagicMock()
        >>> resp2.choices = [MagicMock(message=msg_text)]

        # Assign the sequence of responses to the mock client
        >>> c.client.chat.completions.create.side_effect = [resp1, resp2]

        # Execute the method; it should run the tool and loop back for the final text
        >>> c.send_message('What is 5 + 5?')
        'The answer is 10.'
        
        # Verify the message history correctly recorded all 4 steps:
        # [User prompt, LLM tool request, Tool result, Final LLM reply]
        >>> len(c.messages)
        4
        >>> c.messages[2]['role']
        'tool'
        >>> c.messages[2]['content']
        '10'

        # 2. Test the empty content fallback logic (msg.content or '')
        >>> msg_empty = MagicMock()
        >>> msg_empty.tool_calls = None
        >>> msg_empty.content = None
        >>> resp3 = MagicMock()
        >>> resp3.choices = [MagicMock(message=msg_empty)]
        >>> c.client.chat.completions.create.side_effect = [resp3]
        
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
    ...         return "I hear you."
    >>> globals()['Chat'] = StubChat
    >>> input_sequence = ['Hello agent!', EOFError()]
    >>> def fake_input(prompt):
    ...     val = input_sequence.pop(0)
    ...     if isinstance(val, Exception):
    ...         raise val
    ...     return val
    >>> builtins.input = fake_input
    >>> repl() 
    Hello! How can I assist you today?
    <BLANKLINE>

    >>> os.path.isdir = original_isdir
    >>> os.path.isfile = original_isfile
    >>> builtins.input = original_input
    >>> globals()['Chat'] = original_chat
    """
    # Check for .git folder in current directory
    if not os.path.isdir('.git'):
        print('Error: no .git folder found. Please run chat from a git repo.')
        sys.exit(1)

    chat = Chat()

    # Load AGENTS.md into the conversation if it exists
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
            response = chat.send_message(user_input, temperature=0.0)
            print(response)
    except (KeyboardInterrupt, EOFError):
        print()

if __name__ == "__main__":
    import doctest
    doctest.testmod()
    repl()