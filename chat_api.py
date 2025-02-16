import io
from PIL import Image
from fastapi import FastAPI, HTTPException, File,UploadFile,Form,Body
from fastapi.responses import JSONResponse
import uvicorn # type: ignore
import json,re
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from receipt_reader import extract_text_from_image_stream


# Import the helper functions from consolemain.
from consolemain import configure_genai, initialize_chat, generate_prompt

from datetime import datetime

def get_current_time_string():
    """
    Returns the current time as a string in the format YYYY-MM-DD-HH:MM:SS.
    """
    return datetime.now().strftime("%Y-%m-%d-%H:%M:%S")


app = FastAPI()

# Configure CORS for the FastAPI app
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",  # This regex matches any origin.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the Pydantic model that describes the expected request payload.
class ChatRequest(BaseModel):
    Budget: Dict[str, Any]
    conversation: Optional[str] = ""  # Defaults to an empty string if not provided.



def log_message(message: Optional[str]):
    with open("log.txt", "a") as f:
        f.write(get_current_time_string() + " -- "+ message + "\n")
        
import os
log_message("\nDEBUG: New Attempt")
log_message("DEBUG: Current working directory: " + os.getcwd())

@app.post("/chat")
def send_one_chat(current_state: ChatRequest = Body(...)):
    try:
        # Convert the incoming Pydantic model to a dictionary.
        state_dict = current_state.dict()
        print(state_dict)

        # Configure the generative AI model.
        model = configure_genai()

        # Initialize chat session only if there is no conversation history.
        # Otherwise, re-create the chat session with the existing conversation.
        if not state_dict["Budget"].get("conversations"):
            chat_session = initialize_chat(model, state_dict)
        else:
            # Rebuild chat history from previous conversation turns.
            chat_history = []
            for conversation in state_dict["Budget"]["conversations"]:
                chat_history.append({
                    "role": "user",
                    "parts": [{"text": conversation["user_message"]}]
                })
                chat_history.append({
                    "role": "model",
                    "parts": [{"text": conversation["ai_response"]}]
                })
            # Add the new user input to the history.
            chat_history.append({
                "role": "user",
                "parts": [{"text": state_dict.get("conversation", "")}]
            })
            print(chat_history)
            chat_session = model.start_chat(history=chat_history)

        # Generate the prompt using the current state.
        prompt = generate_prompt(state_dict, state_dict.get("conversation", ""))
        

        # Generate response from the AI.
        response = chat_session.send_message(prompt)
        ai_response = response.text
        print("DEBUG: Raw AI response text:")
        print(ai_response)

        # Try to parse the AI response.
        try:
            parsed_ai_response = json.loads(ai_response)
            
        except json.JSONDecodeError:
            parsed_ai_response = {"ai_response": ai_response}
            

        # Extract the conversation reply.
        # If the "conversation" key exists and is a dict, use its "ai_response" value.
        # Otherwise, use a default message instead of the entire API return.
        if "conversation" in parsed_ai_response and isinstance(parsed_ai_response["conversation"], dict):
            ai_reply = parsed_ai_response["conversation"].get("ai_response", "Operation completed.")
        else:
            ai_reply = "Operation completed."
        

        # Append the new conversation turn to the conversation history.
        if "conversations" not in state_dict["Budget"]:
            state_dict["Budget"]["conversations"] = []
        state_dict["Budget"]["conversations"].append({
            "user_message": state_dict.get("conversation", ""),
            "ai_response": ai_reply
        })
        # Update budget items if provided in the AI response.
        if ("Budget" in parsed_ai_response 
                and isinstance(parsed_ai_response["Budget"], dict) 
                and "items" in parsed_ai_response["Budget"]):
            state_dict["Budget"]["items"] = parsed_ai_response["Budget"]["items"]
            
        else:
            print("DEBUG: No update to 'items' was found in the AI response.")
        
        state_dict["Budget"]["budget_limit"] = parsed_ai_response["Budget"]["budget_limit"]
        print(state_dict)
        return state_dict

    except Exception as e:
        print("DEBUG: Exception encountered:", e)
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")



