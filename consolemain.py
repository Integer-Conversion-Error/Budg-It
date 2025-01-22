import os
import json
import google.generativeai as genai


def load_config():
    """
    Load API keys and other configurations from config.json.
    """
    config_path = "config.json"
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"{config_path} not found. Please create the file with the necessary configurations.")
    with open(config_path, "r") as file:
        return json.load(file)

flattenedSchema = {
  "title": "BudgetRequest",
  "type": "object",
  "properties": {
    "Budget": {
      "title": "Budget",
      "type": "object",
      "properties": {
        "budget_limit": {
          "type": "number"
        },
        "items": {
          "title": "items",
          "type": "array",
          "items": {
            "title": "BudgetItem",
            "type": "object",
            "properties": {
              "item_name": {
                "type": "string"
              },
              "amount": {
                "type": "number"
              },
              "category": {
                "type": "string"
              },
              "importance_rank": {
                "type": "integer"
              },
              "recurrence_schedule": {
                "type": ["string", "null"]
              },
              "due_date": {
                "type": ["number", "null"]
              }
            },
            "required": [
              "item_name",
              "amount",
              "category",
              "importance_rank"
            ]
          }
        },
        "warnings": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "conversations": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      },
      "required": [
        "budget_limit",
        "items",
        "warnings",
        "conversations"
      ]
    },
    "conversation": {
      "type": "string"
    }
  },
  "required": [
    "Budget",
    "conversation"
  ]
}


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
        1.3 The data structure is concretely defined in here. Do not stray from this: {flattenedSchema}
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
    12. If there is no user input, assume it is the beginning input. 
    13. Encourage prudent financial practices.

        13.1 Emergency Fund: Emphasize the importance of saving at least three to six months’ worth of expenses in an accessible emergency fund. If the user’s budget does not currently allocate funds for emergencies, consider prompting them to add a line item to gradually build this reserve.
        13.2 Savings Goals: If the user has upcoming expenses—like a vacation or a major purchase—encourage them to set incremental saving targets. Suggest adding these goals as budget items with a monthly amount, even if small.
        13.3 Debt Reduction: If the user mentions debts, guide them to prioritize paying off high-interest debts first. Encourage them to allocate an item specifically for extra debt payments if room exists in the budget.

    14. Include caution around fees and interest rates.

        14.1 Credit Card Fees: If the user wants to purchase an item on credit, remind them that interest charges or annual fees can eat into their budget. Ask whether they’re accounting for those additional costs.
        14.2 Loan Interest: If they mention financing or personal loans, prompt them to consider total interest over time. They might need to budget for monthly or weekly payments, including interest.
        14.3 Banking/Overdraft Fees: Suggest tracking any recurring banking fees, overdraft fees, or other finance charges, so they’re reflected in the budget items.

    15. Offer disclaimers.

        15.1 Scope of Advice: Clarify that you provide general budgeting guidance, not personalized or certified financial or investment advice.
        15.2 Professional Consultations: If the user is dealing with large sums, complex investments, or major life changes (like a home purchase), gently recommend consulting a professional (e.g., a certified financial planner or accountant).
        15.3 Accuracy & Assumptions: Note that all advice is based on the current information provided; if key data changes, the user’s financial strategy may need to be updated.

    16. Consider best-practice budgeting guidelines (e.g., 50/30/20 rule).

        16.1 Overview: Explain common budgeting frameworks, such as spending 50% of take-home pay on needs (housing, food, utilities), 30% on wants (entertainment, dining out), and 20% on savings or debt reduction.
        16.2 Customization: Remind the user that these rules are guidelines, not absolutes. Encourage them to adapt percentages to their lifestyle or region’s cost of living.
        16.3 Practical Steps: If the user wants to adopt such a rule, help them categorize expenses into “needs” vs. “wants” vs. “savings” and track whether each category stays within its recommended percentage of the total budget.

    17. When discussing adjustments or trade-offs.

        17.1 Prioritizing Items: When the user’s expenses surpass the budget limit, help them identify optional vs. essential expenses. Suggest cutting back on discretionary items first.
        17.2 Opportunity Costs: Emphasize that every increase in one budget item may require a decrease elsewhere. Guide the user on how to shift funds from lower-priority to higher-priority areas.
        17.3 Long-Term Impact: If the user removes or reduces items, prompt them to consider how that change affects future months (e.g., deferring maintenance on a car could lead to higher costs later).
        17.4 Alternatives & Creative Solutions: Offer suggestions for cheaper alternatives (e.g., “Instead of eating out 4 times a week, reduce it to 2 times, and use the savings toward your credit card debt.”).
    User input: {user_input}
    """


def configure_genai():
    """
    Configure the generative AI model with API key and settings.
    """
    config = load_config()
    genai.configure(api_key=config["GEMINI_API_KEY"])

    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        #"max_output_tokens": 8192 * 64,
        "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config=generation_config,
    )
    return model


def initialize_chat(model, current_budget):
    """
    Initialize a chat session with the generative model.
    """
    chat_session = model.start_chat(
        history=[
            {
                "role": "user",
                "parts": [{"text": f"System prompt: {generate_prompt(current_budget, '')} Respond understood if you got it."}],
            },
            {
                "role": "model",
                "parts": [{"text": "Understood."}],
            },
        ]
    )
    return chat_session


def chat_with_user(chat_session, current_budget):
    """
    Interact with the user in a chat loop.
    """
    print(chat_session.last)

    response = chat_session.send_message(generate_prompt(current_budget, input("Enter budget info: ")))
    print(response.text)

    while True:
        try:
            user_input = input(json.loads(response.text)["conversation"] + " ")
            response = chat_session.send_message(generate_prompt(current_budget, user_input))
            print(response.text)
        except KeyboardInterrupt:
            print("\nExiting chat. Goodbye!")
            break


def main():
    """
    Main function to execute the budgeting assistant.
    """
    # Load and configure generative AI
    model = configure_genai()

    # Initial budget structure
    current_budget = {
        "Budget": {
            "budget_limit": 0.0,
            "items": [],
            "warnings": []
        }
    }

    # Start chat session
    chat_session = initialize_chat(model, current_budget)

    # Enter the chat loop
    chat_with_user(chat_session, current_budget)


if __name__ == "__main__":
    main()
