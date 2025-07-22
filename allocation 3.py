import pandas as pd
from datetime import datetime

# === Load Prediction Data ===
pred_df = pd.read_excel("rf_predictions_2026_2027_dynamic.xlsx")
pred_df["Hospital_norm"] = pred_df["Hospital"].str.strip().str.lower()

# === Load Distance Matrix ===
distance_df = pd.read_csv("distance matrix.csv", index_col=0)
distance_df.index = distance_df.index.str.strip().str.lower()
distance_df.columns = distance_df.columns.str.strip().str.lower()
distance_df = distance_df.apply(pd.to_numeric, errors='coerce')

# === Severity Classification Functions ===
def calculate_severity(age, platelet, igg, igm, ns1):
    score = ns1 + igm + 0.5 * igg
    if age < 15:
        score += 1
    if platelet < 50000:
        score += 3
    elif platelet < 100000:
        score += 2
    elif platelet < 150000:
        score += 1
    return score

def get_verdict(score):
    if score <= 1:
        return "Mild"
    elif score == 2:
        return "Moderate"
    elif score == 3:
        return "Severe"
    else:
        return "Very Severe"

def get_required_resource(verdict):
    return "ICU Beds Occupied" if verdict in ["Severe", "Very Severe"] else "Beds Occupied"

def get_resource_type(resource):
    return "ICU" if "ICU" in resource else "General Bed"

# === Allocation Logic ===
def allocate_patient_realistic(hospital_input, date_input, age, weight, platelet, igg, igm, ns1):
    hospital_norm = hospital_input.strip().lower()

    # Convert date
    try:
        date_obj = datetime.strptime(date_input, "%Y-%m-%d")
        month, year = date_obj.month, date_obj.year
    except ValueError:
        return {"Error": "Invalid date format. Use YYYY-MM-DD."}

    # Calculate severity and required resources
    severity_score = calculate_severity(age, platelet, igg, igm, ns1)
    verdict = get_verdict(severity_score)
    resource_col = get_required_resource(verdict)
    resource_type = get_resource_type(resource_col)
    capacity_col = 'ICU Beds Total' if "ICU" in resource_col else 'Beds Total'

    # Filter predictions for given month and year
    month_df = pred_df[(pred_df["Year"] == year) & (pred_df["Month"] == month)].copy()
    month_df["Hospital_norm"] = month_df["Hospital"].str.strip().str.lower()

    # Summarize hospital status
    status = month_df.groupby("Hospital_norm")[[
        'Beds Occupied', 'ICU Beds Occupied', 'Beds Total', 'ICU Beds Total'
    ]].mean()

    output = {
        "Date": date_input,
        "Verdict": verdict,
        "Resource Needed": resource_type,
        "Hospital Tried": hospital_input,
    }

    # Step 1: Check current hospital availability
    if hospital_norm in status.index:
        occ = status.loc[hospital_norm, resource_col]
        cap = status.loc[hospital_norm, capacity_col]
        if cap > occ:
            output["Assigned Hospital"] = hospital_input
            output["Available at Current Hospital"] = "Yes"
            output["Note"] = "Assigned at selected hospital"
            return output
        else:
            output["Available at Current Hospital"] = "No"
    else:
        output["Available at Current Hospital"] = "Unknown"
        output["Note"] = "Hospital not found in prediction data"
        return output

    # Step 2: Try nearest hospitals using distance matrix
    if hospital_norm not in distance_df.columns:
        output["Note"] = "Hospital not found in distance matrix"
        return output

    for alt_hosp_norm in distance_df[hospital_norm].sort_values().index:
        if alt_hosp_norm == hospital_norm or alt_hosp_norm not in status.index:
            continue
        alt_occ = status.loc[alt_hosp_norm, resource_col]
        alt_cap = status.loc[alt_hosp_norm, capacity_col]
        if alt_cap > alt_occ:
            alt_name = pred_df[pred_df["Hospital_norm"] == alt_hosp_norm]["Hospital"].values[0]
            distance_km = distance_df.loc[alt_hosp_norm, hospital_norm]
            output["Assigned Hospital"] = alt_name
            output["Distance (KM)"] = round(distance_km, 2)
            output["Note"] = f"Redirected to nearest hospital with available {resource_type}"
            return output

    output["Assigned Hospital"] = None
    output["Note"] = "No nearby hospital has available resource"
    return output

# === Manual Input Interface ===
print("---- PATIENT ALLOCATION SYSTEM (REALISTIC) ----")
hospital = input("Enter Hospital Name: ")
date_str = input("Enter Date (YYYY-MM-DD): ")
age = int(input("Enter Age: "))
weight = float(input("Enter Weight (kg): "))
platelet = int(input("Enter Platelet Count: "))
igg = int(input("Enter IgG (0 or 1): "))
igm = int(input("Enter IgM (0 or 1): "))
ns1 = int(input("Enter NS1 (0 or 1): "))

# Run the allocation
result = allocate_patient_realistic(hospital, date_str, age, weight, platelet, igg, igm, ns1)

print("\n--- ALLOCATION RESULT ---")
for k, v in result.items():
    print(f"{k}: {v}")
