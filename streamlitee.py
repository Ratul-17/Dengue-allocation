import streamlit as st
import pandas as pd
from datetime import datetime

# Load prediction and distance data
pred_df = pd.read_excel("rf_predictions_2026_2027_dynamic.xlsx")
distance_df = pd.read_csv("distance matrix.csv", index_col=0)

# Clean column names (fix KeyError: 'Date')
pred_df.columns = pred_df.columns.str.strip()

if 'Date' in pred_df.columns:
    pred_df["Date"] = pd.to_datetime(pred_df["Date"])
else:
    st.error("❌ 'Date' column not found in the prediction dataset.")
    st.stop()

# Dropdown hospital list
hospital_list = sorted(pred_df["Hospital"].unique())

# ------------------------ Allocation Logic ------------------------ #
def determine_verdict(platelet, igg, igm, ns1):
    if ns1 == 'Positive' or igg == 'Positive' or igm == 'Positive':
        if platelet < 100000:
            if platelet < 50000:
                return "Very Severe"
            return "Severe"
        return "Moderate"
    return "Normal"

def allocate(hospital, date_input, age, weight, platelet, igg, igm, ns1):
    verdict = determine_verdict(platelet, igg, igm, ns1)
    date = pd.to_datetime(date_input)

    # Resource needed
    resource_needed = "ICU" if verdict in ["Severe", "Very Severe"] else "General Bed"

    # Try to get row for that hospital and date
    try:
        row = pred_df[(pred_df["Hospital"] == hospital) & (pred_df["Date"] == date)].iloc[0]
    except IndexError:
        return {
            "Date": date.strftime("%Y-%m-%d"),
            "Verdict": verdict,
            "Resource Needed": resource_needed,
            "Hospital Tried": hospital,
            "Available at Current Hospital": "No",
            "Note": "Hospital/date not found in dataset"
        }

    # Check resource availability
    total_beds = row["Beds Total"]
    total_icu = row["ICU Beds Total"]
    occ_beds = row["Beds Occupied"]
    occ_icu = row["ICU Beds Occupied"]

    available = False
    note = ""
    assigned_hospital = hospital
    rerouted_distance = None

    if resource_needed == "ICU":
        available = occ_icu < total_icu
    else:
        available = occ_beds < total_beds

    if available:
        note = "Assigned at selected hospital"
    else:
        # Find alternate hospital by distance
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
                alt_beds = alt_row["Beds Occupied"]
                alt_total_beds = alt_row["Beds Total"]
                alt_icu = alt_row["ICU Beds Occupied"]
                alt_total_icu = alt_row["ICU Beds Total"]

                if resource_needed == "ICU" and alt_icu < alt_total_icu:
                    available = True
                    assigned_hospital = alt_hospital
                    rerouted_distance = distances[alt_hospital]
                    note = f"Rerouted to nearest hospital with ICU"
                    break
                elif resource_needed == "General Bed" and alt_beds < alt_total_beds:
                    available = True
                    assigned_hospital = alt_hospital
                    rerouted_distance = distances[alt_hospital]
                    note = f"Rerouted to nearest hospital with General Bed"
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
        "Distance (km)" if rerouted_distance else "Note": rerouted_distance if rerouted_distance else note,
    }

# ------------------------ Streamlit UI ------------------------ #
st.set_page_config(page_title="Dengue Hospital Allocation", layout="centered")
st.title("🏥 Dengue Patient Allocation System")

with st.form("allocation_form"):
    st.subheader("🔍 Patient Information")
    hospital = st.selectbox("Hospital Name", hospital_list)
    date_input = st.date_input("Admission/Test Date", value=datetime(2026, 10, 25))
    age = st.number_input("Age", min_value=0, max_value=120, value=25)
    weight = st.number_input("Weight (kg)", min_value=1, max_value=200, value=60)
    platelet = st.number_input("Platelet Count", min_value=0, value=120000)
    igg = st.selectbox("IgG", ["Positive", "Negative"])
    igm = st.selectbox("IgM", ["Positive", "Negative"])
    ns1 = st.selectbox("NS1", ["Positive", "Negative"])

    submit = st.form_submit_button("🚑 Allocate Patient")

if submit:
    st.subheader("📋 Allocation Result")
    result = allocate(hospital, date_input, age, weight, platelet, igg, igm, ns1)
    st.json(result)
