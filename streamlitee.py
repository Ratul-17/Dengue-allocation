import streamlit as st
import pandas as pd
import datetime

# Load prediction and distance data
pred_df = pd.read_excel("rf_predictions_2026_2027_dynamic.xlsx")

# Clean column names to remove extra whitespace and standardize
pred_df.columns = pred_df.columns.str.strip()

# Check for possible variations of "Date"
if 'Date' not in pred_df.columns:
    # Print all column names if debugging locally
    st.write("⚠ Columns found:", list(pred_df.columns))

# Convert Date column (if exists) to datetime
if 'Date' in pred_df.columns:
    pred_df["Date"] = pd.to_datetime(pred_df["Date"])
else:
    st.error("❌ 'Date' column not found in the prediction dataset.")

distance_df = pd.read_csv("distance matrix.csv", index_col=0)

# Ensure datetime is in correct format
pred_df["Date"] = pd.to_datetime(pred_df["Date"])

# Hospital list for dropdown (adjust as needed)
hospital_list = pred_df["Hospital"].unique().tolist()
hospital_list.sort()

# Main title
st.title("🏥 Dengue Patient Allocation System")

# Input fields
hospital = st.selectbox("Select Hospital", options=hospital_list)
date_input = st.date_input("Select Admission Date", min_value=datetime.date(2026, 1, 1), max_value=datetime.date(2027, 12, 31))
age = st.number_input("Patient Age", min_value=0, max_value=120)
weight = st.number_input("Patient Weight (kg)", min_value=0.0, format="%.1f")
platelet = st.number_input("Platelet Count (×10⁹/L)", min_value=0)
igg = st.radio("IgG Result", options=["Positive", "Negative"])
igm = st.radio("IgM Result", options=["Positive", "Negative"])
ns1 = st.radio("NS1 Result", options=["Positive", "Negative"])

# Convert result flags to binary
igg_flag = 1 if igg == "Positive" else 0
igm_flag = 1 if igm == "Positive" else 0
ns1_flag = 1 if ns1 == "Positive" else 0

# Verdict logic
def determine_verdict(age, platelet, igg, igm, ns1):
    if platelet < 50 or (igg and igm and ns1):
        return "Very Severe"
    elif platelet < 100 or ((igg and igm) or ns1):
        return "Severe"
    else:
        return "Mild"

# Allocation logic
def allocate(hospital, date_input, age, weight, platelet, igg, igm, ns1):
    verdict = determine_verdict(age, platelet, igg, igm, ns1)
    date = pd.to_datetime(date_input)

    try:
        row = pred_df[(pred_df["Hospital"] == hospital) & (pred_df["Date"] == date)].iloc[0]
    except IndexError:
        return {"Date": date.strftime("%Y-%m-%d"), "Verdict": verdict,
                "Hospital Tried": hospital, "Available at Current Hospital": "No",
                "Note": "Date or hospital not found in predictions."}

    # Determine need
    need = "ICU" if verdict in ["Severe", "Very Severe"] else "General Bed"
    icu_avail = row["ICU Beds Total"] - row["ICU Beds Occupied"]
    gen_avail = row["Beds Total"] - row["Beds Occupied"]

    if (need == "ICU" and icu_avail > 0) or (need == "General Bed" and gen_avail > 0):
        return {
            "Date": date.strftime("%Y-%m-%d"),
            "Verdict": verdict,
            "Resource Needed": need,
            "Hospital Tried": hospital,
            "Available at Current Hospital": "Yes",
            "Assigned Hospital": hospital,
            "Distance (KM)": 0,
            "Note": "Assigned at selected hospital"
        }

    # Nearest hospital routing
    if hospital not in distance_df.columns:
        return {
            "Date": date.strftime("%Y-%m-%d"),
            "Verdict": verdict,
            "Resource Needed": need,
            "Hospital Tried": hospital,
            "Available at Current Hospital": "No",
            "Note": "Hospital not found in distance matrix."
        }

    distances = distance_df[hospital].sort_values()
    for alt_hospital in distances.index:
        if alt_hospital == hospital:
            continue
        try:
            alt_row = pred_df[(pred_df["Hospital"] == alt_hospital) & (pred_df["Date"] == date)].iloc[0]
            alt_icu = alt_row["ICU Beds Total"] - alt_row["ICU Beds Occupied"]
            alt_gen = alt_row["Beds Total"] - alt_row["Beds Occupied"]
            if (need == "ICU" and alt_icu > 0) or (need == "General Bed" and alt_gen > 0):
                return {
                    "Date": date.strftime("%Y-%m-%d"),
                    "Verdict": verdict,
                    "Resource Needed": need,
                    "Hospital Tried": hospital,
                    "Available at Current Hospital": "No",
                    "Assigned Hospital": alt_hospital,
                    "Distance (KM)": distances[alt_hospital],
                    "Note": f"Assigned to nearest hospital with availability"
                }
        except IndexError:
            continue

    return {
        "Date": date.strftime("%Y-%m-%d"),
        "Verdict": verdict,
        "Resource Needed": need,
        "Hospital Tried": hospital,
        "Available at Current Hospital": "No",
        "Note": "No available hospital found for the selected date"
    }

# Run on button press
if st.button("Allocate Patient"):
    result = allocate(hospital, date_input, age, weight, platelet, igg_flag, igm_flag, ns1_flag)
    st.subheader("📋 Allocation Result")
    st.json(result)
