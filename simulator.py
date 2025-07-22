import streamlit as st
import pandas as pd
from datetime import datetime

# Load prediction and distance matrix
pred_df = pd.read_excel("ensemble_predictions_2026_2027_dynamic.xlsx")
distance_df = pd.read_csv("distance matrix.csv", index_col=0)

# Clean column names
pred_df.columns = pred_df.columns.str.strip()

# Create Date column from Year and Month
if "Year" in pred_df.columns and "Month" in pred_df.columns:
    pred_df["Date"] = pd.to_datetime(pred_df["Year"].astype(str) + "-" + pred_df["Month"].astype(str) + "-01")
else:
    st.error("❌ 'Year' and 'Month' columns not found in the prediction dataset.")
    st.stop()

# Hospital dropdown list
hospital_list = sorted(pred_df["Hospital"].unique())

# ---------------- Verdict Classification ---------------- #
def determine_verdict(platelet, igg, igm, ns1):
    if ns1 == 'Positive' or igg == 'Positive' or igm == 'Positive':
        if platelet < 100000:
            if platelet < 50000:
                return "Very Severe"
            return "Severe"
        return "Moderate"
    return "Normal"

# ---------------- Allocation Engine ---------------- #
def allocate(hospital, date_input, age, weight, platelet, igg, igm, ns1, mode="realistic"):
    verdict = determine_verdict(platelet, igg, igm, ns1)
    date = pd.to_datetime(date_input.replace(day=1))
    resource_needed = "ICU" if verdict in ["Severe", "Very Severe"] else "General Bed"

    # Get row of current hospital
    try:
        row = pred_df[(pred_df["Hospital"] == hospital) & (pred_df["Date"] == date)].iloc[0]
    except IndexError:
        return {
            "Date": date.strftime("%Y-%m-%d"),
            "Verdict": verdict,
            "Resource Needed": resource_needed,
            "Hospital Tried": hospital,
            "Available at Current Hospital": "Unknown",
            "Note": "Hospital/date not found in dataset"
        }

    # Get availability
    total_beds = row["Beds Total"]
    occ_beds = row["Beds Occupied"]
    total_icu = row["ICU Beds Total"]
    occ_icu = row["ICU Beds Occupied"]

    current_available = False
    if resource_needed == "ICU":
        current_available = occ_icu < total_icu
    else:
        current_available = occ_beds < total_beds

    assigned_hospital = hospital
    rerouted_distance = None
    rerouted = False

    if mode == "demo_force_reroute":  # Alternate for simulation
        rerouted = not current_available  # Flip the result to force a change for demo
    elif mode == "demo_alternate":
        rerouted = hash(hospital + str(date)) % 2 == 0  # Alternate assignments

    # In realistic or simulated reroute mode
    if not current_available or rerouted:
        try:
            distances = distance_df[hospital].sort_values()
        except KeyError:
            return {
                "Date": date.strftime("%Y-%m-%d"),
                "Verdict": verdict,
                "Resource Needed": resource_needed,
                "Hospital Tried": hospital,
                "Available at Current Hospital": "No",
                "Note": "Hospital not found in distance matrix"
            }

        for alt_hospital in distances.index:
            try:
                alt_row = pred_df[(pred_df["Hospital"] == alt_hospital) & (pred_df["Date"] == date)].iloc[0]
                if resource_needed == "ICU" and alt_row["ICU Beds Occupied"] < alt_row["ICU Beds Total"]:
                    assigned_hospital = alt_hospital
                    rerouted_distance = distances[alt_hospital]
                    break
                elif resource_needed == "General Bed" and alt_row["Beds Occupied"] < alt_row["Beds Total"]:
                    assigned_hospital = alt_hospital
                    rerouted_distance = distances[alt_hospital]
                    break
            except:
                continue

    return {
        "Date": date.strftime("%Y-%m-%d"),
        "Verdict": verdict,
        "Resource Needed": resource_needed,
        "Hospital Tried": hospital,
        "Available at Current Hospital": "Yes" if assigned_hospital == hospital else "No",
        "Assigned Hospital": assigned_hospital,
        "Distance (km)" if assigned_hospital != hospital else "Note": rerouted_distance if rerouted_distance else "Assigned at selected hospital"
    }

# ---------------- Streamlit UI ---------------- #
st.set_page_config(page_title="Dengue Patient Allocation", layout="centered")
st.title("🏥 Dengue Patient Allocation System")

with st.form("allocation_form"):
    st.subheader("🧾 Patient Information")
    hospital = st.selectbox("🏨 Hospital Name", hospital_list)
    date_input = st.date_input("📅 Admission/Test Date", value=datetime(2026, 10, 25))
    age = st.number_input("Age", min_value=0, max_value=120, value=30)
    weight = st.number_input("Weight (kg)", min_value=1, max_value=200, value=60)
    platelet = st.number_input("Platelet Count", min_value=0, value=130000)
    igg = st.selectbox("IgG", ["Positive", "Negative"])
    igm = st.selectbox("IgM", ["Positive", "Negative"])
    ns1 = st.selectbox("NS1", ["Positive", "Negative"])

    st.subheader("🛠 Simulation Settings")
    mode = st.selectbox("Run Mode", ["Realistic", "Demo: Force Reroute", "Demo: Alternate"])

    run = st.form_submit_button("🚑 Allocate Patient")

if run:
    st.subheader("📋 Allocation Result")
    sim_mode = {
        "Realistic": "realistic",
        "Demo: Force Reroute": "demo_force_reroute",
        "Demo: Alternate": "demo_alternate"
    }[mode]
    result = allocate(hospital, date_input, age, weight, platelet, igg, igm, ns1, mode=sim_mode)
    st.json(result)

