#!/usr/bin/env python3
import json
import sys
from PIL import Image
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
import google.generativeai as genai
from consolemain import load_config


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
    #text = ai_filter_receipt_text(text)
    return text


def ai_filter_receipt_text(text):
    """
    Sends the raw OCR text from a receipt to Gemini (via google.generativeai),
    instructing it to parse the receipt items into a structured format (like JSON).

    :param text: The raw extracted text from a receipt (string).
    :return: A parsed dictionary of receipt information or an original text if parsing fails.
    """

    # 1. Configure the Gemini API.
    # Replace 'YOUR_API_KEY' with your actual key. 
    # Or load it securely from a config file / env variable.
    config = load_config()
    genai.configure(api_key=config["GEMINI_API_KEY"])

    # 2. Set up the model and generation parameters.
    # Adjust model name or generation_config as needed.
    model = genai.GenerativeModel(
        model_name="gemini-2.0-pro-exp-02-05",
        generation_config={
            "temperature": 0.8,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 102400,
        },
    )

    # 3. Start a chat session with a strong system message:
    # The system message is your "system prompt" that ensures the AI stays on task.
    # Here, we instruct it how to interpret and format the data.
    system_message = (
        "You are an expert receipt parser. Your job is to take raw text from a store "
        "receipt and parse out individual purchased items, their price, quantity, and "
        "any other relevant data. Always respond in valid JSON with the structure:\n"
        "{\n"
        "  'items': [\n"
        "    {\n"
        "       'name': 'string',\n"
        "       'price': number,\n"
        "       'quantity': number,\n"
        "       'category': 'string'  // optional\n"
        "    },\n"
        "  ],\n"
        "  'tax': number, // if found\n"
        "  'total': number // if found\n"
        "}\n\n"
        "If you cannot detect a certain value (like quantity or category), you may default "
        "them to 1 or leave them blank, but ensure the JSON structure remains valid. "
        "Do not include any commentary outside the JSON response."
    )

    # Initialize chat with a system role
    chat = model.start_chat(history=[
        {
            "role": "system",
            "parts": [{"text": system_message}],
        }
    ])

    # 4. Send the user's raw receipt text. 
    # The AI should respond with structured JSON as per the instructions above.
    response = chat.send_message(text)

    # The raw text from Gemini
    raw_response = response.text.strip()

    # 5. Parse the JSON if possible.
    # We wrap in a try/catch in case the AI didn't return valid JSON.
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError:
        # If the AI returns something invalid, fallback to original text
        return {"unparsed_text": raw_response }


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
