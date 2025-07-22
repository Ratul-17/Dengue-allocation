import streamlit as st
import pandas as pd

# Load prediction and distance matrix data
pred_df = pd.read_excel("rf_predictions_2026_2027_dynamic.xlsx")
distance_df = pd.read_csv("distance matrix.csv", index_col=0)

# Format date column from Year and Month
pred_df["Date"] = pd.to_datetime(pred_df["Year"].astype(str) + "-" + pred_df["Month"].astype(str) + "-01")

# Hospital dropdown options
hospital_list = sorted(pred_df["Hospital"].unique())

# Verdict classification
def classify_verdict(platelet, igg, igm, ns1):
    if ns1 == "Positive" and (igg == "Positive" or igm == "Positive"):
        if platelet < 20000:
            return "Very Severe", "ICU"
        elif platelet < 50000:
            return "Severe", "ICU"
        else:
            return "Moderate", "General"
    return "Normal", "General"

# Main allocation function
def allocate_patient(hospital, date_input, age, weight, platelet, igg, igm, ns1):
    date = pd.to_datetime(date_input)
    verdict, resource = classify_verdict(platelet, igg, igm, ns1)

    try:
        row = pred_df[(pred_df["Hospital"] == hospital) & (pred_df["Date"] == date)].iloc[0]
    except IndexError:
        return {
            "Date": date.strftime("%Y-%m-%d"),
            "Verdict": verdict,
            "Resource Needed": resource,
            "Hospital Tried": hospital,
            "Note": "Hospital not found in prediction"
        }

    available = False
    if resource == "ICU":
        available = row["ICU Beds Occupied"] < row["ICU Beds Total"]
    else:
        available = row["Beds Occupied"] < row["Beds Total"]

    if available:
        return {
            "Date": date.strftime("%Y-%m-%d"),
            "Verdict": verdict,
            "Resource Needed": resource,
            "Hospital Tried": hospital,
            "Available at Current Hospital": "Yes",
            "Assigned Hospital": hospital,
            "Note": "Assigned at selected hospital"
        }

    if hospital not in distance_df.columns:
        return {
            "Date": date.strftime("%Y-%m-%d"),
            "Verdict": verdict,
            "Resource Needed": resource,
            "Hospital Tried": hospital,
            "Available at Current Hospital": "No",
            "Assigned Hospital": "None Found",
            "Note": "Hospital not found in distance matrix"
        }

    sorted_hospitals = distance_df[hospital].sort_values()
    for alt_hospital in sorted_hospitals.index:
        if alt_hospital == hospital:
            continue
        try:
            alt_row = pred_df[(pred_df["Hospital"] == alt_hospital) & (pred_df["Date"] == date)].iloc[0]
        except IndexError:
            continue

        if resource == "ICU" and alt_row["ICU Beds Occupied"] < alt_row["ICU Beds Total"]:
            return {
                "Date": date.strftime("%Y-%m-%d"),
                "Verdict": verdict,
                "Resource Needed": resource,
                "Hospital Tried": hospital,
                "Available at Current Hospital": "No",
                "Assigned Hospital": alt_hospital,
                "Distance (km)": sorted_hospitals[alt_hospital],
                "Note": "Rerouted to nearest hospital with ICU"
            }

        if resource == "General" and alt_row["Beds Occupied"] < alt_row["Beds Total"]:
            return {
                "Date": date.strftime("%Y-%m-%d"),
                "Verdict": verdict,
                "Resource Needed": resource,
                "Hospital Tried": hospital,
                "Available at Current Hospital": "No",
                "Assigned Hospital": alt_hospital,
                "Distance (km)": sorted_hospitals[alt_hospital],
                "Note": "Rerouted to nearest hospital with General Bed"
            }

    return {
        "Date": date.strftime("%Y-%m-%d"),
        "Verdict": verdict,
        "Resource Needed": resource,
        "Hospital Tried": hospital,
        "Available at Current Hospital": "No",
        "Assigned Hospital": "None Found",
        "Note": "No available hospitals found nearby"
    }

# Streamlit UI
st.set_page_config(page_title="Dengue Patient Allocation", layout="centered")
st.title("🏥 Dengue Patient Allocation System")
st.markdown("Assigns ICU or General Beds based on patient severity and real-time availability.")

hospital = st.selectbox("🏨 Select Hospital", hospital_list)
date_input = st.date_input("📅 Admission/Test Date")
age = st.number_input("👤 Age", min_value=0)
weight = st.number_input("⚖️ Weight (kg)", min_value=0)
platelet = st.number_input("🩸 Platelet Count", min_value=0)

igg = st.selectbox("🧪 IgG Result", ["Positive", "Negative"])
igm = st.selectbox("🧪 IgM Result", ["Positive", "Negative"])
ns1 = st.selectbox("🧪 NS1 Result", ["Positive", "Negative"])

if st.button("🚨 Allocate Patient"):
    result = allocate_patient(hospital, date_input, age, weight, platelet, igg, igm, ns1)
    st.subheader("📋 Allocation Result")
    st.json(result)
