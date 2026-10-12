import sqlite3
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ricemill.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Bills Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ricemill_bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_no TEXT UNIQUE,
        bill_date TEXT,
        party_name TEXT,
        lorry_no TEXT,
        batch_no TEXT,
        lot_no TEXT,
        billing_mode TEXT, -- 'single_batch' or 'multi_lot'
        data_json TEXT,
        total_paddy_weight REAL DEFAULT 0,
        total_paddy_bags REAL DEFAULT 0,
        total_charges REAL DEFAULT 0,
        total_recoveries REAL DEFAULT 0,
        net_payable REAL DEFAULT 0,
        notes TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """)
    
    # Settings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ricemill_settings (
        key TEXT PRIMARY KEY,
        value_json TEXT
    )
    """)
    
    conn.commit()
    conn.close()

def get_default_settings() -> Dict[str, Any]:
    return {
        "mill_name": "SRI MODERN RICE MILL",
        "mill_tagline": "Paddy Processing & Modern Rice Milling Specialists",
        "mill_address": "NH-48 Main Road, Industrial Estate, Tamil Nadu - 635109",
        "mill_phone": "+91 98765 43210 / +91 94432 10987",
        "gstin": "33AABCS1429B1Z8",
        "standard_paddy_bag_weight": 70,
        "default_rates": {
            "paddy_70kg_milling_rate": 100.0,
            "multi_paddy_70kg_rate": 110.0,
            "unloading_rate": 4.0,
            "gage_cutting_rate": 6.0,
            "rice_pack_load_26kg_rate": 4.0,
            "bkn_pack_load_26kg_rate": 4.0,
            "bkn_pack_load_50kg_rate": 8.0,
            "bran_pack_load_50kg_rate": 8.0,
            "blower_pack_load_50kg_rate": 8.0,
            "outton_rate": 8.0,
            "rej_bkn_pack_load_50kg_rate": 8.0,
            "empty_bags_rice_rate": 11.5,
            "empty_bags_broken_rate": 0.0,
            "shifting_cutting_paddy_rate": 6.0,
            "empty_gunny_50kg_rate": 9.0,
            "stitching_thread_amount": 200.0,
            "outton_fixed_amount": 500.0,
            "bran_default_rate": 28.96,
            "multi_bran_rate": 25.80
        }
    }

def get_settings() -> Dict[str, Any]:
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value_json FROM ricemill_settings WHERE key = 'mill_config'")
    row = cursor.fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row["value_json"])
        except Exception:
            pass
    defaults = get_default_settings()
    save_settings(defaults)
    return defaults

def save_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO ricemill_settings (key, value_json) VALUES ('mill_config', ?)",
        (json.dumps(settings),)
    )
    conn.commit()
    conn.close()
    return settings

def get_all_bills(search: Optional[str] = None, mode: Optional[str] = None) -> List[Dict[str, Any]]:
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM ricemill_bills WHERE 1=1"
    params = []
    
    if mode:
        query += " AND billing_mode = ?"
        params.append(mode)
        
    if search:
        query += " AND (party_name LIKE ? OR lorry_no LIKE ? OR batch_no LIKE ? OR bill_no LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s])
        
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for r in rows:
        item = dict(r)
        try:
            item["data_json"] = json.loads(item["data_json"])
        except Exception:
            item["data_json"] = {}
        result.append(item)
    return result

def get_bill_by_id(bill_id: int) -> Optional[Dict[str, Any]]:
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ricemill_bills WHERE id = ?", (bill_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    item = dict(row)
    try:
        item["data_json"] = json.loads(item["data_json"])
    except Exception:
        item["data_json"] = {}
    return item

