from flask import Flask, send_from_directory, jsonify, request, redirect, url_for
from consolemain import configure_genai, initialize_chat, generate_prompt
import json
from fastapi import FastAPI, HTTPException
import os

app = Flask(__name__)

# Route to serve the login page as the default landing page
@app.route("/")
def index():
    return send_from_directory(directory="static", path="login.html")

# Route to serve the budget interface
@app.route("/budget")
def budget_interface():
    return send_from_directory(directory="static", path="index.html")

# Route to serve static files (like CSS and JS if needed)
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(directory="static", path=filename)

# Example API route to simulate the chat endpoint
@app.route("/chat", methods=["POST"])
def send_one_chat():
    try:
        # Get current state from request JSON
        current_state = request.json
        
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
        return jsonify(json.loads(ai_response))
    except Exception as e:
        # Return error as JSON response
        return jsonify({"error": f"Error processing chat: {str(e)}"}), 500


# Simple route for testing login functionality
@app.route("/login", methods=["POST"])
def login():
    # For demonstration purposes, we're not actually validating credentials
    # In a real app, you would validate against a database
    return jsonify({"success": True, "message": "Login successful"})


if __name__ == "__main__":
    # Ensure the static folder exists for hosting HTML
    if not os.path.exists("static"):
        os.makedirs("static")

    print("Place your HTML files in the 'static' directory.")
    print("Access the app at http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)