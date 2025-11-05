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
    "tin": ["indoor_temperature", "T_in", "temperature"],
    "tout": ["outdoor_dry_bulb_temperature", "outdoor_temperature", "T_out"],
    "sp": ["cooling_sp", "cooling_setpoint", "setpoint"],
    "band": ["comfort_band"],
    "cool_demand": ["cooling demand", "cooling_demand", "cool_dmd", "cooling_power", "cooling_energy"],
    "heat_demand": ["heating demand", "heating_demand", "heat_demand", "heating_power", "heating_energy"],
    # ***FIX 2: Added dhw_demand mapping***
    "dhw_demand": ["dhw demand", "dhw_demand", "dhw_power", "dhw_energy"],
}

# ***FIX 3: Updated action columns***
ACTION_COLUMNS = ["heating_storage", "electrical_storage", "heating_device"]

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
            standardized["comfort_low"] = standardized["sp"] - standardized["band"]
            standardized["comfort_high"] = standardized["sp"] + standardized["band"]

        # Clip demands to non-negative
        if "cool_demand" in standardized.columns:
            standardized["cool_demand"] = standardized["cool_demand"].clip(lower=0)
        if "heat_demand" in standardized.columns:
            standardized["heat_demand"] = standardized["heat_demand"].clip(lower=0)
        # ***FIX 2: Clip dhw_demand***
        if "dhw_demand" in standardized.columns:
            standardized["dhw_demand"] = standardized["dhw_demand"].clip(lower=0)

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
    if "cool_demand" in df.columns:
        kpis["Total Cooling Demand"] = df["cool_demand"].sum()
        kpis["Avg Cooling Demand"] = df["cool_demand"].mean()
        kpis["Max Cooling Demand"] = df["cool_demand"].max()

    if "heat_demand" in df.columns:
        kpis["Total Heating Demand"] = df["heat_demand"].sum()
        kpis["Avg Heating Demand"] = df["heat_demand"].mean()
        kpis["Max Heating Demand"] = df["heat_demand"].max()

    # ***FIX 2: Add DHW KPIs***
    if "dhw_demand" in df.columns:
        kpis["Total DHW Demand"] = df["dhw_demand"].sum()
        kpis["Avg DHW Demand"] = df["dhw_demand"].mean()
        kpis["Max DHW Demand"] = df["dhw_demand"].max()

    if "cool_demand" in df.columns and "heat_demand" in df.columns:
        total_energy = df["cool_demand"].sum() + df["heat_demand"].sum()
        if "dhw_demand" in df.columns:
            total_energy += df["dhw_demand"].sum()
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
    from plotly.subplots import make_subplots
    n_buildings = len(selected_buildings)

    fig = make_subplots(
        rows=n_buildings, cols=1,
        subplot_titles=[f"Building {bid}" for bid in selected_buildings],
        shared_xaxes=True,
        vertical_spacing=0.05
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

    fig.update_layout(
        title=dict(
            text=f"Temperature Profile - {len(selected_buildings)} Building(s), {len(selected_configs)} Configuration(s)",
            font=dict(size=18, color='#2c3e50')
        ),
        hovermode='x unified',
        height=400 * n_buildings,
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

    return dcc.Graph(figure=fig, config={'displayModeBar': True, 'displaylogo': False})


def render_demands_tab(dataset, selected_buildings, selected_configs, season,
                       start_date, end_date, configs_data):
    """Render energy demands visualization for multiple buildings."""
    n_buildings = len(selected_buildings)

    # ***FIX 2: Update rows and titles for 3 demands***
    fig = make_subplots(
        rows=n_buildings * 3, cols=1,
        subplot_titles=[item for bid in selected_buildings for item in
                        (f"Building {bid} - Cooling", f"Building {bid} - Heating", f"Building {bid} - DHW")],
        shared_xaxes=True,
        vertical_spacing=0.03
    )

    # Load data for each building
    for bldg_idx, building_id in enumerate(selected_buildings):
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
            if 'cool_demand' in df_filtered.columns:
                fig.add_trace(go.Scatter(
                    x=df_filtered.index,
                    y=df_filtered['cool_demand'],
                    name=legend_name + (f" - B{building_id}" if n_buildings > 1 else ""),
                    line=dict(color=color, width=2.5),
                    mode='lines',
                    showlegend=(bldg_idx == 0),
                    fill='tozeroy',
                    fillcolor=f'rgba{tuple(list(px.colors.hex_to_rgb(color)) + [0.1])}'
                ), row=row_cooling, col=1)

            # Heating demand
            if 'heat_demand' in df_filtered.columns:
                fig.add_trace(go.Scatter(
                    x=df_filtered.index,
                    y=df_filtered['heat_demand'],
                    name=legend_name + (f" - B{building_id}" if n_buildings > 1 else ""),
                    line=dict(color=color, width=2.5, dash='dash'),
                    mode='lines',
                    showlegend=False,
                    fill='tozeroy',
                    fillcolor=f'rgba{tuple(list(px.colors.hex_to_rgb(color)) + [0.1])}'
                ), row=row_heating, col=1)

            # ***FIX 2: Add DHW demand plot***
            if 'dhw_demand' in df_filtered.columns:
                fig.add_trace(go.Scatter(
                    x=df_filtered.index,
                    y=df_filtered['dhw_demand'],
                    name=legend_name + (f" - B{building_id}" if n_buildings > 1 else ""),
                    line=dict(color=color, width=2.5, dash='dot'),
                    mode='lines',
                    showlegend=False,
                    fill='tozeroy',
                    fillcolor=f'rgba{tuple(list(px.colors.hex_to_rgb(color)) + [0.1])}'
                ), row=row_dhw, col=1)

    # Update axes
    # ***FIX 2: Update axis loop***
    for i in range(1, n_buildings * 3 + 1):
        fig.update_yaxes(title_text="Power (kW)", row=i, col=1)
    fig.update_xaxes(title_text="Time", row=n_buildings * 3, col=1)

    fig.update_layout(
        title=dict(
            text=f"Energy Demands - {len(selected_buildings)} Building(s), {len(selected_configs)} Configuration(s)",
            font=dict(size=18, color='#2c3e50')
        ),
        hovermode='x unified',
        # ***FIX 2: Update figure height***
        height=300 * n_buildings * 3,
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

    return dcc.Graph(figure=fig, config={'displayModeBar': True, 'displaylogo': False})


def render_actions_tab(dataset, selected_buildings, selected_configs, season,
                       start_date, end_date, configs_data):
    """Render actions visualization with smart KPIs."""
    # Use first selected building for actions
    building_id = selected_buildings[0] if selected_buildings else 0

    # ***FIX 3: Update subplot titles based on new ACTION_COLUMNS***
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=("Heating Storage Action", "Electrical Storage Action", "Heating Device Action"),
        shared_xaxes=True,
        vertical_spacing=0.08
    )

    # ***FIX 3: ACTION_COLUMNS is now defined globally, no need to redefine***
    # action_cols = ["heating_storage", "electrical_storage", "heating_device"]

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

        # Plot each action dimension
        # ***FIX 3: Iterates over global ACTION_COLUMNS***
        for row_idx, col_name in enumerate(ACTION_COLUMNS, start=1):
            if col_name in df_filtered.columns:
                fig.add_trace(go.Scatter(
                    x=df_filtered.index,
                    y=df_filtered[col_name],
                    name=legend_name,
                    line=dict(color=color, width=2.5),
                    mode='lines',
                    showlegend=(row_idx == 1)  # Only show legend once
                ), row=row_idx, col=1)

    fig.update_xaxes(title_text="Time", row=3, col=1)
    for i in range(1, 4):
        fig.update_yaxes(title_text="Action Value", row=i, col=1)

    fig.update_layout(
        title=dict(
            text=f"Controller Actions - Building {building_id}",
            font=dict(size=18, color='#2c3e50')
        ),
        hovermode='x unified',
        height=900,
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

    # Calculate action KPIs
    kpi_data = []
    for config_key in selected_configs:
        config = configs_data[config_key]
        df = load_action_data(dataset, config, building_id, season)

        if df is not None and not df.empty:
            df_filtered = df.loc[start_date:end_date]
            kpis = calculate_action_kpis(df_filtered)

            # Create full legend name for table
            algo_name_formatted = config['algorithm'].replace('_', ' ').title()
            config_display_name = config['display_name']
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
                        html.Tr([html.Th('Configuration', style={
                            'backgroundColor': '#667eea',
                            'color': 'white',
                            'padding': '12px',
                            'textAlign': 'left',
                            'borderRadius': '5px 0 0 0'
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
                                    html.Td(row['Configuration'], style={
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

        return html.Div([
            dcc.Graph(figure=fig, config={'displayModeBar': True, 'displaylogo': False}),
            table
        ])

    return dcc.Graph(figure=fig, config={'displayModeBar': True, 'displaylogo': False})


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

    # Create detailed KPI table with improved styling
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
                            style={
                                'padding': '12px 10px',
                                'borderBottom': '1px solid #e0e0e0',
                                'textAlign': 'left' if col == 'Configuration' else 'center',
                                'fontWeight': '600' if col == 'Configuration' else 'normal',
                                'fontSize': '12px',
                                'fontFamily': 'monospace' if col != 'Configuration' else 'inherit',
                                'color': '#2c3e50' if col == 'Configuration' else '#34495e'
                            }
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
                    if "cool_demand" in df_filtered.columns and "heat_demand" in df_filtered.columns:
                        energy = df_filtered["cool_demand"].sum() + df_filtered["heat_demand"].sum()
                        if "dhw_demand" in df_filtered.columns:
                            energy += df_filtered["dhw_demand"].sum()
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
    if len(scatter_df) > 0:
        categories = ['Comfort Violations', 'Total Energy', 'Violation Rate (%)']
        if scatter_df['Electricity Cost'].sum() > 0:
            categories.append('Electricity Cost')

        fig3 = go.Figure()

        for i, row in scatter_df.iterrows():
            # Normalize values to 0-100 scale (inverted for lower-is-better metrics)
            values = []
            for cat in categories:
                if cat == 'Violation Rate (%)':
                    val = row['Violation Rate']
                else:
                    val = row[cat.replace(' (%)', '')]

                max_val = scatter_df[cat.replace(' (%)', '')].max() if cat != 'Violation Rate (%)' else scatter_df[
                    'Violation Rate'].max()

                # Invert normalization (100 = best, 0 = worst)
                if max_val > 0:
                    normalized = 100 - (val / max_val * 100)
                else:
                    normalized = 100
                values.append(normalized)

            values.append(values[0])  # Close the polygon

            fig3.add_trace(go.Scatterpolar(
                r=values,
                theta=categories + [categories[0]],
                name=row['Configuration'],
                fill='toself',
                line=dict(color=COLORS[i % len(COLORS)], width=2)
            ))

        fig3.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    ticktext=['Worst', '', '', '', '', 'Best'],
                    tickvals=[0, 20, 40, 60, 80, 100]
                )
            ),
            showlegend=True,
            title=dict(
                text="Multi-dimensional Performance Comparison<br><sub>(Higher = Better Performance)</sub>",
                font=dict(size=16, color='#2c3e50')
            ),
            template='plotly_white',
            height=500,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
    else:
        fig3 = None

    # Create layout
    graphs = []

    # Row 1: Energy-Comfort scatter
    graphs.append(
        html.Div([
            dcc.Graph(figure=fig1, config={'displayModeBar': True, 'displaylogo': False})
        ], style={'marginBottom': '30px'})
    )

    # Row 2: Cost-Emissions scatter and Radar chart
    if fig2 and fig3:
        graphs.append(
            html.Div([
                html.Div([
                    dcc.Graph(figure=fig2, config={'displayModeBar': True, 'displaylogo': False})
                ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
                html.Div([
                    dcc.Graph(figure=fig3, config={'displayModeBar': True, 'displaylogo': False})
                ], style={'width': '48%', 'display': 'inline-block', 'marginLeft': '4%', 'verticalAlign': 'top'}),
            ], style={'marginBottom': '30px'})
        )
    elif fig3:
        graphs.append(
            html.Div([
                dcc.Graph(figure=fig3, config={'displayModeBar': True, 'displaylogo': False})
            ], style={'marginBottom': '30px'})
        )

    # Interpretation guide
    guide = html.Div([
        html.H4("📖 Interpretation Guide", style={'marginBottom': '15px', 'color': '#2c3e50'}),
        html.Ul([
            html.Li("Lower comfort violations = better comfort maintenance across all buildings"),
            html.Li("Lower total energy = more efficient operation at district level"),
            html.Li(
                "The ideal configuration is in the bottom-left corner of the Energy-Comfort plot (low violations, low energy)"),
            html.Li("In the radar chart, configurations closer to the outer edge perform better across all dimensions"),
            html.Li("Bubble size represents the magnitude of the third variable for additional context"),
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
        guide
    ])


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("AAC-MADRL Interactive Dashboard")
    print("=" * 80)
    print(f"\nData directory: {DATA_DIR}")
    print(f"Available countries: {', '.join(available_countries)}")
    print("\nStarting server...")
    print("=" * 80)

    app.run(debug=True, port=8050)