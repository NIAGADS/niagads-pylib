import nh3


def sanitize(htmlStr: str) -> str:
    """
    ammonia sanitization that turns a string into unformatted HTML.
    used to sanitize incoming API query and path arguments

    Args:
        htmlStr (str): string to be cleaned

    Returns:
        str: cleaned string
    """
    if htmlStr is not None:
        return nh3.clean_text(htmlStr.strip())

    return htmlStr