def save_or_update_bill(data: Dict[str, Any]) -> Dict[str, Any]:
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bill_id = data.get("id")
    bill_no = data.get("bill_no")
    if not bill_no:
        bill_no = f"RM-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp()) % 10000:04d}"
        
    bill_date = data.get("bill_date") or datetime.now().strftime("%Y-%m-%d")
    party_name = data.get("party_name", "").strip() or "Standard Mill Party"
    lorry_no = data.get("lorry_no", "").strip()
    batch_no = str(data.get("batch_no", "1"))
    lot_no = str(data.get("lot_no", ""))
    billing_mode = data.get("billing_mode", "single_batch")
    
    total_paddy_weight = float(data.get("total_paddy_weight", 0.0))
    total_paddy_bags = float(data.get("total_paddy_bags", 0.0))
    total_charges = float(data.get("total_charges", 0.0))
    total_recoveries = float(data.get("total_recoveries", 0.0))
    net_payable = float(data.get("net_payable", 0.0))
    notes = data.get("notes", "")
    
    data_json_str = json.dumps(data)
    
    if bill_id:
        cursor.execute("""
            UPDATE ricemill_bills
            SET bill_no = ?, bill_date = ?, party_name = ?, lorry_no = ?, batch_no = ?,
                lot_no = ?, billing_mode = ?, data_json = ?, total_paddy_weight = ?,
                total_paddy_bags = ?, total_charges = ?, total_recoveries = ?,
                net_payable = ?, notes = ?, updated_at = ?
            WHERE id = ?
        """, (
            bill_no, bill_date, party_name, lorry_no, batch_no,
            lot_no, billing_mode, data_json_str, total_paddy_weight,
            total_paddy_bags, total_charges, total_recoveries,
            net_payable, notes, now, bill_id
        ))
    else:
        cursor.execute("""
            INSERT INTO ricemill_bills (
                bill_no, bill_date, party_name, lorry_no, batch_no,
                lot_no, billing_mode, data_json, total_paddy_weight,
                total_paddy_bags, total_charges, total_recoveries,
                net_payable, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            bill_no, bill_date, party_name, lorry_no, batch_no,
            lot_no, billing_mode, data_json_str, total_paddy_weight,
            total_paddy_bags, total_charges, total_recoveries,
            net_payable, notes, now, now
        ))
        bill_id = cursor.lastrowid

    conn.commit()
    conn.close()
    
    return get_bill_by_id(bill_id)

def delete_bill(bill_id: int) -> bool:
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ricemill_bills WHERE id = ?", (bill_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_sample_preset_data() -> Dict[str, Any]:
    """
    Returns the exact parsed datasets from the user's spreadsheet,
    ready to be loaded or used dynamically!
    """
    return {
        "single_batch": {
            "bill_no": "RM-2026-B001",
            "bill_date": datetime.now().strftime("%Y-%m-%d"),
            "party_name": "M/S Sri Venkateswara Traders",
            "lorry_no": "TN29BF8709",
            "batch_no": "1",
            "lot_no": "LOT-A1",
            "billing_mode": "single_batch",
            "paddy_bag_size": 70,
            "paddy_weight": 27536,
            "paddy_bags": 380,
            "paddy_rate": 100,
            "labor_items": [
                {"id": "1", "particulars": "Paddy 70KG", "bags": 393.37142857142857, "weight": 27536, "rate": 100, "amount": 39337.142857142855, "is_paddy": True},
                {"id": "2", "particulars": "Unloading", "bags": 0, "weight": None, "rate": 4, "amount": 0},
                {"id": "3", "particulars": "Gage Cutting & Dumping", "bags": 380, "weight": None, "rate": 6, "amount": 2280},
                {"id": "4", "particulars": "Rice Pack & Load 26kg", "bags": 475, "weight": None, "rate": 4, "amount": 1900},
                {"id": "5", "particulars": "Bkn Pack & Load 26kg", "bags": 0, "weight": None, "rate": 4, "amount": 0},
                {"id": "6", "particulars": "Bkn Pack & Load 50kg", "bags": 54, "weight": None, "rate": 8, "amount": 432},
                {"id": "7", "particulars": "Bran pack&load 50 kg", "bags": 35.3, "weight": None, "rate": 8, "amount": 282.4},
                {"id": "8", "particulars": "blower pack & load50kg", "bags": 20.4, "weight": None, "rate": 8, "amount": 163.2},
                {"id": "9", "particulars": "Outton", "bags": 12, "weight": None, "rate": 8, "amount": 96},
                {"id": "10", "particulars": "Rej Bkn pack & load 50KG", "bags": 2, "weight": None, "rate": 8, "amount": 16},
                {"id": "11", "particulars": "Empty Bags Rice", "bags": 0, "weight": None, "rate": 11.5, "amount": 0},
                {"id": "12", "particulars": "Empty Bags Broken", "bags": 0, "weight": None, "rate": 0, "amount": 0},
                {"id": "13", "particulars": "Shifting & Cutting Paddy", "bags": 30, "weight": None, "rate": 6, "amount": 180},
                {"id": "14", "particulars": "Empty gunny 50kg", "bags": 0, "weight": None, "rate": 9, "amount": 0},
                {"id": "15", "particulars": "Stiching Thread", "bags": 1, "weight": None, "rate": 200, "amount": 200},
                {"id": "16", "particulars": "Outton", "bags": 1, "weight": None, "rate": 500, "amount": 500}
            ],
            "byproducts": [
                {"id": "b1", "particulars": "rice 26kg", "bags": 0, "weight": 0, "rate": 0, "amount": 0},
                {"id": "b2", "particulars": "Broken 26kg", "bags": 0, "weight": 0, "rate": 0, "amount": 0},
                {"id": "b3", "particulars": "Broken 50kg", "bags": 0, "weight": 0, "rate": 0, "amount": 0},
                {"id": "b4", "particulars": "Bran 50kg", "bags": 35.3, "weight": 1775, "rate": 28.96, "amount": 51404},
                {"id": "b5", "particulars": "Blower 50kg", "bags": 0, "weight": 0, "rate": 0, "amount": 0},
                {"id": "b6", "particulars": "Rejection Rice 26 KG", "bags": 0, "weight": 0, "rate": 0, "amount": 0},
                {"id": "b7", "particulars": "Rejection Broken 26kg", "bags": 0, "weight": 0, "rate": 0, "amount": 0},
                {"id": "b8", "particulars": "Gunny", "bags": 0, "weight": None, "rate": 0, "amount": 0}
            ],
            "total_paddy_weight": 27536,
            "total_paddy_bags": 380,
            "total_charges": 45386.742857142854,
            "total_recoveries": 51404,
            "net_payable": 6017.2571428571464, # Recoveries - Charges = Payable by Mill to Party
            "notes": "TN29BF8709 Batch 1 processing settlement"
        },
        "multi_lot": {
            "bill_no": "RM-2026-ML001",
            "bill_date": datetime.now().strftime("%Y-%m-%d"),
            "party_name": "M/S Sri Venkateswara Traders",
            "lorry_no": "TN29BF8709 & Others",
            "batch_no": "1",
            "lot_no": "500/256bg",
            "billing_mode": "multi_lot",
            "paddy_bag_size": 70,
            "paddy_loads": [
                {"id": "l1", "load_no": 1, "lorry_no": "TN29BF8709", "paddy_weight": 27500, "bags": 350},
                {"id": "l2", "load_no": 2, "lorry_no": "TN28AE4120", "paddy_weight": 34596, "bags": 450},
                {"id": "l3", "load_no": 3, "lorry_no": "KA01MF9832", "paddy_weight": 25745, "bags": 650},
                {"id": "l4", "load_no": 4, "lorry_no": "TN30CK1124", "paddy_weight": 47825, "bags": 152}
            ],
            "paddy_70kg_rate": 110.0,
            "paddy_labor": [
                {"id": "pl1", "particulars": "Paddy", "lot_no": "500/256bg", "bags": 500, "rate": 6, "amount": 3000},
                {"id": "pl2", "particulars": "Unloading", "lot_no": "", "bags": 100, "rate": 5, "amount": 500},
                {"id": "pl3", "particulars": "shifting&cutting", "lot_no": "", "bags": 20, "rate": 5.5, "amount": 110}
            ],
            "rice_labor": [
                {"id": "rl1", "particulars": "Rice 26kgs", "lot_no": "", "bags": 200, "rate": 3, "amount": 600},
                {"id": "rl2", "particulars": "Bkn 50kgs", "lot_no": "", "bags": 50, "rate": 6, "amount": 300},
                {"id": "rl3", "particulars": "Bkn 26kgs", "lot_no": "", "bags": 10, "rate": 3, "amount": 30},
                {"id": "rl4", "particulars": "Bran 50kgs", "lot_no": "", "bags": 10, "rate": 6, "amount": 60},
                {"id": "rl5", "particulars": "BB 50kgs", "lot_no": "", "bags": 11, "rate": 6, "amount": 66},
                {"id": "rl6", "particulars": "2nd Bkn 50kgs", "lot_no": "", "bags": 12, "rate": 6, "amount": 72},
                {"id": "rl7", "particulars": "Rej Rice 50kgs", "lot_no": "", "bags": 13, "rate": 6, "amount": 78},
                {"id": "rl8", "particulars": "Rej bkn 50kgs", "lot_no": "", "bags": 14, "rate": 6, "amount": 84},
                {"id": "rl9", "particulars": "Rice Gunny", "lot_no": "", "bags": 15, "rate": 0, "amount": 0},
                {"id": "rl10", "particulars": "Gunny", "lot_no": "", "bags": 15, "rate": 15, "amount": 225},
                {"id": "rl11", "particulars": "Outan", "lot_no": "", "bags": 1, "rate": 500, "amount": 500},
                {"id": "rl12", "particulars": "Thread", "lot_no": "", "bags": 2, "rate": 200, "amount": 400}
            ],
            "rice_labor_override_total": 2049, # From user sheet, or dynamically computed
            "bran_realization": {
                "particulars": "Bran Amount",
                "weight": 5500,
                "rate": 25.8,
                "amount": 141900
            },
            "total_paddy_weight": 135666,
            "total_paddy_bags": 1602,
            "paddy_70kg_bags": 1938.0857142857142,
            "paddy_70kg_amount": 213189.42857142855,
            "total_paddy_labor": 3610,
            "total_rice_labor": 2049,
            "total_charges": 218848.42857142855,
            "total_recoveries": 141900,
            "net_payable": -76948.42857142855, # Bran (141900) - Total (218848.43) = -76948.43 (Party owes Mill)
            "notes": "4 Lorry Consolidated Paddy Milling & Labor Settlement"
        }
    }
