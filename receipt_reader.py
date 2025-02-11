#!/usr/bin/env python3
import sys
from PIL import Image
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"



def extract_text_from_image_stream(image_stream):
    """
    Takes an image stream (a file-like object) and returns all text extracted from the image.
    
    :param image_stream: A file-like object containing image data (opened in binary mode).
    :return: A string containing the text extracted from the image.
    """
    # Open the image using Pillow (PIL)
    image = Image.open(image_stream)
    # Use pytesseract to perform OCR on the image
    text = pytesseract.image_to_string(image)
    return text

def main():
    # Ensure the user has provided the path to an image file as an argument.
    
    
    image_file_path = "reciept_test_1.png"
    try:
        # Open the image file in binary mode.
        with open(image_file_path, "rb") as image_file:
            extracted_text = extract_text_from_image_stream(image_file)
            print("Extracted Text:")
            print(extracted_text)
    except Exception as e:
        print(f"An error occurred while processing the image: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
