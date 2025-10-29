from pathlib import Path
import pandas as pd
import numpy as np
from typing import List, Optional, Tuple

# ---------- path helpers ----------

ALGO_DIR = {
    # "AAC-MADRL": "aac_madrl",
    "SAC": "sac",
    # "P_RBC": "P_rbc",
    # "PI_RBC": "PI_rbc",
    "PID_RBC": "PID_rbc",
    # "GB_PID_RBC": "GB_PID_rbc",
}

def find_obs_csv(outputs_root: Path, dataset_key: str, algorithm: str, beta: float, lr: float, gamma: float) -> Path:
    """
    Trova district_obs.csv nel layout nuovo (beta=..._gamma=.../lr=...) con fallback al layout vecchio (beta=.../lr=...).
    Struttura base: <outputs_root>/<dataset_key>/schema.json/obs/<algo_dir>/...
    """
    algo = algorithm.upper()
    algo_dir = ALGO_DIR.get(algo, algo.lower())
    base = outputs_root / dataset_key / "schema.json" / "obs" / algo_dir

    if "RBC" in algo:
        candidates = [base / "district_obs.csv"]
    else:
        candidates = [
            base / f"beta={beta}_gamma={gamma}" / f"lr={lr}" / "district_obs.csv",  # nuovo
            base / f"beta={beta}"              / f"lr={lr}" / "district_obs.csv",   # vecchio (senza gamma)
        ]

    for p in candidates:
        if p.exists():
            return p

    raise FileNotFoundError(
        f"district_obs.csv non trovato per {algorithm}. Cercati: {', '.join(map(str, candidates))}"
    )

def ensure_parent(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)

def load_or_init_kpi_csv(kpi_path: Path) -> pd.DataFrame:
    """Apre il KPI CSV se esiste, altrimenti crea un dataframe vuoto con indice 'cost_function'."""
    if kpi_path.exists():
        try:
            return pd.read_csv(kpi_path, index_col="cost_function")
        except Exception:
            return pd.read_csv(kpi_path, index_col=0)

    idx = [
        "Import",
        "Variance",
        "Daily Peak Average",
        "Avg Num Comfort Violations",
        "Avg Comfort Violation Above (°C)",
        "Avg Comfort Violation Below (°C)",
        "Avg Num Comfort Violations Above",
        "Avg Num Comfort Violations Below",
        # --- NEW FUEL KPIs ---
        "Fuel Import",  # Total Fuel Consumption
        "Fuel Variance",  # Fuel Consumption Variance
        "Fuel Cost",  # Total Fuel Cost (optional, if data exists)
        "Fuel Emissions",  # Total Fuel Emissions (optional, if data exists)
    ]
    df = pd.DataFrame(index=pd.Index(idx, name="cost_function"))
    df["District"] = np.nan
    return df

# ---------- comfort helpers ----------

