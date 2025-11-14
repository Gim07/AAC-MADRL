"""
Interactive Dashboard for AAC-MADRL Algorithm Visualization

This dashboard provides:
- Dynamic visualization of observations (temperature, demands) for each algorithm
- Action analysis and KPIs
- Scalable and portable across different countries and algorithms
- Comparative analysis across algorithms and buildings

Author: Generated for AAC-MADRL Project
Date: 2025-01-05

REFACTORED: 2025-11-05 to a two-column layout (sidebar + main content)
REFACTORED: 2025-11-05 to fix visualization (legends, bar chart padding)
REFACTORED: 2025-11-05 to fix KPI layout, update demands, and update action columns
"""

import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
import math # Needed for KPI layout

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "outputs" / "data"

# Expected column names with alternatives
COLUMN_MAPPINGS = {
    # Temperature and comfort
    "tin": ["indoor_temperature", "T_in", "temperature", "indoor_dry_bulb_temperature"],
    "tout": ["outdoor_dry_bulb_temperature", "outdoor_temperature", "T_out"],
    "sp": ["heating_sp", "cooling_setpoint", "setpoint"],
    "band": ["comfort_band"],

    # Energy demands
    "cooling demand": ["cooling demand", "cooling_demand", "cool_dmd", "cooling_power", "cooling_energy"],
    "heating demand": ["heating demand", "heating_demand", "heating_power", "heating_energy"],
    "dhw demand": ["dhw demand", "dhw_demand", "dhw_power", "dhw_energy"],
    "non shiftable load": ["non shiftable load", "non_shiftable_load", "energy to non shiftable load"],

    # Electricity consumption and generation
    "net electricity consumption": ["net electricity consumption", "net_electricity_consumption"],
    "positive net electricity consumption": ["positive net electricity consumption", "positive_net_electricity_consumption"],
    "solar generation": ["solar_generation", "solar generation", "pv_generation"],

    # Electricity costs and emissions
    "net electricity cost": ["net electricity consumption cost", "net electricity cost",
                             "Net Electricity Consumption Cost", "total_electricity_cost",
                             "net_electricity_cost"],
    "net electricity emission": ["net electricity consumption emission", "net electricity emission",
                                 "Net Electricity Consumption Emission", "total_electricity_emissions",
                                 "net_electricity_emission"],

    # Fuel consumption, costs and emissions
    "net fuel consumption": ["net_fuel_consumption", "fuel_consumption", "Net Fuel Consumption"],
    "net fuel cost": ["net_fuel_consumption_cost", "fuel_cost", "Net Fuel Cost",
                     "total_fuel_cost", "net_fuel_cost"],
    "net fuel emission": ["net_fuel_consumption_emission", "fuel_emission", "Net Fuel Emission",
                         "total_fuel_emissions", "net_fuel_emission"],

    # Storage SOC (State of Charge)
    "heating storage soc": ["heating storage soc", "heating_storage_soc"],
    "cooling storage soc": ["cooling storage soc", "cooling_storage_soc"],
    "electrical storage soc": ["electrical storage soc", "electrical_storage_soc",
                               "battery soc", "battery_soc"],
    "dhw storage soc": ["dhw storage soc", "dhw_storage_soc"],

    # Energy from/to heating storage
    "energy from heating device to heating storage": ["energy from heating device to heating storage",
                                                       "energy_from_heating_device_to_heating_storage"],
    "energy from heating fuel device to heating storage": ["energy from heating fuel device to heating storage",
                                                           "energy_from_heating_fuel_device_to_heating_storage"],
    "energy from heating storage": ["energy from heating storage", "energy_from_heating_storage"],

    # Energy from/to cooling storage
    "energy from cooling device to cooling storage": ["energy from cooling device to cooling storage",
                                                       "energy_from_cooling_device_to_cooling_storage"],
    "energy from cooling storage": ["energy from cooling storage", "energy_from_cooling_storage"],

    # Energy from/to electrical storage
    "electrical storage electricity consumption": ["electrical storage electricity consumption",
                                                   "electrical_storage_electricity_consumption",
                                                   "energy to electrical storage"],
    "energy from electrical storage": ["energy from electrical storage", "energy_from_electrical_storage"],
    "energy to electrical storage": ["energy to electrical storage", "energy_to_electrical_storage"],

    # Energy from/to DHW storage
    "energy from dhw device to dhw storage": ["energy from dhw device to dhw storage",
                                              "energy_from_dhw_device_to_dhw_storage"],
    "energy from dhw storage": ["energy from dhw storage", "energy_from_dhw_storage"],

    # Energy from devices
    "energy from heating device": ["energy from heating device", "energy_from_heating_device"],
    "energy from heating fuel device": ["energy from heating fuel device", "energy_from_heating_fuel_device"],
    "energy from cooling device": ["energy from cooling device", "energy_from_cooling_device"],
    "energy from dhw device": ["energy from dhw device", "energy_from_dhw_device"],

    # Detailed electricity consumption by component
    "cooling electricity consumption": ["cooling electricity consumption", "cooling_electricity_consumption"],
    "heating electricity consumption": ["heating electricity consumption", "heating_electricity_consumption"],
    "dhw electricity consumption": ["dhw electricity consumption", "dhw_electricity_consumption"],
    "dhw storage electricity consumption": ["dhw storage electricity consumption",
                                            "dhw_storage_electricity_consumption"],
    "cooling storage electricity consumption": ["cooling storage electricity consumption",
                                                "cooling_storage_electricity_consumption"],
    "heating storage electricity consumption": ["heating storage electricity consumption",
                                                "heating_storage_electricity_consumption"],

    # Pricing and carbon intensity
    "electricity pricing": ["electricity_pricing", "electricity_price", "pricing"],
    "fuel pricing": ["fuel_pricing", "fuel_price", "natural_gas_pricing"],
    "carbon intensity": ["carbon_intensity", "electricity_carbon_intensity"],
    "fuel carbon intensity": ["fuel_carbon_intensity", "natural_gas_carbon_intensity"],
}

# ***FIX 3: Updated action columns***
ACTION_COLUMNS = ["heating_storage", "electrical_storage", "heating_device", "heating_fuel_device"]

# Season configurations
SEASONS = {
    "winter": pd.Timestamp("2023-01-01 00:00:00"),
    "summer": pd.Timestamp("2023-07-01 00:00:00"),
}

# Color palette for algorithms
COLORS = px.colors.qualitative.Set2


# ============================================================================
# DATA DISCOVERY AND LOADING
# ============================================================================

def discover_countries() -> List[str]:
    """Discover all available countries/datasets in the data directory."""
    if not DATA_DIR.exists():
        return []

    countries = []
    for item in DATA_DIR.iterdir():
        if item.is_dir() and "_dynamics" in item.name:
            # Extract country code (e.g., "CA" from "CA_20_dynamics")
            country = item.name.split("_")[0]
            if country not in countries:
                countries.append(country)

    return sorted(countries)


def discover_datasets(country: str) -> List[str]:
    """Discover all datasets for a given country."""
    datasets = []
    for item in DATA_DIR.iterdir():
        if item.is_dir() and item.name.startswith(country):
            datasets.append(item.name)
    return sorted(datasets)


def discover_algorithms(dataset: str) -> List[str]:
    """
    Discover all unique algorithm names in a dataset (without parameters).
    Returns list of algorithm names (e.g., ['sac', 'aac_madrl', 'PI_rbc'])
    """
    dataset_path = DATA_DIR / dataset / "schema.json" / "obs"

    if not dataset_path.exists():
        return []

    algorithms = []

    for algo_dir in dataset_path.iterdir():
        if not algo_dir.is_dir():
            continue

        algo_name = algo_dir.name

        # Check if algorithm has any observation files
        has_obs = False

        # Check for parameter subdirectories
        for subdir in algo_dir.rglob("obs_building_*.csv"):
            has_obs = True
            break

        # Also check for direct files
        if not has_obs:
            if any((algo_dir / f"obs_building_{i}.csv").exists() for i in range(20)):
                has_obs = True

        if has_obs and algo_name not in algorithms:
            algorithms.append(algo_name)

    return sorted(algorithms)


def discover_algorithm_configurations(dataset: str, algorithm: str) -> List[Dict[str, any]]:
    """
    Discover all parameter configurations for a specific algorithm.
    Returns list of dicts with configuration info: {key, display_name, path, params}
    """
    dataset_path = DATA_DIR / dataset / "schema.json" / "obs"
    algo_dir = dataset_path / algorithm

    if not algo_dir.exists():
        return []

    configurations = []

    # Check if this has parameter subdirectories (e.g., beta=X_gamma=Y)
    has_params = False
    param_configs = {}

    for obs_file in algo_dir.rglob("obs_building_*.csv"):
        rel_path = obs_file.parent.relative_to(dataset_path)
        path_str = str(rel_path).replace("\\", "/")
        param_str = path_str.replace(algorithm, "").strip("/")

        if param_str and param_str not in param_configs:
            has_params = True

            # Create a nice display name from parameters
            display_parts = []
            for part in param_str.split("/"):
                if "beta=" in part or "gamma=" in part or "lr=" in part:
                    display_parts.append(part)

            display_name = " | ".join(display_parts) if display_parts else param_str
            config_key = f"{algorithm}_{param_str.replace('/', '_')}"

            param_configs[param_str] = {
                'key': config_key,
                'algorithm': algorithm,
                'display_name': display_name,
                'path': path_str,
                'params': param_str
            }

    if has_params:
        configurations = list(param_configs.values())
    else:
        # Direct algorithm without parameters
        if any((algo_dir / f"obs_building_{i}.csv").exists() for i in range(20)):
            configurations.append({
                'key': algorithm,
                'algorithm': algorithm,
                'display_name': 'Default Configuration',
                'path': algorithm,
                'params': None
            })

    return configurations


def get_num_buildings(dataset: str, algorithm: Dict) -> int:
    """Get the number of buildings for a dataset/algorithm."""
    # Convert path string to Path object
    algo_path = Path(algorithm['path']) if isinstance(algorithm['path'], str) else algorithm['path']
    obs_path = DATA_DIR / dataset / "schema.json" / "obs" / algo_path

    count = 0
    for i in range(100):  # Max 100 buildings
        if (obs_path / f"obs_building_{i}.csv").exists():
            count += 1
        elif count > 0:  # Stop if we've found buildings and now don't
            break

    return count


