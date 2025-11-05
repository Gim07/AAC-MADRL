import pandas as pd
from pathlib import Path
from typing import Dict, Tuple
import numpy as np


def calculate_composite_kpi(csv_file: Path, weights: Dict[str, float] = None) -> float:
    """
    Calculate a composite KPI that balances comfort violations, costs, and emissions.

    Args:
        csv_file: Path to the CSV file containing KPIs
        weights: Dictionary of weights for each component. Default weights if None:
                {
                    'comfort_violations': 0.4,  # Prioritize comfort
                    'cost': 0.3,               # Balance costs
                    'emissions': 0.3           # Balance emissions
                }

    Returns:
        Composite KPI score (lower is better)
    """
    if weights is None:
        weights = {
            'comfort_violations': 0.4,
            'cost': 0.3,
            'emissions': 0.3
        }

    try:
        # Read the CSV file
        df = pd.read_csv(csv_file, header=None, names=['kpi_name', 'value'])

        # Extract relevant KPIs
        kpi_dict = {}
        for _, row in df.iterrows():
            kpi_name = str(row['kpi_name']).strip()
            value_str = str(row['value']).strip()

            if value_str and value_str != '' and value_str != 'nan':
                try:
                    kpi_dict[kpi_name] = float(value_str)
                except (ValueError, TypeError):
                    continue

        # Calculate comfort score (violations count + severity)
        comfort_score = 0
        if 'Avg Comfort Violation Above (°C)' in kpi_dict:
            comfort_score += kpi_dict['Avg Comfort Violation Above (°C)'] * 50  # Weight severity
        if 'Avg Comfort Violation Below (°C)' in kpi_dict:
            comfort_score += kpi_dict['Avg Comfort Violation Below (°C)'] * 50  # Weight severity

        # Calculate total cost
        total_cost = 0
        if 'Electricity Cost' in kpi_dict:
            total_cost += kpi_dict['Electricity Cost']
        if 'Fuel Cost' in kpi_dict:
            total_cost += kpi_dict['Fuel Cost']

        # Calculate total emissions
        total_emissions = 0
        if 'Electricity Emissions' in kpi_dict:
            total_emissions += kpi_dict['Electricity Emissions']
        if 'Fuel Emissions' in kpi_dict:
            total_emissions += kpi_dict['Fuel Emissions']

        # Normalize and combine with weights
        # Note: These are raw values, normalization will happen across all simulations
        composite = (
            weights['comfort_violations'] * comfort_score +
            weights['cost'] * total_cost +
            weights['emissions'] * total_emissions
        )

        return composite

    except Exception as e:
        return float('inf')  # Return infinity if we can't calculate


