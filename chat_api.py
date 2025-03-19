
import json, re, os, io, uvicorn
from PIL import Image
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Body, Request
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, Dict, Any

from receipt_reader import extract_text_from_image_stream

from firebase_auth import get_current_user
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends


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
# app.add_middleware(
#     CORSMiddleware,
#     allow_origin_regex=".*",  # This regex matches any origin
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
#     expose_headers=["Authorization"],  # Important for auth
# )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    log_message(f"DEBUG: Received request: {request.method} {request.url}")
    log_message(f"DEBUG: Headers: {request.headers}")
    
    # Process the request
    response = await call_next(request)
    
    log_message(f"DEBUG: Response status code: {response.status_code}")
    return response


# Mount static files directory
app.mount("/static", StaticFiles(directory="public"), name="static")

# Define templates
templates = Jinja2Templates(directory="public")

# Define the Pydantic model that describes the expected request payload.
class ChatRequest(BaseModel):
    Budget: Dict[str, Any]
    conversation: Optional[str] = ""  # Defaults to an empty string if not provided.

# Define a simple login request model
class LoginRequest(BaseModel):
    username: str
    password: str


def log_message(message: Optional[str]):
    with open("log.txt", "a") as f:
        f.write(get_current_time_string() + " -- "+ message + "\n")
        

log_message("\nDEBUG: New Attempt")
log_message("DEBUG: Current working directory: " + os.getcwd())


def calculate_surplus(state):
    total = 0
    budget = state["Budget"]["budget_limit"] if state["Budget"]["budget_limit"] != None else 0
    items = state["Budget"]["items"]
    
    for item in items:
        total += item["amount"]
    surp_amount = round(budget - total,2)
    state["Budget"]["budget_surplus"] = surp_amount
    print(f"Surplus amount: {surp_amount}")
    return state

# Root route - serve the login page
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Budget interface route
@app.get("/budget", response_class=HTMLResponse)
async def budget_interface(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Login API endpoint
@app.post("/login")
async def login(login_data: LoginRequest):
    # For demonstration, we're accepting any credentials
    # In a real app, you would validate against Firebase Authentication
    return {"success": True, "message": "Use Firebase Authentication"}


# Add a route to verify tokens and get user info (add this to your app routes)
@app.post("/verify-token")
async def verify_token(user: dict = Depends(get_current_user)):
    """
    Verify Firebase auth token and return user info.
    This endpoint can be used by the frontend to check if a token is valid.
    """
    return {"success": True, "user": user}


USE_AUTH = False  # Set to True when ready for production

# If you're using a security dependency, modify it to be optional
# This function can replace the get_current_user function
async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = None):
    """
    A development version that doesn't require authentication
    """
    # Just return a mock user for development
    return {
        "uid": "dev-user-id",
        "email": "dev-user@example.com"
    }

# Now update your routes to use this function instead of strict authentication
@app.post("/chat")

def send_one_chat(current_state: ChatRequest = Body(...)):
    # No authentication dependency

    try:
        # Log the request for debugging
        log_message("DEBUG: Chat endpoint hit")
        
        # Rest of your existing code...
        state_dict = current_state.dict()

        # Ensure conversations array exists
        if "conversations" not in state_dict["Budget"]:
            state_dict["Budget"]["conversations"] = []
            

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
                    "parts": [{"text": conversation.get("user_message", "")}]
                })
                chat_history.append({
                    "role": "model",
                    "parts": [{"text": conversation.get("ai_response", "")}]
                })
            # Add the new user input to the history.
            chat_history.append({
                "role": "user",
                "parts": [{"text": state_dict.get("conversation", "")}]
            })

            chat_session = model.start_chat(history=chat_history)

        # Generate the prompt using the current state.
        prompt = generate_prompt(state_dict, state_dict.get("conversation", ""))
        
        # Generate response from the AI.
        response = chat_session.send_message(prompt)
        ai_response = response.text

        # Try to parse the AI response.
        try:
            parsed_ai_response = json.loads(ai_response)
        except json.JSONDecodeError:
            parsed_ai_response = {"ai_response": ai_response}
            
        # Extract the conversation reply.
        if "conversation" in parsed_ai_response and isinstance(parsed_ai_response["conversation"], dict):
            ai_reply = parsed_ai_response["conversation"].get("ai_response", "Operation completed, but error returning from the agent. Ask to see your budget through chat.")
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

        
        state_dict["Budget"]["budget_limit"] = parsed_ai_response["Budget"]["budget_limit"]
        
        # Calculate budget surplus
        state_dict = calculate_surplus(state_dict)
        

        return state_dict

    except Exception as e:
        log_message(f"DEBUG: Exception encountered: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")
@app.post("/receipt")
async def process_receipt(
    receipt: UploadFile = File(...),
    current_state: str = Form(...),
    command: Optional[str] = Form(None)#,
    #user: dict = Depends(get_current_user)
):
    log_message("DEBUG: /receipt endpoint hit")
    temp_file_path = None
    try:
        log_message("DEBUG: Received current_state (raw): " + current_state)
        if command:
            log_message("DEBUG: Received command: " + command)
        
        # Convert JSON string to dict
        state_data = json.loads(current_state)
        
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
        
        # Call the chat logic function
        updated_state = process_chat_logic(state_data, state_data["conversation"])

        # Return the updated state
        print(json.dumps(updated_state,indent=2))
        updated_state = calculate_surplus(updated_state)
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
                "parts": [{"text": conversation.get("user_message", "")}]
            })
            chat_history.append({
                "role": "model",
                "parts": [{"text": conversation.get("ai_response", "")}]
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
    pattern = re.compile(r'(.+?)\s+\$?(\d+\.\d{2})')
    
    for line in lines:
        match = pattern.search(line)
        if match:
            item_name = match.group(1).strip()
            try:
                amount = float(match.group(2))
            except ValueError:

                continue  # Skip lines that don't parse correctly
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
    # Make sure the static directory exists
    if not os.path.exists("static"):
        os.makedirs("static")
    
    # Start the server
    uvicorn.run(app, host="127.0.0.1", port=8000)