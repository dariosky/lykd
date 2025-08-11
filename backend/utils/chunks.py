def reverse_block_chunks(haystack: list, size):
    """iterate through the list with a given size so the blocks keep their inner order,
    but we get them from the latest"""
    start, end = len(haystack) - size, len(haystack)
    while end > 0:
        yield haystack[start:end]
        start, end = max(0, start - size), start