def find_best_kpis_with_composite(root_directory: str,
                                   composite_weights: Dict[str, float] = None) -> Tuple[Dict[str, Tuple[str, float]], Dict[str, float]]:
    """
    Extended version that also calculates composite KPI for each simulation.

    Args:
        root_directory: The root directory to search for CSV files
        composite_weights: Weights for the composite KPI calculation

    Returns:
        Tuple of (best_individual_kpis, composite_kpis_dict)
    """
    kpi_data = {}  # {kpi_name: [(simulation_name, value), ...]}
    composite_kpis = {}  # {simulation_name: composite_score}

    # For normalization of composite KPI
    all_comfort_scores = []
    all_costs = []
    all_emissions = []
    raw_data = {}  # {simulation_name: {'comfort': x, 'cost': y, 'emissions': z}}

    # Search for all CSV files recursively
    root_path = Path(root_directory)
    csv_files = list(root_path.rglob("*.csv"))

    print(f"Found {len(csv_files)} CSV files")

    # First pass: collect all data
    for csv_file in csv_files:
        try:
            # Read the CSV file
            df = pd.read_csv(csv_file, header=None, names=['kpi_name', 'value'])

            # Get simulation name from file path (relative to root)
            simulation_name = str(csv_file.relative_to(root_path))

            # Extract KPIs for composite calculation
            kpi_dict = {}
            for _, row in df.iterrows():
                kpi_name = str(row['kpi_name']).strip()
                value_str = str(row['value']).strip()

                if not value_str or value_str == '' or value_str == 'nan':
                    continue

                try:
                    value = float(value_str)

                    if np.isnan(value):
                        continue

                    kpi_dict[kpi_name] = value

                    # Add to tracking dictionary for individual KPIs
                    if kpi_name not in kpi_data:
                        kpi_data[kpi_name] = []
                    kpi_data[kpi_name].append((simulation_name, value))

                except (ValueError, TypeError):
                    continue

            # Calculate components for composite KPI
            comfort_score = 0
            comfort_score += kpi_dict.get('Avg Comfort Violation Above (°C)', 0) * 50
            comfort_score += kpi_dict.get('Avg Comfort Violation Below (°C)', 0) * 50

            total_cost = kpi_dict.get('Electricity Cost', 0) + kpi_dict.get('Fuel Cost', 0)
            total_emissions = kpi_dict.get('Electricity Emissions', 0) + kpi_dict.get('Fuel Emissions', 0)

            raw_data[simulation_name] = {
                'comfort': comfort_score,
                'cost': total_cost,
                'emissions': total_emissions
            }

            all_comfort_scores.append(comfort_score)
            all_costs.append(total_cost)
            all_emissions.append(total_emissions)

        except Exception as e:
            print(f"Warning: Could not process {csv_file}: {e}")
            continue

    # Normalize and calculate composite KPIs
    if composite_weights is None:
        composite_weights = {
            'comfort_violations': 0.4,
            'cost': 0.3,
            'emissions': 0.3
        }

    # Min-max normalization
    min_comfort = min(all_comfort_scores) if all_comfort_scores else 0
    max_comfort = max(all_comfort_scores) if all_comfort_scores else 1
    min_cost = min(all_costs) if all_costs else 0
    max_cost = max(all_costs) if all_costs else 1
    min_emissions = min(all_emissions) if all_emissions else 0
    max_emissions = max(all_emissions) if all_emissions else 1

    for sim_name, data in raw_data.items():
        # Normalize each component to [0, 1]
        norm_comfort = (data['comfort'] - min_comfort) / (max_comfort - min_comfort) if max_comfort > min_comfort else 0
        norm_cost = (data['cost'] - min_cost) / (max_cost - min_cost) if max_cost > min_cost else 0
        norm_emissions = (data['emissions'] - min_emissions) / (max_emissions - min_emissions) if max_emissions > min_emissions else 0

        # Calculate weighted composite score
        composite_score = (
            composite_weights['comfort_violations'] * norm_comfort +
            composite_weights['cost'] * norm_cost +
            composite_weights['emissions'] * norm_emissions
        )

        composite_kpis[sim_name] = composite_score

    # Find the best (minimum) value for each individual KPI
    best_kpis = {}
    for kpi_name, simulations in kpi_data.items():
        if simulations:
            best_sim, best_value = min(simulations, key=lambda x: x[1])
            best_kpis[kpi_name] = (best_sim, best_value)

    return best_kpis, composite_kpis


