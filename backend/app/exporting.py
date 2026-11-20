"""Plain-text, DOCX, and PDF exports for a novel."""

import html
from io import BytesIO

from app.textutil import plain_text


def novel_text(title: str, chapters: list[tuple[str, str]]) -> str:
    parts = [title, ""]
    for chapter_title, content in chapters:
        parts.append(chapter_title)
        parts.append(plain_text(content).strip())
        parts.append("")
    return "\n".join(parts).strip() + "\n"


def novel_docx(title: str, chapters: list[tuple[str, str]]) -> bytes:
    from docx import Document

    document = Document()
    document.add_heading(title, 0)
    for chapter_title, content in chapters:
        document.add_heading(chapter_title, 1)
        body = plain_text(content).strip()
        for paragraph in body.splitlines() or [""]:
            document.add_paragraph(paragraph)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def novel_pdf(title: str, chapters: list[tuple[str, str]]) -> bytes:
    blocks = "".join(
        f"<h2>{html.escape(chapter_title)}</h2><p>{html.escape(plain_text(content)).replace(chr(10), '<br>')}</p>"
        for chapter_title, content in chapters
    )
    markup = (
        "<html><head><meta charset='utf-8'>"
        "<style>body{font-family:'Microsoft YaHei','SimSun',sans-serif;font-size:14px;line-height:1.7}"
        "h1,h2{font-weight:600}</style></head><body>"
        f"<h1>{html.escape(title)}</h1>{blocks}</body></html>"
    )
    try:
        from weasyprint import HTML

        return HTML(string=markup).write_pdf()
    except (ImportError, OSError) as exc:
        raise RuntimeError("WeasyPrint 缺少系统库，暂时不能导出 PDF") from exc
