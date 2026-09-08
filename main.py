import io
import os
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
from pypdf.errors import PyPdfError
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles


# Import from your new custom modules
from config import CATEGORY_ID_MAP, CATEGORY_NAME_BY_ID
from pre_processor import extract_phonepe_data, pre_process_merchant
from classifier import classify_merchant_local
from merchant_cache_client import lookup_merchant_cache, save_merchant_cache




BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="PhonePe AI Parser (Production Edition)")

# Allow the React frontend to call this service from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to your frontend URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request, userId: str = None):
    # Renders the HTML page and passes the userId into the frontend
    return templates.TemplateResponse(
        request = request,
        name = "index.html",
        context = {
            "userId": userId,
            "categories" : CATEGORY_ID_MAP,
        }
    )
@app.post("/parser/process")
async def process_statement(
    file: UploadFile = File(...),
    userId: int = None,   # Passed by Spring Boot so we can do per-user cache lookup
):
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF.")

    try:
        pdf_content = await file.read()
        reader = PdfReader(io.BytesIO(pdf_content))
    except PyPdfError as e:
        raise HTTPException(status_code=400, detail=f"Invalid or corrupted PDF file: {str(e)}")

    page_texts = [text for page in reader.pages if (text := page.extract_text())]
    full_text = "".join(text + "\n" for text in page_texts)

    if not full_text.strip():
        
        raise HTTPException(
            status_code=422,
            detail="Could not extract any text from the PDF. It may be a scanned or image-based document."
        )

    try:
        # 1. Extract data
        expenses = extract_phonepe_data(full_text)

        if not expenses:
            return {"status": "success", "data": [], "message": "No debit transactions found."}

        final_payload = []
        for expense in expenses:
            raw_name = expense["raw_merchant"]

            # ── Tier 0A: Redis cache (fastest — sub-millisecond) ──────────────────
            # ── Tier 0B: Spring Boot DB (persistent backup, warms Redis on hit) ──
            category_name = lookup_merchant_cache(userId, raw_name)
            if category_name:
                print(f"[Cache HIT]  '{raw_name}' → '{category_name}'")

            # ── Tier 1: known_merchants.json static dictionary ────────────────────
            if category_name is None:
                category_name = pre_process_merchant(raw_name)
                if category_name:
                    print(f"[Dict HIT]   '{raw_name}' → '{category_name}'")

            # ── Tier 2: Groq AI classifier ────────────────────────────────────────
            if category_name is None:
                print(f"[Groq]       Classifying '{raw_name}'...")
                category_name = classify_merchant_local(raw_name)
                # Save newly learned merchant to Redis + Spring Boot for next time
                if userId and category_name and category_name != "Uncategorized":
                    save_merchant_cache(userId, raw_name, category_name)
                    print(f"[Cache SAVE] '{raw_name}' → '{category_name}'")

            final_payload.append({
                "categoryId":   0,  # Spring Boot resolves by categoryName, not id
                "categoryName": category_name,
                "merchantName": raw_name,   # Needed so approve endpoint can update cache
                "note":         expense["note"],
                "amount":       expense["amount"],
                "timestamp":    expense["timestamp"]
            })

        return {
            "status": "success",
            "total_extracted": len(final_payload),
            "data": final_payload
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Engine Exception: {str(e)}")

# ── Approve endpoint ─────────────────────────────────────────────────────────
class ApprovedTransaction(BaseModel):
    merchantName: str
    categoryName: str

class ApproveRequest(BaseModel):
    userId: int | None = None
    transactions: List[ApprovedTransaction]

@app.post("/parser/approve")
async def approve_transactions(body: ApproveRequest):
    """
    Called by the frontend when the user clicks 'Approve & Download JSON'.
    Saves every confirmed merchant → category mapping into Redis + Spring Boot
    cache so future uploads never need to call Groq for the same merchant.
    """
    if not body.userId:
        return {"status": "skipped", "message": "No userId provided — cache not updated."}

    saved = 0
    for txn in body.transactions:
        merchant = txn.merchantName.strip()
        category = txn.categoryName.strip()
        if merchant and category and category != "Uncategorized":
            save_merchant_cache(body.userId, merchant, category)
            print(f"[Approve] Saved '{merchant}' → '{category}' for user {body.userId}")
            saved += 1

    return {"status": "success", "saved": saved}


if __name__ == "__main__":
    # pyrefly: ignore [missing-import]
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))