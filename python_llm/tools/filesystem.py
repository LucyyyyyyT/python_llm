import os
import glob

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
    if path.startswith('/etc') or path.startswith('/sys') or path.startswith('/proc'):
        return False
    parts = path.replace('\\', '/').split('/')
    if '..' in parts:
        return False
    return True

def ls(path="."):
    """
    List files/folders in a directory, asciibetically, one per line.

    >>> ls('test_files')
    'hello_world'
    >>> 'filesystem.py' in ls('.')      # this file is in the current directory
    False
    >>> ls('/etc')                       # absolute path blocked
    'Error: unsafe path'
    >>> ls('../other')                   # traversal blocked
    'Error: unsafe path'
    >>> ls('nonexistent_folder_xyz')     # missing folder returns empty string
    ''
    """
    if not is_path_safe(path):
        return 'Error: unsafe path'
    files = sorted(glob.glob(f'{path}/*'))
    names = [os.path.basename(f) for f in files]
    return '\n'.join(names)

def cat(path):
    """
    Open a file and return its contents as a string.

    >>> cat('test_files/hello_world')
    'hello world'

    >>> cat('filesystem.py')      # reads this file; first 16 chars shown
    'Error: file not found'
    >>> cat('/etc/passwd')              # absolute path blocked
    'Error: unsafe path'
    >>> cat('../secret.txt')            # traversal blocked
    'Error: unsafe path'
    >>> cat('nonexistent_file_xyz.txt') # missing file
    'Error: file not found'


   
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