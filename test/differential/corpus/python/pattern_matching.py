def describe(value):
    match value:
        case {"kind": "point", "x": x, "y": y}:
            return f"({x}, {y})"
        case [first, *rest] if first is not None:
            return first, rest
        case _:
            return None
