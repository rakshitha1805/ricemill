import os
import sys
import json
import io
import pandas as pd
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, File, UploadFile, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.predict import predict_sample
from ml.train import train_all_models
from backend.history_store import (
    get_all_history, add_history_record, delete_history_record, clear_all_history
)
from backend.ricemill_store import (
    get_all_bills, get_bill_by_id, save_or_update_bill, delete_bill,
    get_settings, save_settings, get_sample_preset_data
)
from backend.ricemill_calc import calculate_single_batch, calculate_multi_lot

app = FastAPI(
    title="Paddy & Modern Rice Mill Dynamic Billing System API",
    description="REST API for Dynamic Rice Mill Billing, Milling Charges, Labor and By-Product Accounting",
    version="2.0.0"
)

# Enable CORS for Frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PredictRequest(BaseModel):
    features: Dict[str, float]

@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "Breast Cancer Detection ML Decision-Support API",
        "disclaimer": "For Educational & Research Purposes Only. Not a Clinical Diagnosis Tool.",
        "endpoints": [
            "/api/predict",
            "/api/model-performance",
            "/api/dataset-statistics",
            "/api/train",
            "/api/history"
        ]
    }

@app.post("/api/predict")
def predict_endpoint(req: PredictRequest):
    try:
        sample_dict = req.features
        if not sample_dict:
            raise HTTPException(status_code=400, detail="Features dictionary cannot be empty.")
            
        result = predict_sample(sample_dict)
        # Store in prediction history
        add_history_record(result, sample_dict)
        return result
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=500, detail=str(fnf))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

