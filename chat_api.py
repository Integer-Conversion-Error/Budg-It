from fastapi import FastAPI, HTTPException
import uvicorn
from consolemain import configure_genai, initialize_chat, generate_prompt
import consolemain
import json
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()


# Configure CORS for the FastAPI app
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",  # This regex matches any origin.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat")
def send_one_chat(current_state: dict):
    """
    API function to process a single user input in the budgeting assistant.
    
    Parameters:
        current_state (dict): The current budget state.
    
    Returns:
        dict: The updated budget state with AI responses.
    """
    try:
        # Configure the generative AI model
        model = configure_genai()

        # Initialize the chat session with the current state
        chat_session = initialize_chat(model, current_state)

        # Generate response from the AI
        response = chat_session.send_message(
            generate_prompt(current_state, current_state.get("conversation", ""))
        )

        # Parse and return the AI response
        ai_response = response.text
        return json.loads(ai_response)
    except Exception as e:
        # Raise an HTTPException for any errors
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")
    
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

