import pandas as pd
import numpy as np
from datetime import datetime

# Load data
pred_df = pd.read_excel("rf_predictions_2026_2027_dynamic.xlsx")
distance_df = pd.read_csv("distance matrix.csv", index_col=0)

# Clean whitespace
pred_df["Hospital"] = pred_df["Hospital"].str.strip()
distance_df.columns = distance_df.columns.str.strip()
distance_df.index = distance_df.index.str.strip()

# Hospital list for UI dropdown
hospital_list = sorted(pred_df["Hospital"].unique())

# Determine severity
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

    # Filter for current hospital and date
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

    if resource == "General" and general_vacant > 0:
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

    if resource == "ICU" and icu_vacant > 0:
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

    # Reroute to nearest
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
                "Note": "Assigned at nearest hospital"
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
