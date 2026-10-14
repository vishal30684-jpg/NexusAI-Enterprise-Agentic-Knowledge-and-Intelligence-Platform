import pymupdf


def extract_pages_from_pdf(file_path: str) -> list[dict]:
  with pymupdf.open(file_path) as document:

    pages = []

    for page_number, page in enumerate(document, start=1):
        page_text = page.get_text().strip()

        if page_text:
            pages.append({
                "page_number": page_number,
                "text": page_text
            })

    

    return pages