def find_best_kpis(root_directory: str) -> Dict[str, Tuple[str, float]]:
    """
    Searches all CSV files in a parent root directory and returns the simulation name
    with the best (minimum) value for each KPI.

    Args:
        root_directory: The root directory to search for CSV files

    Returns:
        A dictionary where:
        - Keys are KPI names
        - Values are tuples of (simulation_name, best_value)
    """
    kpi_data = {}  # {kpi_name: [(simulation_name, value), ...]}

    # Search for all CSV files recursively
    root_path = Path(root_directory)
    csv_files = list(root_path.rglob("*.csv"))

    print(f"Found {len(csv_files)} CSV files")

    for csv_file in csv_files:
        try:
            # Read the CSV file
            df = pd.read_csv(csv_file, header=None, names=['kpi_name', 'value'])

            # Get simulation name from file path (relative to root)
            simulation_name = str(csv_file.relative_to(root_path))

            # Process each KPI in the file
            for _, row in df.iterrows():
                kpi_name = str(row['kpi_name']).strip()
                value_str = str(row['value']).strip()

                # Skip if value is empty or not a number
                if not value_str or value_str == '' or value_str == 'nan':
                    continue

                try:
                    value = float(value_str)

                    # Skip if value is NaN
                    if np.isnan(value):
                        continue

                    # Add to our tracking dictionary
                    if kpi_name not in kpi_data:
                        kpi_data[kpi_name] = []

                    kpi_data[kpi_name].append((simulation_name, value))

                except (ValueError, TypeError):
                    # Skip values that can't be converted to float
                    continue

        except Exception as e:
            # Skip files that can't be read properly
            print(f"Warning: Could not process {csv_file}: {e}")
            continue

    # Find the best (minimum) value for each KPI
    best_kpis = {}
    for kpi_name, simulations in kpi_data.items():
        if simulations:
            # Find the simulation with minimum value
            best_sim, best_value = min(simulations, key=lambda x: x[1])
            best_kpis[kpi_name] = (best_sim, best_value)

    return best_kpis


def print_composite_kpis(composite_kpis: Dict[str, float], weights: Dict[str, float]):
    """
    Print the composite KPI rankings.

    Args:
        composite_kpis: Dictionary of simulation_name -> composite_score
        weights: Weights used for the composite calculation
    """
    print("\n" + "="*80)
    print("COMPOSITE KPI RANKING (Comfort + Cost + Emissions)")
    print("="*80)
    print(f"\nWeights used:")
    print(f"  - Comfort Violations: {weights['comfort_violations']:.1%}")
    print(f"  - Cost: {weights['cost']:.1%}")
    print(f"  - Emissions: {weights['emissions']:.1%}")
    print(f"\nLower score is better (normalized to 0-1 scale)\n")

    # Sort by composite score (ascending - lower is better)
    sorted_composite = sorted(composite_kpis.items(), key=lambda x: x[1])

    print(f"{'Rank':<6} {'Score':<12} {'Simulation Name'}")
    print("-" * 80)

    for rank, (simulation_name, score) in enumerate(sorted_composite, start=1):
        print(f"{rank:<6} {score:<12.6f} {simulation_name}")

    print("\n" + "="*80)
    print(f"🏆 BEST OVERALL CONTROLLER (Composite KPI): {sorted_composite[0][0]}")
    print(f"   Composite Score: {sorted_composite[0][1]:.6f}")
    print(f"   This controller achieves the best balance between comfort, cost, and emissions")
    print("="*80 + "\n")


def print_best_kpis(best_kpis: Dict[str, Tuple[str, float]], composite_kpis: Dict[str, float] = None):
    """
    Print the best KPIs in a readable format.

    Args:
        best_kpis: Dictionary of KPI name -> (simulation_name, value)
        composite_kpis: Optional dictionary of composite KPI scores
    """
    print("\n" + "="*80)
    print("BEST INDIVIDUAL KPI VALUES AND THEIR SIMULATIONS")
    print("="*80 + "\n")

    for kpi_name, (simulation_name, value) in sorted(best_kpis.items()):
        print(f"KPI: {kpi_name}")
        print(f"  Best Value: {value}")
        print(f"  Simulation: {simulation_name}")
        print()

    # Summary: Count how many times each simulation achieved the best KPI
    print("\n" + "="*80)
    print("SUMMARY - BEST ALGORITHM BY INDIVIDUAL KPIs")
    print("="*80 + "\n")

    simulation_counts = {}
    for kpi_name, (simulation_name, value) in best_kpis.items():
        if simulation_name not in simulation_counts:
            simulation_counts[simulation_name] = 0
        simulation_counts[simulation_name] += 1

    # Sort by count (descending)
    sorted_simulations = sorted(simulation_counts.items(), key=lambda x: x[1], reverse=True)

    print(f"{'Rank':<6} {'Best KPIs Count':<18} {'Simulation Name'}")
    print("-" * 80)

    for rank, (simulation_name, count) in enumerate(sorted_simulations, start=1):
        percentage = (count / len(best_kpis)) * 100
        print(f"{rank:<6} {count:<18} ({percentage:5.1f}%)  {simulation_name}")

    print("\n" + "="*80)
    print(f"🥇 BEST BY INDIVIDUAL KPIs: {sorted_simulations[0][0]}")
    print(f"   Won {sorted_simulations[0][1]} out of {len(best_kpis)} KPIs ({(sorted_simulations[0][1]/len(best_kpis)*100):.1f}%)")
    print("="*80 + "\n")


