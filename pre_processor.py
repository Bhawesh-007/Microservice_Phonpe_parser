import re
from datetime import datetime
from typing import List, Dict, Any
from config import KNOWN_MERCHANTS, CATEGORY_ID_MAP

def pre_process_merchant(merchant: str) -> int:
    merchant_upper = merchant.upper()
    
    # Tier 1: Dictionary Match
    # Word-boundary match rather than plain substring: a naive `key in merchant_upper`
    # check lets short keys like "VI" (Vodafone-Idea) false-positive on any merchant
    # that merely contains "VI" as a substring (e.g. "DEVI STORES", "NAVIN KUMAR").
    for key, cat_id in KNOWN_MERCHANTS.items():
        if re.search(rf"\b{re.escape(key)}\b", merchant_upper):
            return cat_id
            
    # Tier 2: Heuristic Personal Name Check
    business_suffixes = ["LTD", "PVT", "ENTERPRISE", "INFOCOMM", "STORE", "MART", "CAFE", "UNIVERSITY", "UPOS", "COMMUNICATION"]
    
    if not any(biz in merchant_upper for biz in business_suffixes):
        if len(merchant_upper.split()) <= 3:
            return CATEGORY_ID_MAP.get("Personal Transfer", 8)
            
    return None # Proceed to AI

def extract_phonepe_data(text: str) -> List[Dict[str, Any]]:
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