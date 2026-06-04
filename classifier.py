from transformers import pipeline
from config import CATEGORY_POOL, CATEGORY_ID_MAP

print("🧠 Loading local AI model...")
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
print("✅ AI Model loaded and ready!")

def classify_merchant_local(merchant: str) -> int:
    try:
        result = classifier(merchant, candidate_labels=CATEGORY_POOL)
        top_category = result["labels"][0]
        return CATEGORY_ID_MAP.get(top_category, CATEGORY_ID_MAP.get("Uncategorized", 7))
    except Exception as e:
        print(f"❌ Local classification failed for '{merchant}': {str(e)}")
        return CATEGORY_ID_MAP.get("Uncategorized", 7)