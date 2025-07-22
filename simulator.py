import pandas as pd
import numpy as np
import streamlit as st

# Load prediction and distance matrix
pred_df = pd.read_excel("rf_predictions_2026_2027_dynamic.xlsx")
distance_df = pd.read_csv("distance matrix.csv", index_col=0)

# Clean names
pred_df["Hospital"] = pred_df["Hospital"].str.strip()
distance_df.columns = distance_df.columns.str.strip()
distance_df.index = distance_df.index.str.strip()

# Unique hospital list
hospital_list = sorted(pred_df["Hospital"].unique())

# Verdict logic
def determine_verdict(platelet, igg, igm, ns1):
    if ns1 == "Positive" and (igg == "Positive" or igm == "Positive") and platelet < 50000:
        return "Very Severe"
    elif ns1 == "Positive" and platelet < 100000:
        return "Severe"
    else:
        return "Normal"

# Resource needed
def resource_needed(verdict):
    return "ICU" if verdict == "Very Severe" else "General"

# Main allocation function
def allocate_patient(hospital, year, month, age, weight, platelet, igg, igm, ns1):
    verdict = determine_verdict(platelet, igg, igm, ns1)
    resource = resource_needed(verdict)

    # Filter prediction data
    match = pred_df[
        (pred_df["Hospital"] == hospital) &
        (pred_df["Year"] == int(year)) &
        (pred_df["Month"] == int(month))
    ]

    if match.empty:
        return {
            "Year": year,
            "Month": month,
            "Verdict": verdict,
            "Resource Needed": resource,
            "Hospital Tried": hospital,
            "Note": "Hospital not found in prediction data"
        }

    row = match.iloc[0]
    general_vacant = row["Beds Total"] - row["Beds Occupied"]
    icu_vacant = row["ICU Beds Total"] - row["ICU Beds Occupied"]

    if (resource == "General" and general_vacant > 0) or (resource == "ICU" and icu_vacant > 0):
        return {
            "Year": year,
            "Month": month,
            "Verdict": verdict,
            "Resource Needed": resource,
            "Hospital Tried": hospital,
            "Assigned Hospital": hospital,
            "Distance (km)": 0,
            "Note": "Assigned at current hospital"
        }

    # Check distance rerouting
    try:
        distances = distance_df[hospital].sort_values()
    except KeyError:
        return {
            "Year": year,
            "Month": month,
            "Verdict": verdict,
            "Resource Needed": resource,
            "Hospital Tried": hospital,
            "Note": "Hospital not found in distance matrix"
        }

    for alt_hospital in distances.index:
        if alt_hospital == hospital:
            continue

        alt_match = pred_df[
            (pred_df["Hospital"] == alt_hospital) &
            (pred_df["Year"] == int(year)) &
            (pred_df["Month"] == int(month))
        ]

        if alt_match.empty:
            continue

        alt_row = alt_match.iloc[0]
        alt_general = alt_row["Beds Total"] - alt_row["Beds Occupied"]
        alt_icu = alt_row["ICU Beds Total"] - alt_row["ICU Beds Occupied"]

        if (resource == "General" and alt_general > 0) or (resource == "ICU" and alt_icu > 0):
            return {
                "Year": year,
                "Month": month,
                "Verdict": verdict,
                "Resource Needed": resource,
                "Hospital Tried": hospital,
                "Assigned Hospital": alt_hospital,
                "Distance (km)": float(distances[alt_hospital]),
                "Note": "Rerouted to nearest hospital with availability"
            }

    return {
        "Year": year,
        "Month": month,
        "Verdict": verdict,
        "Resource Needed": resource,
        "Hospital Tried": hospital,
        "Assigned Hospital": "None Found",
        "Note": "No available hospitals found nearby"
    }

# Streamlit UI
st.title("🏥 Dengue Patient Allocation System")

hospital = st.selectbox("Hospital Visited", hospital_list)
year = st.selectbox("Admission Year", sorted(pred_df["Year"].unique()))
month = st.selectbox("Admission Month", sorted(pred_df["Month"].unique()))
age = st.number_input("Age", min_value=0, max_value=120, value=30)
weight = st.number_input("Weight (kg)", min_value=1, max_value=200, value=60)
platelet = st.number_input("Platelet Count", min_value=0, value=150000)
igg = st.radio("IgG", ["Positive", "Negative"])
igm = st.radio("IgM", ["Positive", "Negative"])
ns1 = st.radio("Ns1", ["Positive", "Negative"])

if st.button("Allocate Patient"):
    result = allocate_patient(hospital, year, month, age, weight, platelet, igg, igm, ns1)
    st.subheader("📋 Allocation Result")
    st.json(result)
