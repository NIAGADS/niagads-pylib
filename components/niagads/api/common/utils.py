import nh3


def sanitize(html_str: str) -> str:
    """
    ammonia sanitization that turns a string into unformatted HTML.
    used to sanitize incoming API query and path arguments

    Args:
        html_str (str): string to be cleaned

    Returns:
        str: cleaned string
    """
    if html_str is not None:
        return nh3.clean_text(html_str.strip())

    return html_str


def get_none():  # for placeholder dependency injection
    return None
