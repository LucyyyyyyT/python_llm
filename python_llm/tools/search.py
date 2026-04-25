"""Search tool for grepping files and directories."""
import os
import re

from python_llm.tools.filesystem import is_path_safe


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

    >>> os.mkdir('test_grep_dir')
    >>> with open('test_grep_dir/file1.txt', 'w', encoding='utf-8') as f:
    ...     _ = f.write('hello\\nsearch target\\nworld')
    >>> os.mkdir('test_grep_dir/subdir')
    >>> with open('test_grep_dir/subdir/file2.txt', 'w', encoding='utf-8') as f:
    ...     _ = f.write('another search target here')
    >>> os.mkdir('test_grep_dir/.hidden')
    >>> with open('test_grep_dir/.hidden/file3.txt', 'w', encoding='utf-8') as f:
    ...     _ = f.write('search target hidden')

    >>> grep('target', 'test_grep_dir/file1.txt').replace('\\\\', '/')
    'test_grep_dir/file1.txt:search target'

    >>> result = grep('target', 'test_grep_dir').replace('\\\\', '/')
    >>> expected = [
    ...     'test_grep_dir/file1.txt:search target',
    ...     'test_grep_dir/subdir/file2.txt:another search target here'
    ... ]
    >>> result.split('\\n') == expected    True

    >>> 'test_grep_dir/file1.txt:search target' in grep('search target').replace('\\\\', '/')
    True

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
