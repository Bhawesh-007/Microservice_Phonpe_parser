from config import CATEGORY_POOL, CATEGORY_ID_MAP

# The zero-shot model (~400MB) is only loaded on first actual use, not at
# module import time. This is the tier-3 fallback - most requests never
# reach it (tiers 1/2 in pre_processor.py resolve first) - so importing this
# module, or even starting the whole app, no longer pays the load cost
# up front (e.g. on every uvicorn --reload).
_classifier = None


def _get_classifier():
    global _classifier
    if _classifier is None:
        from transformers import pipeline
        print("Loading local AI model (facebook/bart-large-mnli)...")
        _classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
        print("AI model loaded and ready.")
    return _classifier


def classify_merchant_local(merchant: str) -> int:
    try:
        clf = _get_classifier()
        result = clf(merchant, candidate_labels=CATEGORY_POOL)
        top_category = result["labels"][0]
        return CATEGORY_ID_MAP.get(top_category, CATEGORY_ID_MAP.get("Uncategorized", 7))
    except Exception as e:
        print(f"Local classification failed for '{merchant}': {str(e)}")
        return CATEGORY_ID_MAP.get("Uncategorized", 7)
