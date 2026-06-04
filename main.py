import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from pypdf import PdfReader
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import requests


# Import from your new custom modules
from config import CATEGORY_ID_MAP
from pre_processor import extract_phonepe_data, pre_process_merchant
from classifier import classify_merchant_local

app = FastAPI(title="PhonePe AI Parser (Production Edition)")
templates = Jinja2Templates(directory="templates")
@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request, userId: str = None):
    # Renders the HTML page and passes the userId into the frontend
    return templates.TemplateResponse(request=request, name="index.html", context={"userId": userId})
@app.post("/parser/process")
async def process_statement(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF.")

    try:
        pdf_content = await file.read()
        reader = PdfReader(io.BytesIO(pdf_content))
        
        full_text = "".join(page.extract_text() + "\n" for page in reader.pages if page.extract_text())
        
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
            category_name = list(CATEGORY_ID_MAP.keys())[list(CATEGORY_ID_MAP.values()).index(category_id)]
            
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
    uvicorn.run(app, host="127.0.0.1", port=8000)