import os
import re
import io
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException
from pypdf import PdfReader

# 1. Import the local AI pipeline
from transformers import pipeline

app = FastAPI(title="PhonePe AI Parser (Local Offline Edition)")

# ==========================================
# 2. Load the Model into RAM (Happens once on startup)
# ==========================================
print("🧠 Loading local AI model... (This will take a minute on the first run to download)")
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
print("✅ AI Model loaded and ready!")

# ==========================================
# 3. Category Pool & Mapping
# ==========================================
CATEGORY_POOL = ["Food and Dining", "Transport", "Utilities", "Groceries", "Shopping", "Entertainment", "Uncategorized"]

CATEGORY_ID_MAP = {
    "Food and Dining": 1,
    "Transport": 2,
    "Utilities": 3,
    "Groceries": 4,
    "Shopping": 5,
    "Entertainment": 6,
    "Uncategorized": 7
}

# ==========================================
# 4. Core Functions
# ==========================================
def classify_merchant_local(merchant: str) -> int:
    """Uses the local Hugging Face model on your machine to categorize text."""
    try:
        # This requires zero internet connection!
        result = classifier(merchant, candidate_labels=CATEGORY_POOL)
        top_category = result["labels"][0]
        return CATEGORY_ID_MAP.get(top_category, CATEGORY_ID_MAP["Uncategorized"])
    except Exception as e:
        print(f"❌ Local classification failed for '{merchant}': {str(e)}")
        return CATEGORY_ID_MAP["Uncategorized"]

def extract_phonepe_data(text: str) -> List[Dict[str, Any]]:
    """Extracts raw transaction details using Regex."""
    dates = re.findall(r"([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})", text)
    times = re.findall(r"(\d{1,2}:\d{2}\s+(?:am|pm))", text.lower())
    merchants = re.findall(r"(?:Paid to|Payment to)\s+([^\r\n\"]+)", text)
    tx_ids = re.findall(r"Transaction ID\s+([A-Z0-9]+)", text)
    
    amounts_raw = re.findall(r"(?:Rs\.|₹)\s*([\d,]+(?:\.\d{2})?)", text)
    amounts = [float(amt.replace(",", "")) for amt in amounts_raw]

    parsed_transactions = []
    for i in range(len(tx_ids)):
        try:
            merchant = merchants[i].strip() if i < len(merchants) else "Unknown Vendor"
            amount = amounts[i] if i < len(amounts) else 0.0
            date_part = dates[i] if i < len(dates) else datetime.now().strftime("%b %d, %Y")
            time_part = times[i] if i < len(times) else "12:00 am"
            tx_id = tx_ids[i]
            
            try:
                datetime_obj = datetime.strptime(f"{date_part} {time_part.upper()}", "%b %d, %Y %I:%M %p")
                iso_timestamp = datetime_obj.isoformat()
            except ValueError:
                iso_timestamp = datetime.now().isoformat()

            parsed_transactions.append({
                "note": f"{merchant} (Txn: {tx_id})",
                "raw_merchant": merchant, 
                "amount": amount,
                "timestamp": iso_timestamp
            })
        except IndexError:
            continue
    return parsed_transactions

# ==========================================
# 5. FastAPI Routes
# ==========================================
@app.post("/parser/process")
async def process_statement(file: UploadFile = File(...)):
    """Receives a PDF, parses it, categorizes it locally, and returns JSON."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF.")

    try:
        pdf_content = await file.read()
        reader = PdfReader(io.BytesIO(pdf_content))
        
        full_text = "".join(page.extract_text() + "\n" for page in reader.pages if page.extract_text())
        expenses = extract_phonepe_data(full_text)
        
        if not expenses:
            return {"status": "success", "data": [], "message": "No debit transactions found."}

        # Look how much simpler this is! No async httpx, no semaphores, no rate limits.
        final_payload = []
        for expense in expenses:
            category_id = classify_merchant_local(expense["raw_merchant"])
            
            final_payload.append({
                "categoryId": category_id, 
                "categoryName": list(CATEGORY_ID_MAP.keys())[list(CATEGORY_ID_MAP.values()).index(category_id)],
                "note": expense["note"],
                "amount": expense["amount"],
                "timestamp": expense["timestamp"]
            })
                    
        return {
            "status": "success",
            "total_extracted": len(final_payload),
            "data": final_payload
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Engine Exception: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)