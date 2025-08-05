import os
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import tempfile

# Load environment variables
load_dotenv()

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'havn_cube_db')

if MONGO_URL:
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    estimates_collection = db.estimates
    clients_collection = db.clients
else:
    print("Warning: MONGO_URL not set")
    client = None
    db = None
    estimates_collection = None
    clients_collection = None

# Pydantic models
class LineItem(BaseModel):
    id: str = ""
    particulars: str
    length_feet: Optional[int] = 0
    length_inches: Optional[int] = 0
    width_feet: Optional[int] = 0
    width_inches: Optional[int] = 0
    quantity: float = 0
    unit: str = "SQFT"  # SQFT or NOS
    rate: float = 0
    amount: float = 0

class EstimateRequest(BaseModel):
    client_name: str
    client_address: str = ""
    client_phone: str = ""
    estimate_number: str = ""
    date: str = ""
    line_items: List[LineItem]
    tax_rate: float = 18.0
    subtotal: float = 0
    tax_amount: float = 0
    total_amount: float = 0

class EstimateResponse(BaseModel):
    id: str
    client_name: str
    client_address: str
    client_phone: str
    estimate_number: str
    date: str
    line_items: List[LineItem]
    tax_rate: float
    subtotal: float
    tax_amount: float
    total_amount: float
    created_at: datetime
    updated_at: datetime

@app.get("/")
async def root():
    return {"message": "Havn Cube Billing & Estimation API"}

@app.get("/api/health")
async def health():
    return {"status": "healthy", "database": "connected" if db else "disconnected"}

@app.post("/api/estimates", response_model=EstimateResponse)
async def create_estimate(estimate: EstimateRequest):
    if estimates_collection is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    # Generate ID and timestamps
    estimate_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Generate estimate number if not provided
    if not estimate.estimate_number:
        count = await estimates_collection.count_documents({})
        estimate.estimate_number = f"HCE-{count + 1:04d}"
    
    # Add IDs to line items
    for item in estimate.line_items:
        if not item.id:
            item.id = str(uuid.uuid4())
    
    estimate_data = {
        "id": estimate_id,
        **estimate.model_dump(),
        "created_at": now,
        "updated_at": now
    }
    
    await estimates_collection.insert_one(estimate_data)
    
    return EstimateResponse(**estimate_data)

@app.get("/api/estimates", response_model=List[EstimateResponse])
async def get_estimates():
    if estimates_collection is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    estimates = []
    async for estimate in estimates_collection.find().sort("created_at", -1):
        estimates.append(EstimateResponse(**estimate))
    
    return estimates

@app.get("/api/estimates/{estimate_id}", response_model=EstimateResponse)
async def get_estimate(estimate_id: str):
    if not estimates_collection:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    estimate = await estimates_collection.find_one({"id": estimate_id})
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    return EstimateResponse(**estimate)

@app.put("/api/estimates/{estimate_id}", response_model=EstimateResponse)
async def update_estimate(estimate_id: str, estimate: EstimateRequest):
    if not estimates_collection:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    existing = await estimates_collection.find_one({"id": estimate_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    # Add IDs to line items if missing
    for item in estimate.line_items:
        if not item.id:
            item.id = str(uuid.uuid4())
    
    update_data = {
        **estimate.model_dump(),
        "updated_at": datetime.utcnow()
    }
    
    await estimates_collection.update_one(
        {"id": estimate_id},
        {"$set": update_data}
    )
    
    updated_estimate = await estimates_collection.find_one({"id": estimate_id})
    return EstimateResponse(**updated_estimate)

@app.delete("/api/estimates/{estimate_id}")
async def delete_estimate(estimate_id: str):
    if not estimates_collection:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    result = await estimates_collection.delete_one({"id": estimate_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    return {"message": "Estimate deleted successfully"}

@app.post("/api/estimates/{estimate_id}/pdf")
async def generate_pdf(estimate_id: str):
    if not estimates_collection:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    estimate = await estimates_collection.find_one({"id": estimate_id})
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    # Create temporary PDF file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    
    try:
        # Create PDF document
        doc = SimpleDocTemplate(temp_file.name, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#1a365d'),
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        company_style = ParagraphStyle(
            'CompanyStyle',
            parent=styles['Normal'],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=10
        )
        
        # Header
        story.append(Paragraph("HAVN CUBE", title_style))
        story.append(Paragraph("Interior Design & Execution", company_style))
        story.append(Paragraph("Contact: +91-XXXXXXXXXX | Email: info@havncube.com", company_style))
        story.append(Spacer(1, 20))
        
        # Estimate details
        estimate_info = [
            [f"Estimate No: {estimate.get('estimate_number', '')}", f"Date: {estimate.get('date', '')}"],
            [f"Client: {estimate.get('client_name', '')}", ""],
            [f"Address: {estimate.get('client_address', '')}", ""],
            [f"Phone: {estimate.get('client_phone', '')}", ""]
        ]
        
        info_table = Table(estimate_info, colWidths=[3*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        # Line items table
        table_data = [['Sn', 'Particulars', 'Qty', 'Unit', 'Rate (₹)', 'Amount (₹)']]
        
        for i, item in enumerate(estimate.get('line_items', []), 1):
            qty_display = item.get('quantity', 0)
            if item.get('unit') == 'SQFT' and item.get('length_feet', 0) > 0:
                length = item.get('length_feet', 0) + (item.get('length_inches', 0) / 12)
                width = item.get('width_feet', 0) + (item.get('width_inches', 0) / 12)
                qty_display = round(length * width, 2)
            
            table_data.append([
                str(i),
                item.get('particulars', ''),
                f"{qty_display:.2f}",
                item.get('unit', ''),
                f"₹{item.get('rate', 0):,.2f}",
                f"₹{item.get('amount', 0):,.2f}"
            ])
        
        # Add subtotal, tax, and total
        subtotal = estimate.get('subtotal', 0)
        tax_amount = estimate.get('tax_amount', 0)
        total = estimate.get('total_amount', 0)
        
        table_data.extend([
            ['', '', '', '', 'Subtotal:', f"₹{subtotal:,.2f}"],
            ['', '', '', '', f"Tax ({estimate.get('tax_rate', 18)}%):", f"₹{tax_amount:,.2f}"],
            ['', '', '', '', 'Total:', f"₹{total:,.2f}"]
        ])
        
        # Create table
        main_table = Table(table_data, colWidths=[0.5*inch, 3*inch, 1*inch, 0.8*inch, 1.2*inch, 1.5*inch])
        main_table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Data styling
            ('FONTNAME', (0, 1), (-1, -4), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -4), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -4), [colors.white, colors.HexColor('#f7fafc')]),
            ('GRID', (0, 0), (-1, -4), 1, colors.black),
            
            # Totals styling
            ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -3), (-1, -1), 10),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#edf2f7')),
            ('GRID', (0, -3), (-1, -1), 1, colors.black),
            
            # Alignment
            ('ALIGN', (1, 1), (1, -4), 'LEFT'),  # Particulars left aligned
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),  # Numbers right aligned
        ]))
        
        story.append(main_table)
        story.append(Spacer(1, 30))
        
        # Footer
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.grey
        )
        
        story.append(Paragraph("Thank you for choosing Havn Cube!", footer_style))
        story.append(Paragraph("This estimate is valid for 30 days.", footer_style))
        
        # Build PDF
        doc.build(story)
        
        return FileResponse(
            temp_file.name,
            media_type='application/pdf',
            filename=f"Estimate_{estimate.get('estimate_number', estimate_id)}.pdf"
        )
        
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)