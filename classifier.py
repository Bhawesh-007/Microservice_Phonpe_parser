import os
import json
from groq import Groq
from dotenv import load_dotenv
from config import STANDARD_CATEGORIES

load_dotenv()

api_key = os.environ.get("GROK_API_KEY")
if not api_key:
    print("Warning: GROK_API_KEY environment variable is not set!")

client = Groq(api_key=api_key)

# Using qwen3.8-27b — available on this account, fast and accurate for classification
GROQ_MODEL = "qwen/qwen3.8-27b"

FEW_SHOT_EXAMPLES = """Examples:
- "SWIGGY" → "Food and Dining"
- "UBER" → "Transport"
- "NETFLIX" → "Entertainment"
- "APOLLO PHARMACY" → "Health and Medical"
- "BYJU'S" → "Education"
- "HDFC BANK CHARGES" → "Uncategorized"
- "RAHUL SHARMA" → "Personal Transfer"
- "AMAZON" → "Shopping"
- "DMART" → "Groceries"
- "JIO RECHARGE" → "Utilities"
"""


def classify_merchant_local(merchant: str) -> str:
    """
    Classifies a single merchant name using Groq's LLM API.
    Returns one of the STANDARD_CATEGORIES strings.
    """
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a financial categorization AI for an Indian expense tracker. "
                        f"Your ONLY job is to classify merchant names into one of these categories: "
                        f"{', '.join(STANDARD_CATEGORIES)}.\n\n"
                        f"{FEW_SHOT_EXAMPLES}"
                        f"Rules:\n"
                        f"1. Reply with ONLY the exact category name. No punctuation, no explanation.\n"
                        f"2. If unsure, reply with 'Uncategorized'."
                    )
                },
                {
                    "role": "user",
                    "content": f"Merchant: {merchant}"
                }
            ],
            temperature=0.0,
            max_tokens=10,       # Category names are short — no need for more tokens
        )

        predicted = response.choices[0].message.content.strip()

        # Validate the response is one of our allowed categories
        if predicted in STANDARD_CATEGORIES:
            return predicted
        return "Uncategorized"

    except Exception as e:
        print(f"Groq classification failed for '{merchant}': {str(e)}")
        return "Uncategorized"