def save_results_to_csv(best_kpis: Dict[str, Tuple[str, float]],
                        output_file: str,
                        composite_kpis: Dict[str, float] = None,
                        composite_output_file: str = None):
    """
    Save the best KPIs results to CSV files.

    Args:
        best_kpis: Dictionary of KPI name -> (simulation_name, value)
        output_file: Path to the output CSV file for individual KPIs
        composite_kpis: Optional dictionary of simulation_name -> composite_score
        composite_output_file: Optional path to the output CSV file for composite KPIs
    """
    # Save individual KPIs
    data = []
    for kpi_name, (simulation_name, value) in best_kpis.items():
        data.append({
            'KPI_Name': kpi_name,
            'Best_Value': value,
            'Simulation_Name': simulation_name
        })

    df = pd.DataFrame(data)
    df.to_csv(output_file, index=False)
    print(f"\nIndividual KPI results saved to: {output_file}")

    # Save composite KPIs if provided
    if composite_kpis and composite_output_file:
        composite_data = []
        for simulation_name, score in sorted(composite_kpis.items(), key=lambda x: x[1]):
            composite_data.append({
                'Rank': len(composite_data) + 1,
                'Simulation_Name': simulation_name,
                'Composite_Score': score
            })

        df_composite = pd.DataFrame(composite_data)
        df_composite.to_csv(composite_output_file, index=False)
        print(f"Composite KPI rankings saved to: {composite_output_file}")


if __name__ == "__main__":
    # Set the root directory to search
    root_dir = "./outputs/data/CA_20_dynamics/schema.json/kpi/test"

    # Customize weights for the composite KPI
    # You can adjust these based on your priorities
    custom_weights = {
        'comfort_violations': 0.7,  # 40% weight on comfort
        'cost': 0.0,                # 30% weight on cost
        'emissions': 0.3            # 30% weight on emissions
    }

    # Alternative weights examples:
    # Prioritize comfort more:
    # custom_weights = {'comfort_violations': 0.5, 'cost': 0.25, 'emissions': 0.25}
    #
    # Prioritize cost:
    # custom_weights = {'comfort_violations': 0.3, 'cost': 0.5, 'emissions': 0.2}

    print(f"Searching for CSV files in: {root_dir}\n")

    # Find best KPIs with composite calculation
    best_kpis, composite_kpis = find_best_kpis_with_composite(root_dir, custom_weights)

    # Print results for individual KPIs
    print_best_kpis(best_kpis, composite_kpis)

    # Print composite KPI rankings
    print_composite_kpis(composite_kpis, custom_weights)

    # Save to CSV
    save_results_to_csv(best_kpis, "best_kpi_results.csv",
                        composite_kpis, "composite_kpi_rankings.csv")

    print(f"\n{'='*80}")
    print(f"ANALYSIS SUMMARY")
    print(f"{'='*80}")
    print(f"Total KPIs analyzed: {len(best_kpis)}")
    print(f"Total simulations analyzed: {len(set(sim for sim, val in best_kpis.values()))}")
    print(f"Composite KPI uses normalized scores (0-1) with custom weights")
    print(f"{'='*80}\n")
