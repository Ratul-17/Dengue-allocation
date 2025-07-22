import streamlit as st
import pandas as pd
from datetime import datetime

# Load prediction and distance data
pred_df = pd.read_excel("rf_predictions_2026_2027_dynamic.xlsx")
distance_df = pd.read_csv("distance matrix.csv", index_col=0)

# Combine Year and Month into Date
pred_df['Date'] = pd.to_datetime(pred_df[['Year', 'Month']].assign(DAY=1))
hospital_list = sorted(pred_df['Hospital'].unique().tolist())

# Severity verdict function
def determine_verdict(age, weight, platelet, igg, igm, ns1):
    if ns1 == "Positive" or igg == "Positive" or igm == "Positive":
        if platelet < 20 or (age > 60 and weight < 45):
            return "Very Severe", "ICU"
        elif platelet < 50 or weight < 50:
            return "Severe", "ICU"
        else:
            return "Moderate", "General"
    else:
        return "Mild", "General"

# Allocation logic
def allocate_patient(hospital, date_input, age, weight, platelet, igg, igm, ns1):
    date = pd.to_datetime(date_input)
    verdict, resource_needed = determine_verdict(age, weight, platelet, igg, igm, ns1)
    result = {
        "Date": date.strftime("%Y-%m-%d"),
        "Verdict": verdict,
        "Resource Needed": resource_needed,
        "Hospital Tried": hospital
    }

    try:
        row = pred_df[(pred_df['Hospital'] == hospital) & (pred_df['Date'] == date)].iloc[0]
    except IndexError:
        result.update({
            "Available at Current Hospital": "No",
            "Assigned Hospital": "None Found",
            "Note": "Hospital not found in prediction"
        })
        return result

    total_beds = row["Beds Total"]
    total_icu = row["ICU Beds Total"]
    occ_beds = row["Beds Occupied"]
    occ_icu = row["ICU Beds Occupied"]

    # Determine availability
    available_beds = max(0, total_beds - occ_beds)
    available_icu = max(0, total_icu - occ_icu)

    if resource_needed == "ICU":
        if available_icu > 0:
            result.update({
                "Available at Current Hospital": "Yes",
                "Assigned Hospital": hospital,
                "Note": "Assigned at selected hospital"
            })
        else:
            # Check nearby hospitals
            try:
                distances = distance_df[hospital].sort_values()
            except KeyError:
                result.update({
                    "Available at Current Hospital": "No",
                    "Assigned Hospital": "None Found",
                    "Note": "Hospital not found in distance matrix"
                })
                return result

            for nearby_hospital in distances.index:
                if nearby_hospital == hospital:
                    continue
                try:
                    nearby_row = pred_df[(pred_df['Hospital'] == nearby_hospital) & (pred_df['Date'] == date)].iloc[0]
                    if nearby_row["ICU Beds Total"] - nearby_row["ICU Beds Occupied"] > 0:
                        result.update({
                            "Available at Current Hospital": "No",
                            "Assigned Hospital": nearby_hospital,
                            "Note": f"Rerouted to nearest hospital with ICU vacancy",
                            "Distance (km)": float(distances[nearby_hospital])
                        })
                        return result
                except IndexError:
                    continue
            result.update({
                "Available at Current Hospital": "No",
                "Assigned Hospital": "None Found",
                "Note": "No available hospitals found nearby"
            })
    else:  # General bed case
        if available_beds > 0:
            result.update({
                "Available at Current Hospital": "Yes",
                "Assigned Hospital": hospital,
                "Note": "Assigned at selected hospital"
            })
        else:
            try:
                distances = distance_df[hospital].sort_values()
            except KeyError:
                result.update({
                    "Available at Current Hospital": "No",
                    "Assigned Hospital": "None Found",
                    "Note": "Hospital not found in distance matrix"
                })
                return result

            for nearby_hospital in distances.index:
                if nearby_hospital == hospital:
                    continue
                try:
                    nearby_row = pred_df[(pred_df['Hospital'] == nearby_hospital) & (pred_df['Date'] == date)].iloc[0]
                    if nearby_row["Beds Total"] - nearby_row["Beds Occupied"] > 0:
                        result.update({
                            "Available at Current Hospital": "No",
                            "Assigned Hospital": nearby_hospital,
                            "Note": f"Rerouted to nearest hospital with general bed vacancy",
                            "Distance (km)": float(distances[nearby_hospital])
                        })
                        return result
                except IndexError:
                    continue
            result.update({
                "Available at Current Hospital": "No",
                "Assigned Hospital": "None Found",
                "Note": "No available hospitals found nearby"
            })
    return result

# Streamlit UI
st.title("🏥 Dengue Patient Allocation System")

with st.form("patient_form"):
    st.subheader("📌 Patient Information")
    hospital = st.selectbox("Select Hospital Visited for Admission/Test", hospital_list)
    date_input = st.date_input("Date of Admission/Test", value=datetime(2026, 10, 15))
    age = st.number_input("Age", min_value=0)
    weight = st.number_input("Weight (kg)", min_value=0)
    platelet = st.number_input("Platelet Count (x10⁹/L)", min_value=0)
    igg = st.selectbox("IgG", ["Positive", "Negative"])
    igm = st.selectbox("IgM", ["Positive", "Negative"])
    ns1 = st.selectbox("Ns1", ["Positive", "Negative"])
    submitted = st.form_submit_button("Allocate Patient")

if submitted:
    output = allocate_patient(hospital, date_input, age, weight, platelet, igg, igm, ns1)
    st.subheader("🧾 Allocation Result")
    st.json(output)