def find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Find the first matching column name from candidates."""
    for c in candidates:
        if c in df.columns:
            return c

    # Try case-insensitive matching
    lower_cols = {col.lower().replace(" ", ""): col for col in df.columns}
    for cand in candidates:
        key = cand.lower().replace(" ", "")
        if key in lower_cols:
            return lower_cols[key]

    return None


def color_to_rgba(color: str, alpha: float = 0.1) -> str:
    """
    Convert a color (hex or rgb) to rgba format.

    Args:
        color: Color in hex (#RRGGBB) or rgb(r,g,b) format
        alpha: Alpha transparency value (0-1)

    Returns:
        Color in rgba(r,g,b,a) format
    """
    if color.startswith('rgb('):
        # Already in rgb format: rgb(102, 194, 165)
        # Extract numbers and add alpha
        rgb_values = color[4:-1]  # Remove 'rgb(' and ')'
        return f'rgba({rgb_values}, {alpha})'
    elif color.startswith('#'):
        # Hex format: convert to rgb first
        rgb = px.colors.hex_to_rgb(color)
        return f'rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha})'
    else:
        # Fallback: return as is with some default
        return f'rgba(100, 100, 100, {alpha})'


def load_district_observation_data(dataset: str, algorithm: Dict, season: str = "winter") -> Optional[pd.DataFrame]:
    """Load district-level observation data (aggregated data for all buildings)."""
    algo_path = Path(algorithm['path']) if isinstance(algorithm['path'], str) else algorithm['path']
    district_obs_file = (DATA_DIR / dataset / "schema.json" / "obs" /
                         algo_path / "district_obs.csv")

    print(f"[DEBUG] Looking for district observation file: {district_obs_file}")

    if not district_obs_file.exists():
        print(f"[WARNING] District file does not exist: {district_obs_file}")
        return None

    try:
        df = pd.read_csv(district_obs_file)
        print(f"[DEBUG] Successfully read district CSV with {len(df)} rows")

        if df.empty:
            print(f"[WARNING] District CSV file is empty: {district_obs_file}")
            return None

        # Add datetime index
        start_date = SEASONS.get(season, SEASONS["winter"])
        df.index = pd.date_range(start=start_date, periods=len(df), freq="h")

        return df

    except Exception as e:
        print(f"[ERROR] Error loading {district_obs_file}: {e}")
        import traceback
        traceback.print_exc()
        return None


def load_observation_data(dataset: str, algorithm: Dict, building_id: int,
                          season: str = "winter") -> Optional[pd.DataFrame]:
    """Load observation data for a specific building and algorithm."""
    # Convert path string to Path object if needed
    algo_path = Path(algorithm['path']) if isinstance(algorithm['path'], str) else algorithm['path']
    obs_file = (DATA_DIR / dataset / "schema.json" / "obs" /
                algo_path / f"obs_building_{building_id}.csv")

    print(f"[DEBUG] Looking for observation file: {obs_file}")

    if not obs_file.exists():
        print(f"[WARNING] File does not exist: {obs_file}")
        return None

    try:
        df = pd.read_csv(obs_file)
        print(f"[DEBUG] Successfully read CSV with {len(df)} rows and columns: {list(df.columns[:5])}")

        if df.empty:
            print(f"[WARNING] CSV file is empty: {obs_file}")
            return None

        # Add datetime index
        start_date = SEASONS.get(season, SEASONS["winter"])
        df.index = pd.date_range(start=start_date, periods=len(df), freq="h")

        # Standardize column names
        standardized = pd.DataFrame(index=df.index)

        for key, candidates in COLUMN_MAPPINGS.items():
            col = find_column(df, candidates)
            if col:
                standardized[key] = pd.to_numeric(df[col], errors="coerce")
                print(f"[DEBUG] Mapped '{col}' to '{key}'")

        # Calculate comfort bounds if possible
        if "sp" in standardized.columns and "band" in standardized.columns:
            standardized["comfort_low"] = standardized["sp"] - standardized["band"]/2
            standardized["comfort_high"] = standardized["sp"] + standardized["band"]/2

        # Clip demands to non-negative
        if "cooling demand" in standardized.columns:
            standardized["cooling demand"] = standardized["cooling demand"].clip(lower=0)
        if "heating demand" in standardized.columns:
            standardized["heating demand"] = standardized["heating demand"].clip(lower=0)
        # ***FIX 2: Clip dhw demand***
        if "dhw demand" in standardized.columns:
            standardized["dhw demand"] = standardized["dhw demand"].clip(lower=0)

        print(f"[DEBUG] Standardized columns: {list(standardized.columns)}")
        return standardized

    except Exception as e:
        print(f"[ERROR] Error loading {obs_file}: {e}")
        import traceback
        traceback.print_exc()
        return None


def load_action_data(dataset: str, algorithm: Dict, building_id: int,
                     season: str = "winter") -> Optional[pd.DataFrame]:
    """Load action data for a specific building and algorithm."""
    # Convert path string to Path object if needed
    algo_path = Path(algorithm['path']) if isinstance(algorithm['path'], str) else algorithm['path']
    action_file = (DATA_DIR / dataset / "schema.json" / "obs" /
                   algo_path / f"action_building_{building_id}.csv")

    if not action_file.exists():
        return None

    try:
        df = pd.read_csv(action_file)
        if df.empty:
            return None

        # Add datetime index
        start_date = SEASONS.get(season, SEASONS["winter"])
        df.index = pd.date_range(start=start_date, periods=len(df), freq="h")

        # Ensure numeric
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    except Exception as e:
        print(f"Error loading {action_file}: {e}")
        return None


# ============================================================================
# KPI CALCULATION
# ============================================================================

def calculate_observation_kpis(df: pd.DataFrame) -> Dict[str, float]:
    """Calculate KPIs from observation data - matches evaluate_kpi.py methodology."""
    kpis = {}

    if df is None or df.empty:
        return kpis

    # ========== COMFORT VIOLATIONS ==========
    if all(col in df.columns for col in ["tin", "comfort_low", "comfort_high"]):
        violations_above = (df["tin"] > df["comfort_high"]).sum()
        violations_below = (df["tin"] < df["comfort_low"]).sum()
        total_violations = violations_above + violations_below

        kpis["Avg Num Comfort Violations"] = total_violations
        kpis["Avg Num Comfort Violations Above"] = violations_above
        kpis["Avg Num Comfort Violations Below"] = violations_below
        kpis["Total Comfort Violations"] = total_violations
        kpis["Comfort Violation Rate (%)"] = (total_violations / len(df)) * 100

        # Severity
        temp_above = (df["tin"] - df["comfort_high"]).clip(lower=0)
        temp_below = (df["comfort_low"] - df["tin"]).clip(lower=0)

        kpis["Avg Comfort Violation Above (°C)"] = temp_above[temp_above > 0].mean() if temp_above.sum() > 0 else 0
        kpis["Avg Comfort Violation Below (°C)"] = temp_below[temp_below > 0].mean() if temp_below.sum() > 0 else 0

    # ========== ELECTRICITY KPIs ==========
    # Try to find electricity consumption columns (multiple naming conventions)
    elec_cols = {
        'net': ['net electricity consumption', 'net_electricity_consumption'],
        'pos': ['positive net electricity consumption', 'positive_net_electricity_consumption'],
        'cost': ['net electricity consumption cost', 'net electricity cost',
                 'Net Electricity Consumption Cost', 'total_electricity_cost'],
        'emis': ['net electricity consumption emission', 'net electricity emission',
                 'Net Electricity Consumption Emission', 'total_electricity_emissions']
    }

    # Electricity Import (positive consumption)
    col_pos_elec = find_column(df, elec_cols['pos'])
    if col_pos_elec:
        elec_import = pd.to_numeric(df[col_pos_elec], errors='coerce').fillna(0).clip(lower=0).sum()
        kpis["Electricity Import"] = float(elec_import)

    # Electricity Variance
    col_net_elec = find_column(df, elec_cols['net'])
    if col_net_elec:
        elec_variance = pd.to_numeric(df[col_net_elec], errors='coerce').fillna(0).var()
        kpis["Electricity Variance"] = float(elec_variance)

    # Electricity Cost
    col_elec_cost = find_column(df, elec_cols['cost'])
    if col_elec_cost:
        elec_cost = pd.to_numeric(df[col_elec_cost], errors='coerce').fillna(0).clip(lower=0).sum()
        kpis["Electricity Cost"] = float(elec_cost)

    # Electricity Emissions
    col_elec_emis = find_column(df, elec_cols['emis'])
    if col_elec_emis:
        elec_emis = pd.to_numeric(df[col_elec_emis], errors='coerce').fillna(0).clip(lower=0).sum()
        kpis["Electricity Emissions"] = float(elec_emis)

    # Daily Peak Average (average of daily maximum consumption)
    if col_net_elec:
        # Group by day and get daily max, then average
        df_temp = df.copy()
        df_temp['elec'] = pd.to_numeric(df_temp[col_net_elec], errors='coerce').fillna(0)
        df_temp['date'] = df_temp.index.date if hasattr(df_temp.index, 'date') else pd.to_datetime(df_temp.index).date
        daily_peaks = df_temp.groupby('date')['elec'].max()
        kpis["Daily Peak Average"] = float(daily_peaks.mean()) if len(daily_peaks) > 0 else 0.0

    # ========== FUEL KPIs ==========
    fuel_cols = {
        'cons': ['net_fuel_consumption', 'fuel_consumption', 'Net Fuel Consumption'],
        'cost': ['net_fuel_consumption_cost', 'fuel_cost', 'Net Fuel Cost', 'total_fuel_cost'],
        'emis': ['net_fuel_consumption_emission', 'fuel_emission', 'Net Fuel Emission', 'total_fuel_emissions']
    }

    # Fuel Import (consumption)
    col_fuel_cons = find_column(df, fuel_cols['cons'])
    if col_fuel_cons:
        fuel_import = pd.to_numeric(df[col_fuel_cons], errors='coerce').fillna(0).clip(lower=0).sum()
        kpis["Fuel Import"] = float(fuel_import)

        # Fuel Variance
        fuel_variance = pd.to_numeric(df[col_fuel_cons], errors='coerce').fillna(0).var()
        kpis["Fuel Variance"] = float(fuel_variance)

    # Fuel Cost
    col_fuel_cost = find_column(df, fuel_cols['cost'])
    if col_fuel_cost:
        fuel_cost = pd.to_numeric(df[col_fuel_cost], errors='coerce').fillna(0).clip(lower=0).sum()
        kpis["Fuel Cost"] = float(fuel_cost)

    # Fuel Emissions
    col_fuel_emis = find_column(df, fuel_cols['emis'])
    if col_fuel_emis:
        fuel_emis = pd.to_numeric(df[col_fuel_emis], errors='coerce').fillna(0).clip(lower=0).sum()
        kpis["Fuel Emissions"] = float(fuel_emis)

    # ========== ENERGY DEMANDS (legacy for backward compatibility) ==========
    if "cooling demand" in df.columns:
        kpis["Total Cooling Demand"] = df["cooling demand"].sum()
        kpis["Avg Cooling Demand"] = df["cooling demand"].mean()
        kpis["Max Cooling Demand"] = df["cooling demand"].max()

    if "heating demand" in df.columns:
        kpis["Total Heating Demand"] = df["heating demand"].sum()
        kpis["Avg Heating Demand"] = df["heating demand"].mean()
        kpis["Max Heating Demand"] = df["heating demand"].max()

    # ***FIX 2: Add DHW KPIs***
    if "dhw demand" in df.columns:
        kpis["Total DHW Demand"] = df["dhw demand"].sum()
        kpis["Avg DHW Demand"] = df["dhw demand"].mean()
        kpis["Max DHW Demand"] = df["dhw demand"].max()

    if "cooling demand" in df.columns and "heating demand" in df.columns:
        total_energy = df["cooling demand"].sum() + df["heating demand"].sum()
        if "dhw demand" in df.columns:
            total_energy += df["dhw demand"].sum()
        kpis["Total Energy Demand"] = total_energy

    return kpis


def calculate_action_kpis(df: pd.DataFrame) -> Dict[str, float]:
    """Calculate KPIs from action data."""
    kpis = {}

    if df is None or df.empty:
        return kpis

    for col in df.columns:
        if col in df.columns:
            kpis[f"{col}_mean"] = df[col].mean()
            kpis[f"{col}_std"] = df[col].std()
            kpis[f"{col}_min"] = df[col].min()
            kpis[f"{col}_max"] = df[col].max()
            kpis[f"{col}_range"] = df[col].max() - df[col].min()

            # Action smoothness (variance of differences)
            action_changes = df[col].diff().abs()
            kpis[f"{col}_smoothness"] = action_changes.mean()

    return kpis


# ============================================================================
# DASH APP
# ============================================================================

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "AAC-MADRL Dashboard"

# Discover available data
available_countries = discover_countries()

# --- Define Layout Components ---

header = html.Div([
    html.H1("🏢 AAC-MADRL Algorithm Visualization Dashboard",
            style={'textAlign': 'center', 'color': 'white', 'marginBottom': 10, 'fontWeight': 'bold', 'fontSize': '24px'}),
    html.P(
        "Interactive visualization and comparison of multi-agent reinforcement learning algorithms for building energy management",
        style={'textAlign': 'center', 'color': 'rgba(255,255,255,0.9)', 'marginBottom': 0, 'fontSize': '14px'}),
], style={
    'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    'padding': '20px',
    'marginBottom': '20px',
    'borderRadius': '10px',
    'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
})

controls_section = html.Div([
    html.H3("⚙️ Configuration", style={'marginBottom': '20px', 'color': '#2c3e50'}),
    html.Div([
        # Row 1: Country, Dataset, Season
        html.Div([
            html.Div([
                html.Label("🌍 County",
                           style={'fontWeight': 'bold', 'marginBottom': '5px', 'display': 'block'}),
                dcc.Dropdown(
                    id='country-dropdown',
                    options=[{'label': c, 'value': c} for c in available_countries],
                    value=available_countries[0] if available_countries else None,
                    clearable=False,
                    style={'width': '100%'}
                ),
            ], style={'flex': '1', 'marginRight': '15px'}),

            html.Div([
                html.Label("📁 Dataset", style={'fontWeight': 'bold', 'marginBottom': '5px', 'display': 'block'}),
                dcc.Dropdown(
                    id='dataset-dropdown',
                    clearable=False,
                    style={'width': '100%'}
                ),
            ], style={'flex': '1', 'marginRight': '15px'}),

            html.Div([
                html.Label("🌤️ Season", style={'fontWeight': 'bold', 'marginBottom': '5px', 'display': 'block'}),
                dcc.Dropdown(
                    id='season-dropdown',
                    options=[
                        {'label': '❄️ Winter (Jan 2023)', 'value': 'winter'},
                        {'label': '☀️ Summer (Jul 2023)', 'value': 'summer'},
                    ],
                    value='winter',
                    clearable=False,
                    style={'width': '100%'}
                ),
            ], style={'flex': '1'}),
        ], style={'display': 'flex', 'marginBottom': '20px'}),

        # Row 2: Date Range
        html.Div([
            html.Label("📅 Date Range", style={'fontWeight': 'bold', 'marginBottom': '5px', 'display': 'block'}),
            dcc.DatePickerRange(
                id='date-range',
                start_date='2023-01-01',
                end_date='2023-01-08',
                display_format='YYYY-MM-DD',
                style={'width': '100%'}
            ),
        ], style={'marginBottom': '0'}),
    ]),
], style={
    'marginBottom': '25px',
    'padding': '25px',
    'backgroundColor': '#f8f9fa',
    'borderRadius': '10px',
    'boxShadow': '0 2px 8px rgba(0,0,0,0.05)'
})

algorithm_selection = html.Div([
    html.H3("🤖 Algorithm Selection", style={'marginBottom': '15px', 'color': '#2c3e50'}),
    html.P("Select one or more algorithm configurations to compare:",
           style={'color': '#7f8c8d', 'marginBottom': '15px'}),
    html.Div(id='algorithm-configs-container', children=[]),
], style={
    'marginBottom': '25px',
    'padding': '25px',
    'backgroundColor': '#f8f9fa',
    'borderRadius': '10px',
    'boxShadow': '0 2px 8px rgba(0,0,0,0.05)'
})

building_selection = html.Div([
    html.H3("🏗️ Building Selection", style={'marginBottom': '15px', 'color': '#2c3e50'}),
    html.P(
        "Select one or more buildings to visualize (for KPIs, all selected buildings contribute to district-level metrics):",
        style={'color': '#7f8c8d', 'marginBottom': '15px'}),
    dcc.Checklist(
        id='building-checklist',
        options=[],
        value=[],
        inline=True,
        labelStyle={
            'marginRight': '20px',
            'display': 'inline-block',
            'padding': '8px 15px',
            'backgroundColor': '#e9ecef',  # Updated background
            'borderRadius': '5px',
            'cursor': 'pointer',
            'marginBottom': '10px'
        },
        inputStyle={'marginRight': '8px'}
    ),
], style={
    'marginBottom': '25px',
    'padding': '25px',
    'backgroundColor': '#f8f9fa',
    'borderRadius': '10px',
    'boxShadow': '0 2px 8px rgba(0,0,0,0.05)'
})

tabs = dcc.Tabs(id='tabs', value='tab-temperature', children=[
    dcc.Tab(label='🌡️ Temperature & Comfort', value='tab-temperature',
            style={'padding': '12px', 'fontWeight': 'bold'},
            selected_style={'padding': '12px', 'fontWeight': 'bold', 'backgroundColor': '#667eea',
                            'color': 'white'}),
    dcc.Tab(label='⚡ Energy Demands', value='tab-demands',
            style={'padding': '12px', 'fontWeight': 'bold'},
            selected_style={'padding': '12px', 'fontWeight': 'bold', 'backgroundColor': '#667eea',
                            'color': 'white'}),
    dcc.Tab(label='🎮 Actions', value='tab-actions',
            style={'padding': '12px', 'fontWeight': 'bold'},
            selected_style={'padding': '12px', 'fontWeight': 'bold', 'backgroundColor': '#667eea',
                            'color': 'white'}),
    dcc.Tab(label='🔋 Storage', value='tab-storage',
            style={'padding': '12px', 'fontWeight': 'bold'},
            selected_style={'padding': '12px', 'fontWeight': 'bold', 'backgroundColor': '#667eea',
                            'color': 'white'}),
    dcc.Tab(label='🏙️ District', value='tab-district',
            style={'padding': '12px', 'fontWeight': 'bold'},
            selected_style={'padding': '12px', 'fontWeight': 'bold', 'backgroundColor': '#667eea',
                            'color': 'white'}),
    dcc.Tab(label='📊 KPIs Summary', value='tab-kpis',
            style={'padding': '12px', 'fontWeight': 'bold'},
            selected_style={'padding': '12px', 'fontWeight': 'bold', 'backgroundColor': '#667eea',
                            'color': 'white'}),
    dcc.Tab(label='📈 Comparative Analysis', value='tab-comparison',
            style={'padding': '12px', 'fontWeight': 'bold'},
            selected_style={'padding': '12px', 'fontWeight': 'bold', 'backgroundColor': '#667eea',
                            'color': 'white'}),
], style={'marginBottom': '25px', 'position': 'sticky', 'top': 0, 'backgroundColor': 'white', 'zIndex': 99})

tab_content = html.Div(id='tab-content', style={
    'padding': '25px',
    'backgroundColor': 'white',
    'borderRadius': '10px',
    'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
    'minHeight': '400px'
})

store = dcc.Store(id='algorithms-store')

# --- Main App Layout ---

app.layout = html.Div([
    # --- LEFT COLUMN (SIDEBAR) ---
    html.Div([
        header,
        controls_section,
        algorithm_selection,
        building_selection
    ], style={
        'width': '450px',
        'padding': '25px',
        'backgroundColor': 'white',
        'height': '100vh',
        'overflowY': 'auto',
        'position': 'fixed',
        'left': 0,
        'top': 0,
        'boxShadow': '0 4px 12px rgba(0,0,0,0.1)',
        'zIndex': 100
    }),

    # --- RIGHT COLUMN (MAIN CONTENT) ---
    html.Div([
        tabs,
        tab_content
    ], style={
        'marginLeft': '450px',
        'padding': '30px',
        'minHeight': '100vh',
        'width': 'calc(100% - 450px)'  # Takes up remaining space
    }),

    store

], style={
    'fontFamily': "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    'backgroundColor': '#f5f7fa',
})


# ============================================================================
# CALLBACKS
# ============================================================================

@app.callback(
    Output('dataset-dropdown', 'options'),
    Output('dataset-dropdown', 'value'),
    Input('country-dropdown', 'value')
)
def update_dataset_dropdown(country):
    """Update available datasets when country changes."""
    if not country:
        return [], None

    datasets = discover_datasets(country)
    options = [{'label': d, 'value': d} for d in datasets]
    value = datasets[0] if datasets else None

    return options, value


@app.callback(
    Output('algorithm-configs-container', 'children'),
    Output('algorithms-store', 'data'),
    Input('dataset-dropdown', 'value')
)
def update_algorithm_configs(dataset):
    """Create dynamic algorithm and configuration selectors."""
    if not dataset:
        return [], None

    algorithms = discover_algorithms(dataset)

    if not algorithms:
        return html.Div("No algorithms found in dataset.",
                        style={'color': '#e74c3c', 'padding': '20px', 'textAlign': 'center'}), None

    # Create a container for each algorithm with its configurations
    algorithm_divs = []
    all_configs = {}

    for algo in algorithms:
        configurations = discover_algorithm_configurations(dataset, algo)

        if configurations:
            # Store configurations
            for cfg in configurations:
                all_configs[cfg['key']] = cfg

            # Create checklist for this algorithm's configurations
            config_options = [{'label': f"{algo.replace('_', ' ').title()}: {cfg['display_name']}",
                               'value': cfg['key']} for cfg in configurations]

            # Select first configuration by default
            default_values = [configurations[0]['key']]

            algorithm_divs.append(
                html.Div([
                    html.H4(f"🔹 {algo.replace('_', ' ').title()}",
                            style={'color': '#667eea', 'marginBottom': '10px', 'fontSize': '16px'}),
                    dcc.Checklist(
                        id={'type': 'algo-config-checklist', 'algorithm': algo},
                        options=config_options,
                        value=default_values,
                        inline=True,
                        labelStyle={
                            'marginRight': '15px',
                            'display': 'inline-block',
                            'fontSize': '14px',
                            'padding': '6px 12px',
                            'backgroundColor': '#e9ecef',
                            'borderRadius': '5px',
                            'marginBottom': '8px',
                            'cursor': 'pointer'
                        },
                        inputStyle={'marginRight': '6px'}
                    ),
                ], style={
                    'marginBottom': '20px',
                    'paddingBottom': '15px',
                    'borderBottom': '1px solid #e0e0e0'
                })
            )

    return algorithm_divs, all_configs


@app.callback(
    Output('building-checklist', 'options'),
    Output('building-checklist', 'value'),
    Input('dataset-dropdown', 'value'),
    Input('algorithms-store', 'data')
)
def update_building_checklist(dataset, configs_data):
    """Update available buildings when dataset changes."""
    print(f"[DEBUG] update_building_checklist called: dataset={dataset}, configs_data={configs_data is not None}")

    if not dataset:
        print("[DEBUG] No dataset selected")
        return [], []

    if not configs_data:
        print("[DEBUG] No configurations data available")
        return [], []

    try:
        # Get number of buildings from first configuration
        if not configs_data:
            print("[DEBUG] configs_data is empty")
            return [], []

        first_config = list(configs_data.values())[0]
        print(f"[DEBUG] First configuration: {first_config.get('key', 'unknown')}")

        n_buildings = get_num_buildings(dataset, first_config)
        print(f"[DEBUG] Found {n_buildings} buildings")

        if n_buildings == 0:
            print(f"[WARNING] No buildings found for dataset {dataset}")
            return [], []

        options = [{'label': f'Building {i}', 'value': i} for i in range(n_buildings)]
        # Select first building by default
        default_values = [0]

        return options, default_values

    except Exception as e:
        print(f"[ERROR] Error in update_building_checklist: {e}")
        import traceback
        traceback.print_exc()
        return [], []


@app.callback(
    Output('date-range', 'start_date'),
    Output('date-range', 'end_date'),
    Input('season-dropdown', 'value')
)
def update_date_range(season):
    """Update date range based on season."""
    if season == 'summer':
        return '2023-07-01', '2023-07-08'
    else:
        return '2023-01-01', '2023-01-08'


@app.callback(
    Output('tab-content', 'children'),
    Input('tabs', 'value'),
    Input('dataset-dropdown', 'value'),
    Input('building-checklist', 'value'),
    Input('season-dropdown', 'value'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date'),
    Input({'type': 'algo-config-checklist', 'algorithm': dash.dependencies.ALL}, 'value'),
    State('algorithms-store', 'data')
)
def render_tab_content(tab, dataset, selected_buildings, season,
                       start_date, end_date, all_config_selections, configs_data):
    """Render content based on selected tab."""
    print(f"[DEBUG] render_tab_content called:")
    print(f"  - tab: {tab}")
    print(f"  - dataset: {dataset}")
    print(f"  - selected_buildings: {selected_buildings}")
    print(f"  - all_config_selections: {all_config_selections}")
    print(f"  - configs_data: {configs_data is not None}")

    # Collect selected configurations from all algorithm checkboxes
    selected_configs = []
    if all_config_selections:
        for selections in all_config_selections:
            if selections:  # If this checklist has selections
                selected_configs.extend(selections)

    # If no configs collected, try to get all available configs
    if not selected_configs and configs_data:
        # Use all available configurations (for initial load)
        selected_configs = list(configs_data.keys())[:3]  # Limit to first 3

    print(f"  - selected_configs: {selected_configs}")

    if not all([dataset, selected_buildings, selected_configs, configs_data]):
        missing = []
        if not dataset:
            missing.append("dataset")
        if not selected_buildings:
            missing.append("building(s)")
        if not selected_configs:
            missing.append("configuration(s)")
        if not configs_data:
            missing.append("configurations data")

        print(f"[WARNING] Missing parameters: {', '.join(missing)}")
        return html.Div([
            html.Div("⚠️", style={'fontSize': '48px', 'marginBottom': '20px'}),
            html.H4(f"Please select all required parameters", style={'color': '#7f8c8d'}),
            html.P(f"Missing: {', '.join(missing)}", style={'color': '#95a5a6'})
        ], style={'textAlign': 'center', 'padding': '80px'})

    try:
        if tab == 'tab-temperature':
            return render_temperature_tab(dataset, selected_buildings, selected_configs, season,
                                          start_date, end_date, configs_data)
        elif tab == 'tab-demands':
            return render_demands_tab(dataset, selected_buildings, selected_configs, season,
                                      start_date, end_date, configs_data)
        elif tab == 'tab-actions':
            return render_actions_tab(dataset, selected_buildings, selected_configs, season,
                                      start_date, end_date, configs_data)
        elif tab == 'tab-storage':
            return render_storage_tab(dataset, selected_buildings, selected_configs, season,
                                      start_date, end_date, configs_data)
        elif tab == 'tab-district':
            return render_district_tab(dataset, selected_buildings, selected_configs, season,
                                      start_date, end_date, configs_data)
        elif tab == 'tab-kpis':
            return render_kpis_tab(dataset, selected_buildings, selected_configs, season,
                                   start_date, end_date, configs_data)
        elif tab == 'tab-comparison':
            return render_comparison_tab(dataset, selected_buildings, selected_configs, season,
                                         start_date, end_date, configs_data)

        return html.Div("Tab not implemented yet.")

    except Exception as e:
        print(f"[ERROR] Error rendering tab {tab}: {e}")
        import traceback
        traceback.print_exc()
        return html.Div([
            html.Div("❌", style={'fontSize': '48px', 'marginBottom': '20px'}),
            html.H4(f"Error rendering visualization", style={'color': '#e74c3c'}),
            html.P(str(e), style={'color': '#95a5a6', 'fontFamily': 'monospace'})
        ], style={'textAlign': 'center', 'padding': '80px'})


def render_temperature_tab(dataset, selected_buildings, selected_configs, season,
                           start_date, end_date, configs_data):
    """Render temperature and comfort visualization for multiple buildings."""
    print(
        f"[DEBUG] render_temperature_tab: Loading data for {len(selected_configs)} configuration(s) and {len(selected_buildings)} building(s)")

    # Create subplots for each building
    n_buildings = len(selected_buildings)

    # Calculate dynamic spacing based on number of buildings
    # More buildings = tighter spacing to maintain readability
    vertical_spacing = max(0.02, min(0.05, 1.0 / (n_buildings * 20)))

    fig = make_subplots(
        rows=n_buildings, cols=1,
        subplot_titles=[f"Building {bid}" for bid in selected_buildings],
        shared_xaxes=True,
        vertical_spacing=vertical_spacing
    )

    data_loaded = False
    outdoor_temp_plotted = False  # Track if we've plotted outdoor temperature

    # Load data for each building
    for bldg_idx, building_id in enumerate(selected_buildings, start=1):
        first_config_for_building = True

        # Load data for each selected configuration
        for i, config_key in enumerate(selected_configs):
            config = configs_data[config_key]
            print(f"[DEBUG] Loading Building {building_id}, Config: {config.get('display_name', 'unknown')}")

            # Create full legend name
            algo_name_formatted = config['algorithm'].replace('_', ' ').title()
            config_display_name = config['display_name']
            legend_name = f"{algo_name_formatted}: {config_display_name}"

            df = load_observation_data(dataset, config, building_id, season)

            if df is None or df.empty:
                print(f"[WARNING] No data loaded for Building {building_id}, {config.get('display_name', 'unknown')}")
                continue

            print(f"[DEBUG] Loaded {len(df)} rows")
            data_loaded = True

            # Filter by date range
            df_filtered = df.loc[start_date:end_date]

            if df_filtered.empty:
                continue

            color = COLORS[i % len(COLORS)]

            # Indoor temperature
            if 'tin' in df_filtered.columns:
                fig.add_trace(go.Scatter(
                    x=df_filtered.index,
                    y=df_filtered['tin'],
                    name=legend_name + (f" - B{building_id}" if n_buildings > 1 else ""),
                    line=dict(color=color, width=2.5),
                    mode='lines',
                    showlegend=(bldg_idx == 1)  # Only show legend for first building
                ), row=bldg_idx, col=1)

            # Comfort bounds (only for first config of each building)
            if first_config_for_building:
                if 'comfort_low' in df_filtered.columns and 'comfort_high' in df_filtered.columns:
                    fig.add_trace(go.Scatter(
                        x=df_filtered.index,
                        y=df_filtered['comfort_high'],
                        name='Comfort Band',
                        line=dict(color='rgba(255, 243, 176, 0)', width=0),
                        showlegend=False,
                        hoverinfo='skip'
                    ), row=bldg_idx, col=1)
                    fig.add_trace(go.Scatter(
                        x=df_filtered.index,
                        y=df_filtered['comfort_low'],
                        name='Comfort Band',
                        fill='tonexty',
                        fillcolor='rgba(255, 200, 100, 0.2)',
                        line=dict(color='rgba(255, 200, 100, 0)', width=0),
                        showlegend=(bldg_idx == 1),
                        hoverinfo='skip'
                    ), row=bldg_idx, col=1)

                # Setpoint
                if 'sp' in df_filtered.columns:
                    fig.add_trace(go.Scatter(
                        x=df_filtered.index,
                        y=df_filtered['sp'],
                        name='Setpoint',
                        line=dict(color='black', width=1.5, dash='dash'),
                        mode='lines',
                        showlegend=(bldg_idx == 1)
                    ), row=bldg_idx, col=1)

                first_config_for_building = False

            # Outdoor temperature - plot only once for first building, first config
            if not outdoor_temp_plotted and 'tout' in df_filtered.columns:
                fig.add_trace(go.Scatter(
                    x=df_filtered.index,
                    y=df_filtered['tout'],
                    name="Outdoor T",
                    line=dict(color='gray', width=1.5, dash='dot'),
                    mode='lines',
                    opacity=0.5,
                    showlegend=True
                ), row=bldg_idx, col=1)
                outdoor_temp_plotted = True

    if not data_loaded:
        return html.Div([
            html.Div("📊", style={'fontSize': '48px', 'marginBottom': '20px'}),
            html.H4("No data could be loaded", style={'color': '#e74c3c'}),
            html.P("Please check that CSV files exist for the selected configurations.",
                   style={'color': '#95a5a6'})
        ], style={'textAlign': 'center', 'padding': '80px'})

    # Update axes
    for i in range(1, n_buildings + 1):
        fig.update_yaxes(title_text="Temperature (°C)", row=i, col=1)

    fig.update_xaxes(title_text="Time", row=n_buildings, col=1)

    # Calculate height: minimum 350px per subplot to maintain readability
    # This ensures plots don't become too thin when many buildings are selected
    plot_height = max(350 * n_buildings, 400)

    fig.update_layout(
        title=dict(
            text=f"",
            font=dict(size=18, color='#2c3e50')
        ),
        hovermode='x unified',
        height=plot_height,
        template='plotly_white',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(255,255,255,0.8)'
        )
    )

    # Add colored background rectangles for better building separation
    # Using proper subplot domain calculation
    if n_buildings > 1:
        # Get actual subplot positions from figure layout
        for i in range(1, n_buildings + 1):
            if i % 2 == 0:
                # Access the subplot's yaxis domain
                yaxis_name = f'yaxis{i}' if i > 1 else 'yaxis'

                # Calculate approximate domain based on equal spacing
                # Accounting for vertical_spacing
                subplot_height = (1.0 - vertical_spacing * (n_buildings - 1)) / n_buildings
                spacing_total = vertical_spacing * (i - 1)

                # Position from bottom (Plotly uses bottom-to-top)
                y_bottom = (n_buildings - i) * (subplot_height + vertical_spacing)
                y_top = y_bottom + subplot_height

                fig.add_shape(
                    type="rect",
                    xref="paper", yref="paper",
                    x0=0, y0=y_bottom,
                    x1=1, y1=y_top,
                    layer="below",
                    line=dict(color="rgba(100, 150, 200, 0.3)", width=0),  # Add subtle border
                )

    return dcc.Graph(figure=fig, config={'displayModeBar': True, 'displaylogo': False})


def render_demands_tab(dataset, selected_buildings, selected_configs, season,
                       start_date, end_date, configs_data):
    """Render energy demands visualization for multiple buildings."""
    # OPTIMIZATION: Limit to first 5 buildings for better performance
    MAX_BUILDINGS_DEMANDS = 5
    original_count = len(selected_buildings)
    selected_buildings_limited = list(selected_buildings)[:MAX_BUILDINGS_DEMANDS]
    show_warning = original_count > MAX_BUILDINGS_DEMANDS

    n_buildings = len(selected_buildings_limited)
    total_rows = n_buildings * 3  # 3 demand types per building

    # Calculate dynamic spacing based on number of rows
    # Must be less than 1/(total_rows - 1) to avoid errors
    # More rows = tighter spacing to maintain readability
    max_allowed_spacing = 1.0 / (total_rows - 1) if total_rows > 1 else 0.03
    vertical_spacing = max(0.01, min(0.03, max_allowed_spacing * 0.8))  # Use 80% of max to be safe

    # ***FIX 2: Update rows and titles for 3 demands***
    fig = make_subplots(
        rows=total_rows, cols=1,
        subplot_titles=[item for bid in selected_buildings_limited for item in
                        (f"Building {bid} - Cooling", f"Building {bid} - Heating", f"Building {bid} - DHW")],
        shared_xaxes=True,
        vertical_spacing=vertical_spacing
    )

    # Load data for each building
    for bldg_idx, building_id in enumerate(selected_buildings_limited):
        # ***FIX 2: Update row indices***
        row_cooling = bldg_idx * 3 + 1
        row_heating = bldg_idx * 3 + 2
        row_dhw = bldg_idx * 3 + 3

        # Load data for each selected configuration
        for i, config_key in enumerate(selected_configs):
            config = configs_data[config_key]

            # Create full legend name
            algo_name_formatted = config['algorithm'].replace('_', ' ').title()
            config_display_name = config['display_name']
            legend_name = f"{algo_name_formatted}: {config_display_name}"

            df = load_observation_data(dataset, config, building_id, season)

            if df is None or df.empty:
                continue

            # Filter by date range
            df_filtered = df.loc[start_date:end_date]

            if df_filtered.empty:
                continue

            color = COLORS[i % len(COLORS)]

            # Cooling demand
            if 'cooling demand' in df_filtered.columns:
                fig.add_trace(go.Scatter(
                    x=df_filtered.index,
                    y=df_filtered['cooling demand'],
                    name=legend_name + (f" - B{building_id}" if n_buildings > 1 else ""),
                    line=dict(color=color, width=2.5),
                    mode='lines',
                    showlegend=(bldg_idx == 0)
                ), row=row_cooling, col=1)

            # Heating demand
            if 'heating demand' in df_filtered.columns:
                fig.add_trace(go.Scatter(
                    x=df_filtered.index,
                    y=df_filtered['heating demand'],
                    name=legend_name + (f" - B{building_id}" if n_buildings > 1 else ""),
                    line=dict(color=color, width=2.5),
                    mode='lines',
                    showlegend=False
                ), row=row_heating, col=1)

            # DHW demand
            if 'dhw demand' in df_filtered.columns:
                fig.add_trace(go.Scatter(
                    x=df_filtered.index,
                    y=df_filtered['dhw demand'],
                    name=legend_name + (f" - B{building_id}" if n_buildings > 1 else ""),
                    line=dict(color=color, width=2.5),
                    mode='lines',
                    showlegend=False
                ), row=row_dhw, col=1)

    # Update axes
    # ***FIX 2: Update axis loop***
    for i in range(1, n_buildings * 3 + 1):
        fig.update_yaxes(title_text="Power (kW)", row=i, col=1)
    fig.update_xaxes(title_text="Time", row=n_buildings * 3, col=1)

    # Calculate height: minimum 250px per subplot (demand type) to maintain readability
    # This ensures plots don't become too thin when many buildings are selected
    # With 20 buildings × 3 demands = 60 subplots, height will be 15,000px
    plot_height = max(250 * n_buildings * 3, 600)

    fig.update_layout(
        title=dict(
            text=f"Energy Demands - {len(selected_buildings)} Building(s), {len(selected_configs)} Configuration(s)",
            font=dict(size=18, color='#2c3e50')
        ),
        hovermode='x unified',
        height=plot_height,
        template='plotly_white',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(255,255,255,0.8)'
        )
    )

    # Add colored background rectangles to visually group the 3 demand types per building
    if n_buildings > 1:
        total_rows = n_buildings * 3

        # Calculate subplot dimensions
        subplot_height = (1.0 - vertical_spacing * (total_rows - 1)) / total_rows

        for bldg_idx in range(n_buildings):
            if bldg_idx % 2 != 0:
                # Calculate the domain for all 3 rows of this building
                rows_start = bldg_idx * 3  # 0, 3, 6, 9, ...
                rows_end = rows_start + 3   # 3, 6, 9, 12, ...

                # Position from bottom (Plotly uses bottom-to-top, row 1 is at top)
                y_bottom = (total_rows - rows_end) * (subplot_height + vertical_spacing)
                y_top = (total_rows - rows_start) * (subplot_height + vertical_spacing)

                fig.add_shape(
                    type="rect",
                    xref="paper", yref="paper",
                    x0=0, y0=y_bottom,
                    x1=1, y1=y_top,
                    fillcolor="rgba(135, 206, 235, 0.1)",  # Sky blue with 20% opacity
                    layer="below",
                    line=dict(color="rgba(100, 150, 200, 0.3)", width=1),  # Add subtle border
                )

    # Create the graph component
    graph_component = dcc.Graph(figure=fig, config={'displayModeBar': True, 'displaylogo': False})

    # Add warning if buildings were limited
    if show_warning:
        return html.Div([
            html.Div([
                html.Span("⚠️ ", style={'fontSize': '20px', 'marginRight': '10px'}),
                html.Span(f"Performance Optimization: Showing first {MAX_BUILDINGS_DEMANDS} of {original_count} selected buildings. ",
                         style={'fontWeight': 'bold', 'color': '#e67e22'}),
                html.Span(f"Reduce selection to see specific buildings.",
                         style={'color': '#7f8c8d'})
            ], style={
                'backgroundColor': '#fff3cd',
                'border': '1px solid #ffc107',
                'borderRadius': '5px',
                'padding': '12px 20px',
                'marginBottom': '15px',
                'display': 'flex',
                'alignItems': 'center'
            }),
            graph_component
        ])

    return graph_component


def render_actions_tab(dataset, selected_buildings, selected_configs, season,
                       start_date, end_date, configs_data):
    """Render actions visualization for multiple buildings."""
    # OPTIMIZATION: Limit to first 5 buildings for better performance
    MAX_BUILDINGS_ACTIONS = 5
    original_count = len(selected_buildings)
    selected_buildings_limited = list(selected_buildings)[:MAX_BUILDINGS_ACTIONS]
    show_warning = original_count > MAX_BUILDINGS_ACTIONS

    n_buildings = len(selected_buildings_limited)
    n_action_cols = len(ACTION_COLUMNS)
    total_rows = n_buildings * n_action_cols  # Each building gets all action columns

    # Calculate dynamic spacing based on number of rows
    max_allowed_spacing = 1.0 / (total_rows - 1) if total_rows > 1 else 0.08
    vertical_spacing = max(0.01, min(0.08, max_allowed_spacing * 0.8))

    # Create subplot titles for each building and action
    subplot_titles = [f"Building {bid} - {col.replace('_', ' ').title()}"
                      for bid in selected_buildings_limited
                      for col in ACTION_COLUMNS]

    fig = make_subplots(
        rows=total_rows, cols=1,
        subplot_titles=subplot_titles,
        shared_xaxes=True,
        vertical_spacing=vertical_spacing
    )

    # Load data for each building
    for bldg_idx, building_id in enumerate(selected_buildings_limited):
        # Calculate row indices for this building's action columns
        base_row = bldg_idx * n_action_cols

        # Load data for each selected configuration
        for i, config_key in enumerate(selected_configs):
            config = configs_data[config_key]

            # Create full legend name
            algo_name_formatted = config['algorithm'].replace('_', ' ').title()
            config_display_name = config['display_name']
            legend_name = f"{algo_name_formatted}: {config_display_name}"

            df = load_action_data(dataset, config, building_id, season)

            if df is None or df.empty:
                continue

            # Filter by date range
            df_filtered = df.loc[start_date:end_date]

            if df_filtered.empty:
                continue

            color = COLORS[i % len(COLORS)]

            # Plot each action dimension for this building
            for action_idx, col_name in enumerate(ACTION_COLUMNS):
                row_num = base_row + action_idx + 1  # +1 because rows are 1-indexed

                if col_name in df_filtered.columns:
                    fig.add_trace(go.Scatter(
                        x=df_filtered.index,
                        y=df_filtered[col_name],
                        name=legend_name + (f" - B{building_id}" if n_buildings > 1 else ""),
                        line=dict(color=color, width=2.5),
                        mode='lines',
                        showlegend=(bldg_idx == 0 and action_idx == 0)  # Only show legend once
                    ), row=row_num, col=1)

    # Update axes
    for i in range(1, total_rows + 1):
        fig.update_yaxes(title_text="Action Value", row=i, col=1)
    fig.update_xaxes(title_text="Time", row=total_rows, col=1)

    # Calculate height: minimum 200px per subplot to maintain readability
    plot_height = max(200 * total_rows, 800)

    fig.update_layout(
        title=dict(
            text=f"Controller Actions - {n_buildings} Building(s), {len(selected_configs)} Configuration(s)",
            font=dict(size=18, color='#2c3e50')
        ),
        hovermode='x unified',
        height=plot_height,
        template='plotly_white',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(255,255,255,0.8)'
        )
    )

    # Add colored background rectangles to visually group actions per building
    if n_buildings > 1:
        subplot_height = (1.0 - vertical_spacing * (total_rows - 1)) / total_rows

        for bldg_idx in range(n_buildings):
            if bldg_idx % 2 != 0:
                # Calculate the domain for all action rows of this building
                rows_start = bldg_idx * n_action_cols
                rows_end = rows_start + n_action_cols

                # Position from bottom (Plotly uses bottom-to-top)
                y_bottom = (total_rows - rows_end) * (subplot_height + vertical_spacing)
                y_top = (total_rows - rows_start) * (subplot_height + vertical_spacing)

                fig.add_shape(
                    type="rect",
                    xref="paper", yref="paper",
                    x0=0, y0=y_bottom,
                    x1=1, y1=y_top,
                    fillcolor="rgba(135, 206, 235, 0.2)",  # Sky blue with 20% opacity
                    layer="below",
                    line=dict(color="rgba(100, 150, 200, 0.3)", width=1),
                )

    # Calculate action KPIs for all buildings (limited list)
    kpi_data = []
    for building_id in selected_buildings_limited:
        for config_key in selected_configs:
            config = configs_data[config_key]
            df = load_action_data(dataset, config, building_id, season)

            if df is not None and not df.empty:
                df_filtered = df.loc[start_date:end_date]
                kpis = calculate_action_kpis(df_filtered)

                # Create full legend name for table
                algo_name_formatted = config['algorithm'].replace('_', ' ').title()
                config_display_name = config['display_name']
                kpis['Building'] = f"Building {building_id}"
                kpis['Configuration'] = f"{algo_name_formatted}: {config_display_name}"

                kpi_data.append(kpis)

    # Create KPI summary table
    if kpi_data:
        kpi_df = pd.DataFrame(kpi_data)

        # Select interesting metrics
        metrics_to_show = [col for col in kpi_df.columns
                           if any(x in col for x in ['mean', 'std', 'smoothness', 'range'])]

        # Improved table styling
        table = html.Div([
            html.H4("📈 Action Statistics Summary",
                    style={'marginTop': 30, 'marginBottom': 15, 'color': '#2c3e50'}),
            html.Div([
                html.Table([
                    html.Thead(
                        html.Tr([html.Th('Building', style={
                            'backgroundColor': '#667eea',
                            'color': 'white',
                            'padding': '12px',
                            'textAlign': 'left',
                            'borderRadius': '5px 0 0 0'
                        })] +
                                [html.Th('Configuration', style={
                                    'backgroundColor': '#667eea',
                                    'color': 'white',
                                    'padding': '12px',
                                    'textAlign': 'left'
                                })] +
                                [html.Th(m.replace('_', ' ').title(), style={
                                    'backgroundColor': '#667eea',
                                    'color': 'white',
                                    'padding': '12px',
                                    'textAlign': 'center'
                                }) for m in metrics_to_show])
                    ),
                    html.Tbody([
                        html.Tr([
                                    html.Td(row['Building'], style={
                                        'padding': '12px',
                                        'borderBottom': '1px solid #e0e0e0',
                                        'fontWeight': '600',
                                        'color': '#2c3e50'
                                    })] +
                                    [html.Td(row['Configuration'], style={
                                        'padding': '12px',
                                        'borderBottom': '1px solid #e0e0e0',
                                        'fontWeight': '600',
                                        'color': '#2c3e50'
                                    })] +
                                [html.Td(f"{row.get(m, 0):.4f}", style={
                                    'padding': '12px',
                                    'borderBottom': '1px solid #e0e0e0',
                                    'textAlign': 'center',
                                    'fontFamily': 'monospace'
                                }) for m in metrics_to_show],
                                style={'backgroundColor': '#f8f9fa' if idx % 2 == 0 else 'white'}
                                )
                        for idx, (_, row) in enumerate(kpi_df.iterrows())
                    ])
                ], style={
                    'width': '100%',
                    'borderCollapse': 'collapse',
                    'marginTop': 10,
                    'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
                    'borderRadius': '8px',
                    'overflow': 'hidden'
                }),
            ], style={'overflowX': 'auto'})
        ])

        graph_and_table = html.Div([
            dcc.Graph(figure=fig, config={'displayModeBar': True, 'displaylogo': False}),
            table
        ])

        # Add warning if buildings were limited
        if show_warning:
            return html.Div([
                html.Div([
                    html.Span("⚠️ ", style={'fontSize': '20px', 'marginRight': '10px'}),
                    html.Span(f"Performance Optimization: Showing first {MAX_BUILDINGS_ACTIONS} of {original_count} selected buildings. ",
                             style={'fontWeight': 'bold', 'color': '#e67e22'}),
                    html.Span(f"Reduce selection to see specific buildings.",
                             style={'color': '#7f8c8d'})
                ], style={
                    'backgroundColor': '#fff3cd',
                    'border': '1px solid #ffc107',
                    'borderRadius': '5px',
                    'padding': '12px 20px',
                    'marginBottom': '15px',
                    'display': 'flex',
                    'alignItems': 'center'
                }),
                graph_and_table
            ])

        return graph_and_table

    # No table case - just graph
    graph_component = dcc.Graph(figure=fig, config={'displayModeBar': True, 'displaylogo': False})

    if show_warning:
        return html.Div([
            html.Div([
                html.Span("⚠️ ", style={'fontSize': '20px', 'marginRight': '10px'}),
                html.Span(f"Performance Optimization: Showing first {MAX_BUILDINGS_ACTIONS} of {original_count} selected buildings. ",
                         style={'fontWeight': 'bold', 'color': '#e67e22'}),
                html.Span(f"Reduce selection to see specific buildings.",
                         style={'color': '#7f8c8d'})
            ], style={
                'backgroundColor': '#fff3cd',
                'border': '1px solid #ffc107',
                'borderRadius': '5px',
                'padding': '12px 20px',
                'marginBottom': '15px',
                'display': 'flex',
                'alignItems': 'center'
            }),
            graph_component
        ])

    return graph_component


def render_kpis_tab(dataset, selected_buildings, selected_configs, season,
                    start_date, end_date, configs_data):
    """Render District-level KPIs summary - Uses district_obs.csv for aggregate electricity/fuel metrics."""

    print(f"[DEBUG] render_kpis_tab: Calculating district-level KPIs for {len(selected_buildings)} buildings")

    # Collect KPIs for all configurations at DISTRICT LEVEL
    all_kpis = []

    for config_key in selected_configs:
        config = configs_data[config_key]

        # Create full legend name
        algo_name_formatted = config['algorithm'].replace('_', ' ').title()
        config_display_name = config['display_name']
        full_config_name = f"{algo_name_formatted}: {config_display_name}"

        # Initialize district-level accumulators
        district_kpis = {
            'Configuration': full_config_name,
            # Comfort (from individual buildings)
            'district_violations_total': 0,
            'district_violations_above': 0,
            'district_violations_below': 0,
            'violations_above_severity': [],
            'violations_below_severity': [],
            'total_timesteps': 0
        }

        # Load DISTRICT-LEVEL data for electricity and fuel KPIs
        df_district = load_district_observation_data(dataset, config, season)

        # Filter by date range
        if df_district is not None and not df_district.empty:
            df_district_filtered = df_district.loc[start_date:end_date]
        else:
            df_district_filtered = None
            print(f"[WARNING] No district data available for {config['display_name']}")

        # Aggregate COMFORT KPIs across all selected buildings (requires individual building data)
        for building_id in selected_buildings:
            df_obs = load_observation_data(dataset, config, building_id, season)

            if df_obs is not None and not df_obs.empty:
                df_filtered = df_obs.loc[start_date:end_date]

                if not df_filtered.empty:
                    district_kpis['total_timesteps'] += len(df_filtered)

                    # ===== COMFORT VIOLATIONS =====
                    if all(col in df_filtered.columns for col in ["tin", "comfort_low", "comfort_high"]):
                        violations_above = (df_filtered["tin"] > df_filtered["comfort_high"]).sum()
                        violations_below = (df_filtered["tin"] < df_filtered["comfort_low"]).sum()

                        district_kpis['district_violations_total'] += violations_above + violations_below
                        district_kpis['district_violations_above'] += violations_above
                        district_kpis['district_violations_below'] += violations_below

                        # Severity
                        temp_above = (df_filtered["tin"] - df_filtered["comfort_high"]).clip(lower=0)
                        temp_below = (df_filtered["comfort_low"] - df_filtered["tin"]).clip(lower=0)

                        if temp_above.sum() > 0:
                            district_kpis['violations_above_severity'].append(temp_above[temp_above > 0].mean())
                        if temp_below.sum() > 0:
                            district_kpis['violations_below_severity'].append(temp_below[temp_below > 0].mean())

        # ===== ELECTRICITY & FUEL KPIs (from district_obs.csv) =====
        # These are already aggregated at district level in district_obs.csv
        elec_import = 0
        elec_variance = 0
        elec_cost = 0
        elec_emissions = 0
        daily_peak_avg = 0
        fuel_import = 0
        fuel_variance = 0
        fuel_cost = 0
        fuel_emissions = 0

        if df_district_filtered is not None and not df_district_filtered.empty:
            # Electricity columns
            elec_cols = {
                'net': ['net electricity consumption', 'net_electricity_consumption'],
                'pos': ['positive net electricity consumption', 'positive_net_electricity_consumption'],
                'cost': ['net electricity cost', 'net_electricity_cost'],
                'emis': ['net electricity emission', 'net_electricity_emission']
            }

            # Electricity Import
            col_pos_elec = find_column(df_district_filtered, elec_cols['pos'])
            if col_pos_elec:
                elec_import = pd.to_numeric(df_district_filtered[col_pos_elec], errors='coerce').fillna(0).clip(
                    lower=0).sum()

            # Electricity Variance
            col_net_elec = find_column(df_district_filtered, elec_cols['net'])
            if col_net_elec:
                net_values = pd.to_numeric(df_district_filtered[col_net_elec], errors='coerce').fillna(0)
                elec_variance = net_values.var()

                # Daily Peak Average
                df_temp = df_district_filtered.copy()
                df_temp['elec'] = net_values
                df_temp['date'] = df_temp.index.date if hasattr(df_temp.index,
                                                               'date') else pd.to_datetime(df_temp.index).date
                daily_max = df_temp.groupby('date')['elec'].max()
                daily_peak_avg = daily_max.mean() if len(daily_max) > 0 else 0

            # Electricity Cost
            col_elec_cost = find_column(df_district_filtered, elec_cols['cost'])
            if col_elec_cost:
                elec_cost = pd.to_numeric(df_district_filtered[col_elec_cost], errors='coerce').fillna(0).clip(
                    lower=0).sum()

            # Electricity Emissions
            col_elec_emis = find_column(df_district_filtered, elec_cols['emis'])
            if col_elec_emis:
                elec_emissions = pd.to_numeric(df_district_filtered[col_elec_emis], errors='coerce').fillna(0).clip(
                    lower=0).sum()

            # Fuel columns
            fuel_cols = {
                'cons': ['net fuel consumption', 'net_fuel_consumption'],
                'cost': ['net fuel cost', 'net_fuel_cost'],
                'emis': ['net fuel emission', 'net_fuel_emission']
            }

            # Fuel Import
            col_fuel_cons = find_column(df_district_filtered, fuel_cols['cons'])
            if col_fuel_cons:
                fuel_values = pd.to_numeric(df_district_filtered[col_fuel_cons], errors='coerce').fillna(0)
                fuel_import = fuel_values.clip(lower=0).sum()
                fuel_variance = fuel_values.var()

            # Fuel Cost
            col_fuel_cost = find_column(df_district_filtered, fuel_cols['cost'])
            if col_fuel_cost:
                fuel_cost = pd.to_numeric(df_district_filtered[col_fuel_cost], errors='coerce').fillna(0).clip(
                    lower=0).sum()

            # Fuel Emissions
            col_fuel_emis = find_column(df_district_filtered, fuel_cols['emis'])
            if col_fuel_emis:
                fuel_emissions = pd.to_numeric(df_district_filtered[col_fuel_emis], errors='coerce').fillna(0).clip(
                    lower=0).sum()

        # Calculate final district KPIs
        n_buildings = len(selected_buildings)
        final_kpis = {
            'Configuration': full_config_name,
            # Comfort
            'Avg Num Comfort Violations': district_kpis['district_violations_total'] / n_buildings if n_buildings > 0 else 0,
            'Avg Comfort Violation Above (°C)': np.mean(
                district_kpis['violations_above_severity']) if district_kpis['violations_above_severity'] else 0,
            'Avg Comfort Violation Below (°C)': np.mean(
                district_kpis['violations_below_severity']) if district_kpis['violations_below_severity'] else 0,
            'Avg Num Comfort Violations Above': district_kpis['district_violations_above'] / n_buildings if n_buildings > 0 else 0,
            'Avg Num Comfort Violations Below': district_kpis['district_violations_below'] / n_buildings if n_buildings > 0 else 0,
            'Comfort Violation Rate (%)': (district_kpis['district_violations_total'] / district_kpis[
                'total_timesteps'] * 100) if district_kpis['total_timesteps'] > 0 else 0,
            # Electricity (from district_obs.csv)
            'Electricity Import': float(elec_import),
            'Electricity Variance': float(elec_variance),
            'Electricity Cost': float(elec_cost),
            'Electricity Emissions': float(elec_emissions),
            'Daily Peak Average': float(daily_peak_avg),
            # Fuel (from district_obs.csv)
            'Fuel Import': float(fuel_import),
            'Fuel Variance': float(fuel_variance),
            'Fuel Cost': float(fuel_cost),
            'Fuel Emissions': float(fuel_emissions),
        }

        all_kpis.append(final_kpis)

    if not all_kpis:
        return html.Div([
            html.Div("📊", style={'fontSize': '48px', 'marginBottom': '20px'}),
            html.H4("No KPI data available", style={'color': '#e74c3c'}),
            html.P("No data available for selected configurations.", style={'color': '#95a5a6'})
        ], style={'textAlign': 'center', 'padding': '80px'})

    kpi_df = pd.DataFrame(all_kpis)

    # Define KPI categories for visualization
    kpi_categories = {
        'Comfort Violations': {
            'metrics': [
                'Avg Num Comfort Violations',
                'Comfort Violation Rate (%)',
                'Avg Comfort Violation Above (°C)',
                'Avg Comfort Violation Below (°C)'
            ],
            'icon': '🌡️',
            'color': '#e74c3c'
        },
        'Electricity': {
            'metrics': [
                'Electricity Import',
                'Electricity Cost',
                'Electricity Emissions',
                'Daily Peak Average'
            ],
            'icon': '⚡',
            'color': '#3498db'
        },
        'Fuel': {
            'metrics': [
                'Fuel Import',
                'Fuel Cost',
                'Fuel Emissions'
            ],
            'icon': '🔥',
            'color': '#e67e22'
        }
    }

    # Create bar charts for each category
    charts = []
    for category, info in kpi_categories.items():
        metrics = info['metrics']
        # Filter to available metrics
        available_metrics = [m for m in metrics if m in kpi_df.columns and kpi_df[m].sum() != 0]

        if not available_metrics:
            continue

        # Create SEPARATE bar charts for each metric
        metric_charts = []
        for metric in available_metrics:
            # Create individual bar chart for this metric
            fig = go.Figure()

            # Get max value for axis padding
            max_val = kpi_df[metric].max()
            # Give 25% padding at the top for the text
            y_axis_range = [0, max_val * 1.25] if max_val > 0 else [0, 1]

            # Add one bar per configuration
            colors_list = [COLORS[i % len(COLORS)] for i in range(len(kpi_df))]

            fig.add_trace(go.Bar(
                x=kpi_df['Configuration'],
                y=kpi_df[metric],
                text=kpi_df[metric].round(2),
                textposition='outside',
                marker=dict(
                    color=colors_list,
                    line=dict(color='rgba(0,0,0,0.1)', width=1)
                ),
                hovertemplate='<b>%{x}</b><br>' + metric + ': %{y:.2f}<extra></extra>'
            ))

            fig.update_layout(
                title=dict(
                    text=metric,
                    font=dict(size=14, color='#2c3e50'),
                    x=0.5,
                    xanchor='center'
                ),
                template='plotly_white',
                height=350,
                showlegend=False,
                xaxis=dict(
                    title='',
                    tickangle=-45 if len(kpi_df) > 3 else 0
                ),
                yaxis=dict(title='Value', range=y_axis_range),
                margin=dict(t=50, b=80, l=60, r=20)
            )

            metric_charts.append(
                # ***FIX 1: Update style to be 48% width for 2-column layout***
                html.Div([
                    dcc.Graph(figure=fig, config={'displayModeBar': False, 'displaylogo': False})
                ], style={'flex': '1 1 48%', 'minWidth': '300px', 'marginBottom': '15px'})
            )

        # ***FIX 1: Group metric charts into rows of 2***
        chart_rows = []
        for i in range(0, len(metric_charts), 2):
            row_children = metric_charts[i:i+2]
            chart_rows.append(
                html.Div(row_children, style={
                    'display': 'flex',
                    'flexWrap': 'wrap',
                    'gap': '20px',
                    'justifyContent': 'flex-start' # Start from left
                })
            )

        # Group metric charts in a flex container
        charts.append(
            html.Div([
                html.Div([
                    html.H3([
                        html.Span(info['icon'], style={'marginRight': '10px'}),
                        category
                    ], style={
                        'color': info['color'],
                        'marginBottom': '20px',
                        'borderBottom': f'3px solid {info["color"]}',
                        'paddingBottom': '10px'
                    }),
                ]),
                # ***FIX 1: Add the new chart_rows list here***
                html.Div(chart_rows)
            ], style={
                'marginBottom': '40px',
                'padding': '25px',
                'backgroundColor': 'white',
                'borderRadius': '10px',
                'boxShadow': '0 2px 8px rgba(0,0,0,0.1)'
            })
        )

    # Create detailed KPI table with improved styling and best/worst highlighting
    # Calculate min/max for each numeric column to highlight best/worst
    column_stats = {}
    for col in kpi_df.columns:
        if col != 'Configuration':
            numeric_vals = []
            for val in kpi_df[col]:
                if isinstance(val, (int, float)):
                    numeric_vals.append(val)
            if numeric_vals:
                column_stats[col] = {
                    'min': min(numeric_vals),
                    'max': max(numeric_vals)
                }

    # Determine which KPIs are "lower is better" vs "higher is better"
    # Lower is better: violations, cost, emissions, ramping, import, variance, peak, fuel, etc.
    # Higher is better: generation, efficiency, etc.
    lower_is_better_keywords = [
        'violation', 'cost', 'emission', 'ramping', 'switch', 'penalty',
        'import', 'variance', 'peak', 'fuel'
    ]

    def get_cell_style(col, val, base_style):
        """Get cell style with highlighting for best/worst values"""
        if col == 'Configuration' or not isinstance(val, (int, float)):
            return base_style

        if col not in column_stats:
            return base_style

        stats = column_stats[col]
        if stats['min'] == stats['max']:  # All values are the same
            return base_style

        # Determine if lower or higher is better
        lower_is_better = any(keyword in col.lower() for keyword in lower_is_better_keywords)

        style = base_style.copy()

        if lower_is_better:
            # Lower is better: min is best (green), max is worst (red)
            if val == stats['min']:
                style.update({
                    'backgroundColor': '#d4edda',  # Light green
                    'color': '#155724',  # Dark green
                    'fontWeight': 'bold'
                })
            elif val == stats['max']:
                style.update({
                    'backgroundColor': '#f8d7da',  # Light red
                    'color': '#721c24',  # Dark red
                    'fontWeight': 'bold'
                })
        else:
            # Higher is better: max is best (green), min is worst (red)
            if val == stats['max']:
                style.update({
                    'backgroundColor': '#d4edda',  # Light green
                    'color': '#155724',  # Dark green
                    'fontWeight': 'bold'
                })
            elif val == stats['min']:
                style.update({
                    'backgroundColor': '#f8d7da',  # Light red
                    'color': '#721c24',  # Dark red
                    'fontWeight': 'bold'
                })

        return style

    table = html.Div([
        html.H3([
            html.Span("📋", style={'marginRight': '10px'}),
            "Detailed District-Level KPI Comparison"
        ], style={
            'marginTop': 40,
            'marginBottom': 20,
            'color': '#2c3e50',
            'borderBottom': '3px solid #667eea',
            'paddingBottom': '10px'
        }),
        html.Div([
            html.Div([
                html.Span("🟢 ", style={'color': '#28a745', 'fontSize': '14px'}),
                html.Span("Best value", style={'marginRight': '20px', 'fontSize': '12px', 'color': '#155724'}),
                html.Span("🔴 ", style={'color': '#dc3545', 'fontSize': '14px'}),
                html.Span("Worst value", style={'fontSize': '12px', 'color': '#721c24'}),
            ], style={'marginBottom': '10px', 'fontSize': '12px', 'color': '#7f8c8d'}),
            html.Table([
                html.Thead(
                    html.Tr(
                        [html.Th(col if col == 'Configuration' else col.replace('Avg ', '').replace('Total ', ''),
                                 style={
                                     'backgroundColor': '#667eea',
                                     'color': 'white',
                                     'padding': '14px 10px',
                                     'textAlign': 'left' if col == 'Configuration' else 'center',
                                     'fontSize': '13px',
                                     'fontWeight': 'bold',
                                     'position': 'sticky',
                                     'top': 0,
                                     'zIndex': 10
                                 }) for col in kpi_df.columns])
                ),
                html.Tbody([
                    html.Tr([
                        html.Td(
                            f"{val:.4f}" if isinstance(val, (int, float)) and col != 'Configuration' else val,
                            style=get_cell_style(col, val, {
                                'padding': '12px 10px',
                                'borderBottom': '1px solid #e0e0e0',
                                'textAlign': 'left' if col == 'Configuration' else 'center',
                                'fontWeight': '600' if col == 'Configuration' else 'normal',
                                'fontSize': '12px',
                                'fontFamily': 'monospace' if col != 'Configuration' else 'inherit',
                                'color': '#2c3e50' if col == 'Configuration' else '#34495e'
                            })
                        )
                        for col, val in zip(kpi_df.columns, row)
                    ], style={
                        'backgroundColor': '#f8f9fa' if idx % 2 == 0 else 'white',
                        'transition': 'background-color 0.2s'
                    })
                    for idx, row in enumerate(kpi_df.values)
                ])
            ], style={
                'width': '100%',
                'borderCollapse': 'collapse',
                'marginTop': 10,
                'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
                'borderRadius': '8px',
                'overflow': 'hidden'
            }),
        ], style={'overflowX': 'auto', 'maxWidth': '100%'})
    ], style={
        'marginTop': '30px',
        'padding': '25px',
        'backgroundColor': 'white',
        'borderRadius': '10px',
        'boxShadow': '0 2px 8px rgba(0,0,0,0.1)'
    })

    # Summary info box
    summary_box = html.Div([
        html.Div([
            html.Div([
                html.H4(f"{len(selected_buildings)}",
                        style={'fontSize': '32px', 'margin': '0', 'color': '#667eea'}),
                html.P("Buildings", style={'margin': '5px 0 0 0', 'color': '#7f8c8d', 'fontSize': '14px'})
            ], style={'textAlign': 'center', 'flex': '1'}),
            html.Div([
                html.H4(f"{len(selected_configs)}",
                        style={'fontSize': '32px', 'margin': '0', 'color': '#667eea'}),
                html.P("Configurations", style={'margin': '5px 0 0 0', 'color': '#7f8c8d', 'fontSize': '14px'})
            ], style={'textAlign': 'center', 'flex': '1'}),
            html.Div([
                html.H4("District", style={'fontSize': '32px', 'margin': '0', 'color': '#667eea'}),
                html.P("Level Analysis", style={'margin': '5px 0 0 0', 'color': '#7f8c8d', 'fontSize': '14px'})
            ], style={'textAlign': 'center', 'flex': '1'}),
        ], style={'display': 'flex', 'justifyContent': 'space-around'}),
        html.Hr(style={'margin': '20px 0', 'border': 'none', 'borderTop': '1px solid #e0e0e0'}),
        html.P([
            html.Strong("ℹ️ Note: "),
            "All KPIs are calculated at the district level by aggregating data from all selected buildings. ",
            "Each bar represents the total/average performance across the entire district for that configuration."
        ], style={'margin': '0', 'color': '#34495e', 'fontSize': '13px', 'lineHeight': '1.6'})
    ], style={
        'marginBottom': '30px',
        'padding': '25px',
        'backgroundColor': '#f8f9fa',
        'borderRadius': '10px',
        'border': '2px solid #667eea'
    })

    return html.Div([
        summary_box,
        html.Div(charts),
        table
    ])


def render_comparison_tab(dataset, selected_buildings, selected_configs, season,
                          start_date, end_date, configs_data):
    """Render comparative analysis across configurations using district-level KPIs."""

    # Create scatter plot: Comfort vs Energy (District Level)
    scatter_data = []

    for config_key in selected_configs:
        config = configs_data[config_key]

        # Create full legend name
        algo_name_formatted = config['algorithm'].replace('_', ' ').title()
        config_display_name = config['display_name']
        full_config_name = f"{algo_name_formatted}: {config_display_name}"

        # Aggregate district-level metrics
        district_comfort_violations = 0
        district_total_energy = 0
        district_elec_cost = 0
        district_elec_emissions = 0
        total_timesteps = 0

        for building_id in selected_buildings:
            df_obs = load_observation_data(dataset, config, building_id, season)

            if df_obs is not None and not df_obs.empty:
                df_filtered = df_obs.loc[start_date:end_date]

                if not df_filtered.empty:
                    # Comfort violations
                    if all(col in df_filtered.columns for col in ["tin", "comfort_low", "comfort_high"]):
                        violations = ((df_filtered["tin"] > df_filtered["comfort_high"]) |
                                      (df_filtered["tin"] < df_filtered["comfort_low"])).sum()
                        district_comfort_violations += violations

                    # Energy (***FIX 2: Updated to include DHW***)
                    if "cooling demand" in df_filtered.columns and "heating demand" in df_filtered.columns:
                        energy = df_filtered["cooling demand"].sum() + df_filtered["heating demand"].sum()
                        if "dhw demand" in df_filtered.columns:
                            energy += df_filtered["dhw demand"].sum()
                        district_total_energy += energy

                    # Electricity cost
                    elec_cols = {'cost': ['net electricity consumption cost', 'net electricity cost',
                                          'Net Electricity Consumption Cost', 'total_electricity_cost']}
                    col_elec_cost = find_column(df_filtered, elec_cols['cost'])
                    if col_elec_cost:
                        district_elec_cost += pd.to_numeric(df_filtered[col_elec_cost],
                                                            errors='coerce').fillna(0).clip(
                            lower=0).sum()

                    # Electricity emissions
                    elec_emis_cols = {'emis': ['net electricity consumption emission', 'net electricity emission',
                                               'Net Electricity Consumption Emission',
                                               'total_electricity_emissions']}
                    col_elec_emis = find_column(df_filtered, elec_emis_cols['emis'])
                    if col_elec_emis:
                        district_elec_emissions += pd.to_numeric(df_filtered[col_elec_emis],
                                                                 errors='coerce').fillna(
                            0).clip(lower=0).sum()

                    total_timesteps += len(df_filtered)

        violation_rate = (district_comfort_violations / total_timesteps * 100) if total_timesteps > 0 else 0

        scatter_data.append({
            'Configuration': full_config_name,
            'Comfort Violations': district_comfort_violations,
            'Total Energy': district_total_energy,
            'Violation Rate': violation_rate,
            'Electricity Cost': district_elec_cost,
            'Electricity Emissions': district_elec_emissions
        })

    if not scatter_data:
        return html.Div([
            html.Div("📈", style={'fontSize': '48px', 'marginBottom': '20px'}),
            html.H4("No data available for comparison", style={'color': '#e74c3c'}),
        ], style={'textAlign': 'center', 'padding': '80px'})

    scatter_df = pd.DataFrame(scatter_data)

    # Scatter plot 1: Comfort vs Energy
    fig1 = px.scatter(
        scatter_df,
        x='Comfort Violations',
        y='Total Energy',
        text='Configuration',
        size='Violation Rate',
        color='Configuration',
        title=f'Energy-Comfort Trade-off Analysis (District Level - {len(selected_buildings)} Buildings)',
        labels={
            'Comfort Violations': 'Total Comfort Violations (count)',
            'Total Energy': 'Total Energy Demand (kWh)'
        },
        template='plotly_white',
        height=500,
        color_discrete_sequence=COLORS
    )
    fig1.update_traces(textposition='top center', textfont=dict(size=10))
    fig1.update_layout(
        showlegend=True,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.05),
        title=dict(font=dict(size=16, color='#2c3e50'))
    )

    # Scatter plot 2: Cost vs Emissions
    if scatter_df['Electricity Cost'].sum() > 0 and scatter_df['Electricity Emissions'].sum() > 0:
        fig2 = px.scatter(
            scatter_df,
            x='Electricity Cost',
            y='Electricity Emissions',
            text='Configuration',
            size='Total Energy',
            color='Configuration',
            title=f'Cost-Emissions Trade-off (District Level)',
            labels={
                'Electricity Cost': 'Total Electricity Cost ($)',
                'Electricity Emissions': 'Total Electricity Emissions (kg CO₂)'
            },
            template='plotly_white',
            height=500,
            color_discrete_sequence=COLORS
        )
        fig2.update_traces(textposition='top center', textfont=dict(size=10))
        fig2.update_layout(
            showlegend=True,
            legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.05),
            title=dict(font=dict(size=16, color='#2c3e50'))
        )
    else:
        fig2 = None

    # Radar chart for multi-dimensional comparison
    # Comparing: Total Violations, Total Cost, Total Emissions (lower is better for all)
    if len(scatter_df) > 0:
        # Define categories for comparison
        categories = ['Total Violations', 'Total Cost ($)', 'Total Emissions (kg CO₂)']

        # Calculate min and max for each metric (for table display)
        metrics_stats = {
            'Total Violations': {
                'min': scatter_df['Comfort Violations'].min(),
                'max': scatter_df['Comfort Violations'].max(),
                'values': scatter_df['Comfort Violations']
            },
            'Total Cost ($)': {
                'min': scatter_df['Electricity Cost'].min(),
                'max': scatter_df['Electricity Cost'].max(),
                'values': scatter_df['Electricity Cost']
            },
            'Total Emissions (kg CO₂)': {
                'min': scatter_df['Electricity Emissions'].min(),
                'max': scatter_df['Electricity Emissions'].max(),
                'values': scatter_df['Electricity Emissions']
            }
        }

        fig3 = go.Figure()

        for i, row in scatter_df.iterrows():
            # Collect raw values for normalization
            values = []

            # Total Violations
            total_violations = row['Comfort Violations']

            # Total Cost
            total_cost = row['Electricity Cost']

            # Total Emissions
            total_emissions = row['Electricity Emissions']

            # Normalize to 0-100 scale: DIRECT (higher value = higher on chart)
            # Min value → 0 (center), Max value → 100 (outer edge)
            for cat in categories:
                if cat == 'Total Violations':
                    val = total_violations
                    min_val = metrics_stats[cat]['min']
                    max_val = metrics_stats[cat]['max']
                elif cat == 'Total Cost ($)':
                    val = total_cost
                    min_val = metrics_stats[cat]['min']
                    max_val = metrics_stats[cat]['max']
                elif cat == 'Total Emissions (kg CO₂)':
                    val = total_emissions
                    min_val = metrics_stats[cat]['min']
                    max_val = metrics_stats[cat]['max']
                else:
                    val = 0
                    min_val = 0
                    max_val = 1

                # Direct normalization: min → 0 (center), max → 100 (outer)
                if max_val > min_val:
                    score = ((val - min_val) / (max_val - min_val)) * 100
                else:
                    score = 0
                values.append(score)

            # Close the polygon
            values.append(values[0])

            # Add trace with NO FILL, only border line
            fig3.add_trace(go.Scatterpolar(
                r=values,
                theta=categories + [categories[0]],
                name=row['Configuration'],
                fill='none',  # NO FILL - only border line
                line=dict(color=COLORS[i % len(COLORS)], width=3),
                mode='lines'
            ))

        fig3.update_layout(
            polar=dict(
                bgcolor='white',  # White background
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    ticktext=['Min', '', '', '', '', 'Max'],
                    tickvals=[0, 20, 40, 60, 80, 100],
                    gridcolor='lightgray',
                    linecolor='lightgray'
                ),
                angularaxis=dict(
                    gridcolor='lightgray',
                    linecolor='gray'
                ),
                domain=dict(x=[0, 1], y=[0.15, 1])  # Reduce polar plot size to make room for legend
            ),
            showlegend=True,
            title=dict(
                text="Multi-dimensional Performance Comparison<br><sub>(Center = Min, Outer = Max | Lower is Better)</sub>",
                font=dict(size=16, color='#2c3e50')
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=580,  # Increased height to accommodate legend
            margin=dict(l=80, r=80, t=100, b=120),  # Increased bottom margin for legend
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.05,  # Position legend just below the plot
                xanchor="center",
                x=0.5,
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='#e0e0e0',
                borderwidth=1
            )
        )

        # Create min/max values table
        radar_table = html.Div([
            html.H4("📊 Radar Chart Scale Reference",
                   style={'marginTop': 20, 'marginBottom': 15, 'color': '#2c3e50', 'fontSize': '16px'}),
            html.Table([
                html.Thead(
                    html.Tr([
                        html.Th('Metric', style={
                            'backgroundColor': '#667eea',
                            'color': 'white',
                            'padding': '12px',
                            'textAlign': 'left',
                            'fontWeight': 'bold',
                            'borderRadius': '5px 0 0 0'
                        }),
                        html.Th('Minimum (Center)', style={
                            'backgroundColor': '#667eea',
                            'color': 'white',
                            'padding': '12px',
                            'textAlign': 'center',
                            'fontWeight': 'bold'
                        }),
                        html.Th('Maximum (Outer Edge)', style={
                            'backgroundColor': '#667eea',
                            'color': 'white',
                            'padding': '12px',
                            'textAlign': 'center',
                            'fontWeight': 'bold',
                            'borderRadius': '0 5px 0 0'
                        })
                    ])
                ),
                html.Tbody([
                    html.Tr([
                        html.Td('Total Violations', style={
                            'padding': '12px',
                            'borderBottom': '1px solid #e0e0e0',
                            'fontWeight': '600',
                            'color': '#2c3e50'
                        }),
                        html.Td(f"{metrics_stats['Total Violations']['min']:.0f}", style={
                            'padding': '12px',
                            'borderBottom': '1px solid #e0e0e0',
                            'textAlign': 'center',
                            'fontFamily': 'monospace',
                            'color': '#27ae60',
                            'fontWeight': 'bold'
                        }),
                        html.Td(f"{metrics_stats['Total Violations']['max']:.0f}", style={
                            'padding': '12px',
                            'borderBottom': '1px solid #e0e0e0',
                            'textAlign': 'center',
                            'fontFamily': 'monospace',
                            'color': '#e74c3c',
                            'fontWeight': 'bold'
                        })
                    ], style={'backgroundColor': '#f8f9fa'}),
                    html.Tr([
                        html.Td('Total Cost ($)', style={
                            'padding': '12px',
                            'borderBottom': '1px solid #e0e0e0',
                            'fontWeight': '600',
                            'color': '#2c3e50'
                        }),
                        html.Td(f"${metrics_stats['Total Cost ($)']['min']:.2f}", style={
                            'padding': '12px',
                            'borderBottom': '1px solid #e0e0e0',
                            'textAlign': 'center',
                            'fontFamily': 'monospace',
                            'color': '#27ae60',
                            'fontWeight': 'bold'
                        }),
                        html.Td(f"${metrics_stats['Total Cost ($)']['max']:.2f}", style={
                            'padding': '12px',
                            'borderBottom': '1px solid #e0e0e0',
                            'textAlign': 'center',
                            'fontFamily': 'monospace',
                            'color': '#e74c3c',
                            'fontWeight': 'bold'
                        })
                    ], style={'backgroundColor': 'white'}),
                    html.Tr([
                        html.Td('Total Emissions (kg CO₂)', style={
                            'padding': '12px',
                            'fontWeight': '600',
                            'color': '#2c3e50'
                        }),
                        html.Td(f"{metrics_stats['Total Emissions (kg CO₂)']['min']:.2f}", style={
                            'padding': '12px',
                            'textAlign': 'center',
                            'fontFamily': 'monospace',
                            'color': '#27ae60',
                            'fontWeight': 'bold'
                        }),
                        html.Td(f"{metrics_stats['Total Emissions (kg CO₂)']['max']:.2f}", style={
                            'padding': '12px',
                            'textAlign': 'center',
                            'fontFamily': 'monospace',
                            'color': '#e74c3c',
                            'fontWeight': 'bold'
                        })
                    ], style={'backgroundColor': '#f8f9fa'})
                ])
            ], style={
                'width': '100%',
                'borderCollapse': 'collapse',
                'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
                'borderRadius': '8px',
                'overflow': 'hidden'
            }),
            html.P([
                html.Strong("💡 Note: "),
                "The radar chart shows the relative position of each configuration between the minimum (center) and maximum (outer edge) values. ",
                "Configurations closer to the center have lower values and are therefore better (lower violations, cost, and emissions)."
            ], style={
                'marginTop': 15,
                'padding': '15px',
                'backgroundColor': '#e8f4f8',
                'borderRadius': '5px',
                'fontSize': '13px',
                'color': '#2c3e50',
                'lineHeight': '1.6',
                'border': '1px solid #bee5eb'
            })
        ], style={
            'marginTop': 20,
            'padding': '20px',
            'backgroundColor': 'white',
            'borderRadius': '10px',
            'boxShadow': '0 2px 8px rgba(0,0,0,0.1)'
        })
    else:
        fig3 = None
        radar_table = None

    # Create layout
    graphs = []

    # Row 1: Energy-Comfort scatter (full width)
    graphs.append(
        html.Div([
            dcc.Graph(figure=fig1, config={'displayModeBar': True, 'displaylogo': False})
        ], style={'width': '100%', 'marginBottom': '30px'})
    )

    # Row 2: Cost-Emissions scatter (full width)
    if fig2:
        graphs.append(
            html.Div([
                dcc.Graph(figure=fig2, config={'displayModeBar': True, 'displaylogo': False})
            ], style={'width': '100%', 'marginBottom': '30px'})
        )

    # Row 3: Radar chart (left) and Table (right)
    if fig3:
        graphs.append(
            html.Div([
                # Radar chart on the left
                html.Div([
                    dcc.Graph(figure=fig3, config={'displayModeBar': True, 'displaylogo': False})
                ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
                # Table on the right
                html.Div([
                    radar_table if radar_table else html.Div()
                ], style={'width': '48%', 'display': 'inline-block', 'marginLeft': '4%', 'verticalAlign': 'top'}),
            ], style={'width': '100%', 'marginBottom': '30px'})
        )

    # Interpretation guide
    guide = html.Div([
        html.H4("📖 Interpretation Guide", style={'marginBottom': '15px', 'color': '#2c3e50'}),
        html.Ul([
            html.Li("Lower comfort violations = better comfort maintenance across all buildings"),
            html.Li("Lower total cost = more economically efficient operation"),
            html.Li("Lower total emissions = more environmentally sustainable operation"),
            html.Li(
                "The ideal configuration is in the bottom-left corner of scatter plots (low values on both axes)"),
            html.Li([
                html.Strong("Radar chart: "),
                "Configurations closer to the CENTER perform better (lower violations, cost, and emissions). ",
                "The chart shows absolute values from minimum (center) to maximum (outer edge)."
            ]),
            html.Li("The best algorithm minimizes all three metrics: Total Violations, Total Cost, Total Emissions"),
            html.Li("Refer to the table below the radar chart for exact minimum and maximum values"),
            html.Li("Bubble size in scatter plots represents the magnitude of the third variable"),
            html.Li(
                f"📊 Analysis includes data from {len(selected_buildings)} building(s) and {len(selected_configs)} configuration(s)")
        ], style={'lineHeight': '1.8', 'color': '#34495e'})
    ], style={
        'backgroundColor': '#f8f9fa',
        'padding': '25px',
        'borderRadius': '10px',
        'border': '2px solid #667eea',
        'marginTop': 20
    })

    return html.Div([
        html.Div([
            html.H3([
                html.Span("📈", style={'marginRight': '10px'}),
                f"Comparative Analysis - District Level ({len(selected_buildings)} Buildings)"
            ], style={
                'marginBottom': 20,
                'color': '#2c3e50',
                'borderBottom': '3px solid #667eea',
                'paddingBottom': '10px'
            })
        ]),
        html.Div(graphs),
        guide,
        # Best Configuration Finder Section
        html.Hr(style={'marginTop': '50px', 'marginBottom': '30px', 'border': '2px solid #667eea'}),
        render_best_config_finder(dataset, selected_configs, season, start_date, end_date, configs_data, selected_buildings)
    ])


def render_best_config_finder(dataset, selected_configs, season, start_date, end_date, configs_data, selected_buildings):
    """
    Render the Best Configuration Finder section with custom weights and ranking.
    """
    return html.Div([
        html.H3([
            html.Span("🏆", style={'marginRight': '10px'}),
            "Best Configuration Finder"
        ], style={
            'marginBottom': 20,
            'color': '#2c3e50',
            'borderBottom': '3px solid #667eea',
            'paddingBottom': '10px'
        }),

        # Description
        html.P([
            "Trova la migliore configurazione in base ai tuoi obiettivi personalizzati. ",
            "Regola i pesi per dare priorità a comfort, costi o emissioni, poi clicca 'Calculate Best Configuration' per vedere il ranking."
        ], style={'color': '#34495e', 'marginBottom': '25px', 'lineHeight': '1.6'}),

        # Weight Sliders Toolbar
        html.Div([
            html.H4("⚖️ Custom Weights", style={'color': '#2c3e50', 'marginBottom': '20px'}),
            html.Div([
                # Comfort Weight
                html.Div([
                    html.Label("Comfort Violations Weight:", style={'fontWeight': 'bold', 'color': '#667eea'}),
                    dcc.Slider(
                        id='weight-comfort',
                        min=0,
                        max=1,
                        step=0.05,
                        value=0.4,
                        marks={i/10: f'{i/10:.1f}' for i in range(0, 11, 2)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                ], style={'width': '30%', 'display': 'inline-block', 'paddingRight': '3%', 'verticalAlign': 'top'}),

                # Cost Weight
                html.Div([
                    html.Label("Cost Weight:", style={'fontWeight': 'bold', 'color': '#667eea'}),
                    dcc.Slider(
                        id='weight-cost',
                        min=0,
                        max=1,
                        step=0.05,
                        value=0.3,
                        marks={i/10: f'{i/10:.1f}' for i in range(0, 11, 2)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                ], style={'width': '30%', 'display': 'inline-block', 'paddingRight': '3%', 'verticalAlign': 'top'}),

                # Emissions Weight
                html.Div([
                    html.Label("Emissions Weight:", style={'fontWeight': 'bold', 'color': '#667eea'}),
                    dcc.Slider(
                        id='weight-emissions',
                        min=0,
                        max=1,
                        step=0.05,
                        value=0.3,
                        marks={i/10: f'{i/10:.1f}' for i in range(0, 11, 2)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top'}),
            ], style={'marginBottom': '20px'}),

            # Weight sum indicator
            html.Div(id='weight-sum-indicator', style={'marginBottom': '15px', 'fontSize': '14px'}),

            # Calculate Button
            html.Button(
                '🔍 Calculate Best Configuration',
                id='calculate-best-config-btn',
                n_clicks=0,
                style={
                    'backgroundColor': '#667eea',
                    'color': 'white',
                    'border': 'none',
                    'padding': '12px 30px',
                    'fontSize': '16px',
                    'fontWeight': 'bold',
                    'borderRadius': '8px',
                    'cursor': 'pointer',
                    'boxShadow': '0 4px 6px rgba(0,0,0,0.1)',
                    'transition': 'all 0.3s'
                }
            ),
        ], style={
            'backgroundColor': '#f8f9fa',
            'padding': '25px',
            'borderRadius': '10px',
            'marginBottom': '30px',
            'border': '2px solid #e0e0e0'
        }),

        # Results Container
        html.Div(id='best-config-results', style={'marginTop': '30px'})
    ])


# ============================================================================
# HEATING SYSTEM VISUALIZATION
# ============================================================================

def create_storage_dashboard(df: pd.DataFrame, building_id: int = None):
    """
    Create a dashboard with visualizations of storage systems (heating, cooling, electrical).

    Parameters
    ----------
    df: pd.DataFrame
        DataFrame containing time series data with storage information
    building_id : int, optional
        Building ID to display (for the title)

    Returns
    -------
    fig : plotly.graph_objects.Figure
        Plotly figure with storage balance graphs
    """
    # Define column mappings for all storage types
    storage_columns = {
        'heating': {
            'soc': find_column(df, ['heating storage soc', 'heating_storage_soc']),
            'charge_sources': [
                {
                    'column': find_column(df, ['energy from heating device to heating storage']),
                    'name': 'Electric Device Charge',
                    'color': 'rgba(255, 99, 71, 0.7)'
                },
                {
                    'column': find_column(df, ['energy from heating fuel device to heating storage']),
                    'name': 'Fuel Device Charge',
                    'color': 'rgba(255, 165, 0, 0.7)'
                }
            ],
            'discharge': find_column(df, ['energy from heating storage']),
            'discharge_color': 'rgba(30, 144, 255, 0.7)',
            'soc_color': 'purple'
        },
        'cooling': {
            'soc': find_column(df, ['cooling storage soc', 'cooling_storage_soc']),
            'charge_sources': [
                {
                    'column': find_column(df, ['energy from cooling device to cooling storage']),
                    'name': 'Charge',
                    'color': 'rgba(46, 204, 113, 0.7)'
                }
            ],
            'discharge': find_column(df, ['energy from cooling storage']),
            'discharge_color': 'rgba(52, 152, 219, 0.7)',
            'soc_color': 'teal'
        },
        'electrical': {
            'soc': find_column(df, ['electrical storage soc', 'electrical_storage_soc', 'battery soc', 'battery_soc']),
            'consumption_column': find_column(df, ['electrical storage electricity consumption']),
            'discharge_color': 'rgba(230, 126, 34, 0.7)',
            'charge_color': 'rgba(241, 196, 15, 0.7)',
            'soc_color': 'darkgoldenrod'
        }
    }

    # Determine which storages are available
    available_storages = []
    for storage_type, cols in storage_columns.items():
        if cols['soc'] and cols['soc'] in df.columns:
            # Check if there's actual data (not all zeros)
            if df[cols['soc']].abs().sum() > 0.001:
                available_storages.append(storage_type)

    if not available_storages:
        # Return empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="No storage data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=20, color="#e74c3c")
        )
        return fig

    # Create subplots - one row per available storage
    num_storages = len(available_storages)
    subplot_titles = [f'{storage.capitalize()} Storage Balance' for storage in available_storages]

    fig = make_subplots(
        rows=num_storages,
        cols=1,
        subplot_titles=subplot_titles,
        vertical_spacing=0.08,
        specs=[[{"secondary_y": True}] for _ in range(num_storages)]
    )

    for idx, storage_type in enumerate(available_storages, start=1):
        cols = storage_columns[storage_type]

        # Prepare SOC data
        soc_data = pd.to_numeric(df[cols['soc']], errors='coerce').fillna(0)

        # Handle electrical storage differently (single consumption column)
        if storage_type == 'electrical' and 'consumption_column' in cols:
            consumption_col = cols['consumption_column']
            if consumption_col and consumption_col in df.columns:
                consumption_data = pd.to_numeric(df[consumption_col], errors='coerce').fillna(0)
                charge_data = consumption_data.clip(lower=0)
                discharge_data = -consumption_data.clip(upper=0)

                # Add charge bar
                if charge_data.sum() > 0:
                    fig.add_trace(
                        go.Bar(
                            x=df.index,
                            y=charge_data,
                            name='Charge',
                            marker=dict(color=cols['charge_color']),
                            legendgroup=f'{storage_type}_ops',
                            showlegend=True
                        ),
                        row=idx, col=1
                    )

                # Add discharge bar
                if discharge_data.sum() > 0:
                    fig.add_trace(
                        go.Bar(
                            x=df.index,
                            y=-discharge_data,
                            name='Discharge',
                            marker=dict(color=cols['discharge_color']),
                            legendgroup=f'{storage_type}_ops',
                            showlegend=True
                        ),
                        row=idx, col=1
                    )
        else:
            # Handle heating and cooling with charge_sources
            if 'charge_sources' in cols:
                for charge_source in cols['charge_sources']:
                    charge_col = charge_source['column']
                    if charge_col and charge_col in df.columns:
                        charge_data = pd.to_numeric(df[charge_col], errors='coerce').fillna(0)

                        # Only add trace if there's actual data
                        if charge_data.sum() > 0:
                            fig.add_trace(
                                go.Bar(
                                    x=df.index,
                                    y=charge_data,
                                    name=charge_source['name'],
                                    marker=dict(color=charge_source['color']),
                                    legendgroup=f'{storage_type}_ops',
                                    showlegend=True
                                ),
                                row=idx, col=1
                            )

            # Handle discharge
            discharge_col = cols.get('discharge')
            if discharge_col and discharge_col in df.columns:
                discharge_data = pd.to_numeric(df[discharge_col], errors='coerce').fillna(0)

                if discharge_data.sum() > 0:
                    fig.add_trace(
                        go.Bar(
                            x=df.index,
                            y=-discharge_data,
                            name=f'{storage_type.capitalize()} Discharge',
                            marker=dict(color=cols['discharge_color']),
                            legendgroup=f'{storage_type}_ops',
                            showlegend=True
                        ),
                        row=idx, col=1
                    )

        # Add SOC line on secondary axis
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=soc_data,
                name=f'{storage_type.capitalize()} SOC',
                line=dict(color=cols['soc_color'], width=2.5, dash='dot'),
                mode='lines',
                legendgroup=f'{storage_type}_soc',
                showlegend=True
            ),
            row=idx, col=1, secondary_y=True
        )

        # Update axes
        fig.update_xaxes(title_text="Timestep" if idx == num_storages else "", row=idx, col=1)
        fig.update_yaxes(title_text="Energy (kWh)", row=idx, col=1, secondary_y=False)
        fig.update_yaxes(title_text="SOC", row=idx, col=1, secondary_y=True, range=[0, 1])

    # General layout
    title_text = f"Storage Systems Dashboard"
    if building_id is not None:
        title_text += f" - Building {building_id}"

    fig.update_layout(
        height=400 * num_storages,
        showlegend=True,
        barmode='stack',  # Stack the bars instead of overlaying
        title=dict(
            text=title_text,
            font=dict(size=18, color='#2c3e50'),
            x=0.5,
            xanchor='center'
        ),
        hovermode='x unified',
        template='plotly_white',
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="right",
            x=1.12,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='#e0e0e0',
            borderwidth=1
        )
    )

    return fig


def render_storage_tab(dataset, selected_buildings, selected_configs, season, start_date, end_date, configs_data):
    """
    Render storage systems visualization showing charge/discharge balance for all available storages.

    Parameters
    ----------
    dataset : str
        Dataset name
    selected_buildings : list
        List of building IDs
    selected_configs : list
        List of selected configuration keys
    season : str
        Season ('winter' or 'summer')
    start_date : str
        Start date for filtering
    end_date : str
        End date for filtering
    configs_data : dict
        Dictionary of configuration data

    Returns
    -------
    html.Div
        Dash HTML div containing the storage visualizations
    """
    if not selected_buildings:
        return html.Div([
            html.Div("🔋", style={'fontSize': '48px', 'marginBottom': '20px'}),
            html.H4("Select at least one building", style={'color': '#e74c3c'}),
        ], style={'textAlign': 'center', 'padding': '80px'})

    # OPTIMIZATION: Show all configurations but only for the first building
    building_id = selected_buildings[0]
    total_buildings = len(selected_buildings)
    show_info = total_buildings > 1

    graphs = []

    # Process all configurations for the first building only
    for config_key in selected_configs:
        config = configs_data[config_key]

        # Configuration name
        algo_name_formatted = config['algorithm'].replace('_', ' ').title()
        config_display_name = config['display_name']
        full_config_name = f"{algo_name_formatted}: {config_display_name}"

        # Load data
        df = load_observation_data(dataset, config, building_id, season)

        if df is None or df.empty:
            continue

        # Filter by date range
        df_filtered = df.loc[start_date:end_date]

        if df_filtered.empty:
            continue

        # Create the storage dashboard
        fig = create_storage_dashboard(df_filtered, building_id)

        # Update title with configuration name
        fig.update_layout(
            title=dict(
                text=f"Storage Systems - Building {building_id}<br><sub>{full_config_name}</sub>",
                font=dict(size=18, color='#2c3e50')
            )
        )

        graphs.append(
            html.Div([
                html.H4(full_config_name, style={
                    'color': '#667eea',
                    'marginBottom': '15px',
                    'marginTop': '30px' if graphs else '0px'
                }),
                dcc.Graph(figure=fig, config={'displayModeBar': True, 'displaylogo': False})
            ])
        )

    if not graphs:
        return html.Div([
            html.Div("📊", style={'fontSize': '48px', 'marginBottom': '20px'}),
            html.H4("No data available", style={'color': '#e74c3c'}),
            html.P("Please verify that storage data is present in the CSV files.",
                   style={'color': '#95a5a6'})
        ], style={'textAlign': 'center', 'padding': '80px'})

    # Interpretation guide
    guide = html.Div([
        html.H4("📖 Interpretation Guide", style={'marginBottom': '15px', 'color': '#2c3e50'}),
        html.Ul([
            html.Li([
                html.Strong("Storage Balance: "),
                "Each graph shows the charge/discharge dynamics for a specific storage type (heating, cooling, or electrical)."
            ]),
            html.Li([
                html.Strong("Heating Storage - Dual Charge Sources: "),
                html.Span([
                    "For heating storage, charge is shown separately for ",
                    html.Span("Electric Device", style={'color': 'rgb(255, 99, 71)', 'fontWeight': 'bold'}),
                    " (heat pump/electric heater) and ",
                    html.Span("Fuel Device", style={'color': 'rgb(255, 165, 0)', 'fontWeight': 'bold'}),
                    " (gas boiler). This allows you to see the contribution of each energy source."
                ])
            ]),
            html.Li([
                html.Strong("Charge (positive bars): "),
                "Energy being stored. For cooling/electrical storage, single bar. For heating, two bars (electric + fuel)."
            ]),
            html.Li([
                html.Strong("Discharge (negative bars): "),
                "Energy being released from storage to meet demands. Shown as negative values for easy visualization."
            ]),
            html.Li([
                html.Strong("SOC Line (dotted): "),
                "State of Charge shows the current energy level in the storage as a fraction of total capacity (0-1 range). Purple line on secondary axis."
            ]),
            html.Li([
                html.Strong("Optimal strategy: "),
                "Charge when energy is cheap/abundant (e.g., solar production, off-peak hours). Discharge when needed or when grid energy is expensive. For heating, prioritize electric device when renewable energy is available, use fuel device as backup."
            ]),
        ], style={'lineHeight': '1.8', 'color': '#34495e'})
    ], style={
        'backgroundColor': '#f8f9fa',
        'padding': '25px',
        'borderRadius': '10px',
        'border': '2px solid #667eea',
        'marginTop': 30
    })

    storage_content = html.Div([
        html.Div([
            html.H3([
                html.Span("🔋", style={'marginRight': '10px'}),
                f"Storage Systems - Building {building_id}"
            ], style={
                'marginBottom': 20,
                'color': '#2c3e50',
                'borderBottom': '3px solid #667eea',
                'paddingBottom': '10px'
            })
        ]),
        html.Div(graphs),
        guide
    ])

    # Add info banner if multiple buildings were selected
    if show_info:
        return html.Div([
            html.Div([
                html.Span("ℹ️ ", style={'fontSize': '20px', 'marginRight': '10px'}),
                html.Span(f"Configuration Comparison: Showing all {len(selected_configs)} configuration(s) for Building {building_id}. ",
                         style={'fontWeight': 'bold', 'color': '#3498db'}),
                html.Span(f"({total_buildings} buildings selected)",
                         style={'color': '#7f8c8d'})
            ], style={
                'backgroundColor': '#d1ecf1',
                'border': '1px solid #3498db',
                'borderRadius': '5px',
                'padding': '12px 20px',
                'marginBottom': '15px',
                'display': 'flex',
                'alignItems': 'center'
            }),
            storage_content
        ])

    return storage_content
# ============================================================================
# DISTRICT LEVEL VISUALIZATION
# ============================================================================

def render_district_tab(dataset, selected_buildings, selected_configs, season,
                       start_date, end_date, configs_data):
    """
    Render district-level aggregated metrics visualization.

    Shows cumulative electrical consumption, heating demand, and other important KPIs
    aggregated across all selected buildings for each configuration.

    Parameters
    ----------
    dataset : str
        Dataset name
    selected_buildings : list
        List of building IDs
    selected_configs : list
        List of selected configuration keys
    season : str
        Season ('winter' or 'summer')
    start_date : str
        Start date for filtering
    end_date : str
        End date for filtering
    configs_data : dict
        Dictionary of configuration data

    Returns
    -------
    html.Div
        Dash HTML div containing district-level visualizations
    """

    print(f"\n[DEBUG] render_district_tab: Aggregating data for {len(selected_buildings)} buildings")

    if not selected_buildings or not selected_configs:
        return html.Div([
            html.Div("🏙️", style={'fontSize': '48px', 'marginBottom': '20px'}),
            html.H4("Select buildings and configurations", style={'color': '#e74c3c'}),
            html.P("Please select at least one building and one configuration to view district metrics.",
                   style={'color': '#95a5a6'})
        ], style={'textAlign': 'center', 'padding': '80px'})

    # Dictionary to store aggregated data for each configuration
    district_data = {}

    for config_key in selected_configs:
        config = configs_data[config_key]

        # Configuration name
        algo_name_formatted = config['algorithm'].replace('_', ' ').title()
        config_display_name = config['display_name']
        full_config_name = f"{algo_name_formatted}: {config_display_name}"

        print(f"[DEBUG] Processing configuration: {full_config_name}")

        # Initialize aggregated dataframes
        aggregated_data = None

        # Aggregate data across all selected buildings
        for building_id in selected_buildings:
            # Load observation data
            df = load_observation_data(dataset, config, building_id, season)

            if df is None or df.empty:
                print(f"[WARNING] No data for building {building_id}")
                continue

            # Filter by date range
            df_filtered = df.loc[start_date:end_date].copy()

            if df_filtered.empty:
                continue

            # Load the raw CSV to get all columns
            algo_path = Path(config['path']) if isinstance(config['path'], str) else config['path']
            obs_file = (DATA_DIR / dataset / "schema.json" / "obs" /
                       algo_path / f"obs_building_{building_id}.csv")

            if obs_file.exists():
                df_raw = pd.read_csv(obs_file)

                # Add datetime index
                start_date_dt = SEASONS.get(season, SEASONS["winter"])
                df_raw.index = pd.date_range(start=start_date_dt, periods=len(df_raw), freq="h")
                df_raw_filtered = df_raw.loc[start_date:end_date]

                # Extract important columns for district aggregation
                cols_to_aggregate = {}

                # Electrical consumption
                net_elec = find_column(df_raw_filtered, ['net electricity consumption', 'net_electricity_consumption'])
                if net_elec:
                    cols_to_aggregate['net_electricity_consumption'] = pd.to_numeric(df_raw_filtered[net_elec], errors='coerce').fillna(0)

                pos_elec = find_column(df_raw_filtered, ['positive net electricity consumption'])
                if pos_elec:
                    cols_to_aggregate['positive_electricity_consumption'] = pd.to_numeric(df_raw_filtered[pos_elec], errors='coerce').fillna(0)

                # Solar generation
                solar = find_column(df_raw_filtered, ['solar_generation', 'solar generation'])
                if solar:
                    cols_to_aggregate['solar_generation'] = pd.to_numeric(df_raw_filtered[solar], errors='coerce').fillna(0)

                # Demands
                heating = find_column(df_raw_filtered, ['heating_demand', 'heating demand'])
                if heating:
                    cols_to_aggregate['heating_demand'] = pd.to_numeric(df_raw_filtered[heating], errors='coerce').fillna(0)

                cooling = find_column(df_raw_filtered, ['cooling_demand', 'cooling demand'])
                if cooling:
                    cols_to_aggregate['cooling_demand'] = pd.to_numeric(df_raw_filtered[cooling], errors='coerce').fillna(0)

                dhw = find_column(df_raw_filtered, ['dhw_demand', 'dhw demand'])
                if dhw:
                    cols_to_aggregate['dhw_demand'] = pd.to_numeric(df_raw_filtered[dhw], errors='coerce').fillna(0)

                # Energy from devices
                heat_dev = find_column(df_raw_filtered, ['energy from heating device'])
                if heat_dev:
                    cols_to_aggregate['energy_from_heating_device'] = pd.to_numeric(df_raw_filtered[heat_dev], errors='coerce').fillna(0)

                heat_fuel = find_column(df_raw_filtered, ['energy from heating fuel device'])
                if heat_fuel:
                    cols_to_aggregate['energy_from_heating_fuel_device'] = pd.to_numeric(df_raw_filtered[heat_fuel], errors='coerce').fillna(0)

                # Fuel consumption
                fuel_cons = find_column(df_raw_filtered, ['net fuel consumption', 'net_fuel_consumption'])
                if fuel_cons:
                    cols_to_aggregate['fuel_consumption'] = pd.to_numeric(df_raw_filtered[fuel_cons], errors='coerce').fillna(0)

                # Cost and emissions
                elec_cost = find_column(df_raw_filtered, ['net electricity cost', 'net_electricity_cost'])
                if elec_cost:
                    cols_to_aggregate['electricity_cost'] = pd.to_numeric(df_raw_filtered[elec_cost], errors='coerce').fillna(0)

                elec_emis = find_column(df_raw_filtered, ['net electricity emission', 'net_electricity_emission'])
                if elec_emis:
                    cols_to_aggregate['electricity_emissions'] = pd.to_numeric(df_raw_filtered[elec_emis], errors='coerce').fillna(0)

                fuel_cost = find_column(df_raw_filtered, ['net fuel cost', 'net_fuel_cost'])
                if fuel_cost:
                    cols_to_aggregate['fuel_cost'] = pd.to_numeric(df_raw_filtered[fuel_cost], errors='coerce').fillna(0)

                fuel_emis = find_column(df_raw_filtered, ['net fuel emission', 'net_fuel_emission'])
                if fuel_emis:
                    cols_to_aggregate['fuel_emissions'] = pd.to_numeric(df_raw_filtered[fuel_emis], errors='coerce').fillna(0)

                # Pricing data (not aggregated, same for all buildings)
                elec_price = find_column(df_raw_filtered, ['electricity_pricing', 'electricity price', 'electricity_price', 'pricing'])
                if elec_price:
                    cols_to_aggregate['electricity_price'] = pd.to_numeric(df_raw_filtered[elec_price], errors='coerce').fillna(0)

                fuel_price = find_column(df_raw_filtered, ['fuel_pricing', 'fuel price', 'fuel_price', 'natural_gas_pricing'])
                if fuel_price:
                    cols_to_aggregate['fuel_price'] = pd.to_numeric(df_raw_filtered[fuel_price], errors='coerce').fillna(0)

                # Carbon intensity data (not aggregated, same for all buildings)
                carbon_int = find_column(df_raw_filtered, ['carbon_intensity', 'electricity carbon intensity', 'electricity_carbon_intensity'])
                if carbon_int:
                    cols_to_aggregate['electricity_carbon_intensity'] = pd.to_numeric(df_raw_filtered[carbon_int], errors='coerce').fillna(0)

                fuel_carbon = find_column(df_raw_filtered, ['fuel carbon intensity', 'fuel_carbon_intensity', 'natural_gas_carbon_intensity'])
                if fuel_carbon:
                    cols_to_aggregate['fuel_carbon_intensity'] = pd.to_numeric(df_raw_filtered[fuel_carbon], errors='coerce').fillna(0)

                # Detailed electricity consumption components
                # Cooling electricity
                cool_elec = find_column(df_raw_filtered, ['cooling electricity consumption', 'cooling_electricity_consumption'])
                if cool_elec:
                    cols_to_aggregate['cooling_electricity_consumption'] = pd.to_numeric(df_raw_filtered[cool_elec], errors='coerce').fillna(0)

                # Heating electricity
                heat_elec = find_column(df_raw_filtered, ['heating electricity consumption', 'heating_electricity_consumption'])
                if heat_elec:
                    cols_to_aggregate['heating_electricity_consumption'] = pd.to_numeric(df_raw_filtered[heat_elec], errors='coerce').fillna(0)

                # DHW electricity
                dhw_elec = find_column(df_raw_filtered, ['dhw electricity consumption', 'dhw_electricity_consumption'])
                if dhw_elec:
                    cols_to_aggregate['dhw_electricity_consumption'] = pd.to_numeric(df_raw_filtered[dhw_elec], errors='coerce').fillna(0)

                # DHW storage electricity consumption
                dhw_stor_elec = find_column(df_raw_filtered, ['dhw storage electricity consumption', 'dhw_storage_electricity_consumption'])
                if dhw_stor_elec:
                    cols_to_aggregate['dhw_storage_electricity_consumption'] = pd.to_numeric(df_raw_filtered[dhw_stor_elec], errors='coerce').fillna(0)

                # Non-shiftable load
                non_shift = find_column(df_raw_filtered, ['non shiftable load', 'non_shiftable_load', 'energy to non shiftable load'])
                if non_shift:
                    cols_to_aggregate['non_shiftable_load'] = pd.to_numeric(df_raw_filtered[non_shift], errors='coerce').fillna(0)

                # Electrical storage
                el_stor = find_column(df_raw_filtered, ['electrical storage electricity consumption', 'energy to electrical storage'])
                if el_stor:
                    cols_to_aggregate['electrical_storage_electricity_consumption'] = pd.to_numeric(df_raw_filtered[el_stor], errors='coerce').fillna(0)

                # Alternative: energy from/to storage
                from_stor = find_column(df_raw_filtered, ['energy from electrical storage'])
                if from_stor:
                    cols_to_aggregate['energy_from_electrical_storage'] = pd.to_numeric(df_raw_filtered[from_stor], errors='coerce').fillna(0)

                to_stor = find_column(df_raw_filtered, ['energy to electrical storage'])
                if to_stor:
                    cols_to_aggregate['energy_to_electrical_storage'] = pd.to_numeric(df_raw_filtered[to_stor], errors='coerce').fillna(0)

                # Create dataframe from extracted columns
                if cols_to_aggregate:
                    df_building = pd.DataFrame(cols_to_aggregate, index=df_raw_filtered.index)

                    # Aggregate
                    if aggregated_data is None:
                        aggregated_data = df_building
                    else:
                        # For price and carbon intensity, use the first building's values (don't sum)
                        # For energy/cost/emissions, sum across buildings
                        price_carbon_cols = ['electricity_pricing', 'fuel_pricing', 'carbon_intensity', 'fuel_carbon_intensity']

                        for col in df_building.columns:
                            if col in price_carbon_cols:
                                # Don't aggregate these - keep first building's values
                                if col not in aggregated_data.columns:
                                    aggregated_data[col] = df_building[col]
                            else:
                                # Sum these (energy, cost, emissions)
                                if col in aggregated_data.columns:
                                    aggregated_data[col] = aggregated_data[col].add(df_building[col], fill_value=0)
                                else:
                                    aggregated_data[col] = df_building[col]

        if aggregated_data is not None and not aggregated_data.empty:
            district_data[full_config_name] = aggregated_data
            print(f"[DEBUG] Aggregated data shape: {aggregated_data.shape}")

    if not district_data:
        return html.Div([
            html.Div("📊", style={'fontSize': '48px', 'marginBottom': '20px'}),
            html.H4("No district data available", style={'color': '#e74c3c'}),
            html.P("Could not load data for the selected configurations and buildings.",
                   style={'color': '#95a5a6'})
        ], style={'textAlign': 'center', 'padding': '80px'})

    # Create visualizations
    graphs = []

    # 1. ELECTRICAL CONSUMPTION TIME SERIES
    fig_elec = go.Figure()

    for i, (config_name, data) in enumerate(district_data.items()):
        if 'net_electricity_consumption' in data.columns:
            color = COLORS[i % len(COLORS)]
            fig_elec.add_trace(go.Scatter(
                x=data.index,
                y=data['net_electricity_consumption'],
                name=config_name,
                line=dict(color=color, width=2.5),
                mode='lines'
            ))

    fig_elec.update_layout(
        title=dict(
            text=f"District Net Electrical Consumption - {len(selected_buildings)} Buildings",
            font=dict(size=18, color='#2c3e50')
        ),
        xaxis_title="Time",
        yaxis_title="Net Electricity (kWh)",
        hovermode='x unified',
        template='plotly_white',
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    graphs.append(html.Div([
        html.H4("⚡ Electrical Consumption", style={'color': '#667eea', 'marginBottom': '15px'}),
        dcc.Graph(figure=fig_elec, config={'displayModeBar': True, 'displaylogo': False})
    ], style={'marginBottom': '30px'}))

    # 2. HEATING DEMAND TIME SERIES
    fig_heat = go.Figure()

    for i, (config_name, data) in enumerate(district_data.items()):
        if 'heating_demand' in data.columns:
            color = COLORS[i % len(COLORS)]
            fig_heat.add_trace(go.Scatter(
                x=data.index,
                y=data['heating_demand'],
                name=config_name,
                line=dict(color=color, width=2.5),
                mode='lines',
                fill='tozeroy',
                fillcolor=color_to_rgba(color, 0.2)
            ))

    fig_heat.update_layout(
        title=dict(
            text=f"District Heating Demand - {len(selected_buildings)} Buildings",
            font=dict(size=18, color='#2c3e50')
        ),
        xaxis_title="Time",
        yaxis_title="Heating Demand (kWh)",
        hovermode='x unified',
        template='plotly_white',
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    graphs.append(html.Div([
        html.H4("🔥 Heating Demand", style={'color': '#667eea', 'marginBottom': '15px'}),
        dcc.Graph(figure=fig_heat, config={'displayModeBar': True, 'displaylogo': False})
    ], style={'marginBottom': '30px'}))

    # 3. COSTS STACKED AREA CHARTS (one per configuration with toggle button)
    for i, (config_name, data) in enumerate(district_data.items()):
        has_elec_cost = 'electricity_cost' in data.columns and data['electricity_cost'].sum() != 0
        has_fuel_cost = 'fuel_cost' in data.columns and data['fuel_cost'].sum() != 0

        if has_elec_cost or has_fuel_cost:
            # Create two versions: all data and positive only
            color = COLORS[i % len(COLORS)]

            # Version 1: All data (including negative costs)
            fig_costs_all = go.Figure()

            if has_elec_cost:
                fig_costs_all.add_trace(go.Scatter(
                    x=data.index,
                    y=data['electricity_cost'],
                    name='Electricity Cost',
                    fill='tozeroy',
                    fillcolor='rgba(33, 150, 243, 0.6)',
                    line=dict(color='blue', width=1),
                    stackgroup='one'
                ))

            if has_fuel_cost:
                fig_costs_all.add_trace(go.Scatter(
                    x=data.index,
                    y=data['fuel_cost'],
                    name='Fuel Cost',
                    fill='tonexty',
                    fillcolor='rgba(244, 67, 54, 0.6)',
                    line=dict(color='red', width=1),
                    stackgroup='one'
                ))

            fig_costs_all.update_layout(
                title=dict(
                    text=f"District Energy Costs: {config_name} - All Values",
                    font=dict(size=16, color='#2c3e50')
                ),
                xaxis_title="Time",
                yaxis_title="Cost (€)",
                hovermode='x unified',
                template='plotly_white',
                height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                showlegend=True
            )

            # Version 2: Positive values only
            fig_costs_pos = go.Figure()

            if has_elec_cost:
                elec_cost_pos = data['electricity_cost'].clip(lower=0)
                fig_costs_pos.add_trace(go.Scatter(
                    x=data.index,
                    y=elec_cost_pos,
                    name='Electricity Cost',
                    fill='tozeroy',
                    fillcolor='rgba(33, 150, 243, 0.6)',
                    line=dict(color='blue', width=1),
                    stackgroup='one'
                ))

            if has_fuel_cost:
                fuel_cost_pos = data['fuel_cost'].clip(lower=0)
                fig_costs_pos.add_trace(go.Scatter(
                    x=data.index,
                    y=fuel_cost_pos,
                    name='Fuel Cost',
                    fill='tonexty',
                    fillcolor='rgba(244, 67, 54, 0.6)',
                    line=dict(color='red', width=1),
                    stackgroup='one'
                ))

            fig_costs_pos.update_layout(
                title=dict(
                    text=f"District Energy Costs: {config_name} - Positive Only",
                    font=dict(size=16, color='#2c3e50')
                ),
                xaxis_title="Time",
                yaxis_title="Cost (€)",
                hovermode='x unified',
                template='plotly_white',
                height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                showlegend=True
            )

            # Create a unique ID for this configuration's toggle
            toggle_id = f'cost-toggle-{i}'
            graph_id = f'cost-graph-{i}'

            # Create the cost section with toggle buttons
            cost_section = html.Div([
                html.Div([
                    html.H4("💰 Energy Costs", style={
                        'color': '#667eea',
                        'marginBottom': '15px',
                        'display': 'inline-block',
                        'marginRight': '20px'
                    }),
                    html.Div([
                        html.Button('All Values',
                                   id={'type': 'cost-btn-all', 'index': i},
                                   n_clicks=0,
                                   style={
                                       'padding': '8px 16px',
                                       'marginRight': '10px',
                                       'backgroundColor': '#667eea',
                                       'color': 'white',
                                       'border': 'none',
                                       'borderRadius': '5px',
                                       'cursor': 'pointer',
                                       'fontWeight': 'bold'
                                   }),
                        html.Button('Positive Only',
                                   id={'type': 'cost-btn-pos', 'index': i},
                                   n_clicks=0,
                                   style={
                                       'padding': '8px 16px',
                                       'backgroundColor': '#e0e0e0',
                                       'color': '#333',
                                       'border': 'none',
                                       'borderRadius': '5px',
                                       'cursor': 'pointer'
                                   })
                    ], style={'display': 'inline-block'})
                ], style={'marginBottom': '10px'}),

                # Store to keep track of which view is active
                dcc.Store(id={'type': 'cost-view-store', 'index': i}, data='all'),

                # Graph that will be updated
                dcc.Graph(
                    id={'type': 'cost-graph', 'index': i},
                    figure=fig_costs_all,
                    config={'displayModeBar': True, 'displaylogo': False}
                )
            ], style={'marginBottom': '30px'})

            graphs.append(cost_section)

            # Note: The callback for toggling will be added at the end of the file

    # 3b. DETAILED ELECTRICITY CONSUMPTION BREAKDOWN (for each configuration)
    for i, (config_name, data) in enumerate(district_data.items()):
        # Create detailed electricity consumption breakdown
        # This should match net_electricity_consumption when properly stacked

        fig_elec_breakdown = make_subplots(specs=[[{"secondary_y": False}]])

        # Define all electricity consumption components
        # Positive contributions (consumption)
        consumption_components = []

        # 1. Solar generation (negative - reduces net consumption)
        if 'solar_generation' in data.columns:
            consumption_components.append({
                'name': 'Solar Generation',
                'data': data['solar_generation'],  # Negative to show as reduction
                'color': 'rgba(255, 215, 0, 0.7)',  # Gold
                'line_color': 'gold'
            })


        # 2. Positive storage consumption (charging)
        if 'electrical_storage_electricity_consumption' in data.columns:
            consumption_components.append({
                'name': 'Storage',
                'data': data['electrical_storage_electricity_consumption'],
                'color': 'rgba(144, 238, 144, 0.7)',  # Light green
                'line_color': 'lightgreen'
            })

        # 3. Cooling electricity consumption
        if 'cooling_electricity_consumption' in data.columns:
            consumption_components.append({
                'name': 'Cooling',
                'data': data['cooling_electricity_consumption'],
                'color': 'rgba(135, 206, 250, 0.7)',  # Light blue
                'line_color': 'skyblue'
            })

        # 4. Heating electricity consumption
        if 'heating_electricity_consumption' in data.columns:
            consumption_components.append({
                'name': 'Heating',
                'data': data['heating_electricity_consumption'],
                'color': 'rgba(255, 140, 0, 0.7)',  # Dark orange
                'line_color': 'darkorange'
            })

        # 5. DHW electricity consumption
        if 'dhw_electricity_consumption' in data.columns:
            consumption_components.append({
                'name': 'DHW',
                'data': data['dhw_electricity_consumption'],
                'color': 'rgba(255, 192, 203, 0.7)',  # Pink
                'line_color': 'pink'
            })

        # 6. DHW storage electricity consumption
        if 'dhw_storage_electricity_consumption' in data.columns:
            consumption_components.append({
                'name': 'DHW Storage Consumption',
                'data': data['dhw_storage_electricity_consumption'],
                'color': 'rgba(255, 105, 180, 0.7)',  # Hot pink
                'line_color': 'hotpink'
            })

        # 7. Non-shiftable load
        if 'non_shiftable_load' in data.columns:
            consumption_components.append({
                'name': 'Non-Shiftable Load',
                'data': data['non_shiftable_load'],
                'color': 'rgba(169, 169, 169, 0.7)',  # Gray
                'line_color': 'gray'
            })




        # Add all components to the figure
        has_components = len(consumption_components) > 0

        if has_components:
            # First add all positive consumption components (stacked)
            for comp in consumption_components:
                fig_elec_breakdown.add_trace(go.Scatter(
                    x=data.index,
                    y=comp['data'],
                    name=comp['name'],
                    fill='tonexty',
                    fillcolor=comp['color'],
                    line=dict(color=comp['line_color'], width=1),
                    stackgroup='consumption',
                    mode='lines'
                ), secondary_y=False)

            # Add net electricity consumption as a line for verification
            if 'net_electricity_consumption' in data.columns:
                fig_elec_breakdown.add_trace(go.Scatter(
                    x=data.index,
                    y=data['net_electricity_consumption'],
                    name='Net Consumption (verify)',
                    line=dict(color='black', width=2.5, dash='dot'),
                    mode='lines'
                ), secondary_y=False)

            fig_elec_breakdown.update_layout(
                title=dict(
                    text=f"District Electricity Consumption Breakdown: {config_name}",
                    font=dict(size=16, color='#2c3e50')
                ),
                xaxis_title="Time",
                yaxis_title="Electricity (kWh)",
                hovermode='x unified',
                template='plotly_white',
                height=500,
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.05,
                    bgcolor='rgba(255,255,255,0.9)',
                    bordercolor='#e0e0e0',
                    borderwidth=1
                ),
                showlegend=True
            )

            # Add explanation note
            breakdown_section = html.Div([
                html.H4("⚡ Detailed Electricity Consumption Breakdown", style={
                    'color': '#667eea',
                    'marginBottom': '10px'
                }),
                html.P([
                    html.Strong("Note: "),
                    "The sum of all stacked areas should equal the net electricity consumption (black dotted line). ",
                    "Positive areas = consumption, negative areas = generation/discharge."
                ], style={
                    'fontSize': '12px',
                    'color': '#7f8c8d',
                    'marginBottom': '10px',
                    'fontStyle': 'italic'
                }),
                dcc.Graph(
                    figure=fig_elec_breakdown,
                    config={'displayModeBar': True, 'displaylogo': False}
                )
            ], style={'marginBottom': '30px'})

            graphs.append(breakdown_section)

    # 3c. ELECTRICITY CONSUMPTION COST BREAKDOWN (for each configuration)
    for i, (config_name, data) in enumerate(district_data.items()):
        # Create electricity cost breakdown as stacked area chart
        # Cost = consumption * price for each component

        # Check if we have pricing data
        price_col = None
        for col_name in ['electricity_pricing', 'electricity_price', 'pricing', 'price']:
            if col_name in data.columns:
                price_col = col_name
                break

        if price_col is not None:
            fig_cost_breakdown = make_subplots(specs=[[{"secondary_y": False}]])

            # Define cost components (consumption * price)
            cost_components = []

            # 1. Cooling electricity cost
            if 'cooling_electricity_consumption' in data.columns:
                cost_components.append({
                    'name': 'Cooling Cost',
                    'data': data['cooling_electricity_consumption'] * data[price_col],
                    'color': 'rgba(135, 206, 250, 0.7)',
                    'line_color': 'skyblue'
                })

            # 2. Heating electricity cost
            if 'heating_electricity_consumption' in data.columns:
                cost_components.append({
                    'name': 'Heating Cost',
                    'data': data['heating_electricity_consumption'] * data[price_col],
                    'color': 'rgba(255, 140, 0, 0.7)',
                    'line_color': 'darkorange'
                })

            # 3. DHW electricity cost
            if 'dhw_electricity_consumption' in data.columns:
                cost_components.append({
                    'name': 'DHW Cost',
                    'data': data['dhw_electricity_consumption'] * data[price_col],
                    'color': 'rgba(255, 192, 203, 0.7)',
                    'line_color': 'pink'
                })

            # 4. Non-shiftable load cost
            if 'non_shiftable_load' in data.columns:
                cost_components.append({
                    'name': 'Non-Shiftable Load Cost',
                    'data': data['non_shiftable_load'] * data[price_col],
                    'color': 'rgba(169, 169, 169, 0.7)',
                    'line_color': 'gray'
                })

            # 5. Storage charging cost
            if 'electrical_storage_electricity_consumption' in data.columns:
                cost_components.append({
                    'name': 'Storage Cost',
                    'data': data['electrical_storage_electricity_consumption'] * data[price_col],
                    'color': 'rgba(144, 238, 144, 0.7)',
                    'line_color': 'lightgreen'
                })

            # 6. DHW storage charging cost
            if 'dhw_storage_electricity_consumption' in data.columns:
                cost_components.append({
                    'name': 'DHW Storage Cost',
                    'data': data['dhw_storage_electricity_consumption'] * data[price_col],
                    'color': 'rgba(221, 160, 221, 0.7)',
                    'line_color': 'plum'
                })

            # 7. Solar generation savings (negative cost)
            if 'solar_generation' in data.columns:
                cost_components.append({
                    'name': 'Solar Savings',
                    'data': data['solar_generation'] * data[price_col],
                    'color': 'rgba(255, 215, 0, 0.7)',
                    'line_color': 'gold'
                })

            has_cost_components = len(cost_components) > 0

            if has_cost_components:
                # Add positive cost components (stacked)
                for comp in cost_components:
                    fig_cost_breakdown.add_trace(go.Scatter(
                        x=data.index,
                        y=comp['data'],
                        name=comp['name'],
                        fill='tonexty',
                        fillcolor=comp['color'],
                        line=dict(color=comp['line_color'], width=1),
                        stackgroup='costs',
                        mode='lines'
                    ), secondary_y=False)


                # Add net electricity cost as verification line
                net_cost_col = None
                for col_name in ['net electricity cost', 'net_electricity_cost', 'net electricity consumption cost']:
                    if col_name in data.columns:
                        net_cost_col = col_name
                        break

                if net_cost_col:
                    fig_cost_breakdown.add_trace(go.Scatter(
                        x=data.index,
                        y=data[net_cost_col],
                        name='Net Cost (verify)',
                        line=dict(color='black', width=2.5, dash='dot'),
                        mode='lines'
                    ), secondary_y=False)

                fig_cost_breakdown.update_layout(
                    title=dict(
                        text=f"District Electricity Cost Breakdown: {config_name}",
                        font=dict(size=16, color='#2c3e50')
                    ),
                    xaxis_title="Time",
                    yaxis_title="Cost (€)",
                    hovermode='x unified',
                    template='plotly_white',
                    height=500,
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=1,
                        xanchor="left",
                        x=1.05,
                        bgcolor='rgba(255,255,255,0.9)',
                        bordercolor='#e0e0e0',
                        borderwidth=1
                    ),
                    showlegend=True
                )

                cost_breakdown_section = html.Div([
                    html.H4("💰 Detailed Electricity Cost Breakdown", style={
                        'color': '#667eea',
                        'marginBottom': '10px'
                    }),
                    html.P([
                        html.Strong("Note: "),
                        "Each component's cost = consumption × electricity price. ",
                        "The sum of all stacked areas should equal the net electricity cost (black dotted line). ",
                        "Positive areas = costs, negative areas = savings from generation/discharge."
                    ], style={
                        'fontSize': '12px',
                        'color': '#7f8c8d',
                        'marginBottom': '10px',
                        'fontStyle': 'italic'
                    }),
                    dcc.Graph(
                        figure=fig_cost_breakdown,
                        config={'displayModeBar': True, 'displaylogo': False}
                    )
                ], style={'marginBottom': '30px'})

                graphs.append(cost_breakdown_section)

    # 4. ENHANCED ENERGY MIX WITH PRICES AND EMISSIONS (for each configuration)
    for i, (config_name, data) in enumerate(district_data.items()):
        has_elec = 'net_electricity_consumption' in data.columns
        has_fuel = 'fuel_consumption' in data.columns

        if has_elec or has_fuel:
            # Create figure with multiple y-axes

            fig_mix = make_subplots(
                specs=[[{"secondary_y": True}]]
            )

            # PRIMARY AXIS: Energy consumption (stacked areas)

            # Electricity consumption
            if has_elec:
                fig_mix.add_trace(go.Scatter(
                    x=data.index,
                    y=data['net_electricity_consumption'],
                    name='Electricity Consumption',
                    fill='tonexty',
                    fillcolor='rgba(33, 150, 243, 0.5)',
                    line=dict(color='blue', width=1),
                    stackgroup='two',
                    yaxis='y'
                ), secondary_y=False)

            # Fuel consumption
            if has_fuel:
                fig_mix.add_trace(go.Scatter(
                    x=data.index,
                    y=data['fuel_consumption'],
                    name='Fuel Consumption',
                    fill='tonexty',
                    fillcolor='rgba(244, 67, 54, 0.5)',
                    line=dict(color='red', width=1),
                    stackgroup='two',
                    yaxis='y'
                ), secondary_y=False)

            # SECONDARY AXIS: Prices (€/kWh) - as line plots
            # Try to find price columns
            elec_price_col = None
            fuel_price_col = None

            # Search for electricity price
            for col_name in ['electricity_price', 'electricity price', 'pricing', 'price']:
                if col_name in data.columns:
                    elec_price_col = col_name
                    break

            # Search for fuel price
            for col_name in ['fuel_pricing', 'fuel_price', 'fuel price', 'natural_gas_pricing']:
                if col_name in data.columns:
                    fuel_price_col = col_name
                    break

            # Add electricity price line
            if elec_price_col:
                fig_mix.add_trace(go.Scatter(
                    x=data.index,
                    y=data[elec_price_col],
                    name='Electricity Price',
                    line=dict(color='darkblue', width=2, dash='dot'),
                    mode='lines',
                    yaxis='y2'
                ), secondary_y=True)

            # Add fuel price line
            if fuel_price_col:
                fig_mix.add_trace(go.Scatter(
                    x=data.index,
                    y=data[fuel_price_col],
                    name='Fuel Price',
                    line=dict(color='darkred', width=2, dash='dot'),
                    mode='lines',
                    yaxis='y2'
                ), secondary_y=True)

            # THIRD AXIS: Carbon Intensity (kgCO₂/kWh) - will be overlaid
            # Search for carbon intensity columns
            elec_carbon_col = None
            fuel_carbon_col = None

            for col_name in ['electricity_carbon_intensity', 'electricity carbon intensity', 'carbon_emission_factor']:
                if col_name in data.columns:
                    elec_carbon_col = col_name
                    break

            for col_name in ['fuel_carbon_intensity', 'fuel carbon intensity', 'natural_gas_carbon_intensity']:
                if col_name in data.columns:
                    fuel_carbon_col = col_name
                    break

            # Add carbon intensity lines (we'll use a workaround to create a third axis)
            # Since plotly doesn't natively support 3 y-axes easily in this mode,
            # we'll add them to secondary axis but with different styling
            if elec_carbon_col:
                fig_mix.add_trace(go.Scatter(
                    x=data.index,
                    y=data[elec_carbon_col] * 100,  # Scale up for visibility
                    name='Elec. Carbon Int. (×100)',
                    line=dict(color='cyan', width=2, dash='dashdot'),
                    mode='lines',
                    yaxis='y2'
                ), secondary_y=True)

            if fuel_carbon_col:
                fig_mix.add_trace(go.Scatter(
                    x=data.index,
                    y=data[fuel_carbon_col] * 100,  # Scale up for visibility
                    name='Fuel Carbon Int. (×100)',
                    line=dict(color='magenta', width=2, dash='dashdot'),
                    mode='lines',
                    yaxis='y2'
                ), secondary_y=True)

            # Update axes labels
            fig_mix.update_xaxes(title_text="Time")
            fig_mix.update_yaxes(title_text="Energy (kWh)", secondary_y=False)
            fig_mix.update_yaxes(title_text="Price (€/kWh) / Carbon Int. (kgCO₂/kWh ×100)", secondary_y=True)

            fig_mix.update_layout(
                title=dict(
                    text=f"District Energy Mix with Pricing & Emissions: {config_name}",
                    font=dict(size=16, color='#2c3e50')
                ),
                hovermode='x unified',
                template='plotly_white',
                height=500,
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.05,
                    bgcolor='rgba(255,255,255,0.9)',
                    bordercolor='#e0e0e0',
                    borderwidth=1
                )
            )

            graphs.append(html.Div([
                dcc.Graph(figure=fig_mix, config={'displayModeBar': True, 'displaylogo': False})
            ], style={'marginBottom': '30px'}))

    # 4. CUMULATIVE METRICS TABLE
    summary_data = []
    for config_name, data in district_data.items():
        row = {'Configuration': config_name}

        # Cumulative values
        if 'net_electricity_consumption' in data.columns:
            row['Total Electricity (kWh)'] = data['net_electricity_consumption'].sum()

        if 'positive_electricity_consumption' in data.columns:
            row['Electricity Import (kWh)'] = data['positive_electricity_consumption'].sum()

        if 'solar_generation' in data.columns:
            row['Solar Generation (kWh)'] = data['solar_generation'].sum()

        if 'heating_demand' in data.columns:
            row['Heating Demand (kWh)'] = data['heating_demand'].sum()

        if 'cooling_demand' in data.columns:
            row['Cooling Demand (kWh)'] = data['cooling_demand'].sum()

        if 'dhw_demand' in data.columns:
            row['DHW Demand (kWh)'] = data['dhw_demand'].sum()

        if 'fuel_consumption' in data.columns:
            row['Fuel Consumption (kWh)'] = data['fuel_consumption'].sum()

        if 'electricity_cost' in data.columns:
            row['Electricity Cost ($)'] = data['electricity_cost'].sum()

        if 'fuel_cost' in data.columns:
            row['Fuel Cost ($)'] = data['fuel_cost'].sum()

        if 'electricity_emissions' in data.columns:
            row['Electricity Emissions (kg CO₂)'] = data['electricity_emissions'].sum()

        if 'fuel_emissions' in data.columns:
            row['Fuel Emissions (kg CO₂)'] = data['fuel_emissions'].sum()

        # Peak values
        if 'net_electricity_consumption' in data.columns:
            row['Peak Electricity (kW)'] = data['net_electricity_consumption'].max()

        if 'heating_demand' in data.columns:
            row['Peak Heating (kW)'] = data['heating_demand'].max()

        summary_data.append(row)

    summary_df = pd.DataFrame(summary_data)

    # Create summary table
    if not summary_df.empty:
        table = html.Div([
            html.H3([
                html.Span("📋", style={'marginRight': '10px'}),
                "District-Level Cumulative Metrics"
            ], style={
                'marginTop': 30,
                'marginBottom': 20,
                'color': '#2c3e50',
                'borderBottom': '3px solid #667eea',
                'paddingBottom': '10px'
            }),
            html.Div([
                html.Table([
                    html.Thead(
                        html.Tr([html.Th(col, style={
                            'backgroundColor': '#667eea',
                            'color': 'white',
                            'padding': '12px',
                            'textAlign': 'left' if col == 'Configuration' else 'center',
                            'fontSize': '13px',
                            'fontWeight': 'bold'
                        }) for col in summary_df.columns])
                    ),
                    html.Tbody([
                        html.Tr([
                            html.Td(
                                f"{val:,.2f}" if isinstance(val, (int, float)) and col != 'Configuration' else val,
                                style={
                                    'padding': '12px',
                                    'borderBottom': '1px solid #e0e0e0',
                                    'textAlign': 'left' if col == 'Configuration' else 'center',
                                    'fontWeight': '600' if col == 'Configuration' else 'normal',
                                    'fontSize': '12px',
                                    'fontFamily': 'monospace' if col != 'Configuration' else 'inherit'
                                }
                            )
                            for col, val in zip(summary_df.columns, row)
                        ], style={
                            'backgroundColor': '#f8f9fa' if idx % 2 == 0 else 'white'
                        })
                        for idx, row in enumerate(summary_df.values)
                    ])
                ], style={
                    'width': '100%',
                    'borderCollapse': 'collapse',
                    'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
                    'borderRadius': '8px',
                    'overflow': 'hidden'
                }),
            ], style={'overflowX': 'auto', 'marginTop': '20px'})
        ], style={
            'marginTop': '30px',
            'padding': '25px',
            'backgroundColor': 'white',
            'borderRadius': '10px',
            'boxShadow': '0 2px 8px rgba(0,0,0,0.1)'
        })

        graphs.append(table)

    # 5. KEY METRICS CARDS
    if len(district_data) > 0:
        first_config_data = list(district_data.values())[0]

        metrics_cards = []

        # Total buildings
        metrics_cards.append(html.Div([
            html.H3(f"{len(selected_buildings)}", style={'fontSize': '36px', 'margin': '0', 'color': '#667eea'}),
            html.P("Buildings", style={'margin': '5px 0 0 0', 'color': '#7f8c8d', 'fontSize': '14px'})
        ], style={
            'textAlign': 'center',
            'padding': '20px',
            'backgroundColor': '#f8f9fa',
            'borderRadius': '10px',
            'flex': '1',
            'minWidth': '150px'
        }))

        # Total electricity
        if 'net_electricity_consumption' in first_config_data.columns:
            total_elec = first_config_data['net_electricity_consumption'].sum()
            metrics_cards.append(html.Div([
                html.H3(f"{total_elec:,.0f}", style={'fontSize': '36px', 'margin': '0', 'color': '#667eea'}),
                html.P("Total Electricity (kWh)", style={'margin': '5px 0 0 0', 'color': '#7f8c8d', 'fontSize': '14px'})
            ], style={
                'textAlign': 'center',
                'padding': '20px',
                'backgroundColor': '#f8f9fa',
                'borderRadius': '10px',
                'flex': '1',
                'minWidth': '150px'
            }))

        # Total heating demand
        if 'heating_demand' in first_config_data.columns:
            total_heat = first_config_data['heating_demand'].sum()
            metrics_cards.append(html.Div([
                html.H3(f"{total_heat:,.0f}", style={'fontSize': '36px', 'margin': '0', 'color': '#667eea'}),
                html.P("Total Heating (kWh)", style={'margin': '5px 0 0 0', 'color': '#7f8c8d', 'fontSize': '14px'})
            ], style={
                'textAlign': 'center',
                'padding': '20px',
                'backgroundColor': '#f8f9fa',
                'borderRadius': '10px',
                'flex': '1',
                'minWidth': '150px'
            }))

        # Solar generation
        if 'solar_generation' in first_config_data.columns:
            total_solar = first_config_data['solar_generation'].sum()
            metrics_cards.append(html.Div([
                html.H3(f"{total_solar:,.0f}", style={'fontSize': '36px', 'margin': '0', 'color': '#667eea'}),
                html.P("Solar Generation (kWh)", style={'margin': '5px 0 0 0', 'color': '#7f8c8d', 'fontSize': '14px'})
            ], style={
                'textAlign': 'center',
                'padding': '20px',
                'backgroundColor': '#f8f9fa',
                'borderRadius': '10px',
                'flex': '1',
                'minWidth': '150px'
            }))

        metrics_row = html.Div(
            metrics_cards,
            style={
                'display': 'flex',
                'gap': '20px',
                'flexWrap': 'wrap',
                'marginBottom': '30px'
            }
        )

        graphs.insert(0, metrics_row)

    # Interpretation guide
    guide = html.Div([
        html.H4("📖 Interpretation Guide", style={'marginBottom': '15px', 'color': '#2c3e50'}),
        html.Ul([
            html.Li([
                html.Strong("District Aggregation: "),
                f"All metrics are aggregated across {len(selected_buildings)} selected buildings to show total district performance."
            ]),
            html.Li([
                html.Strong("Electrical Consumption: "),
                "Shows net electricity consumption (positive = import from grid, negative = export to grid)."
            ]),
            html.Li([
                html.Strong("Heating Demand: "),
                "Total heating energy required by all buildings in the district."
            ]),
            html.Li([
                html.Strong("Energy Costs (Stacked Areas): "),
                "Stacked area chart showing electricity costs (blue) and fuel costs (red). Toggle between 'All Values' (including revenue from export) and 'Positive Only' (expenses only)."
            ]),
            html.Li([
                html.Strong("Electricity Consumption Breakdown: "),
                "Detailed breakdown showing all electricity consumption components: cooling, heating, DHW, non-shiftable loads, and storage charging (positive areas). "
                "Solar generation and storage discharge appear as negative areas. The black dotted line shows net consumption for verification - the sum of all areas should match it."
            ]),
            html.Li([
                html.Strong("Enhanced Energy Mix: "),
                "Stacked areas show energy consumption (kWh). Dotted lines on secondary axis show real-time pricing (€/kWh). Dash-dot lines show carbon intensity (kgCO₂/kWh, scaled ×100 for visibility)."
            ]),
            html.Li([
                html.Strong("Price & Emissions Overlay: "),
                "Blue/red dotted lines = electricity/fuel prices. Cyan/magenta dash-dot lines = carbon intensity. Use this to understand when consuming energy has higher cost or environmental impact."
            ]),
            html.Li([
                html.Strong("Energy Balance Verification: "),
                "In the electricity breakdown, verify that: Cooling + Heating + DHW + Non-Shiftable + Storage Charging - Solar - Storage Discharge = Net Consumption."
            ]),
            html.Li([
                html.Strong("Cumulative Metrics: "),
                "Table shows total energy consumption, costs, and emissions for the selected time period."
            ]),
            html.Li([
                html.Strong("Configuration Comparison: "),
                "Different lines/colors represent different algorithm configurations for comparison."
            ]),
        ], style={'lineHeight': '1.8', 'color': '#34495e'})
    ], style={
        'backgroundColor': '#f8f9fa',
        'padding': '25px',
        'borderRadius': '10px',
        'border': '2px solid #667eea',
        'marginTop': 30
    })

    return html.Div([
        html.Div([
            html.H3([
                html.Span("🏙️", style={'marginRight': '10px'}),
                f"District Level Analysis - {len(selected_buildings)} Buildings"
            ], style={
                'marginBottom': 20,
                'color': '#2c3e50',
                'borderBottom': '3px solid #667eea',
                'paddingBottom': '10px'
            })
        ]),
        html.Div(graphs),
        guide
    ])


# ============================================================================
# CALLBACK FOR COST TOGGLE BUTTONS
# ============================================================================

@app.callback(
    Output({'type': 'cost-graph', 'index': dash.dependencies.MATCH}, 'figure'),
    Output({'type': 'cost-btn-all', 'index': dash.dependencies.MATCH}, 'style'),
    Output({'type': 'cost-btn-pos', 'index': dash.dependencies.MATCH}, 'style'),
    Input({'type': 'cost-btn-all', 'index': dash.dependencies.MATCH}, 'n_clicks'),
    Input({'type': 'cost-btn-pos', 'index': dash.dependencies.MATCH}, 'n_clicks'),
    State('dataset-dropdown', 'value'),
    State('building-checklist', 'value'),
    State('season-dropdown', 'value'),
    State('date-range', 'start_date'),
    State('date-range', 'end_date'),
    State({'type': 'algo-config-checklist', 'algorithm': dash.dependencies.ALL}, 'value'),
    State('algorithms-store', 'data'),
    State({'type': 'cost-graph', 'index': dash.dependencies.MATCH}, 'id')
)
def toggle_cost_view(n_clicks_all, n_clicks_pos, dataset, selected_buildings, season,
                     start_date, end_date, all_config_selections, configs_data, graph_id):
    """Toggle between all cost values and positive-only cost values."""

    # Determine which button was clicked
    ctx = dash.callback_context
    if not ctx.triggered:
        button_id = 'cost-btn-all'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        button_id = eval(button_id)['type']  # Extract the type from the pattern-matching ID

    # Button styles
    active_style = {
        'padding': '8px 16px',
        'backgroundColor': '#667eea',
        'color': 'white',
        'border': 'none',
        'borderRadius': '5px',
        'cursor': 'pointer',
        'fontWeight': 'bold'
    }

    inactive_style = {
        'padding': '8px 16px',
        'backgroundColor': '#e0e0e0',
        'color': '#333',
        'border': 'none',
        'borderRadius': '5px',
        'cursor': 'pointer'
    }

    # Determine which view to show
    show_positive_only = button_id == 'cost-btn-pos'

    # Get the configuration index from the graph_id
    config_idx = graph_id['index']

    # Collect selected configurations
    selected_configs = []
    if all_config_selections:
        for selections in all_config_selections:
            if selections:
                selected_configs.extend(selections)

    if not selected_configs and configs_data:
        selected_configs = list(configs_data.keys())[:3]

    # Check if we have enough data
    if not all([dataset, selected_buildings, selected_configs, configs_data]) or config_idx >= len(selected_configs):
        # Return empty figure with default styles
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title="No data available",
            template='plotly_white',
            height=400
        )
        return empty_fig, active_style if not show_positive_only else inactive_style, inactive_style if not show_positive_only else active_style

    # Get the configuration for this graph
    config_key = selected_configs[config_idx]
    config = configs_data[config_key]

    algo_name_formatted = config['algorithm'].replace('_', ' ').title()
    config_display_name = config['display_name']
    full_config_name = f"{algo_name_formatted}: {config_display_name}"

    # Aggregate data for this configuration
    aggregated_data = None

    for building_id in selected_buildings:
        df = load_observation_data(dataset, config, building_id, season)

        if df is None or df.empty:
            continue

        df_filtered = df.loc[start_date:end_date].copy()

        if df_filtered.empty:
            continue

        # Load raw CSV
        algo_path = Path(config['path']) if isinstance(config['path'], str) else config['path']
        obs_file = (DATA_DIR / dataset / "schema.json" / "obs" /
                   algo_path / f"obs_building_{building_id}.csv")

        if obs_file.exists():
            df_raw = pd.read_csv(obs_file)
            start_date_dt = SEASONS.get(season, SEASONS["winter"])
            df_raw.index = pd.date_range(start=start_date_dt, periods=len(df_raw), freq="h")
            df_raw_filtered = df_raw.loc[start_date:end_date]

            cols_to_aggregate = {}

            # Cost data
            elec_cost = find_column(df_raw_filtered, ['net electricity cost', 'net_electricity_cost'])
            if elec_cost:
                cols_to_aggregate['electricity_cost'] = pd.to_numeric(df_raw_filtered[elec_cost], errors='coerce').fillna(0)

            fuel_cost = find_column(df_raw_filtered, ['net fuel cost', 'net_fuel_cost'])
            if fuel_cost:
                cols_to_aggregate['fuel_cost'] = pd.to_numeric(df_raw_filtered[fuel_cost], errors='coerce').fillna(0)

            if cols_to_aggregate:
                df_building = pd.DataFrame(cols_to_aggregate, index=df_raw_filtered.index)

                if aggregated_data is None:
                    aggregated_data = df_building
                else:
                    for col in df_building.columns:
                        if col in aggregated_data.columns:
                            aggregated_data[col] = aggregated_data[col].add(df_building[col], fill_value=0)
                        else:
                            aggregated_data[col] = df_building[col]

    # Create the figure
    fig = go.Figure()

    if aggregated_data is not None and not aggregated_data.empty:
        has_elec_cost = 'electricity_cost' in aggregated_data.columns
        has_fuel_cost = 'fuel_cost' in aggregated_data.columns

        if show_positive_only:
            # Positive values only
            if has_elec_cost:
                elec_cost_data = aggregated_data['electricity_cost'].clip(lower=0)
                fig.add_trace(go.Scatter(
                    x=aggregated_data.index,
                    y=elec_cost_data,
                    name='Electricity Cost',
                    fill='tozeroy',
                    fillcolor='rgba(33, 150, 243, 0.6)',
                    line=dict(color='blue', width=1),
                    stackgroup='one'
                ))

            if has_fuel_cost:
                fuel_cost_data = aggregated_data['fuel_cost'].clip(lower=0)
                fig.add_trace(go.Scatter(
                    x=aggregated_data.index,
                    y=fuel_cost_data,
                    name='Fuel Cost',
                    fill='tonexty',
                    fillcolor='rgba(244, 67, 54, 0.6)',
                    line=dict(color='red', width=1),
                    stackgroup='one'
                ))

            title_suffix = "Positive Only"
        else:
            # All values
            if has_elec_cost:
                fig.add_trace(go.Scatter(
                    x=aggregated_data.index,
                    y=aggregated_data['electricity_cost'],
                    name='Electricity Cost',
                    fill='tozeroy',
                    fillcolor='rgba(33, 150, 243, 0.6)',
                    line=dict(color='blue', width=1),
                    stackgroup='one'
                ))

            if has_fuel_cost:
                fig.add_trace(go.Scatter(
                    x=aggregated_data.index,
                    y=aggregated_data['fuel_cost'],
                    name='Fuel Cost',
                    fill='tonexty',
                    fillcolor='rgba(244, 67, 54, 0.6)',
                    line=dict(color='red', width=1),
                    stackgroup='one'
                ))

            title_suffix = "All Values"

        fig.update_layout(
            title=dict(
                text=f"District Energy Costs: {full_config_name} - {title_suffix}",
                font=dict(size=16, color='#2c3e50')
            ),
            xaxis_title="Time",
            yaxis_title="Cost (€)",
            hovermode='x unified',
            template='plotly_white',
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            showlegend=True
        )
    else:
        fig.update_layout(
            title="No cost data available",
            template='plotly_white',
            height=400
        )

    # Return figure and button styles
    if show_positive_only:
        return fig, inactive_style, active_style
    else:
        return fig, active_style, inactive_style


# ============================================================================
# MAIN
# ============================================================================

# ============================================================================
# CALLBACKS FOR BEST CONFIGURATION FINDER
# ============================================================================

@app.callback(
    Output('weight-sum-indicator', 'children'),
    Input('weight-comfort', 'value'),
    Input('weight-cost', 'value'),
    Input('weight-emissions', 'value')
)
def update_weight_sum_indicator(w_comfort, w_cost, w_emissions):
    """Display the sum of weights and warn if not equal to 1."""
    total = w_comfort + w_cost + w_emissions

    if abs(total - 1.0) < 0.01:
        return html.Div([
            html.Span("✅ ", style={'marginRight': '5px'}),
            f"Weights sum: {total:.2f} (Normalized)"
        ], style={'color': '#27ae60', 'fontWeight': 'bold'})
    else:
        return html.Div([
            html.Span("⚠️ ", style={'marginRight': '5px'}),
            f"Weights sum: {total:.2f} (Will be automatically normalized)"
        ], style={'color': '#f39c12', 'fontWeight': 'bold'})


@app.callback(
    Output('best-config-results', 'children'),
    Input('calculate-best-config-btn', 'n_clicks'),
    State('weight-comfort', 'value'),
    State('weight-cost', 'value'),
    State('weight-emissions', 'value'),
    State('dataset-dropdown', 'value'),
    State('building-checklist', 'value'),
    State('season-dropdown', 'value'),
    State('date-range', 'start_date'),
    State('date-range', 'end_date'),
    State({'type': 'algo-config-checklist', 'algorithm': dash.dependencies.ALL}, 'value'),
    State('algorithms-store', 'data'),
    prevent_initial_call=True
)
def calculate_best_configuration(n_clicks, w_comfort, w_cost, w_emissions,
                                 dataset, selected_buildings, season,
                                 start_date, end_date, all_config_selections, configs_data):
    """Calculate and display the best configuration based on custom weights."""

    if n_clicks == 0:
        return html.Div()

    # Normalize weights
    total_weight = w_comfort + w_cost + w_emissions
    if total_weight == 0:
        total_weight = 1.0

    weights = {
        'comfort_violations': w_comfort / total_weight,
        'cost': w_cost / total_weight,
        'emissions': w_emissions / total_weight
    }

    # Collect selected configurations
    selected_configs = []
    if all_config_selections:
        for selections in all_config_selections:
            if selections:
                selected_configs.extend(selections)

    if not selected_configs:
        return html.Div([
            html.Div("⚠️", style={'fontSize': '36px', 'marginBottom': '10px'}),
            html.P("Please select at least one configuration to compare.", style={'color': '#e74c3c'})
        ], style={'textAlign': 'center', 'padding': '40px'})

    # Calculate composite scores for each configuration
    composite_scores = []
    raw_metrics = {}

    for config_key in selected_configs:
        config = configs_data[config_key]
        algo_name_formatted = config['algorithm'].replace('_', ' ').title()
        config_display_name = config['display_name']
        full_config_name = f"{algo_name_formatted}: {config_display_name}"

        # Aggregate metrics across buildings
        total_comfort_violations = 0
        total_cost = 0
        total_emissions = 0
        total_energy = 0

        for building_id in selected_buildings:
            df_obs = load_observation_data(dataset, config, building_id, season)

            if df_obs is not None and not df_obs.empty:
                df_filtered = df_obs.loc[start_date:end_date]

                if not df_filtered.empty:
                    # Comfort violations
                    if all(col in df_filtered.columns for col in ["tin", "comfort_low", "comfort_high"]):
                        violations_above = (df_filtered["tin"] > df_filtered["comfort_high"]).sum()
                        violations_below = (df_filtered["tin"] < df_filtered["comfort_low"]).sum()
                        total_comfort_violations += violations_above + violations_below

                    # Energy
                    if "cooling demand" in df_filtered.columns:
                        total_energy += df_filtered["cooling demand"].sum()
                    if "heating demand" in df_filtered.columns:
                        total_energy += df_filtered["heating demand"].sum()
                    if "dhw demand" in df_filtered.columns:
                        total_energy += df_filtered["dhw demand"].sum()

                    # Cost
                    col_elec_cost = find_column(df_filtered, ['net electricity consumption cost', 'net electricity cost'])
                    if col_elec_cost:
                        total_cost += pd.to_numeric(df_filtered[col_elec_cost], errors='coerce').fillna(0).clip(lower=0).sum()

                    # Emissions
                    col_elec_emis = find_column(df_filtered, ['net electricity consumption emission', 'net electricity emission'])
                    if col_elec_emis:
                        total_emissions += pd.to_numeric(df_filtered[col_elec_emis], errors='coerce').fillna(0).clip(lower=0).sum()

        raw_metrics[full_config_name] = {
            'comfort': total_comfort_violations,
            'cost': total_cost,
            'emissions': total_emissions,
            'energy': total_energy
        }

    # Normalize metrics (min-max normalization)
    all_comfort = [m['comfort'] for m in raw_metrics.values()]
    all_costs = [m['cost'] for m in raw_metrics.values()]
    all_emissions = [m['emissions'] for m in raw_metrics.values()]

    min_comfort = min(all_comfort) if all_comfort else 0
    max_comfort = max(all_comfort) if all_comfort else 1
    min_cost = min(all_costs) if all_costs else 0
    max_cost = max(all_costs) if all_costs else 1
    min_emissions = min(all_emissions) if all_emissions else 0
    max_emissions = max(all_emissions) if all_emissions else 1

    for config_name, metrics in raw_metrics.items():
        # Normalize to [0, 1]
        norm_comfort = (metrics['comfort'] - min_comfort) / (max_comfort - min_comfort) if max_comfort > min_comfort else 0
        norm_cost = (metrics['cost'] - min_cost) / (max_cost - min_cost) if max_cost > min_cost else 0
        norm_emissions = (metrics['emissions'] - min_emissions) / (max_emissions - min_emissions) if max_emissions > min_emissions else 0

        # Calculate composite score
        composite = (
            weights['comfort_violations'] * norm_comfort +
            weights['cost'] * norm_cost +
            weights['emissions'] * norm_emissions
        )

        composite_scores.append({
            'Configuration': config_name,
            'Composite Score': composite,
            'Comfort Violations': metrics['comfort'],
            'Total Cost': metrics['cost'],
            'Total Emissions': metrics['emissions'],
            'Total Energy': metrics['energy']
        })

    # Sort by composite score (lower is better)
    composite_scores.sort(key=lambda x: x['Composite Score'])

    # Create ranking table
    table_rows = []
    for rank, score_data in enumerate(composite_scores, start=1):
        # Medal for top 3
        medal = ""
        row_style = {}
        if rank == 1:
            medal = "🥇 "
            row_style = {'backgroundColor': '#fff9e6', 'fontWeight': 'bold'}
        elif rank == 2:
            medal = "🥈 "
            row_style = {'backgroundColor': '#f0f0f0'}
        elif rank == 3:
            medal = "🥉 "
            row_style = {'backgroundColor': '#f8f8f8'}

        table_rows.append(html.Tr([
            html.Td(f"{medal}{rank}", style={'padding': '12px', 'textAlign': 'center'}),
            html.Td(score_data['Configuration'], style={'padding': '12px'}),
            html.Td(f"{score_data['Composite Score']:.4f}", style={'padding': '12px', 'textAlign': 'center', 'fontFamily': 'monospace'}),
            html.Td(f"{score_data['Comfort Violations']:.0f}", style={'padding': '12px', 'textAlign': 'center'}),
            html.Td(f"${score_data['Total Cost']:.2f}", style={'padding': '12px', 'textAlign': 'center'}),
            html.Td(f"{score_data['Total Emissions']:.2f} kg", style={'padding': '12px', 'textAlign': 'center'}),
            html.Td(f"{score_data['Total Energy']:.2f} kWh", style={'padding': '12px', 'textAlign': 'center'}),
        ], style=row_style))

    ranking_table = html.Table([
        html.Thead(html.Tr([
            html.Th('Rank', style={'backgroundColor': '#667eea', 'color': 'white', 'padding': '12px', 'textAlign': 'center'}),
            html.Th('Configuration', style={'backgroundColor': '#667eea', 'color': 'white', 'padding': '12px'}),
            html.Th('Composite Score', style={'backgroundColor': '#667eea', 'color': 'white', 'padding': '12px', 'textAlign': 'center'}),
            html.Th('Comfort Violations', style={'backgroundColor': '#667eea', 'color': 'white', 'padding': '12px', 'textAlign': 'center'}),
            html.Th('Total Cost', style={'backgroundColor': '#667eea', 'color': 'white', 'padding': '12px', 'textAlign': 'center'}),
            html.Th('Total Emissions', style={'backgroundColor': '#667eea', 'color': 'white', 'padding': '12px', 'textAlign': 'center'}),
            html.Th('Total Energy', style={'backgroundColor': '#667eea', 'color': 'white', 'padding': '12px', 'textAlign': 'center'}),
        ])),
        html.Tbody(table_rows)
    ], style={
        'width': '100%',
        'borderCollapse': 'collapse',
        'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
        'borderRadius': '8px',
        'overflow': 'hidden'
    })

    # Create bar chart for composite scores
    fig_composite = go.Figure()

    colors_list = ['#27ae60' if i == 0 else '#667eea' for i in range(len(composite_scores))]

    fig_composite.add_trace(go.Bar(
        x=[s['Configuration'] for s in composite_scores],
        y=[s['Composite Score'] for s in composite_scores],
        marker=dict(color=colors_list),
        text=[f"{s['Composite Score']:.4f}" for s in composite_scores],
        textposition='outside'
    ))

    fig_composite.update_layout(
        title=dict(
            text=f"Composite Score Ranking<br><sub>Weights: Comfort={weights['comfort_violations']:.1%}, Cost={weights['cost']:.1%}, Emissions={weights['emissions']:.1%}</sub>",
            font=dict(size=16, color='#2c3e50')
        ),
        xaxis_title="Configuration",
        yaxis_title="Composite Score (Lower is Better)",
        template='plotly_white',
        height=400,
        showlegend=False
    )

    # Winner announcement
    winner = composite_scores[0]
    winner_box = html.Div([
        html.H3([
            html.Span("🏆 ", style={'fontSize': '32px'}),
            "Best Configuration"
        ], style={'color': '#27ae60', 'marginBottom': '10px'}),
        html.H4(winner['Configuration'], style={'color': '#2c3e50', 'marginBottom': '15px'}),
        html.P([
            html.Strong("Composite Score: "),
            f"{winner['Composite Score']:.4f}"
        ], style={'fontSize': '16px', 'marginBottom': '10px'}),
        html.P([
            "This configuration achieves the best balance between comfort, cost, and emissions ",
            "based on your custom weights."
        ], style={'color': '#7f8c8d', 'lineHeight': '1.6'})
    ], style={
        'backgroundColor': '#e8f8f5',
        'padding': '25px',
        'borderRadius': '10px',
        'border': '3px solid #27ae60',
        'marginBottom': '30px',
        'textAlign': 'center'
    })

    return html.Div([
        winner_box,
        html.Div([
            dcc.Graph(figure=fig_composite, config={'displayModeBar': True, 'displaylogo': False})
        ], style={'marginBottom': '30px'}),
        html.H4("📊 Detailed Rankings", style={'marginTop': '30px', 'marginBottom': '15px', 'color': '#2c3e50'}),
        ranking_table,
        html.P([
            html.Strong("💡 Note: "),
            "The composite score is calculated by normalizing each metric (comfort violations, cost, emissions) to a 0-1 scale, ",
            "then taking a weighted average based on your custom weights. Lower scores indicate better overall performance."
        ], style={
            'marginTop': '20px',
            'padding': '15px',
            'backgroundColor': '#e8f4f8',
            'borderRadius': '5px',
            'fontSize': '13px',
            'color': '#2c3e50',
            'lineHeight': '1.6',
            'border': '1px solid #bee5eb'
        })
    ])


if __name__ == '__main__':
    print("=" * 80)
    print("AAC-MADRL Interactive Dashboard")
    print("=" * 80)
    print(f"\nData directory: {DATA_DIR}")
    print(f"Available countries: {', '.join(available_countries)}")
    print("\nStarting server...")
    print("=" * 80)

    app.run(debug=True, port=8050)

