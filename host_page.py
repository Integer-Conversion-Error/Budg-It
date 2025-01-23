from flask import Flask, send_from_directory, jsonify, request
from consolemain import configure_genai, initialize_chat, generate_prompt
import json
from fastapi import FastAPI, HTTPException
import os

app = Flask(__name__)

# Route to serve the HTML page
@app.route("/")
def index():
    return send_from_directory(directory="static", path="index.html")

# Route to serve static files (like CSS and JS if needed)
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(directory="static", path=filename)

# Example API route to simulate the chat endpoint
# @app.route("/chat", methods=["POST"])
@app.route("/chat", methods=["POST"])
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
    # Ensure the static folder exists for hosting HTML
    if not os.path.exists("static"):
        os.makedirs("static")

    print("Place your 'index.html' and related files in the 'static' directory.")
    app.run(host="0.0.0.0", port=5000, debug=True)
