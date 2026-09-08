import re
from datetime import datetime
from typing import List, Dict, Any
from config import KNOWN_MERCHANTS, CATEGORY_ID_MAP

def pre_process_merchant(merchant: str) -> str:
    merchant_upper = merchant.upper()
    
    # Tier 1: Dictionary Match
    for key, cat_id in KNOWN_MERCHANTS.items():
        if re.search(rf"\b{re.escape(key)}\b", merchant_upper):
            # Return the string name from the static map as fallback, or the ID if we don't have it
            from config import CATEGORY_NAME_BY_ID
            return CATEGORY_NAME_BY_ID.get(cat_id, "Uncategorized")
            
    return None  # Proceed to AI (Groq)

def extract_phonepe_data(text: str) -> List[Dict[str, Any]]:
    """
    Extracts debit transactions from a PhonePe statement PDF text.

    Strategy: locate every Transaction ID, then search ONLY the surrounding
    block of text for that transaction's date, time, merchant, amount, and
    type.  This avoids the index-desync bug that occurred when 5 independent
    regex lists were zipped together and credits were skipped mid-list.
    """

    # Split text into per-transaction blocks on "Transaction ID"
    blocks = re.split(r"(?=Transaction ID\s+[A-Z0-9]+)", text)

    parsed_transactions = []

    for block in blocks:
        # Must have a Transaction ID to be a valid block
        tx_match = re.search(r"Transaction ID\s+([A-Z0-9]+)", block)
        if not tx_match:
            continue
        tx_id = tx_match.group(1)

        # Skip credited transactions
        type_match = re.search(r"\b(DEBIT|CREDIT)\b", block, re.IGNORECASE)
        if type_match and type_match.group(1).upper() == "CREDIT":
            continue

        # Merchant name
        merchant_match = re.search(r"(?:Paid to|Payment to)\s+([^\r\n\"]+)", block)
        merchant = merchant_match.group(1).strip() if merchant_match else "Unknown Vendor"

        # Amount  (first Rs./₹ figure in this block)
        amount_match = re.search(r"(?:Rs\.|\u20b9)\s*([\d,]+(?:\.\d{2})?)", block)
        amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0.0

        # Date
        date_match = re.search(r"([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})", block)
        date_part = date_match.group(1) if date_match else datetime.now().strftime("%b %d, %Y")

        # Time
        time_match = re.search(r"(\d{1,2}:\d{2}\s+(?:am|pm))", block, re.IGNORECASE)
        time_part = time_match.group(1) if time_match else "12:00 am"

        try:
            datetime_obj  = datetime.strptime(f"{date_part} {time_part.upper()}", "%b %d, %Y %I:%M %p")
            iso_timestamp = datetime_obj.isoformat()
        except ValueError:
            iso_timestamp = datetime.now().isoformat()

        parsed_transactions.append({
            "note":         f"{merchant} (Txn: {tx_id})",
            "raw_merchant": merchant,
            "amount":       amount,
            "timestamp":    iso_timestamp,
            "tx_type":      "DEBIT",
        })

    return parsed_transactions
