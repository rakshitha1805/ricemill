# 🌾 Paddy & Modern Rice Mill Dynamic Billing & Accounting System

A high-performance, real-time web application engineered for modern rice mills, paddy processing units, and agro-commodity traders. Designed specifically to calculate **inward paddy weighments**, **milling charges**, **labor/handling expenses**, and **by-product realization (bran, broken rice, blower, rejection, gunny)** dynamically every time.

---

## 🚀 Key Features

1. **100% Dynamic Input & Calculation Engine**:
   - Zero hardcoded constraints: dynamically adjust party names, lorry numbers, dates, batch numbers, lot numbers, and bag weights every time.
   - Live recalculation on every keystroke: instantly calculates equivalent 70kg bags (`Total Weight / 70`), milling charge, line-by-line handling costs, recoveries, and net balance.

2. **Dual Workflow Modes Supported**:
   - **Mode A: Single Batch (Vehicle Slip)**
     - Single vehicle inward weighment (`Paddy Weight`, `Reported Bags`, `Milling Rate`).
     - Line-by-line labor breakdown: Unloading, Gage Cutting & Dumping, Packing (26kg / 50kg), Bran, Blower, Outturn, Rejection, Shifting & Cutting, Stitching Thread, Gunny, etc.
     - Realization breakdown: Bran 50kg (`Weight × Rate`), Broken, Rejection, Gunny.
     - Net balance settlement: `Total Recoveries - Total Charges = Net Payable/Receivable`.
   - **Mode B: Multi-Load (Consolidated Lot Settlement)**
     - Inward weighment grid: add 1, 2, 3, 4, ... N lorry loads dynamically.
     - Automated totals for combined weight (e.g., `135,666 kg`) and combined inward bags.
     - Separate **Paddy Labor** (Paddy dumping, unloading, shifting) and **Rice Labor** (Rice 26kg, Broken, Bran, BB, 2nd Broken, Rejection, Thread, Outan).
     - Bran recovery credit deduction (`Weight × Rate`, e.g. `5,500 kg × ₹25.80 = ₹1,41,900.00`).
     - Consolidated settlement calculation with exact reconciliation.

3. **Dual Comparative View**:
   - Side-by-side comparative ledger matching the spreadsheet's left (vehicle level) and right (lot level) views for instant audit and verification.

4. **Persistent History & Database**:
   - Save every bill to a local SQLite database (`ricemill.db`).
   - Search by Party Name, Vehicle Number, Batch Number, or Date.
   - 1-click re-load into calculator to edit, inspect, or duplicate past settlements.

5. **Printable Invoices & Thermal Slips**:
   - Print-ready modal designed with `@media print` for standard A4 or 80mm thermal receipt printers.
   - Includes mill header, customer/vehicle metadata, itemized tables, net amount in words, driver signature, and authorized mill signature.

6. **Custom Tariff & Mill Settings**:
   - Configure Mill Name, Tagline, Address, Phone, and GSTIN.
   - Configure mill default tariffs (70kg rate, unloading, packing 26kg/50kg, bran rate, etc.) so new bills start with your customized standard rates every time.

7. **Export Capabilities**:
   - One-click CSV and Excel export for any individual bill or full database export.

8. **Indian Currency Number-to-Words Converter**:
   - Auto-generates formal currency text (e.g. `Rupees Six Thousand Seventeen and Twenty-Six Paise Only`).

---

## 📊 Spreadsheet Math Verification

The engine has been verified against the provided mill ledger:

### Single Batch Settlement (Vehicle: TN29BF8709 • Batch 1)
- **Paddy Inward Weight**: `27,536 kg` (380 reported bags)
- **Converted 70kg Bags**: `27,536 / 70 = 393.3714 bags`
- **Paddy Milling Charge (@ ₹100)**: `393.3714 × 100 = ₹39,337.14`
- **Total Labor & Handling Charges**: `₹45,386.74`
- **Bran Realization (1,775 kg @ ₹28.96)**: `₹51,404.00`
- **Net Amount Payable by Mill to Party**: `₹51,404.00 - ₹45,386.74 = ₹6,017.26`

### Multi-Load Consolidated Settlement (Batch 1 • Lot 500/256bg)
- **Lorry Loads (4 Trucks)**: `27,500 kg (350 bg) + 34,596 kg (450 bg) + 25,745 kg (650 bg) + 47,825 kg (152 bg)`
- **Total Consolidated Weight**: `135,666 kg` (1,602 bags)
- **Converted 70kg Bags**: `135,666 / 70 = 1,938.0857 bags`
- **Paddy 70kg Milling (@ ₹110)**: `1,938.0857 × 110 = ₹2,13,189.43`
- **Paddy Handling Labor**: `₹3,610.00`
- **Rice Handling Labor**: `₹2,049.00`
- **Total Gross Charges**: `₹2,13,189.43 + ₹3,610.00 + ₹2,049.00 = ₹2,18,848.43`
- **Bran Credit Deduction (5,500 kg @ ₹25.80)**: `₹1,41,900.00`
- **Net Amount Due from Party to Mill**: `₹1,41,900.00 - ₹2,18,848.43 = -₹76,948.43`

---

## 🏃 Running the Application

### 1. Launch with One Command
```bash
python start_app.py
```
This automatically launches:
- **FastAPI REST Server**: `http://127.0.0.1:8000` (API Docs at `http://127.0.0.1:8000/docs`)
- **React Vite Web UI**: `http://localhost:5173`

### 2. Manual Startup
**Backend**:
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend**:
```bash
cd frontend
npm run dev
```
