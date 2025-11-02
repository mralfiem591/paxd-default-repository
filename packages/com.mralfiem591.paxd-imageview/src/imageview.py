#!/usr/bin/env python3
"""
ImageView - A simple command-line image viewer
Fetches an image from a URL and displays it full-screen in the terminal
"""

import sys
from os import get_terminal_size
import requests
from PIL import Image
from io import BytesIO
import argparse
import ascii_magic # type: ignore

def download_image(url):
    """Download image from URL."""
    try:
        headers = {
            'User-Agent': 'PaxdImgViewer/1.1.4'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Check if the content type is an image
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            raise ValueError(f"URL does not point to an image (content-type: {content_type})")
        
        return Image.open(BytesIO(response.content))
    except requests.RequestException as e:
        raise Exception(f"Failed to download image: {e}")
    except Exception as e:
        raise Exception(f"Failed to process image: {e}")

def image_to_ascii(image, use_color=True):
    term_size = get_terminal_size()
    term_width = term_size.columns
    term_height = term_size.lines

    # Open image and get aspect ratio
    img = image.convert("RGB")
    img_width, img_height = img.size
    # ASCII characters are about twice as tall as they are wide
    aspect_ratio = img_width / (img_height * 0.5)
    # Reserve a few lines for prompt, etc.
    reserved_lines = 2
    usable_height = max(1, term_height - reserved_lines)
    # Calculate max width to fit both width and height
    max_width = min(term_width, int(usable_height * aspect_ratio))

    # Create an AsciiArt object from the image file
    art = ascii_magic.AsciiArt.from_pillow_image(img)

    print(art.to_ascii(columns=max_width, monochrome=not use_color))

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Display an image from a URL in full-screen terminal mode"
    )
    parser.add_argument("url", 
        help="URL of the image to display"
    )
    parser.add_argument(
        "--no-color", 
        action="store_true", 
        help="Use ASCII characters instead of colored blocks"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="ImageView 1.0.0"
    )
    parser.add_argument(
        "--sleep",
        type=int,
        default=0,
        help="Sleep time in seconds after displaying the image"
    )

    args = parser.parse_args()

    if not args.url:
        print("Error: URL is required", file=sys.stderr)
        raise Exception("URL is required")

    # Validate URL
    if not args.url.startswith(('http://', 'https://')):
        print(f"Error: URL must start with http:// or https:// (was: {args.url})", file=sys.stderr)
        raise Exception(f"Invalid URL scheme: {args.url}")
    
    use_color = not args.no_color
    try:
        image_to_ascii(download_image(args.url), use_color)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise Exception(e)
    if args.sleep > 0:
        import time
        time.sleep(args.sleep)


if __name__ == "__main__":
    main()
