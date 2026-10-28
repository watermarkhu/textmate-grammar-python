def render(user, items):
    # TODO: keep the escaped braces and conversion markers visible.
    summary = f"{user.name!s}: {{ {len(items)} items }}"
    formatted = f"{items[0]:>08}" if items else "<empty>"
    return summary, formatted  # type: tuple[str, str]