@app.get("/api/model-performance")
def get_model_performance():
    metrics_path = "saved_models/model_metrics.json"
    if not os.path.exists(metrics_path):
        # Auto-train if metrics missing
        train_all_models()
        
    try:
        with open(metrics_path, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model metrics: {str(e)}")

@app.get("/api/dataset-statistics")
def get_dataset_statistics():
    stats_path = "saved_models/dataset_stats.json"
    if not os.path.exists(stats_path):
        train_all_models()
        
    try:
        with open(stats_path, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dataset stats: {str(e)}")

@app.post("/api/train")
async def train_models_endpoint(
    file: Optional[UploadFile] = File(None)
):
    try:
        csv_path = "ml/dataset/wdbc.csv"
        if file:
            temp_upload_path = "saved_models/custom_uploaded_dataset.csv"
            contents = await file.read()
            with open(temp_upload_path, "wb") as f:
                f.write(contents)
            csv_path = temp_upload_path
            
        results, best_name = train_all_models(csv_path=csv_path)
        return {
            "status": "success",
            "message": f"All models successfully trained! Best model: {best_name}",
            "best_model": best_name,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")

@app.get("/api/history")
def get_history(
    search: Optional[str] = Query(None),
    diagnosis: Optional[str] = Query(None)
):
    records = get_all_history()
    
    if search:
        s = search.lower()
        records = [
            r for r in records 
            if s in r["id"].lower() or s in r["prediction"].lower() or s in r["model_used"].lower()
        ]
        
    if diagnosis and diagnosis != "All":
        records = [r for r in records if r["prediction"].lower() == diagnosis.lower()]
        
    return {
        "total_records": len(records),
        "history": records
    }

@app.delete("/api/history/{record_id}")
def delete_history_item(record_id: str):
    success = delete_history_record(record_id)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"status": "success", "message": f"Record {record_id} deleted"}

@app.post("/api/history/clear")
def clear_history():
    clear_all_history()
    return {"status": "success", "message": "Prediction history cleared"}

@app.get("/api/history/export")
def export_history(format: str = Query("csv")):
    records = get_all_history()
    if not records:
        raise HTTPException(status_code=400, detail="No history records to export")
        
    if format == "json":
        json_str = json.dumps(records, indent=2)
        return StreamingResponse(
            io.BytesIO(json_str.encode("utf-8")),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=prediction_history.json"}
        )
    else: # Default CSV
        df = pd.DataFrame(records)
        if "sample_inputs" in df.columns:
            df = df.drop(columns=["sample_inputs", "top_features"], errors="ignore")
        csv_str = df.to_csv(index=False)
        return StreamingResponse(
            io.BytesIO(csv_str.encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=prediction_history.csv"}
        )

# ==============================================================================
# RICE MILL DYNAMIC BILLING & LABOR ACCOUNTING API ENDPOINTS
# ==============================================================================

class DynamicCalculateRequest(BaseModel):
    mode: str = "single_batch"  # "single_batch" or "multi_lot"
    data: Dict[str, Any]

@app.post("/api/ricemill/calculate")
def calculate_bill_endpoint(req: DynamicCalculateRequest):
    try:
        if req.mode == "multi_lot" or req.data.get("billing_mode") == "multi_lot":
            result = calculate_multi_lot(req.data)
        else:
            result = calculate_single_batch(req.data)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Calculation error: {str(e)}")

@app.get("/api/ricemill/bills")
def list_ricemill_bills(
    search: Optional[str] = Query(None),
    mode: Optional[str] = Query(None)
):
    try:
        bills = get_all_bills(search=search, mode=mode)
        return {"total": len(bills), "bills": bills}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch bills: {str(e)}")

@app.get("/api/ricemill/bills/{bill_id}")
def get_single_ricemill_bill(bill_id: int):
    bill = get_bill_by_id(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    return bill

@app.post("/api/ricemill/bills")
def save_ricemill_bill(payload: Dict[str, Any]):
    try:
        mode = payload.get("billing_mode", "single_batch")
        if mode == "multi_lot":
            calculated = calculate_multi_lot(payload)
        else:
            calculated = calculate_single_batch(payload)
            
        saved = save_or_update_bill(calculated)
        return {"status": "success", "bill": saved}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to save bill: {str(e)}")

@app.put("/api/ricemill/bills/{bill_id}")
def update_ricemill_bill(bill_id: int, payload: Dict[str, Any]):
    try:
        payload["id"] = bill_id
        mode = payload.get("billing_mode", "single_batch")
        if mode == "multi_lot":
            calculated = calculate_multi_lot(payload)
        else:
            calculated = calculate_single_batch(payload)
            
        saved = save_or_update_bill(calculated)
        return {"status": "success", "bill": saved}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update bill: {str(e)}")

@app.delete("/api/ricemill/bills/{bill_id}")
def delete_ricemill_bill(bill_id: int):
    success = delete_bill(bill_id)
    if not success:
        raise HTTPException(status_code=404, detail="Bill not found or already deleted")
    return {"status": "success", "message": f"Bill {bill_id} deleted successfully"}

@app.get("/api/ricemill/sample-data")
def get_ricemill_sample():
    return get_sample_preset_data()

@app.get("/api/ricemill/settings")
def get_ricemill_settings_endpoint():
    return get_settings()

@app.post("/api/ricemill/settings")
def update_ricemill_settings_endpoint(settings_payload: Dict[str, Any]):
    try:
        updated = save_settings(settings_payload)
        return {"status": "success", "settings": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update settings: {str(e)}")

@app.get("/api/ricemill/export/csv/{bill_id}")
def export_bill_csv(bill_id: int):
    bill = get_bill_by_id(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
        
    data = bill.get("data_json", {})
    mode = bill.get("billing_mode", "single_batch")
    
    output = io.StringIO()
    output.write(f"BILL NO,{bill.get('bill_no')},DATE,{bill.get('bill_date')}\n")
    output.write(f"PARTY,{bill.get('party_name')},LORRY NO,{bill.get('lorry_no')}\n")
    output.write(f"BATCH NO,{bill.get('batch_no')},LOT NO,{bill.get('lot_no')}\n\n")
    
    if mode == "single_batch":
        output.write("LABOR & MILLING PARTICULARS,BAGS,WEIGHT,RATE,AMOUNT\n")
        for item in data.get("labor_items", []):
            output.write(f'"{item.get("particulars")}","{item.get("bags","")}","{item.get("weight","")}","{item.get("rate","")}","{item.get("amount","")}"\n')
        output.write(f'TOTAL LABOR CHARGES,,,,"{bill.get("total_charges")}"\n\n')
        
        output.write("BY-PRODUCTS / REALIZATION,BAGS,WEIGHT,RATE,AMOUNT\n")
        for item in data.get("byproducts", []):
            output.write(f'"{item.get("particulars")}","{item.get("bags","")}","{item.get("weight","")}","{item.get("rate","")}","{item.get("amount","")}"\n')
        output.write(f'TOTAL RECOVERIES,,,,"{bill.get("total_recoveries")}"\n\n')
        output.write(f'NET AMOUNT PAYABLE,,,,"{bill.get("net_payable")}"\n')
    else:
        output.write("PADDY INWARD LOADS,LOAD NO,LORRY NO,BAGS,WEIGHT\n")
        for l in data.get("paddy_loads", []):
            output.write(f'LOAD,{l.get("load_no")},"{l.get("lorry_no")}","{l.get("bags")}","{l.get("paddy_weight")}"\n')
        output.write(f'TOTAL PADDY WEIGHT,,,,"{bill.get("total_paddy_weight")}"\n')
        output.write(f'PADDY 70KG CONVERTED BAGS,,,,"{data.get("paddy_70kg_bags")}"\n')
        output.write(f'PADDY 70KG MILLING AMOUNT,,,,"{data.get("paddy_70kg_amount")}"\n\n')
        
        output.write("PADDY LABOR,LOT NO,BAGS,RATE,AMOUNT\n")
        for p in data.get("paddy_labor", []):
            output.write(f'"{p.get("particulars")}","{p.get("lot_no")}","{p.get("bags")}","{p.get("rate")}","{p.get("amount")}"\n')
        output.write(f'PADDY LABOR TOTAL,,,,"{data.get("total_paddy_labor")}"\n\n')
        
        output.write("RICE LABOR,LOT NO,BAGS,RATE,AMOUNT\n")
        for r in data.get("rice_labor", []):
            output.write(f'"{r.get("particulars")}","{r.get("lot_no")}","{r.get("bags")}","{r.get("rate")}","{r.get("amount")}"\n')
        output.write(f'RICE LABOR TOTAL,,,,"{data.get("total_rice_labor")}"\n\n')
        output.write(f'TOTAL MILLING & LABOR CHARGES,,,,"{bill.get("total_charges")}"\n')
        bran = data.get("bran_realization", {})
        output.write(f'BRAN RECOVERY DEDUCTION,WEIGHT: {bran.get("weight")},RATE: {bran.get("rate")},,"{bill.get("total_recoveries")}"\n')
        output.write(f'NET AMOUNT PAYABLE,,,,"{bill.get("net_payable")}"\n')

    csv_bytes = output.getvalue().encode("utf-8")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=ricemill_bill_{bill.get('bill_no')}.csv"}
    )

# ==============================================================================
# PRODUCTION STATIC FRONTEND MOUNT
# ==============================================================================
from fastapi.staticfiles import StaticFiles

frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend_production")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
