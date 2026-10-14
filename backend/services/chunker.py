
def split_pages(
    pages: list[dict],
    chunk_size: int = 1000,
    overlap: int = 200
) -> list[dict]:

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []

    for page in pages:
        text = page["text"]
        page_number = page["page_number"]

        if not text.strip():
            continue

        text_length = len(text)
        start = 0

        while start < text_length:
            # Avoid starting in the middle of a word.
            if start > 0 and not text[start - 1].isspace():
                next_space = text.find(" ", start)
                if next_space != -1 and next_space - start < chunk_size:
                    start = next_space + 1

            end = min(start + chunk_size, text_length)

            # Prefer ending at a word boundary.
            if end < text_length:
                boundary = text.rfind(" ", start, end)
                if boundary > start:
                    end = boundary

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "page_number": page_number,
                    "content": chunk_text
                })

            if end >= text_length:
                # Preserve the existing final-overlap behavior.
                next_start = start + (chunk_size - overlap)

                if next_start < text_length:
                    start = next_start
                    continue

                break

            # Keep overlap, but ensure the next chunk moves forward.
            next_start = max(start + 1, end - overlap)

            # Move to the next word boundary if overlap starts mid-word.
            if next_start > 0 and not text[next_start - 1].isspace():
                next_space = text.find(" ", next_start)
                if next_space != -1 and next_space < end:
                    next_start = next_space + 1

            start = next_start

    return chunks