def _pick_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Finds the first existing column name from a list of candidates (case-insensitive check included)."""
    # Case-sensitive check first
    for c in candidates:
        if c in df.columns:
            return c
    # Case-insensitive check if not found
    df_cols_lower = {col.lower(): col for col in df.columns}
    for c in candidates:
        if c.lower() in df_cols_lower:
            return df_cols_lower[c.lower()]
    return None

def _mean_violation_for_building_csv(csv_path: Path) -> Optional[Tuple[float, float, float, float, float]]:
    """
    Media violazioni per un edificio.
    Ritorna: (num_violazioni_tot, mean_above, mean_below, num_viol_above, num_viol_below)
    """
    try:
        df = pd.read_csv(csv_path)
        if df.empty: return None
    except Exception as e:
        print(f"Error reading building obs file {csv_path}: {e}")
        return None

    # Find columns using _pick_col for flexibility
    col_t_in = _pick_col(df, ["indoor_temperature", "indoor_dry_bulb_temperature", "T_in"])
    col_h_sp = _pick_col(df, ["heating_sp", "indoor_dry_bulb_temperature_heating_set_point", "Heating Setpoint"])
    col_c_sp = _pick_col(df, ["cooling_sp", "indoor_dry_bulb_temperature_cooling_set_point", "Cooling Setpoint"])
    col_band = _pick_col(df, ["comfort_band", "Comfort Band"])

    required_cols = [col_t_in, col_h_sp, col_c_sp, col_band]

    if None in required_cols:
        # print(f"Missing required comfort columns in {csv_path}")
        return None  # Silently skip if columns missing

    # come richiesto: heating_sp == cooling_sp
    if not df["heating_sp"].equals(df["cooling_sp"]):
        raise AssertionError("Set point di riscaldamento e raffreddamento devono essere uguali")

    SP = pd.to_numeric(df["heating_sp"],        errors="coerce")
    T  = pd.to_numeric(df["indoor_temperature"], errors="coerce")
    B  = pd.to_numeric(df["comfort_band"],       errors="coerce").abs()

    low, high = SP - B, SP + B

    above = (T - high).clip(lower=0)
    below = (low - T).clip(lower=0)

    mean_above = float(above[above > 0].mean()) if (above > 0).any() else 0.0
    mean_below = float(below[below > 0].mean()) if (below > 0).any() else 0.0

    num_above = int((above > 0).sum())
    num_below = int((below > 0).sum())
    num_total = num_above + num_below

    return num_total, mean_above, mean_below, num_above, num_below

def mean_comfort_violation_for_folder(obs_folder: Path) -> Tuple[float, float, float, float, float]:
    """
    Scans obs_building_*.csv in a folder and returns the average comfort metrics across buildings.
    Returns averages of: (num_total_violations, mean_above_delta, mean_below_delta, num_above_violations, num_below_violations)
    """
    num_violations, vas, vbs, nvas, nvbs = [], [], [], [], []
    found_files = 0

    for f in sorted(obs_folder.glob("obs_building_*.csv")):
        found_files += 1
        res = _mean_violation_for_building_csv(f)
        if res is None:
            # print(f"Skipping comfort calculation for {f.name} (missing data or error).")
            continue # Skip file if data is missing or error occurs

        num_v, va, vb, nva, nvb = res
        num_violations.append(num_v)
        vas.append(va)
        vbs.append(vb)
        nvas.append(nva)
        nvbs.append(nvb)

    if found_files == 0:
        print(f"Warning: No 'obs_building_*.csv' files found in {obs_folder}")
        return 0.0, 0.0, 0.0, 0.0, 0.0

    # Calculate average only over buildings where calculation was successful
    def _safe_mean(lst: List[float]) -> float:
        return float(np.mean(lst)) if len(lst) > 0 else 0.0

    print(f"Calculated comfort KPIs over {len(num_violations)} buildings in {obs_folder.name}")
    return (
        _safe_mean(num_violations),
        _safe_mean(vas),
        _safe_mean(vbs),
        _safe_mean(nvas),
        _safe_mean(nvbs),
    )

# ---------- KPI core ----------

def process_kpi(outputs_root: Path, dataset_key: str, algorithm: str, kpi_dir: Path, lr: float, beta: float, gamma: float) -> Tuple[pd.DataFrame, pd.DataFrame, Path]:
    """Reads district_obs.csv and updates/saves the algorithm's KPI file (CSV)."""
    try:
        obs_csv = find_obs_csv(outputs_root, dataset_key, algorithm, beta, lr, gamma)
        df_obs = pd.read_csv(obs_csv)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        # Return empty/default dataframes if obs file not found
        kpi_file = kpi_dir / f"{algorithm.lower()}_lr={lr}.csv" if "RBC" not in algorithm.upper() else kpi_dir / f"{algorithm.lower()}.csv"
        df_kpi = load_or_init_kpi_csv(kpi_file) # Will create an empty structure
        return pd.DataFrame(), df_kpi, kpi_file
    except Exception as e:
        print(f"[ERROR] Failed to read {obs_csv}: {e}")
        kpi_file = kpi_dir / f"{algorithm.lower()}_lr={lr}.csv" if "RBC" not in algorithm.upper() else kpi_dir / f"{algorithm.lower()}.csv"
        df_kpi = load_or_init_kpi_csv(kpi_file)
        return pd.DataFrame(), df_kpi, kpi_file

    # KPI file path (CSV)
    algo = algorithm.upper()
    if algo == "RBC":
        kpi_file = kpi_dir / f"{algo.lower()}.csv"
    else:
        kpi_file = kpi_dir / f"{algo.lower()}_lr={lr}.csv"

    ensure_parent(kpi_file)
    df_kpi = load_or_init_kpi_csv(kpi_file)

    FUEL_COLS = {
        "cons": ["net_fuel_consumption", "fuel_consumption", "Net Fuel Consumption"],
        "cost": ["net_fuel_consumption_cost", "fuel_cost", "Net Fuel Cost", "total_fuel_cost"],
        "emis": ["net_fuel_consumption_emission", "fuel_emission", "Net Fuel Emission", "total_fuel_emissions"],
    }

    # --- Find relevant columns ---
    col_net_elec = _pick_col(df_obs, ["net electricity consumption", "net_electricity_consumption"])
    col_pos_elec = _pick_col(df_obs, ["positive net electricity consumption", "positive_net_electricity_consumption"])
    col_fuel_cons = _pick_col(df_obs, FUEL_COLS["cons"])
    col_fuel_cost = _pick_col(df_obs, FUEL_COLS["cost"])
    col_fuel_emis = _pick_col(df_obs, FUEL_COLS["emis"])

    # --- Basic Electricity KPIs ---
    if col_pos_elec:
        total_consumption = float(np.sum(pd.to_numeric(df_obs[col_pos_elec], errors='coerce').fillna(0).clip(lower=0)))
        df_kpi.loc["Import", "District"] = total_consumption
    else:
        print(f"Warning: Positive electricity consumption column not found for {algorithm}.")
        df_kpi.loc["Import", "District"] = np.nan

    if col_net_elec:
        variance = float(np.var(pd.to_numeric(df_obs[col_net_elec], errors='coerce').fillna(0)))
        df_kpi.loc["Variance", "District"] = variance
    else:
        print(f"Warning: Net electricity consumption column not found for {algorithm}.")
        df_kpi.loc["Variance", "District"] = np.nan

    # --- NEW: Fuel KPIs ---
    if col_fuel_cons:
        # Assuming fuel consumption is always >= 0, clipping might be redundant but safe
        total_fuel_consumption = float(
            np.sum(pd.to_numeric(df_obs[col_fuel_cons], errors='coerce').fillna(0).clip(lower=0)))
        fuel_variance = float(np.var(pd.to_numeric(df_obs[col_fuel_cons], errors='coerce').fillna(0)))
        df_kpi.loc["Fuel Import", "District"] = total_fuel_consumption
        df_kpi.loc["Fuel Variance", "District"] = fuel_variance
        print(f"Fuel consumption found and processed for {algorithm}.")
    else:
        print(f"Warning: Fuel consumption column not found for {algorithm}. KPIs set to NaN.")
        df_kpi.loc["Fuel Import", "District"] = np.nan
        df_kpi.loc["Fuel Variance", "District"] = np.nan

    if col_fuel_cost:
        total_fuel_cost = float(np.sum(pd.to_numeric(df_obs[col_fuel_cost], errors='coerce').fillna(0).clip(lower=0)))
        df_kpi.loc["Fuel Cost", "District"] = total_fuel_cost
    else:
        # Don't warn if cost is missing, just leave as NaN (as it might not be provided)
        # print(f"Warning: Fuel cost column not found for {algorithm}.")
        if "Fuel Cost" in df_kpi.index:  # Only set NaN if row exists
            df_kpi.loc["Fuel Cost", "District"] = np.nan

    if col_fuel_emis:
        total_fuel_emission = float(np.sum(pd.to_numeric(df_obs[col_fuel_emis], errors='coerce').fillna(0).clip(lower=0)))
        df_kpi.loc["Fuel Emissions", "District"] = total_fuel_emission
    else:
        # Don't warn if emissions are missing
        # print(f"Warning: Fuel emissions column not found for {algorithm}.")
        if "Fuel Emissions" in df_kpi.index:  # Only set NaN if row exists
            df_kpi.loc["Fuel Emissions", "District"] = np.nan

    # --- Comfort KPIs: averages over all buildings in the folder ---
    obs_folder = obs_csv.parent
    try:
        num_violations, va, vb, nva, nvb = mean_comfort_violation_for_folder(obs_folder)
        df_kpi.loc["Avg Num Comfort Violations", "District"] = float(num_violations)
        df_kpi.loc["Avg Comfort Violation Above (°C)", "District"] = float(va)
        df_kpi.loc["Avg Comfort Violation Below (°C)", "District"] = float(vb)
        df_kpi.loc["Avg Num Comfort Violations Above", "District"] = float(nva)
        df_kpi.loc["Avg Num Comfort Violations Below", "District"] = float(nvb)
    except Exception as e:
        print(f"Error calculating comfort KPIs for {algorithm}: {e}")
        # Set comfort KPIs to NaN on error
        comfort_kpis = ["Avg Num Comfort Violations", "Avg Comfort Violation Above (°C)",
                        "Avg Comfort Violation Below (°C)", "Avg Num Comfort Violations Above",
                        "Avg Num Comfort Violations Below"]
        for kpi_name in comfort_kpis:
            if kpi_name in df_kpi.index:
                df_kpi.loc[kpi_name, "District"] = np.nan

    # Save updated KPI to CSV
    try:
        df_kpi.to_csv(kpi_file, index=True, index_label="cost_function")
    except Exception as e:
        print(f"[ERROR] Failed to save updated KPI file {kpi_file}: {e}")

    return df_obs, df_kpi, kpi_file

