from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
#from google.generativeai import GeneratateContentConfig
import pymongo
import google.generativeai as genai
import json
import os
from google import genai
from google.genai.types import (
    FunctionDeclaration,
    GenerateContentConfig,
    GoogleSearch,
    Part,
    Retrieval,
    SafetySetting,
    Tool,
    VertexAISearch,
)


# Helper Function to Load Configurations
def load_config():
    """Load API keys and other configurations from config.json."""
    config_path = "config.json"
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"{config_path} not found. Please create the file with the necessary configurations.")
    with open(config_path, "r") as file:
        return json.load(file)

PROJECT_ID = "531529171491"
MODEL_ID = "gemini-2.0-flash"
# Load configuration from config.json
config = load_config()

# MongoDB setup
MONGO_URI = config.get("MONGO_URI", "mongodb://localhost:27017/")
LOCATION = "us-central-1"
client = pymongo.MongoClient(MONGO_URI)
db = client["budgeting_db"]
collection = db["budget_data"]

# Google Generative AI setup
GENAI_API_KEY = config.get("GENAI_API_KEY", config["GEMINI_API_KEY"])
#genai.configure(api_key=GENAI_API_KEY)
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
# FastAPI app
app = FastAPI()

# Pydantic Models
class BudgetItem(BaseModel):
    item_name: str
    amount: float
    category: str
    importance_rank: int
    recurrence_schedule: Optional[str] = None
    due_date: Optional[int] = None


class Budget(BaseModel):
    budget_limit: float
    items: List[BudgetItem]
    warnings: List[str] = []
    conversations: List[str] = []


class BudgetRequest(BaseModel):
    Budget: Budget
    conversation: str


class GeminiResponse(BaseModel):
    Budget: Budget
    conversation: str


# Helper Function to Generate Prompt
def generate_prompt(previous_budget: dict, user_input: str):
    """
    Create a prompt for Google Generative AI based on the previous budget and user input.
    """
    return f"""
You are an intelligent budgeting assistant. Your tasks are:
1. Start with the user's existing budget data:
{json.dumps(previous_budget, indent=2).replace('{', '{{').replace('}', '}}')}
    1.1 Make sure to properly transfer over the conversation data. This is crucial. The conversation key must be present in every JSON return.
    1.2 Make sure to also properly transfer over the other data as well.
2. Allow the user to append, delete, or update individual items in the budget. Reflect this in the JSON response.
3. If the total value of the items exceeds the budget limit, add a warning in the 'warnings' field explaining how much over budget they are.
4. When the user inquires about adding a new item, calculate whether the new item would put them over their budget. If it does, include a warning in the response.
5. Always provide the JSON structure as output.
6. Engage in conversation with the user by providing clear, friendly, and helpful responses alongside the JSON data. 
    6.1 Append the previous chats to the array called conversations. The most recent chat is to be put into the standalone conversation field
7. At the end of each chat, make sure to ask the user how else you can help them (within the scope of your duties). This is also part of what is to be added to "conversations".
8. Always factor in one-time purchases to the budget as well, as the budget is always set for the current month. 
9. Make sure to relate any open-ended questions to the budget. 
10. Try to give relevant examples of alternatives for potential items that may place the user outside of the budget. 
    10.1 If the expense is rather important (the expense is a necessary one to maintain the quality of a modern person's life), give suggestions on what expenses to remove based on order of least importance.
11. Make sure to follow the parsing format for items in this way: ( "item_name": "Groceries","amount": 300.0, "category": "Regular", "importance_rank": 2, "recurrence_schedule": "weekly", "due_date": null)

User input: {user_input}
"""


def send_to_google_generativeai(previous_budget: dict, user_input: str) -> dict:
    """
    Send the generated prompt to Google Generative AI using the `generate_text` method and return its response.
    """
    
    try:
        prompt = generate_prompt(previous_budget, user_input)
        response = client.models.generate_content(contents=prompt,model = MODEL_ID,config=GenerateContentConfig(
                temperature=0.4,
                top_p=0.95,
                top_k=20,
                candidate_count=1,
                response_mime_type="application/json",
                response_schema=BudgetRequest,
                #seed=5,
                #max_output_tokens=100,
                stop_sequences=["STOP!"],
                presence_penalty=0.0,
                frequency_penalty=0.0,)
    ,)
        print(f"Response:{response}")
        if not response or not response.candidates:
            raise HTTPException(status_code=500, detail="No response from Google Generative AI.")

        # Extract the first candidate's output
        generated_text = response
        print(response.text)
        # Parse the response (assuming the AI returns JSON in the text)
        result = json.loads(generated_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error communicating with Google Generative AI: {e}")


# API Routes
@app.post("/budget", response_model=GeminiResponse)
def process_budget(request: BudgetRequest):
    """
    Process a budget request by storing it in the database,
    sending it to Google Generative AI, and returning the response.
    """
    # Save to MongoDB
    collection.insert_one(request.dict())

    # Send to Google Generative AI
    google_response = send_to_google_generativeai(request.Budget.dict(), request.conversation)
    return google_response


if __name__ == "__main__":
    import sys

    def main_console():
        """Console application for interacting with the budgeting assistant."""
        print("Welcome to the Budgeting Assistant Console")
        # Load previous budget or start with a new one
        previous_budget = {
            "budget_limit": 2000,
            "items": [],
            "warnings": [],
            "conversations": []
        }

        while True:
            print(f"\nCurrent Budget: {json.dumps(previous_budget, indent=2)}")
            user_input = input("Enter your input (e.g., add an expense, update an item, etc.): ")

            try:
                # Send input to Google Generative AI
                response = send_to_google_generativeai(previous_budget, user_input)
                previous_budget = response["Budget"]
                print("\nResponse from Budgeting Assistant:")
                print(json.dumps(response, indent=2))
            except Exception as e:
                print(f"Error: {e}")

            # Continue or Exit
            cont = input("\nDo you want to continue? (yes/no): ").strip().lower()
            if cont != "yes":
                break

    # Determine mode of operation
    if 1==1:#len(sys.argv) > 1 and sys.argv[1] == "console":
        main_console()
    else:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
