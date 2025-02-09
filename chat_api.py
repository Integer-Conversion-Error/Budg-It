from fastapi import FastAPI, HTTPException, Body
import uvicorn
import json,re
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any

# Import the helper functions from consolemain.
from consolemain import configure_genai, initialize_chat, generate_prompt

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
