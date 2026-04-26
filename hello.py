# hello.py
"""
A simple script that prints "hello world" when executed.

The module provides a ``main`` function that performs the printing, and
executes it when run as a script.

Doctests
========
>>> # Running the module directly prints the greeting.
>>> # This doctest demonstrates the expected output when the script is executed.
>>> # Note: The doctest runner captures stdout, so we use the ``print`` output.
>>> import subprocess, sys, os
>>> result = subprocess.run([sys.executable, os.path.abspath('hello.py')], capture_output=True, text=True)
>>> result.stdout.strip()
'hello world'
"""

def main() -> None:
    """Print ``hello world`` to standard output.

    >>> from io import StringIO
    >>> import sys
    >>> backup = sys.stdout
    >>> sys.stdout = StringIO()
    >>> main()
    >>> output = sys.stdout.getvalue().strip()
    >>> sys.stdout = backup
    >>> output
    'hello world'
    """
    print("hello world")


if __name__ == "__main__":
    main()