# ---------- driver ----------

if __name__ == "__main__":
    # Config
    building_counts = [20]
    learning_rate = 0.0003
    control_algorithms = [
        # "P_RBC",
        "PI_RBC",
        # "PID_RBC",
        "SAC",
        # "GB_PID_RBC"
        ]
    beta = 0.2
    gamma = 3.5
    dataset = "CA"  # per comporre dataset_key
    season = "winter"
    start_date = "2023-01-01 00:00:00"

    outputs_root = Path.cwd() / "outputs" / "data"

    for n in building_counts:
        # es. "TX_10_dynamics"
        dataset_key = f"{dataset}_{n}_dynamics"

        # KPI dir (coerente con layout nuovo, dentro schema.json)
        kpi_dir = outputs_root / dataset_key / "schema.json" / "kpi" / "test" / f"beta={beta}_gamma={gamma}" / f"lr={learning_rate}"
        kpi_dir.mkdir(parents=True, exist_ok=True)

        # Dictionaries to store results for all algorithms
        df_obs_dict = {}
        df_kpi_dict = {}
        kpi_file_dict = {}

        # Process each algorithm and store results
        for algo in control_algorithms:
            print(f"Processing {algo}...")
            df_obs, df_kpi, kpi_file = process_kpi(outputs_root, dataset_key, algo, kpi_dir, learning_rate, beta, gamma)
            df_obs_dict[algo] = df_obs
            df_kpi_dict[algo] = df_kpi
            kpi_file_dict[algo] = kpi_file

        # Align index to datetime for all algorithms
        num_hours = len(df_obs_dict[control_algorithms[0]])
        date_range = pd.date_range(start=start_date, periods=num_hours, freq="h")

        for algo in control_algorithms:
            df_obs_dict[algo].index = date_range

        # Calculate daily aggregates for all algorithms
        daily_dfs = {}
        try:
            for algo in control_algorithms:
                daily_dfs[algo] = df_obs_dict[algo].resample("D").agg({
                    "net electricity consumption": ["max", "mean"],
                    "positive net electricity consumption": ["max", "mean"]
                })
        except Exception as e:
            print(f"Error during daily aggregation: {e}")
            daily_dfs = {algo: pd.DataFrame() for algo in control_algorithms}  # Fallback to empty

        # Update KPI files with Daily Peak Average for each algorithm
        for algo in control_algorithms:
            daily_df = daily_dfs[algo]
            df_kpi = df_kpi_dict[algo]

            # Calculate average daily peak
            average_daily_peak = float(daily_df["net electricity consumption"]["max"].mean())
            df_kpi.loc["Daily Peak Average", "District"] = average_daily_peak

            # Save updated KPI file
            kpi_path = kpi_file_dict[algo]
            df_kpi.to_csv(kpi_path, index=True, index_label="cost_function")
            print(f"Updated KPI file for {algo}: {kpi_path}")

        print(f"Completed processing for {dataset_key}")

