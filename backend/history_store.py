import os
import json
from datetime import datetime
import uuid

HISTORY_FILE = "saved_models/prediction_history.json"

def get_all_history():
    if not os.path.exists(HISTORY_FILE):
        # Initialize with sample demonstration records
        sample_records = [
            {
                "id": "CASE-1001",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "prediction": "Malignant",
                "is_malignant": True,
                "confidence": 96.4,
                "benign_prob": 3.6,
                "malignant_prob": 96.4,
                "model_used": "Logistic Regression",
                "features_summary": "Radius: 17.99, Texture: 10.38, Perimeter: 122.8",
                "sample_inputs": {"mean radius": 17.99, "mean texture": 10.38, "mean perimeter": 122.8, "mean area": 1001.0}
            },
            {
                "id": "CASE-1002",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "prediction": "Benign",
                "is_malignant": False,
                "confidence": 98.2,
                "benign_prob": 98.2,
                "malignant_prob": 1.8,
                "model_used": "Logistic Regression",
                "features_summary": "Radius: 13.54, Texture: 14.36, Perimeter: 87.46",
                "sample_inputs": {"mean radius": 13.54, "mean texture": 14.36, "mean perimeter": 87.46, "mean area": 566.3}
            }
        ]
        save_history(sample_records)
        return sample_records
        
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_history(records):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(records, f, indent=2)

def add_history_record(pred_result, sample_inputs):
    records = get_all_history()
    case_id = f"CASE-{1000 + len(records) + 1}"
    
    # Format summary string of main 3 features
    r_val = sample_inputs.get("mean radius", sample_inputs.get("radius", "N/A"))
    t_val = sample_inputs.get("mean texture", sample_inputs.get("texture", "N/A"))
    p_val = sample_inputs.get("mean perimeter", sample_inputs.get("perimeter", "N/A"))
    summary_str = f"Radius: {r_val}, Texture: {t_val}, Perimeter: {p_val}"

    new_record = {
        "id": case_id,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "prediction": pred_result["prediction"],
        "is_malignant": pred_result["is_malignant"],
        "confidence": pred_result["confidence"],
        "benign_prob": pred_result["probabilities"]["Benign"],
        "malignant_prob": pred_result["probabilities"]["Malignant"],
        "model_used": pred_result["model_used"],
        "features_summary": summary_str,
        "sample_inputs": sample_inputs,
        "top_features": pred_result.get("top_features", [])
    }
    
    records.insert(0, new_record) # Insert newest first
    save_history(records)
    return new_record

def delete_history_record(record_id):
    records = get_all_history()
    filtered = [r for r in records if r["id"] != record_id]
    save_history(filtered)
    return len(records) != len(filtered)

def clear_all_history():
    save_history([])
    return True
