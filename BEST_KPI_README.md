# Best KPI Analysis Tool

## 📊 Overview

This tool analyzes simulation results from CSV files and identifies the best performing controllers based on both **individual KPIs** and a **composite KPI** that balances multiple objectives.

## 🎯 Features

### 1. Individual KPI Analysis
- Finds the best (minimum) value for each individual KPI across all simulations
- Counts how many times each algorithm/controller achieved the best value
- Ranks algorithms by the number of KPIs won

### 2. Composite KPI Analysis (NEW!)
The composite KPI addresses a key challenge: finding a controller that balances **comfort**, **cost**, and **emissions**.

#### How It Works:
The composite KPI combines three main components:

1. **Comfort Violations Score**
   - `Avg Num Comfort Violations` (count of violations)
   - `Avg Comfort Violation Above (°C)` × 50 (severity when too hot)
   - `Avg Comfort Violation Below (°C)` × 50 (severity when too cold)

2. **Total Cost**
   - `Electricity Cost` + `Fuel Cost`

3. **Total Emissions**
   - `Electricity Emissions` + `Fuel Emissions`

#### Normalization & Weighting:
- Each component is **normalized** to [0, 1] using min-max scaling across all simulations
- Components are combined using **customizable weights**:
  - Default: 40% comfort, 30% cost, 30% emissions
  - **Lower composite score is better**

## 🚀 Usage

### Basic Usage:
```python
python best_kpi.py
```

### Customize Weights:
Edit the `custom_weights` dictionary in `best_kpi.py`:

```python
# Prioritize comfort (50%)
custom_weights = {
    'comfort_violations': 0.5,
    'cost': 0.25,
    'emissions': 0.25
}

# Prioritize cost (50%)
custom_weights = {
    'comfort_violations': 0.3,
    'cost': 0.5,
    'emissions': 0.2
}

# Equal weights
custom_weights = {
    'comfort_violations': 0.333,
    'cost': 0.333,
    'emissions': 0.334
}
```

### Change Search Directory:
```python
# Search in different directory
root_dir = "./outputs/data/TX_10_dynamics/schema.json/kpi/test"

# Or search entire outputs folder
root_dir = "./outputs/data"
```

## 📈 Output

The tool generates:

### Console Output:
1. **Individual KPI Results**: Best value and simulation for each KPI
2. **Individual KPI Summary**: Ranking by number of KPIs won
3. **Composite KPI Rankings**: Overall best controller considering all factors

### CSV Files:
1. **`best_kpi_results.csv`**: Individual KPI winners
   - Columns: `KPI_Name`, `Best_Value`, `Simulation_Name`

2. **`composite_kpi_rankings.csv`**: Composite KPI rankings
   - Columns: `Rank`, `Simulation_Name`, `Composite_Score`

## 🎓 Interpretation

### Individual KPIs:
- Shows which controller is best at specific objectives
- A controller winning many individual KPIs might not be balanced

### Composite KPI:
- **Rank 1** = Best overall controller considering all factors
- **Lower score** = Better performance
- Score is in range [0, 1]
- Useful when you need a **balanced solution** rather than optimizing a single metric

## 💡 Examples

### Example Output:
```
================================================================================
COMPOSITE KPI RANKING (Comfort + Cost + Emissions)
================================================================================

Weights used:
  - Comfort Violations: 40.0%
  - Cost: 30.0%
  - Emissions: 30.0%

Lower score is better (normalized to 0-1 scale)

Rank   Score        Simulation Name
--------------------------------------------------------------------------------
1      0.234567     beta=0.2_gamma=3.5/lr=0.0003/aac-madrl_lr=0.0003.csv
2      0.345678     beta=0.5_gamma=3.0/lr=0.0003/sac_lr=0.0003.csv
3      0.456789     beta=0.8_gamma=2.0/lr=0.0003/pi_rbc_lr=0.0003.csv

================================================================================
🏆 BEST OVERALL CONTROLLER (Composite KPI): beta=0.2_gamma=3.5/lr=0.0003/aac-madrl_lr=0.0003.csv
   Composite Score: 0.234567
   This controller achieves the best balance between comfort, cost, and emissions
================================================================================
```

## ⚙️ Technical Details

### Normalization Formula:
```
normalized_value = (value - min_value) / (max_value - min_value)
```

### Composite Score Formula:
```
composite_score = w_comfort × norm_comfort + w_cost × norm_cost + w_emissions × norm_emissions
```

Where:
- `w_*` = weight for each component (sum to 1.0)
- `norm_*` = normalized value in [0, 1]

### Why Normalize?
- Different KPIs have different scales (e.g., cost in thousands, violations in hundreds)
- Normalization ensures all components contribute fairly based on their weights
- Allows meaningful comparison across different units and magnitudes

## 🔧 Customization

You can easily modify the tool to:
- Add more KPIs to the composite score
- Change how comfort severity is weighted (currently × 50)
- Use different normalization methods
- Add custom filtering of simulations

## 📝 Notes

- All simulations must have the same CSV structure (two columns: kpi_name, value)
- Missing or NaN values are automatically skipped
- The tool is robust to file reading errors
- Composite KPI only works if all three components (comfort, cost, emissions) have data

