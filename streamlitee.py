import pandas as pd
import streamlit as st
from datetime import datetime

# Load files
pred_df = pd.read_excel("rf_predictions_2026_2027_dynamic.xlsx")
distance_df = pd.read_csv("distance matrix.csv", index_col=0)

# DEBUG: Print the actual column names to verify
st.write("🔎 Prediction Data Columns:", pred_df.columns.tolist())

# Hospital dropdown options
hospital_list = sorted(pred_df["Hospital"].dropna().unique().tolist())

# Streamlit UI
st.title("🏥 Dengue Patient Allocation System")
st.markdown("Assign patients to appropriate hospitals based on severity and bed availability.")

# Inputs
hospital = st.selectbox("Select Hospital", hospital_list)
date_input = st.date_input("Select Admission Date", min_value=datetime(2026, 1, 1), max_value=datetime(2027, 12, 31))
age = st.number_input("Patient Age", min_value=0, max_value=120)
weight = st.number_input("Weight (kg)", min_value=1.0, step=0.5)
platelet = st.number_input("Platelet Count", min_value=0)
igg = st.selectbox("IgG", ["Positive", "Negative"])
igm = st.selectbox("IgM", ["Positive", "Negative"])
ns1 = st.selectbox("NS1", ["Positive", "Negative"])

# Decision logic
def get_verdict(age, weight, platelet, igg, igm, ns1):
    if platelet < 50000 or (igg == "Positive" and igm == "Positive" and ns1 == "Positive"):
        return "Very Severe", "ICU"
    elif platelet < 100000:
        return "Severe", "ICU"
    else:
        return "Normal", "General"

def allocate(hospital, date_input, age, weight, platelet, igg, igm, ns1):
    verdict, need = get_verdict(age, weight, platelet, igg, igm, ns1)
    date = pd.to_datetime(date_input)
    
    try:
        row = pred_df[(pred_df["Hospital"] == hospital) & (pred_df["<actual_date_column>"] == date)].iloc[0]
    except IndexError:
        return {"Date": date.strftime("%Y-%m-%d"), "Verdict": verdict, "Resource Needed": need, "Hospital Tried": hospital,
                "Available at Current Hospital": "No", "Assigned Hospital": "N/A", "Distance (km)": "N/A", "Note": "Hospital/date not found."}
    
    available = False
    if need == "ICU":
        available = row["ICU Beds Occupied"] < row["ICU Beds Total"]
    else:
        available = row["Beds Occupied"] < row["Beds Total"]
    
    if available:
        return {"Date": date.strftime("%Y-%m-%d"), "Verdict": verdict, "Resource Needed": need, "Hospital Tried": hospital,
                "Available at Current Hospital": "Yes", "Assigned Hospital": hospital, "Distance (km)": 0, "Note": "Assigned at selected hospital"}
    
    try:
        distances = distance_df[hospital].sort_values()
    except KeyError:
        return {"Date": date.strftime("%Y-%m-%d"), "Verdict": verdict, "Resource Needed": need, "Hospital Tried": hospital,
                "Available at Current Hospital": "No", "Assigned Hospital": "N/A", "Distance (km)": "N/A", "Note": "Hospital not in distance matrix"}
    
    for alt in distances.index:
        if alt == hospital:
            continue
        try:
            alt_row = pred_df[(pred_df["Hospital"] == alt) & (pred_df["Date"] == date)].iloc[0]
            if need == "ICU" and alt_row["ICU Beds Occupied"] < alt_row["ICU Beds Total"]:
                return {"Date": date.strftime("%Y-%m-%d"), "Verdict": verdict, "Resource Needed": need, "Hospital Tried": hospital,
                        "Available at Current Hospital": "No", "Assigned Hospital": alt, "Distance (km)": distances[alt], "Note": "Rerouted to nearest ICU available"}
            elif need == "General" and alt_row["Beds Occupied"] < alt_row["Beds Total"]:
                return {"Date": date.strftime("%Y-%m-%d"), "Verdict": verdict, "Resource Needed": need, "Hospital Tried": hospital,
                        "Available at Current Hospital": "No", "Assigned Hospital": alt, "Distance (km)": distances[alt], "Note": "Rerouted to nearest General bed available"}
        except IndexError:
            continue
    
    return {"Date": date.strftime("%Y-%m-%d"), "Verdict": verdict, "Resource Needed": need, "Hospital Tried": hospital,
            "Available at Current Hospital": "No", "Assigned Hospital": "None", "Distance (km)": "N/A", "Note": "No beds/ICU available"}

# Run on submit
if st.button("Allocate Patient"):
    output = allocate(hospital, date_input, age, weight, platelet, igg, igm, ns1)
    st.subheader("📋 Allocation Result")
    st.json(output)
