# hello.py
"""
Simple module that prints a greeting.

This module provides a :func:`hello` function which prints
``"hello world"`` to standard output.  When executed as a script it
will automatically call :func:`hello`.

Doctests
========
>>> from hello import hello
>>> hello()  # doctest: +NORMALIZE_WHITESPACE
hello world
"""

def hello() -> None:
    """Print ``"hello world"`` to standard output.

    Returns
    -------
    None
        The function prints directly and returns ``None``.

    Examples
    --------
    >>> hello()  # doctest: +NORMALIZE_WHITESPACE
    hello world
    """
    print("hello world")


if __name__ == "__main__":
    hello()
