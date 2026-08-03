import io
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="PhonePe AI Parser (Production Edition)")
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
async def process_statement(file: UploadFile = File(...)):
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
        # Distinct from "no transactions found": we couldn't read any text at
        # all, which usually means a scanned/image-only PDF rather than a
        # statement that's genuinely empty of debits.
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

            # 2. Try pre-processor rules first
            category_id = pre_process_merchant(raw_name)

            # 3. Fallback to AI classifier
            if category_id is None:
                category_id = classify_merchant_local(raw_name)

            # Get the category name by its ID
            category_name = CATEGORY_NAME_BY_ID.get(category_id, "Uncategorized")

            final_payload.append({
                "categoryId": category_id,
                "categoryName": category_name,
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
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))