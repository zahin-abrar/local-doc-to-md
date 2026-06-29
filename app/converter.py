"""
Converter module for transforming documents into Markdown format using MarkItDown.
"""
import os
from markitdown import MarkItDown

def convert_to_markdown(input_path: str) -> str:
    """
    Converts a document (PDF, Word, Excel, PowerPoint, HTML, text, etc.) to Markdown 
    using the MarkItDown library.

    Args:
        input_path (str): The path to the input document.

    Returns:
        str: The converted Markdown text.

    Raises:
        FileNotFoundError: If the input file does not exist.
        RuntimeError: If the conversion process fails.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    try:
        md = MarkItDown()
        result = md.convert(input_path)
        if result is None or result.text_content is None:
            raise ValueError("Conversion completed but produced no text content.")
        return result.text_content
    except Exception as e:
        err_msg = str(e)
        # Parse typical error strings to return friendly diagnostic messages
        if "encrypted" in err_msg.lower() or "password" in err_msg.lower():
            raise RuntimeError("The PDF file is encrypted or password-protected. Please decrypt it first before converting.") from e
        if "corrupt" in err_msg.lower() or "damaged" in err_msg.lower():
            raise RuntimeError("The PDF file appears to be corrupted or damaged. Verify it opens correctly on your device.") from e
        raise RuntimeError(f"Conversion error: {err_msg}") from e

