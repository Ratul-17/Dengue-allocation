import streamlit as st
import pandas as pd
from datetime import datetime

# Load data
pred_df = pd.read_excel("rf_predictions_2026_2027_dynamic.xlsx")
distance_df = pd.read_csv("distance matrix.csv", index_col=0)

# Clean up
pred_df.columns = pred_df.columns.str.strip()
distance_df.columns = distance_df.columns.str.strip()
distance_df.index = distance_df.index.str.strip()

# Generate Date column
pred_df["Date"] = pd.to_datetime(pred_df["Year"].astype(str) + "-" + pred_df["Month"].astype(str) + "-01")

# Hospital Dropdown
hospital_list = sorted(pred_df["Hospital"].dropna().unique())

# Verdict logic
def determine_verdict(platelet, igg, igm, ns1):
    if ns1 == 'Positive' or igg == 'Positive' or igm == 'Positive':
        if platelet < 100000:
            if platelet < 50000:
                return "Very Severe"
            return "Severe"
        return "Moderate"
    return "Normal"

# Allocation
def allocate(hospital, date_input, age, weight, platelet, igg, igm, ns1, mode="realistic"):
    verdict = determine_verdict(platelet, igg, igm, ns1)
    date = pd.to_datetime(date_input.replace(day=1))
    resource_needed = "ICU" if verdict in ["Severe", "Very Severe"] else "General Bed"

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

    total_beds = row["Beds Total"]
    occ_beds = row["Beds Occupied"]
    total_icu = row["ICU Beds Total"]
    occ_icu = row["ICU Beds Occupied"]

    current_available = (occ_icu < total_icu) if resource_needed == "ICU" else (occ_beds < total_beds)

    assigned_hospital = hospital
    rerouted_distance = None
    rerouted = False

    if mode == "demo_force_reroute":
        rerouted = not current_available
    elif mode == "demo_alternate":
        rerouted = hash(hospital + str(date)) % 2 == 0

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

# Streamlit UI
st.set_page_config(page_title="🦟 Dengue Patient Allocator", layout="centered")
st.title("🏥 Dengue Patient Allocation Dashboard")

with st.form("allocate_form"):
    st.subheader("🔎 Patient & Test Information")
    hospital = st.selectbox("🏨 Select Hospital", hospital_list)
    date_input = st.date_input("📅 Test/Admission Date", value=datetime(2026, 10, 25))
    age = st.number_input("Age", 0, 120, value=30)
    weight = st.number_input("Weight (kg)", 1, 200, value=65)
    platelet = st.number_input("Platelet Count", 0, 500000, value=130000)
    igg = st.radio("IgG", ["Positive", "Negative"])
    igm = st.radio("IgM", ["Positive", "Negative"])
    ns1 = st.radio("NS1", ["Positive", "Negative"])
    mode = st.selectbox("Mode", ["Realistic", "Demo: Force Reroute", "Demo: Alternate"])

    submitted = st.form_submit_button("🚑 Allocate Patient")

if submitted:
    mode_flag = {
        "Realistic": "realistic",
        "Demo: Force Reroute": "demo_force_reroute",
        "Demo: Alternate": "demo_alternate"
    }[mode]
    result = allocate(hospital, date_input, age, weight, platelet, igg, igm, ns1, mode=mode_flag)
    st.subheader("📋 Allocation Result")
    st.json(result)
