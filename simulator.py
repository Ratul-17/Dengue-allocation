from datetime import datetime
import pandas as pd
import numpy as np

# Load prediction and distance data
pred_df = pd.read_excel("/mnt/data/rf_predictions_2026_2027_dynamic.xlsx")
distance_df = pd.read_csv("/mnt/data/distance matrix.csv", index_col=0)

# Ensure year-month combo column exists
pred_df['Date'] = pd.to_datetime(pred_df['Year'].astype(str) + '-' + pred_df['Month'].astype(str) + '-01')
pred_df['Hospital'] = pred_df['Hospital'].str.strip()

# Verdict function based on rules
def get_verdict(platelet, igg, igm, ns1):
    if platelet < 20000 and ns1 == "Positive":
        return "Very Severe"
    elif platelet < 50000 or (igg == "Positive" and igm == "Positive"):
        return "Severe"
    elif 50000 <= platelet <= 100000 or igg == "Positive":
        return "Moderate"
    else:
        return "Mild"

# Allocation function
def allocate_patient(hospital, date_input, age, weight, platelet, igg, igm, ns1):
    date = pd.to_datetime(date_input)
    verdict = get_verdict(platelet, igg, igm, ns1)
    resource_needed = "ICU" if verdict in ["Very Severe", "Severe"] else "General"

    # Get prediction for that hospital and month
    try:
        row = pred_df[(pred_df["Hospital"] == hospital) & (pred_df["Date"] == pd.to_datetime(f"{date.year}-{date.month}-01"))].iloc[0]
    except IndexError:
        return {
            "Date": date.strftime("%Y-%m-%d"),
            "Verdict": verdict,
            "Resource Needed": resource_needed,
            "Hospital Tried": hospital,
            "Available at Current Hospital": "No",
            "Assigned Hospital": "None Found",
            "Note": "Hospital not found in prediction"
        }

    if resource_needed == "ICU":
        icu_total = row["ICU Beds Total"]
        icu_occupied = row["ICU Beds Occupied"]
        if icu_occupied < icu_total:
            return {
                "Date": date.strftime("%Y-%m-%d"),
                "Verdict": verdict,
                "Resource Needed": "ICU",
                "Hospital Tried": hospital,
                "Available at Current Hospital": "Yes",
                "Assigned Hospital": hospital,
                "Note": "Assigned at selected hospital"
            }
    else:
        beds_total = row["Beds Total"]
        beds_occupied = row["Beds Occupied"]
        if beds_occupied < beds_total:
            return {
                "Date": date.strftime("%Y-%m-%d"),
                "Verdict": verdict,
                "Resource Needed": "General",
                "Hospital Tried": hospital,
                "Available at Current Hospital": "Yes",
                "Assigned Hospital": hospital,
                "Note": "Assigned at selected hospital"
            }

    # Try rerouting to nearest hospitals
    try:
        distances = distance_df[hospital].sort_values()
    except KeyError:
        return {
            "Date": date.strftime("%Y-%m-%d"),
            "Verdict": verdict,
            "Resource Needed": resource_needed,
            "Hospital Tried": hospital,
            "Available at Current Hospital": "No",
            "Assigned Hospital": "None Found",
            "Note": "Hospital not found in distance matrix"
        }

    for near_hosp, dist in distances.items():
        try:
            near_row = pred_df[(pred_df["Hospital"] == near_hosp) & (pred_df["Date"] == pd.to_datetime(f"{date.year}-{date.month}-01"))].iloc[0]
        except IndexError:
            continue

        if resource_needed == "ICU" and near_row["ICU Beds Occupied"] < near_row["ICU Beds Total"]:
            return {
                "Date": date.strftime("%Y-%m-%d"),
                "Verdict": verdict,
                "Resource Needed": "ICU",
                "Hospital Tried": hospital,
                "Available at Current Hospital": "No",
                "Assigned Hospital": near_hosp,
                "Distance (km)": dist,
                "Note": "Rerouted to nearest hospital with ICU"
            }

        if resource_needed == "General" and near_row["Beds Occupied"] < near_row["Beds Total"]:
            return {
                "Date": date.strftime("%Y-%m-%d"),
                "Verdict": verdict,
                "Resource Needed": "General",
                "Hospital Tried": hospital,
                "Available at Current Hospital": "No",
                "Assigned Hospital": near_hosp,
                "Distance (km)": dist,
                "Note": "Rerouted to nearest hospital with general bed"
            }

    return {
        "Date": date.strftime("%Y-%m-%d"),
        "Verdict": verdict,
        "Resource Needed": resource_needed,
        "Hospital Tried": hospital,
        "Available at Current Hospital": "No",
        "Assigned Hospital": "None Found",
        "Note": "No available hospitals found nearby"
    }