@app.post("/receipt")
async def process_receipt(
    receipt: UploadFile = File(...),
    current_state: str = Form(...),
    command: Optional[str] = Form(None)
):
    log_message("DEBUG: /receipt endpoint hit")
    temp_file_path = None
    try:
        log_message("DEBUG: Received current_state (raw): " + current_state)
        if command:
            log_message("DEBUG: Received command: " + command)
        
        # Convert JSON string to dict
        state_data = json.loads(current_state)

        log_message("DEBUG: Received current_state (raw): " + current_state)
        if command:
            log_message("DEBUG: Received command: " + command)
        
        # Parse the JSON string from the form field into a dict.
        state_data = json.loads(current_state)

        
        # Save the uploaded file temporarily
        temp_file_path = f"temp_{receipt.filename}"
        contents = await receipt.read()
        
        log_message(f"DEBUG: Receipt Size: {len(contents)} bytes")
        
        with open(receipt.filename, 'wb') as f:
            f.write(contents)
        
        with open(temp_file_path, "wb") as buffer:
            buffer.write(contents)
        
        log_message(f"DEBUG: Temporary file saved: {temp_file_path}")
        
        # Open the image and convert it to a stream
        with Image.open(temp_file_path) as img:
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
        
        log_message("DEBUG: Image converted to byte stream")
        
        # Extract text from the image stream
        receipt_text = extract_text_from_image_stream(img_byte_arr)
        
        log_message(f"DEBUG: Extracted receipt_text (raw): {receipt_text}")
        
        if isinstance(receipt_text, bytes):
            receipt_text = receipt_text.decode('utf-8', errors='replace')
            log_message(f"DEBUG: Decoded receipt_text: {receipt_text}")
        else:
            log_message("DEBUG: receipt_text is already a string")

        # Combine the OCR text with any extra instructions:
        additional_subprompt = "\nPlease add the above receipt items as budget items."
        full_prompt = receipt_text + additional_subprompt

        # Put it into the conversation key so the helper sees it as "user input"
        state_data["conversation"] = full_prompt
        
        # Call your shared chat logic
        updated_state = process_chat_logic(state_data, state_data["conversation"])

        # Return the updated state
        return JSONResponse(content=updated_state)

    except json.JSONDecodeError:
        log_message("DEBUG: JSON decode error occurred")
        raise HTTPException(status_code=400, detail="Invalid JSON in current_state")
    except Exception as e:
        log_message(f"DEBUG: Exception occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing receipt: {str(e)}")
    finally:
        # Cleanup temp file if desired
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            log_message(f"DEBUG: Temporary file deleted: {temp_file_path}")




def process_chat_logic(state_dict: Dict[str, Any], user_input: str) -> Dict[str, Any]:
    """
    This function replicates the AI chat flow without requiring a FastAPI route.
    - state_dict: Current state of the Budget & conversation (dict).
    - user_input: The new user message to add to the conversation.

    Returns:
        An updated `state_dict` with the AI response appended to .Budget.conversations.
    """
    # 1. Configure the model
    model = configure_genai()

    # 2. Build or rebuild the chat session
    if not state_dict["Budget"].get("conversations"):
        # No existing conversation, so initialize
        chat_session = initialize_chat(model, state_dict)
    else:
        # Rebuild from previous conversation
        chat_history = []
        for conversation in state_dict["Budget"]["conversations"]:
            chat_history.append({
                "role": "user",
                "parts": [{"text": conversation["user_message"]}]
            })
            chat_history.append({
                "role": "model",
                "parts": [{"text": conversation["ai_response"]}]
            })

        # Now add the new user input
        chat_history.append({
            "role": "user",
            "parts": [{"text": user_input}]
        })

        chat_session = model.start_chat(history=chat_history)

    # 3. Generate the prompt
    prompt = generate_prompt(state_dict, user_input)

    # 4. Send the prompt to the model
    response = chat_session.send_message(prompt)
    ai_response = response.text

    # 5. Parse AI response
    try:
        parsed_ai_response = json.loads(ai_response)
    except json.JSONDecodeError:
        parsed_ai_response = {"ai_response": ai_response}

    # 6. Extract conversation AI reply
    if (
        "conversation" in parsed_ai_response 
        and isinstance(parsed_ai_response["conversation"], dict)
    ):
        ai_reply = parsed_ai_response["conversation"].get("ai_response", "Operation completed.")
    else:
        ai_reply = "Operation completed."

    # 7. Append new conversation turn
    if "conversations" not in state_dict["Budget"]:
        state_dict["Budget"]["conversations"] = []
    state_dict["Budget"]["conversations"].append({
        "user_message": user_input,
        "ai_response": ai_reply
    })

    # 8. Check for updated budget items
    if ("Budget" in parsed_ai_response 
        and isinstance(parsed_ai_response["Budget"], dict) 
        and "items" in parsed_ai_response["Budget"]):
        state_dict["Budget"]["items"] = parsed_ai_response["Budget"]["items"]
    else:
        print("DEBUG: No update to 'items' was found in the AI response.")

    # 9. Check budget limit
    state_dict["Budget"]["budget_limit"] = parsed_ai_response.get("Budget", {}).get("budget_limit")

    # Return the updated state
    return state_dict


def parse_receipt_text(text):
    """
    Parses the OCR-extracted text from a receipt.
    Assumes each line with an item has a format like:
      ItemName  <whitespace> $Cost
    Returns a list of budget items.
    """
    items = []
    lines = text.splitlines()
    # Regular expression to capture an item name and a cost.
    # This regex matches lines with text followed by a number (optionally preceded by a $)
    pattern = re.compile(r'(.+?)\s+\$?(\d+\.\d{2})')
    
    for line in lines:
        match = pattern.search(line)
        if match:
            item_name = match.group(1).strip()
            try:
                amount = float(match.group(2))
            except ValueError:
                continue  # Skip lines that don’t parse correctly
            # Append the item to the list; adjust additional fields as needed.
            items.append({
                "item_name": item_name,
                "amount": amount,
                "category": "Receipt",
                "importance_rank": None,
                "recurrence_schedule": None,
                "due_date": None
            })
    return items

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
