# hello.py
"""
A simple script that prints a greeting.

The module provides a ``main`` function that prints ``"hello cat"``
when executed.  The module can be run directly as a script::

    python hello.py

Running the module will output::

    hello cat

Doctest examples demonstrate the expected output.
"""

def main() -> None:
    """Print the greeting ``"hello cat"``.

    >>> import sys, io
    >>> captured = io.StringIO()
    >>> sys_stdout = sys.stdout
    >>> sys.stdout = captured
    >>> main()
    >>> sys.stdout = sys_stdout
    >>> captured.getvalue().strip()
    'hello cat'
    """
    print("hello cat")


if __name__ == "__main__":
    main()
