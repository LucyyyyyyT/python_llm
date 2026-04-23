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

def calculate(expression):
    """
    Evaluate a simple arithmetic expression and return the result as a string.

    Integer results are returned without a decimal point.
    Float results that are whole numbers keep the decimal only when
    produced by true division (/); all other whole-number floats are
    converted to int. Non-terminating floats are returned as-is.

    >>> calculate('2 + 2')              # integer result
    '4'
    >>> calculate('100 / 4')            # exact division -> float string kept
    '25.0'
    >>> calculate('5 * 5.0')            # whole-number float without '/' -> int string
    '25'
    >>> calculate('10 / 3')             # non-terminating float
    '3.3333333333333335'
    >>> calculate('2 ** 10')            # exponentiation
    '1024'
    >>> calculate('17 % 5')             # modulo
    '2'
    >>> calculate('1 / 0')              # division by zero
    'Error: division by zero'
    >>> calculate('1 + (2 *')           # malformed expression
    'Error: invalid expression'
    >>> calculate('__import__("os")')   # unsafe expression blocked by _eval_node
    'Error: invalid expression'
    >>> calculate('None + 1')           # non-numeric constant blocked
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
    except (ValueError, TypeError, SyntaxError):
        return 'Error: invalid expression'