import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# Load prediction and distance data
pred_df = pd.read_excel("rf_predictions_2026_2027_dynamic.xlsx")
distance_df = pd.read_csv("distance matrix.csv", index_col=0)

# Extract hospital names
hospital_list = sorted(pred_df["Hospital"].dropna().unique().tolist())

# Title
st.title("🏥 Dengue Patient Allocation System")

# Inputs
hospital = st.selectbox("Select Hospital", hospital_list)
date_input = st.date_input("Date of Admission", min_value=datetime(2026, 1, 1), max_value=datetime(2027, 12, 31))
age = st.number_input("Age", min_value=1, max_value=120)
weight = st.number_input("Weight (kg)", min_value=1, max_value=200)
platelet = st.number_input("Platelet Count", min_value=1)
igg = st.radio("IgG Result", options=["Positive", "Negative"])
igm = st.radio("IgM Result", options=["Positive", "Negative"])
ns1 = st.radio("NS1 Result", options=["Positive", "Negative"])

# Convert to binary format for logic (if your model expects it)
igg_flag = 1 if igg == "Positive" else 0
igm_flag = 1 if igm == "Positive" else 0
ns1_flag = 1 if ns1 == "Positive" else 0


# Define decision logic
def get_verdict(age, weight, platelet, igg, igm, ns1):
    if platelet < 20000 or (igg > 1.1 and igm > 1.1 and ns1 == "Positive"):
        return "Very Severe"
    elif platelet < 100000 or (igg > 1.0 and igm > 1.0):
        return "Severe"
    else:
        return "Normal"

# Allocation logic
def allocate_patient(hospital, date_input, age, weight, platelet, igg, igm, ns1):
    verdict = get_verdict(age, weight, platelet, igg, igm, ns1)
    resource_needed = "ICU" if verdict == "Very Severe" else "General Bed"

    year = date_input.year
    month = date_input.month

    try:
        row = pred_df[(pred_df["Hospital"] == hospital) & 
                      (pred_df["Year"] == year) & 
                      (pred_df["Month"] == month)].iloc[0]
    except IndexError:
        return {"Date": date_input.strftime("%Y-%m-%d"),
                "Verdict": verdict,
                "Resource Needed": resource_needed,
                "Hospital Tried": hospital,
                "Available at Current Hospital": "Data Not Found",
                "Assigned Hospital": "N/A",
                "Distance (km)": "N/A",
                "Note": "Prediction data not found for selected hospital/date."}

    if resource_needed == "ICU":
        available = row["ICU Beds Total"] - row["ICU Beds Occupied"]
    else:
        available = row["Beds Total"] - row["Beds Occupied"]

    if available > 0:
        return {
            "Date": date_input.strftime("%Y-%m-%d"),
            "Verdict": verdict,
            "Resource Needed": resource_needed,
            "Hospital Tried": hospital,
            "Available at Current Hospital": "Yes",
            "Assigned Hospital": hospital,
            "Distance (km)": 0,
            "Note": "Assigned at selected hospital"
        }

    # No beds/ICU — find nearest available hospital
    try:
        distances = distance_df[hospital].sort_values()
    except KeyError:
        return {
            "Date": date_input.strftime("%Y-%m-%d"),
            "Verdict": verdict,
            "Resource Needed": resource_needed,
            "Hospital Tried": hospital,
            "Available at Current Hospital": "No",
            "Assigned Hospital": "N/A",
            "Distance (km)": "N/A",
            "Note": "Hospital not found in distance matrix"
        }

    for alt_hosp, dist in distances.items():
        if alt_hosp == hospital:
            continue
        try:
            alt_row = pred_df[(pred_df["Hospital"] == alt_hosp) & 
                              (pred_df["Year"] == year) & 
                              (pred_df["Month"] == month)].iloc[0]
            if resource_needed == "ICU":
                alt_avail = alt_row["ICU Beds Total"] - alt_row["ICU Beds Occupied"]
            else:
                alt_avail = alt_row["Beds Total"] - alt_row["Beds Occupied"]

            if alt_avail > 0:
                return {
                    "Date": date_input.strftime("%Y-%m-%d"),
                    "Verdict": verdict,
                    "Resource Needed": resource_needed,
                    "Hospital Tried": hospital,
                    "Available at Current Hospital": "No",
                    "Assigned Hospital": alt_hosp,
                    "Distance (km)": dist,
                    "Note": "Redirected to nearest hospital with availability"
                }

        except IndexError:
            continue

    return {
        "Date": date_input.strftime("%Y-%m-%d"),
        "Verdict": verdict,
        "Resource Needed": resource_needed,
        "Hospital Tried": hospital,
        "Available at Current Hospital": "No",
        "Assigned Hospital": "None Available",
        "Distance (km)": "N/A",
        "Note": "No hospitals with available resources found"
    }

# Submit
if st.button("Allocate Patient"):
    output = allocate_patient(hospital, date_input, age, weight, platelet, igg, igm, ns1)
    st.subheader("📋 Allocation Result")
    st.json(output)
