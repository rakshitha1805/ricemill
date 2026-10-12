from typing import Dict, Any, List
import math

def number_to_indian_words(num: float) -> str:
    """
    Converts a number into Indian Currency word format.
    E.g., 6017.26 -> 'Rupees Six Thousand Seventeen and Twenty-Six Paise Only'
    76948.43 -> 'Rupees Seventy-Six Thousand Nine Hundred Forty-Eight and Forty-Three Paise Only'
    """
    if num is None or math.isnan(num):
        return "Rupees Zero Only"
        
    is_negative = num < 0
    num = abs(num)
    
    rupees = int(num)
    paise = int(round((num - rupees) * 100))
    
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
            "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    def two_digits(n: int) -> str:
        if n == 0:
            return ""
        if n < 20:
            return ones[n]
        rem = n % 10
        t = tens[n // 10]
        return f"{t} {ones[rem]}".strip()
        
    def convert_below_thousand(n: int) -> str:
        res = ""
        h = n // 100
        rem = n % 100
        if h > 0:
            res += f"{ones[h]} Hundred "
        if rem > 0:
            res += two_digits(rem)
        return res.strip()

    parts = []
    # Crores (>= 10,000,000)
    crores = rupees // 10000000
    rupees %= 10000000
    if crores > 0:
        parts.append(f"{convert_below_thousand(crores)} Crore")
        
    # Lakhs (>= 100,000)
    lakhs = rupees // 100000
    rupees %= 100000
    if lakhs > 0:
        parts.append(f"{two_digits(lakhs)} Lakh")
        
    # Thousands (>= 1,000)
    thousands = rupees // 1000
    rupees %= 1000
    if thousands > 0:
        parts.append(f"{two_digits(thousands)} Thousand")
        
    # Remaining hundreds/units
    if rupees > 0:
        parts.append(convert_below_thousand(rupees))
        
    rupees_str = " ".join(parts).strip()
    if not rupees_str:
        rupees_str = "Zero"
        
    result = f"Rupees {rupees_str}"
    if paise > 0:
        result += f" and {two_digits(paise)} Paise"
    result += " Only"
    
    if is_negative:
        result = "Minus " + result
        
    return result

def calculate_single_batch(data: Dict[str, Any]) -> Dict[str, Any]:
    bag_size = float(data.get("paddy_bag_size") or 70.0)
    paddy_weight = float(data.get("paddy_weight") or 0.0)
    paddy_rate = float(data.get("paddy_rate") or 100.0)
    
    # Paddy 70kg bags = weight / bag_size
    paddy_70kg_bags = (paddy_weight / bag_size) if bag_size > 0 else 0.0
    paddy_milling_amount = paddy_70kg_bags * paddy_rate
    
    labor_items = data.get("labor_items") or []
    updated_labor_items = []
    total_charges = 0.0
    
    for item in labor_items:
        it = dict(item)
        particulars = it.get("particulars", "")
        rate = float(it.get("rate") or 0.0)
        
        if it.get("is_paddy") or "Paddy 70" in particulars:
            it["is_paddy"] = True
            it["bags"] = paddy_70kg_bags
            it["weight"] = paddy_weight
            it["rate"] = paddy_rate
            it["amount"] = paddy_milling_amount
        else:
            # If stitching thread / outton fixed amount without bags
            if particulars in ["Stiching Thread", "Outton"] and it.get("bags") == 1 and not rate:
                it["amount"] = float(it.get("amount") or 0.0)
            else:
                bags = float(it.get("bags") or 0.0)
                # If amount already manually set and rate is 0, keep amount, else bags * rate
                if rate > 0:
                    it["amount"] = bags * rate
                elif it.get("amount") is not None:
                    it["amount"] = float(it.get("amount") or 0.0)
                else:
                    it["amount"] = 0.0
                    
        total_charges += float(it.get("amount") or 0.0)
        updated_labor_items.append(it)
        
    byproducts = data.get("byproducts") or []
    updated_byproducts = []
    total_recoveries = 0.0
    
    for item in byproducts:
        it = dict(item)
        rate = float(it.get("rate") or 0.0)
        weight = float(it.get("weight") or 0.0)
        bags = float(it.get("bags") or 0.0)
        
        # In byproducts, Bran 50kg: weight = 1775, rate = 28.96 => amount = weight * rate
        if weight > 0 and rate > 0:
            it["amount"] = round(weight * rate, 2)
        elif bags > 0 and rate > 0:
            it["amount"] = round(bags * rate, 2)
        elif it.get("amount") is not None:
            it["amount"] = float(it.get("amount") or 0.0)
        else:
            it["amount"] = 0.0
            
        total_recoveries += float(it.get("amount") or 0.0)
        updated_byproducts.append(it)
        
    net_payable = total_recoveries - total_charges
    
    return {
        **data,
        "paddy_bag_size": bag_size,
        "paddy_70kg_bags": paddy_70kg_bags,
        "paddy_milling_amount": paddy_milling_amount,
        "labor_items": updated_labor_items,
        "byproducts": updated_byproducts,
        "total_charges": total_charges,
        "total_recoveries": total_recoveries,
        "net_payable": net_payable,
        "net_payable_words": number_to_indian_words(net_payable),
        "settlement_type": "MILL_PAYS_PARTY" if net_payable >= 0 else "PARTY_PAYS_MILL"
    }

def calculate_multi_lot(data: Dict[str, Any]) -> Dict[str, Any]:
    bag_size = float(data.get("paddy_bag_size") or 70.0)
    paddy_loads = data.get("paddy_loads") or []
    paddy_70kg_rate = float(data.get("paddy_70kg_rate") or 110.0)
    
    total_paddy_weight = sum(float(l.get("paddy_weight") or 0.0) for l in paddy_loads)
    total_paddy_bags = sum(float(l.get("bags") or 0.0) for l in paddy_loads)
    
    paddy_70kg_bags = (total_paddy_weight / bag_size) if bag_size > 0 else 0.0
    paddy_70kg_amount = paddy_70kg_bags * paddy_70kg_rate
    
    # Paddy Labor
    paddy_labor = data.get("paddy_labor") or []
    updated_paddy_labor = []
    total_paddy_labor = 0.0
    for it in paddy_labor:
        item = dict(it)
        bags = float(item.get("bags") or 0.0)
        rate = float(item.get("rate") or 0.0)
        if rate > 0:
            item["amount"] = bags * rate
        else:
            item["amount"] = float(item.get("amount") or 0.0)
        total_paddy_labor += float(item.get("amount") or 0.0)
        updated_paddy_labor.append(item)
        
    # Rice Labor
    rice_labor = data.get("rice_labor") or []
    updated_rice_labor = []
    computed_rice_labor_sum = 0.0
    for it in rice_labor:
        item = dict(it)
        bags = float(item.get("bags") or 0.0)
        rate = float(item.get("rate") or 0.0)
        particulars = item.get("particulars", "")
        if particulars in ["Outan", "Thread"] and bags > 0 and rate > 0:
            item["amount"] = bags * rate
        elif rate > 0:
            item["amount"] = bags * rate
        else:
            item["amount"] = float(item.get("amount") or 0.0)
        computed_rice_labor_sum += float(item.get("amount") or 0.0)
        updated_rice_labor.append(item)
        
    # Allow manual override for total rice labor (e.g. 2049 in the user sheet) if specified
    override_rice_labor = data.get("rice_labor_override_total")
    if override_rice_labor is not None and override_rice_labor != "":
        total_rice_labor = float(override_rice_labor)
    else:
        total_rice_labor = computed_rice_labor_sum
        
    # Bran Realization
    bran_info = dict(data.get("bran_realization") or {})
    bran_weight = float(bran_info.get("weight") or 0.0)
    bran_rate = float(bran_info.get("rate") or 0.0)
    bran_amount = float(bran_info.get("amount") or (bran_weight * bran_rate))
    bran_info["amount"] = bran_amount
    
    total_charges = paddy_70kg_amount + total_paddy_labor + total_rice_labor
    total_recoveries = bran_amount
    net_payable = total_recoveries - total_charges
    
    return {
        **data,
        "paddy_bag_size": bag_size,
        "total_paddy_weight": total_paddy_weight,
        "total_paddy_bags": total_paddy_bags,
        "paddy_70kg_bags": paddy_70kg_bags,
        "paddy_70kg_amount": paddy_70kg_amount,
        "paddy_labor": updated_paddy_labor,
        "total_paddy_labor": total_paddy_labor,
        "rice_labor": updated_rice_labor,
        "total_rice_labor": total_rice_labor,
        "computed_rice_labor_sum": computed_rice_labor_sum,
        "bran_realization": bran_info,
        "total_charges": total_charges,
        "total_recoveries": total_recoveries,
        "net_payable": net_payable,
        "net_payable_words": number_to_indian_words(net_payable),
        "settlement_type": "MILL_PAYS_PARTY" if net_payable >= 0 else "PARTY_PAYS_MILL"
    }
