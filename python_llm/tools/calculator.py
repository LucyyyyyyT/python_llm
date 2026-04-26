import ast
import operator

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
