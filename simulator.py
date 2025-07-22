import streamlit as st
import pandas as pd

# Load datasets
pred_df = pd.read_excel("rf_predictions_2026_2027_dynamic.xlsx")
distance_df = pd.read_csv("distance matrix.csv", index_col=0)

# Parse integer year/month into full date
pred_df["Date"] = pd.to_datetime(pred_df[["Year", "Month"]].assign(DAY=1))

# Prepare hospital list
hospital_list = sorted(pred_df["Hospital"].unique().tolist())

# Severity checker
def get_verdict(age, weight, platelet, igg, igm, ns1):
    if platelet < 20000 or ns1 == 'positive':
        return "Very Severe"
    elif platelet < 80000 or igg == 'positive' or igm == 'positive':
        return "Severe"
    else:
        return "Normal"

# Allocation logic
def allocate_patient(hospital, date_input, age, weight, platelet, igg, igm, ns1):
    date = pd.to_datetime(date_input)
    verdict = get_verdict(age, weight, platelet, igg, igm, ns1)
    resource_type = "ICU Beds Occupied" if verdict == "Very Severe" else "Beds Occupied"
    required_total = "ICU Beds Total" if resource_type == "ICU Beds Occupied" else "Beds Total"

    # Check primary hospital
    row = pred_df[(pred_df["Hospital"] == hospital) & (pred_df["Date"] == date)]
    if not row.empty:
        row = row.iloc[0]
        if row[resource_type] < row[required_total]:
            return {
                "Date": date.strftime("%Y-%m-%d"),
                "Verdict": verdict,
                "Resource Needed": "ICU" if verdict == "Very Severe" else "General Bed",
                "Hospital Tried": hospital,
                "Available at Current Hospital": "Yes",
                "Assigned Hospital": hospital,
                "Note": "Assigned at selected hospital"
            }

    # Try rerouting using distance matrix
    if hospital not in distance_df.columns:
        return {
            "Date": date.strftime("%Y-%m-%d"),
            "Verdict": verdict,
            "Resource Needed": "ICU" if verdict == "Very Severe" else "General Bed",
            "Hospital Tried": hospital,
            "Available at Current Hospital": "No",
            "Assigned Hospital": "Not Found",
            "Note": "Hospital not found in distance matrix."
        }

    distances = distance_df[hospital].sort_values()
    for nearby_hospital in distances.index:
        row = pred_df[(pred_df["Hospital"] == nearby_hospital) & (pred_df["Date"] == date)]
        if not row.empty:
            row = row.iloc[0]
            if row[resource_type] < row[required_total]:
                return {
                    "Date": date.strftime("%Y-%m-%d"),
                    "Verdict": verdict,
                    "Resource Needed": "ICU" if verdict == "Very Severe" else "General Bed",
                    "Hospital Tried": hospital,
                    "Available at Current Hospital": "No",
                    "Assigned Hospital": nearby_hospital,
                    "Distance (KM)": float(distances[nearby_hospital]),
                    "Note": "Rerouted to nearest available hospital"
                }

    return {
        "Date": date.strftime("%Y-%m-%d"),
        "Verdict": verdict,
        "Resource Needed": "ICU" if verdict == "Very Severe" else "General Bed",
        "Hospital Tried": hospital,
        "Available at Current Hospital": "No",
        "Assigned Hospital": "None Found",
        "Note": "No available hospitals found nearby"
    }

# Streamlit UI
st.title("🏥 Dengue Patient Allocation System")

hospital = st.selectbox("Select Hospital", hospital_list)
date_input = st.date_input("Select Date")
age = st.number_input("Age", min_value=0, max_value=120)
weight = st.number_input("Weight (kg)", min_value=0.0)
platelet = st.number_input("Platelet Count", min_value=0)
igg = st.radio("IgG", options=["positive", "negative"])
igm = st.radio("IgM", options=["positive", "negative"])
ns1 = st.radio("Ns1", options=["positive", "negative"])

if st.button("Allocate Patient"):
    result = allocate_patient(hospital, date_input, age, weight, platelet, igg, igm, ns1)
    st.subheader("📋 Allocation Result")
    st.json(result)
