def reverse_block_chunks(haystack: list | tuple | set, size):
    """iterate through the list with a given size so the blocks keep their inner order,
    but we get them from the latest"""
    if isinstance(haystack, set):
        haystack = list(haystack)
    start, end = len(haystack) - size, len(haystack)
    while end > 0:
        yield haystack[start:end]
        start, end = max(0, start - size), start
