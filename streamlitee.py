import streamlit as st
from datetime import datetime
import pandas as pd

# Load prediction and distance data
pred_df = pd.read_excel("rf_predictions_2026_2027_dynamic.xlsx")
pred_df["Hospital_norm"] = pred_df["Hospital"].str.strip().str.lower()
distance_df = pd.read_csv("distance matrix.csv", index_col=0)
distance_df.index = distance_df.index.str.strip().str.lower()
distance_df.columns = distance_df.columns.str.strip().str.lower()
distance_df = distance_df.apply(pd.to_numeric, errors='coerce')

# Verdict & severity logic (same as before)
def calculate_severity(age, platelet, igg, igm, ns1):
    score = ns1 + igm + 0.5 * igg
    score += 1 if age < 15 else 0
    if platelet < 50000: score += 3
    elif platelet < 100000: score += 2
    elif platelet < 150000: score += 1
    return score

def get_verdict(score):
    if score <= 1: return "Mild"
    elif score == 2: return "Moderate"
    elif score == 3: return "Severe"
    else: return "Very Severe"

def get_required_resource(verdict):
    return "ICU Beds Occupied" if verdict in ["Severe", "Very Severe"] else "Beds Occupied"

def get_resource_type(resource):
    return "ICU" if "ICU" in resource else "General Bed"

# Allocation function
def allocate_patient_realistic(hospital_input, date_input, age, weight, platelet, igg, igm, ns1):
    hospital_norm = hospital_input.strip().lower()
    try:
        date_obj = datetime.strptime(date_input, "%Y-%m-%d")
        month, year = date_obj.month, date_obj.year
    except ValueError:
        return {"Error": "Invalid date format. Use YYYY-MM-DD."}

    score = calculate_severity(age, platelet, igg, igm, ns1)
    verdict = get_verdict(score)
    resource_col = get_required_resource(verdict)
    capacity_col = "ICU Beds Total" if "ICU" in resource_col else "Beds Total"

    month_df = pred_df[(pred_df["Year"] == year) & (pred_df["Month"] == month)].copy()
    month_df["Hospital_norm"] = month_df["Hospital"].str.strip().str.lower()

    status = month_df.groupby("Hospital_norm")[[
        "Beds Occupied", "ICU Beds Occupied", "Beds Total", "ICU Beds Total"
    ]].mean()

    result = {
        "Date": date_input,
        "Verdict": verdict,
        "Resource Needed": get_resource_type(resource_col),
        "Hospital Tried": hospital_input,
    }

    # Check current hospital
    if hospital_norm in status.index:
        occ = status.loc[hospital_norm, resource_col]
        cap = status.loc[hospital_norm, capacity_col]
        if cap > occ:
            result["Assigned Hospital"] = hospital_input
            result["Available at Current Hospital"] = "Yes"
            result["Note"] = "Assigned at selected hospital"
            return result
        else:
            result["Available at Current Hospital"] = "No"
    else:
        result["Note"] = "Hospital not found in prediction"
        return result

    if hospital_norm not in distance_df.columns:
        result["Note"] = "Hospital not in distance matrix"
        return result

    for alt_h in distance_df[hospital_norm].sort_values().index:
        if alt_h == hospital_norm or alt_h not in status.index:
            continue
        alt_occ = status.loc[alt_h, resource_col]
        alt_cap = status.loc[alt_h, capacity_col]
        if alt_cap > alt_occ:
            alt_name = pred_df[pred_df["Hospital_norm"] == alt_h]["Hospital"].values[0]
            result["Assigned Hospital"] = alt_name
            result["Distance (KM)"] = round(distance_df.loc[alt_h, hospital_norm], 2)
            result["Note"] = f"Redirected to nearest hospital with available {result['Resource Needed']}"
            return result

    result["Note"] = "No nearby hospital has available resource"
    return result

# ==== STREAMLIT UI ====
st.title("🏥 Dengue Patient Hospital Allocation")
st.write("Enter patient details to determine hospital assignment.")

with st.form("patient_form"):
    # List of hospital names from your dataset
hospital_list = [
    "Ad-Din Medical College Hospital",
    "Ahsania Mission Cancer & General Hospital",
    "Anwer Khan Modern Medical College Hospital",
    "Asgar Ali Hospital",
    "Bangladesh Medical College Hospital",
    "BRB Hospitals Limited",
    "Central Hospital Limited",
    "Dhanmondi General and Kidney Hospital",
    "Dhaka Medical College Hospital",
    "Green Life Medical College Hospital",
    "Holy Family Red Crescent Medical College Hospital",
    "Ibrahim Cardiac Hospital & Research Institute",
    "Islami Bank Central Hospital Kakrail",
    "Mugda Medical College",
    "Popular Medical College Hospital",
    "Sir Salimullah Medical College Mitford Hospital",
    "Square Hospital Ltd.",
    "Universal Medical College Hospital"
]

hospital = st.selectbox("Select Hospital", hospital_list)
    date_str = st.date_input("Admission/Test Date").strftime("%Y-%m-%d")
    age = st.number_input("Age", min_value=0, step=1)
    weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1)
    platelet = st.number_input("Platelet Count", step=1000)
    igg = st.selectbox("IgG", [0, 1])
    igm = st.selectbox("IgM", [0, 1])
    ns1 = st.selectbox("NS1", [0, 1])
    submitted = st.form_submit_button("Allocate Hospital")

if submitted:
    result = allocate_patient_realistic(hospital, date_str, age, weight, platelet, igg, igm, ns1)
    st.subheader("📝 Allocation Result")
    for k, v in result.items():
        st.write(f"**{k}**: {v}")
