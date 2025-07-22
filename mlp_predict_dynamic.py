import pandas as pd
import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

# Load data
data = pd.read_excel('dataset new cleaned excel.xlsx')
data['Date'] = pd.to_datetime(data['Date'])
data['Year'] = data['Date'].dt.year
data['Month'] = data['Date'].dt.month

# Recalculate occupancy rates
data['Bed occupancy rate'] = data['Beds Occupied'] / data['Beds Total']
data['ICU occupancy rate'] = data['ICU Beds Occupied'] / data['ICU Beds Total']

# Target variables and fixed features
targets = ['Total Admitted till date', 'Admitted Patient in present', 'Beds Occupied',
           'ICU Beds Occupied', 'Bed occupancy rate', 'ICU occupancy rate']
fixed_cols = ['Beds Total', 'ICU Beds Total']
dynamic_features = ['Year', 'Month', 'Admitted Patient in present', 'Beds Occupied', 'ICU Beds Occupied']

hospitals = data['Hospital (DSCC Region)'].unique()
results = []

for hosp in hospitals:
    hosp_data = data[data['Hospital (DSCC Region)'] == hosp]

    # Estimate base month-wise averages for dynamic inputs
    monthly_avg = hosp_data.groupby('Month')[['Admitted Patient in present', 'Beds Occupied', 'ICU Beds Occupied']].mean().reset_index()

    # Create 2026 base
    future_2026 = monthly_avg.copy()
    future_2026['Year'] = 2026

    # Create 2027 as increased by 10%
    future_2027 = monthly_avg.copy()
    future_2027[['Admitted Patient in present', 'Beds Occupied', 'ICU Beds Occupied']] *= 1.10
    future_2027['Year'] = 2027

    # Combine and prepare
    future_months = pd.concat([future_2026, future_2027], ignore_index=True)
    future_months['Month'] = list(range(1, 13)) * 2
    future_months = future_months[['Year', 'Month', 'Admitted Patient in present', 'Beds Occupied', 'ICU Beds Occupied']]

    predictions = future_months.copy()

    for col in fixed_cols:
        predictions[col] = hosp_data[col].dropna().iloc[0]

    for target in targets:
        y_train = pd.to_numeric(hosp_data[target], errors='coerce')
        combined = pd.concat([hosp_data[dynamic_features], y_train.rename('target')], axis=1)
        combined = combined.dropna().reset_index(drop=True)

        if combined.empty:
            predictions[target] = np.nan
            continue

        X_clean = combined[dynamic_features].astype(float)
        y_clean = combined['target'].astype(float)

        # Normalize features for MLP
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_clean)
        future_scaled = scaler.transform(future_months[X_clean.columns].copy().fillna(0))

        model = MLPRegressor(hidden_layer_sizes=(100, 50), max_iter=500, random_state=42)
        model.fit(X_scaled, y_clean)

        pred = model.predict(future_scaled)

        if target in ['Total Admitted till date', 'Admitted Patient in present', 'Beds Occupied', 'ICU Beds Occupied']:
            predictions[target] = np.clip(np.round(pred), 0, None).astype(int)
        else:
            predictions[target] = np.round(pred, 4)

    predictions['Hospital'] = hosp
    results.append(predictions)

final_df = pd.concat(results, ignore_index=True)
final_df.to_excel('mlp_predictions_2026_2027_dynamic.xlsx', index=False)
print("✅ MLP predictions saved as mlp_predictions_2026_2027_dynamic.xlsx")