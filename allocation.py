import pandas as pd
from datetime import datetime

# Load Excel sheets
xls = pd.ExcelFile("dataset new cleaned excel.xlsx")
distance_matrix = pd.read_csv(xls, sheet_name=2)

# Clean distance matrix
distance_df = distance_matrix.drop(index=0).reset_index(drop=True)
distance_df.columns = distance_df.iloc[0]
distance_df = distance_df.drop(index=0).reset_index(drop=True)
distance_df.set_index(distance_df.columns[0], inplace=True)
distance_df = distance_df.apply(pd.to_numeric, errors='coerce')

# Load prediction data
latest_pred = pd.read_excel("rf_predictions_2026_2027_dynamic.xlsx")

# Severity calculation
def calculate_severity(age, platelet, igg, igm, ns1):
    score = ns1 + igm + 0.5 * igg
    score += 1 if age < 15 else 0
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

def required_resource(verdict):
    return "ICU Beds Occupied" if verdict in ["Severe", "Very Severe"] else "Beds Occupied"

def resource_type_label(resource_col):
    return "ICU" if "ICU" in resource_col else "General Bed"

# Main allocator
def allocate_patient_verbose(hospital, date_str, age, weight, platelet, igg, igm, ns1):
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        month = date_obj.month
        year = date_obj.year
    except:
        return {"Error": "Invalid date format. Use YYYY-MM-DD"}

    score = calculate_severity(age, platelet, igg, igm, ns1)
    verdict = get_verdict(score)
    resource = required_resource(verdict)
    res_type = resource_type_label(resource)
    cap_col = 'ICU Beds Total' if resource == 'ICU Beds Occupied' else 'Beds Total'

    df_month = latest_pred[(latest_pred['Year'] == year) & (latest_pred['Month'] == month)]
    latest_status = df_month.groupby('Hospital')[
        ['Beds Occupied', 'ICU Beds Occupied', 'Beds Total', 'ICU Beds Total']
    ].mean()

    output = {
        "Verdict": verdict,
        "Resource Required": res_type
    }

    try:
        occupied = latest_status.loc[hospital, resource]
        capacity = latest_status.loc[hospital, cap_col]
        available = capacity > occupied
        output["ICU/Bed Available at Current Hospital"] = "Yes" if available else "No"

        if available:
            output["Assigned Hospital"] = hospital
            output["Note"] = "Assigned at current hospital"
            return output
    except KeyError:
        output["ICU/Bed Available at Current Hospital"] = "No data"

    # Fallback to nearest hospital
    distances = distance_df[hospital].sort_values()
    for alt_hospital in distances.index:
        if alt_hospital == hospital:
            continue
        try:
            occ = latest_status.loc[alt_hospital, resource]
            cap = latest_status.loc[alt_hospital, 'ICU Beds Total' if resource == 'ICU Beds Occupied' else 'Beds Total']
            if cap > occ:
                output["Assigned Hospital"] = alt_hospital
                output["Note"] = f"Redirected to nearest available hospital: {alt_hospital}"
                return output
        except KeyError:
            continue

    output["Assigned Hospital"] = None
    output["Note"] = "No available ICU/Bed found in nearby hospitals"
    return output

# ------------------ Manual Input Section ------------------
print("---- DENGUE SEVERITY BASED HOSPITAL ALLOCATION SYSTEM ----")
hospital = input("Enter Hospital Name: ").strip()
date_input = input("Enter Date (YYYY-MM-DD): ").strip()
age = int(input("Enter Age: "))
weight = float(input("Enter Weight (kg): "))
platelet = int(input("Enter Platelet Count: "))
igg = int(input("Enter IgG (0 or 1): "))
igm = int(input("Enter IgM (0 or 1): "))
ns1 = int(input("Enter NS1 (0 or 1): "))

result = allocate_patient_verbose(hospital, date_input, age, weight, platelet, igg, igm, ns1)

print("\n--- Allocation Decision Trace ---")
for k, v in result.items():
    print(f"{k}: {v}")
