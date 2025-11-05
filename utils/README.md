# AAC-MADRL Interactive Dashboard

## Overview

The **AAC-MADRL Interactive Dashboard** is a web-based visualization tool built with [Dash](https://dash.plotly.com/) that provides comprehensive analysis and comparison of multi-agent reinforcement learning algorithms for building energy management.

This dashboard enables researchers and practitioners to:
- Visualize temperature profiles and comfort violations
- Analyze energy demands (cooling and heating)
- Examine controller actions
- Compare Key Performance Indicators (KPIs) across different algorithms
- Perform multi-dimensional comparative analysis

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Data Structure](#data-structure)
- [Components](#components)
- [KPI Calculation](#kpi-calculation)
- [Tabs Description](#tabs-description)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

---

## Features

### 🎯 Core Capabilities

1. **Multi-Algorithm Comparison**
   - Compare multiple RL algorithms (SAC, AAC-MADRL, PI-RBC, etc.)
   - Support for different hyperparameter configurations
   - Side-by-side visualization

2. **Multi-Building Analysis**
   - Analyze individual buildings or entire districts
   - District-level KPI aggregation
   - Building-specific performance metrics

3. **Interactive Visualizations**
   - Temperature and comfort zone tracking
   - Energy demand profiles
   - Controller action analysis
   - KPI comparison charts
   - Multi-dimensional radar charts

4. **Flexible Data Loading**
   - Dynamic dataset discovery
   - Season selection (winter/summer)
   - Custom date range filtering
   - Automatic column mapping

5. **Performance Metrics**
   - Comfort violations (count and severity)
   - Electricity consumption, cost, and emissions
   - Fuel consumption, cost, and emissions
   - Daily peak analysis
   - Action smoothness

---

## Architecture

### Technology Stack

```
┌─────────────────────────────────────┐
│         Dash Framework              │
│  (Flask + Plotly + React)           │
├─────────────────────────────────────┤
│         Application Layer           │
│  - Callbacks                        │
│  - Data Loading                     │
│  - KPI Calculation                  │
├─────────────────────────────────────┤
│         Data Layer                  │
│  - CSV Files (observations)         │
│  - CSV Files (actions)              │
│  - district_obs.csv (aggregated)    │
└─────────────────────────────────────┘
```

### File Structure

```
utils/
├── dashboard.py           # Main dashboard application
└── README.md             # This file

outputs/data/
└── {COUNTRY}_{N}_dynamics/
    └── schema.json/
        ├── obs/
        │   ├── {algorithm}/
        │   │   ├── obs_building_0.csv
        │   │   ├── obs_building_1.csv
        │   │   ├── ...
        │   │   ├── action_building_0.csv
        │   │   ├── action_building_1.csv
        │   │   └── district_obs.csv
        │   └── {algorithm}/{params}/
        │       └── ...
        └── kpi/
```

---

## Installation

### Prerequisites

```bash
pip install dash plotly pandas numpy
```

### Required Python Version

- Python 3.8 or higher

### Dependencies

```python
dash >= 2.0.0
plotly >= 5.0.0
pandas >= 1.3.0
numpy >= 1.20.0
```

---

## Usage

### Starting the Dashboard

#### Method 1: Direct Python Execution
```bash
python utils/dashboard.py
```

#### Method 2: Using Batch File (Windows)
```bash
start_dashboard.bat
```

#### Method 3: Using Shell Script (Linux/Mac)
```bash
./run.sh
```

### Accessing the Dashboard

Once started, open your web browser and navigate to:
```
http://localhost:8050
```

### Basic Workflow

1. **Select Configuration**
   - Choose Country/Region (e.g., CA, TX, VT)
   - Select Dataset (e.g., CA_20_dynamics)
   - Choose Season (Winter or Summer)
   - Set Date Range

2. **Select Algorithms**
   - Check one or more algorithm configurations
   - Each algorithm may have multiple hyperparameter sets

3. **Select Buildings**
   - Choose one or more buildings to analyze
   - For KPIs, all selected buildings contribute to district metrics

4. **Explore Tabs**
   - **Temperature & Comfort**: Indoor/outdoor temperature, comfort zones
   - **Energy Demands**: Cooling and heating demand profiles
   - **Actions**: Controller actions over time
   - **KPIs Summary**: Comprehensive performance metrics
   - **Comparative Analysis**: Multi-dimensional comparison

---

## Data Structure

### Input Data Files

#### 1. Building-Level Observations (`obs_building_{id}.csv`)

Contains time-series data for individual buildings:

```csv
indoor_temperature,outdoor_dry_bulb_temperature,cooling_sp,comfort_band,...
20.5,15.2,22.0,1.0,...
20.6,15.3,22.0,1.0,...
```

**Expected Columns:**
- `indoor_temperature` / `T_in` / `temperature`
- `outdoor_dry_bulb_temperature` / `outdoor_temperature` / `T_out`
- `cooling_sp` / `cooling_setpoint` / `setpoint`
- `comfort_band`
- `cooling demand` / `cooling_demand`
- `heating demand` / `heating_demand`

#### 2. District-Level Observations (`district_obs.csv`)

Contains aggregated data for the entire district:

```csv
net electricity consumption,net electricity cost,net electricity emission,...
125.5,15.2,30.5,...
126.8,15.4,31.2,...
```

**Key Columns:**
- `net electricity consumption`
- `positive net electricity consumption`
- `net electricity cost` ✓
- `net electricity emission` ✓
- `net fuel consumption`
- `net fuel cost` ✓
- `net fuel emission` ✓

> **Important**: District-level cost and emission data are ONLY available in `district_obs.csv`, not in individual building files.

#### 3. Action Files (`action_building_{id}.csv`)

Contains controller actions:

```csv
dhw_storage,electrical_storage,cooling_or_heating_device
0.0,0.5,-0.2
0.1,0.3,-0.1
```

---

## Components

### 1. Data Discovery Functions

#### `discover_countries() -> List[str]`
Scans the data directory and identifies available countries based on folder names.

```python
# Returns: ['CA', 'TX', 'VT']
```

#### `discover_datasets(country: str) -> List[str]`
Lists all datasets for a given country.

```python
# Returns: ['CA_20_dynamics', 'CA_50_dynamics']
```

#### `discover_algorithms(dataset: str) -> List[str]`
Identifies all algorithms with observation data in a dataset.

```python
# Returns: ['aac_madrl', 'sac', 'PI_rbc']
```

#### `discover_algorithm_configurations(dataset: str, algorithm: str) -> List[Dict]`
Discovers all parameter configurations for an algorithm.

```python
# Returns:
# [
#   {
#     'key': 'sac_beta=0.2_gamma=2.0',
#     'algorithm': 'sac',
#     'display_name': 'beta=0.2_gamma=2.0 | lr=0.0003',
#     'path': 'sac/beta=0.2_gamma=2.0/lr=0.0003',
#     'params': 'beta=0.2_gamma=2.0/lr=0.0003'
#   }
# ]
```

### 2. Data Loading Functions

#### `load_district_observation_data(dataset, algorithm, season) -> pd.DataFrame`
**NEW in v2.0** - Loads district-level aggregated data.

```python
df = load_district_observation_data("CA_20_dynamics", config, "winter")
# Returns DataFrame with district-level metrics
# Includes: cost, emissions, net consumption
```

#### `load_observation_data(dataset, algorithm, building_id, season) -> pd.DataFrame`
Loads and standardizes building-level observation data.

```python
df = load_observation_data("CA_20_dynamics", config, 0, "winter")
# Returns DataFrame with standardized column names:
# - tin (indoor temperature)
# - tout (outdoor temperature)
# - sp (setpoint)
# - comfort_low, comfort_high (comfort bounds)
# - cool_demand, heat_demand
```

#### `load_action_data(dataset, algorithm, building_id, season) -> pd.DataFrame`
Loads controller action data for a building.

```python
df = load_action_data("CA_20_dynamics", config, 0, "winter")
# Returns DataFrame with action columns:
# - dhw_storage
# - electrical_storage
# - cooling_or_heating_device
```

### 3. KPI Calculation Functions

#### `calculate_observation_kpis(df: pd.DataFrame) -> Dict[str, float]`
Calculates comprehensive KPIs from observation data.

**Comfort KPIs:**
- Avg Num Comfort Violations
- Avg Comfort Violation Above (°C)
- Avg Comfort Violation Below (°C)
- Comfort Violation Rate (%)

**Electricity KPIs:**
- Electricity Import
- Electricity Cost
- Electricity Emissions
- Electricity Variance
- Daily Peak Average

**Fuel KPIs:**
- Fuel Import
- Fuel Cost
- Fuel Emissions
- Fuel Variance

#### `calculate_action_kpis(df: pd.DataFrame) -> Dict[str, float]`
Calculates action-related KPIs.

**Per Action Dimension:**
- Mean, Std, Min, Max, Range
- Smoothness (mean of absolute changes)

---

## KPI Calculation

### Data Source Strategy

The dashboard uses a **hybrid approach** for KPI calculation:

```
┌─────────────────────────────────────────────┐
│  COMFORT KPIS                               │
│  Source: obs_building_{id}.csv              │
│  Reason: Need indoor temperature per        │
│          building to calculate violations   │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  ELECTRICITY & FUEL KPIS                    │
│  Source: district_obs.csv                   │
│  Reason: Cost/emissions only exist at       │
│          district level (already aggregated)│
└─────────────────────────────────────────────┘
```

### Why District-Level for Electricity/Fuel?

**Problem Solved:**
- Individual `obs_building_{id}.csv` files DO NOT contain cost/emission columns
- These values are calculated at the district level by CityLearn
- Aggregating from individual buildings would result in **zero values**

**Solution:**
- Read electricity/fuel metrics directly from `district_obs.csv`
- This provides accurate cost and emission values
- Better performance (1 file read vs. 20 file reads)

### Comfort Violation Calculation

```python
# For each building
violations_above = (T_indoor > T_comfort_high).sum()
violations_below = (T_indoor < T_comfort_low).sum()

# Severity
severity_above = mean(T_indoor - T_comfort_high) where T_indoor > T_comfort_high
severity_below = mean(T_comfort_low - T_indoor) where T_indoor < T_comfort_low

# District-level
district_violations = sum(violations per building) / num_buildings
```

---

## Tabs Description

### 🌡️ Tab 1: Temperature & Comfort

**Purpose:** Monitor indoor temperature and comfort maintenance

**Visualizations:**
- Indoor temperature traces (one per algorithm)
- Comfort zone (shaded area)
- Setpoint (dashed line)
- Outdoor temperature (dotted gray line)

**Features:**
- Multi-building subplots
- Unified hover for time synchronization
- Color-coded by algorithm

**Use Cases:**
- Identify comfort violations
- Compare temperature control strategies
- Analyze algorithm responsiveness to outdoor conditions

### ⚡ Tab 2: Energy Demands

**Purpose:** Analyze cooling and heating energy consumption

**Visualizations:**
- Cooling demand (solid lines with fill)
- Heating demand (dashed lines with fill)
- Separate subplots per building

**Features:**
- Area charts for demand visualization
- Algorithm comparison
- Date range filtering

**Use Cases:**
- Compare energy efficiency
- Identify demand peaks
- Analyze seasonal patterns

### 🎮 Tab 3: Actions

**Purpose:** Examine controller actions over time

**Visualizations:**
- DHW Storage Action
- Electrical Storage Action
- Cooling/Heating Device Action

**Features:**
- 3-row subplot layout
- Action statistics table (mean, std, smoothness, range)
- Color-coded by algorithm

**Use Cases:**
- Understand control strategies
- Analyze action smoothness
- Compare controller behavior

**Statistics Provided:**
- Mean, Standard Deviation
- Min, Max, Range
- Smoothness (average rate of change)

### 📊 Tab 4: KPIs Summary

**Purpose:** Comprehensive performance comparison

**Structure:**

#### 🌡️ Comfort Violations Section
- Avg Num Comfort Violations
- Comfort Violation Rate (%)
- Avg Comfort Violation Above (°C)
- Avg Comfort Violation Below (°C)

#### ⚡ Electricity Section
- Electricity Import (kWh)
- Electricity Cost ($)
- Electricity Emissions (kg CO₂)
- Daily Peak Average (kW)

#### 🔥 Fuel Section
- Fuel Import (kWh)
- Fuel Cost ($)
- Fuel Emissions (kg CO₂)

**Visualization:**
- Individual bar charts per metric
- Color-coded by algorithm
- Detailed comparison table
- District-level aggregation summary

**Note:** Energy Demands (cooling/heating) are NOT shown here (available in Tab 2)

### 📈 Tab 5: Comparative Analysis

**Purpose:** Multi-dimensional algorithm comparison

**Visualizations:**

#### 1. Energy-Comfort Trade-off Scatter Plot
- X-axis: Total Comfort Violations
- Y-axis: Total Energy Demand
- Bubble size: Violation Rate
- Color: Algorithm

**Interpretation:**
- Bottom-left corner = Best (low violations, low energy)
- Identify Pareto-optimal solutions

#### 2. Cost-Emissions Trade-off Scatter Plot
- X-axis: Electricity Cost
- Y-axis: Electricity Emissions
- Bubble size: Total Energy
- Color: Algorithm

**Interpretation:**
- Bottom-left corner = Best (low cost, low emissions)
- Analyze economic vs. environmental trade-offs

#### 3. Multi-dimensional Radar Chart
- Axes: Comfort, Energy, Cost, Emissions
- Normalized to 0-100 scale (100 = best)
- Inverted for "lower is better" metrics

**Interpretation:**
- Larger area = Better overall performance
- Identify balanced solutions
- Compare across all dimensions simultaneously

---

## Configuration

### Global Constants

```python
# Data directory
DATA_DIR = BASE_DIR / "outputs" / "data"

# Season configurations
SEASONS = {
    "winter": pd.Timestamp("2023-01-01 00:00:00"),
    "summer": pd.Timestamp("2023-07-01 00:00:00"),
}

# Color palette
COLORS = px.colors.qualitative.Set2

# Action columns
ACTION_COLUMNS = ["dhw_storage", "electrical_storage", "cooling_or_heating_device"]
```

### Column Mappings

The dashboard uses flexible column mapping to handle different naming conventions:

```python
COLUMN_MAPPINGS = {
    "tin": ["indoor_temperature", "T_in", "temperature"],
    "tout": ["outdoor_dry_bulb_temperature", "outdoor_temperature", "T_out"],
    "sp": ["cooling_sp", "cooling_setpoint", "setpoint"],
    "band": ["comfort_band"],
    "cool_demand": ["cooling demand", "cooling_demand", "cool_dmd"],
    "heat_demand": ["heating demand", "heating_demand", "heat_demand"],
}
```

### Server Configuration

```python
if __name__ == '__main__':
    app.run(debug=True, port=8050)
```

**To change port:**
```python
app.run(debug=True, port=8080)  # Use port 8080
```

**To enable production mode:**
```python
app.run(debug=False, port=8050, host='0.0.0.0')
```

---

## Troubleshooting

### Common Issues

#### 1. No Data Appears

**Symptoms:**
- Empty dropdowns
- "No data available" messages

**Solutions:**
```bash
# Check data directory structure
ls outputs/data/

# Verify CSV files exist
ls outputs/data/CA_20_dynamics/schema.json/obs/

# Check file permissions
chmod -R 755 outputs/data/
```

#### 2. Cost/Emissions Show Zero

**Cause:** Using old version without district_obs.csv support

**Solution:**
- Ensure you're using the updated dashboard (v2.0+)
- Verify `district_obs.csv` exists
- Check that `load_district_observation_data()` function is present

#### 3. Import Errors

**Error:** `ModuleNotFoundError: No module named 'dash'`

**Solution:**
```bash
pip install dash plotly pandas numpy
```

#### 4. Port Already in Use

**Error:** `OSError: [Errno 98] Address already in use`

**Solution:**
```bash
# Find and kill process using port 8050
# Linux/Mac:
lsof -ti:8050 | xargs kill -9

# Windows:
netstat -ano | findstr :8050
taskkill /PID <PID> /F
```

#### 5. Memory Issues with Large Datasets

**Symptoms:**
- Slow loading
- Browser crashes

**Solutions:**
- Reduce date range
- Select fewer buildings
- Increase system RAM
- Use data downsampling

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check debug output in terminal:
```
[DEBUG] Looking for observation file: outputs/data/.../obs_building_0.csv
[DEBUG] Successfully read CSV with 8760 rows
[DEBUG] Mapped 'indoor_temperature' to 'tin'
```

---

## Development

### Code Structure

```python
# 1. IMPORTS AND CONFIGURATION
import dash
from dash import dcc, html, Input, Output, State
...

# 2. DATA DISCOVERY AND LOADING
def discover_countries() -> List[str]:
    ...

# 3. KPI CALCULATION
def calculate_observation_kpis(df: pd.DataFrame) -> Dict[str, float]:
    ...

# 4. DASH APP AND LAYOUT
app = dash.Dash(__name__)
app.layout = html.Div([...])

# 5. CALLBACKS
@app.callback(...)
def update_dataset_dropdown(country):
    ...

# 6. RENDERING FUNCTIONS
def render_temperature_tab(...):
    ...

# 7. MAIN
if __name__ == '__main__':
    app.run(debug=True, port=8050)
```

### Adding New KPIs

1. **Add calculation in `calculate_observation_kpis()`:**
```python
# Your new KPI
if "your_column" in df.columns:
    kpis["Your New KPI"] = df["your_column"].mean()
```

2. **Add to category in `render_kpis_tab()`:**
```python
kpi_categories = {
    'Your Category': {
        'metrics': ['Your New KPI'],
        'icon': '🎯',
        'color': '#3498db'
    }
}
```

### Adding New Visualizations

1. **Create render function:**
```python
def render_your_new_tab(dataset, selected_buildings, selected_configs, 
                        season, start_date, end_date, configs_data):
    # Your visualization code
    fig = go.Figure()
    # ...
    return dcc.Graph(figure=fig)
```

2. **Add tab to layout:**
```python
dcc.Tab(label='Your Tab', value='tab-your-tab', ...)
```

3. **Add callback handler:**
```python
elif tab == 'tab-your-tab':
    return render_your_new_tab(...)
```

### Testing

```python
# Run tests
python -m pytest tests/

# Test specific function
python -c "from utils.dashboard import load_district_observation_data; print('OK')"

# Validate syntax
python -m py_compile utils/dashboard.py
```

---

## Performance Optimization

### Tips for Large Datasets

1. **Use Date Range Filtering:**
   - Analyze weekly instead of monthly periods
   - Filter early in the data pipeline

2. **Limit Building Selection:**
   - Start with 1-5 buildings
   - Use representative samples

3. **Cache Data:**
   - Consider adding @cache decorator for repeated queries
   - Store preprocessed data

4. **Downsample Time Series:**
   ```python
   # Hourly to daily
   df_resampled = df.resample('D').mean()
   ```

5. **Optimize Plotly:**
   ```python
   fig.update_traces(
       marker=dict(line=dict(width=0)),  # Reduce line rendering
       mode='lines'  # Avoid markers
   )
   ```

---

## Version History

### v2.0 (Current - 2025-01-05)
- ✅ Added `load_district_observation_data()` for district-level metrics
- ✅ Fixed cost/emission KPIs (now uses district_obs.csv)
- ✅ Removed Energy Demands from KPI Summary
- ✅ Improved performance with hybrid data loading
- ✅ Enhanced documentation

### v1.0 (Initial Release)
- Basic multi-tab dashboard
- Temperature, demands, actions, KPIs, comparison tabs
- Multi-algorithm and multi-building support

---

## API Reference

### Core Functions

#### Data Discovery
```python
discover_countries() -> List[str]
discover_datasets(country: str) -> List[str]
discover_algorithms(dataset: str) -> List[str]
discover_algorithm_configurations(dataset: str, algorithm: str) -> List[Dict]
get_num_buildings(dataset: str, algorithm: Dict) -> int
```

#### Data Loading
```python
load_district_observation_data(dataset: str, algorithm: Dict, season: str = "winter") -> Optional[pd.DataFrame]
load_observation_data(dataset: str, algorithm: Dict, building_id: int, season: str = "winter") -> Optional[pd.DataFrame]
load_action_data(dataset: str, algorithm: Dict, building_id: int, season: str = "winter") -> Optional[pd.DataFrame]
```

#### KPI Calculation
```python
calculate_observation_kpis(df: pd.DataFrame) -> Dict[str, float]
calculate_action_kpis(df: pd.DataFrame) -> Dict[str, float]
```

#### Rendering
```python
render_temperature_tab(...) -> dcc.Graph
render_demands_tab(...) -> dcc.Graph
render_actions_tab(...) -> html.Div
render_kpis_tab(...) -> html.Div
render_comparison_tab(...) -> html.Div
```

---

## Contributing

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings to all functions
- Keep functions under 50 lines when possible

### Pull Request Process

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Update documentation
5. Submit pull request

---

## Support

### Getting Help

- Check this README first
- Review the [Troubleshooting](#troubleshooting) section
- Check terminal output for debug messages
- Review CityLearn documentation for data format details

### Reporting Issues

When reporting issues, include:
- Dashboard version
- Python version
- Error messages (full traceback)
- Dataset being used
- Steps to reproduce

---

## License

This dashboard is part of the AAC-MADRL project.

---

## Acknowledgments

- Built with [Dash by Plotly](https://dash.plotly.com/)
- Data from [CityLearn](https://github.com/intelligent-environments-lab/CityLearn) simulations
- Part of the AAC-MADRL research project

---

## Quick Start Example

```python
# 1. Start dashboard
python utils/dashboard.py

# 2. Open browser to http://localhost:8050

# 3. Select:
#    - Country: CA
#    - Dataset: CA_20_dynamics
#    - Season: Winter
#    - Algorithm: AAC-MADRL, SAC
#    - Buildings: 0, 1, 2

# 4. Navigate tabs to explore results!
```

---

**Last Updated:** 2025-01-05  
**Version:** 2.0  
**Author:** AAC-MADRL Project Team

