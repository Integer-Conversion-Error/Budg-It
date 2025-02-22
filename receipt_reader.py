#!/usr/bin/env python3
import json
import sys
from PIL import Image
import pytesseract
import google.generativeai as genai
from consolemain import load_config

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text_from_image_stream(image_stream):
    """
    Takes an image stream (a file-like object) and returns text extracted from the image,
    then passes it to an AI parser for JSON conversion.
    """
    image = Image.open(image_stream)
    ocr_text = pytesseract.image_to_string(image)
    return ai_filter_receipt_text(ocr_text)
    #return ocr_text

def ai_filter_receipt_text(text):
    """
    Sends raw OCR text from a receipt to Gemini via google.generativeai,
    embedding the 'system' prompt in a user message (like your snippet).
    Expects valid JSON in response or a fallback structure if parsing fails.
    """
    # 1. Load config & configure Gemini
    config = load_config()
    genai.configure(api_key=config["GEMINI_API_KEY"])

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config={
            "temperature": 0.8,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 1024,
        },
    )

    # 2. "System" instructions, placed in a user message
    system_instructions = (
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
        "Make sure to group similar items together. If there is a large purchase and a small purchase, and both are of the same category, combine and sum them as one item."
        "If you see a line named Total or total, take its corresponding value instead of the sum if the items can be all grouped together."
        "Always group together add-on fees and taxes with the corresponding product/service. Never ever seperate tax from the item."
        "Make sure to include the date the payment is due on/was completed on."
    )

    # 3. Initialize the chat session (like your snippet: "System prompt: ... Respond understood.")
    chat_session = model.start_chat(
        history=[
            {
                "role": "user",
                "parts": [
                    {
                        "text": f"System prompt: {system_instructions}\n"
                                 "Respond 'Understood.' if you got it."
                    }
                ],
            },
            {
                "role": "model",
                "parts": [{"text": "Understood."}],
            },
        ]
    )

    # 4. Now send the actual receipt text as the new user message
    response = chat_session.send_message(text)

    raw_response = response.text.strip()[7:-3]

    # 5. Parse the response as JSON if possible
    #print(raw_response)
    
    return raw_response

def main():
    image_file_path = "84pxOL1.jpg"
    try:
        with open(image_file_path, "rb") as image_file:
            extracted_info = extract_text_from_image_stream(image_file)
            #print("Extracted Info (JSON or fallback):")
            #print(extracted_info)
    except Exception as e:
        #print(f"An error occurred while processing the image: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
