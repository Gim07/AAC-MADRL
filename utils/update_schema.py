import json
import os
from pathlib import Path

from git.util import join_path


def extract_building_id(filename):
    """Extract building ID from filename (e.g., 'resstock-amy2018-2021-release-1-9634.csv')"""
    return filename.replace('.csv', '').replace('.pth', '')


def get_building_files(folder_path):
    """Get all CSV and PTH files from the folder, grouped by building ID"""
    buildings = {}

    for file in os.listdir(folder_path):
        if file.endswith('.csv') and file.startswith('resstock-'):
            building_id = extract_building_id(file)
            if building_id not in buildings:
                buildings[building_id] = {'csv': None, 'pth': None}
            buildings[building_id]['csv'] = file
        elif file.endswith('.pth') and file.startswith('resstock-'):
            building_id = extract_building_id(file)
            if building_id not in buildings:
                buildings[building_id] = {'csv': None, 'pth': None}
            buildings[building_id]['pth'] = file

    # Filter out buildings that don't have both CSV and PTH files
    complete_buildings = {k: v for k, v in buildings.items() if v['csv'] and v['pth']}

    return complete_buildings


def create_building_config(building_id, csv_file, pth_file, roof_area=126.71988278139312):
    """Create a building configuration dictionary"""
    config = {
        "type": "citylearn.building.LSTMDynamicsBuilding",
        "include": True,
        "energy_simulation": csv_file,
        "weather": "weather.csv",
        "carbon_intensity": "carbon_intensity.csv",
        "pricing": "pricing_2023.csv",
        "inactive_observations": [
            "dhw_storage_soc",
            "dhw_storage_electricity_consumption"
        ],
        "inactive_actions": [
            "dhw_storage"
        ],
        "cooling_device": {
            "type": "citylearn.energy_model.HeatPump",
            "autosize": True
        },
        "heating_device": {
            "type": "citylearn.energy_model.GasBoiler",
            "autosize": True
        },
        "dhw_device": {
            "type": "citylearn.energy_model.ElectricHeater",
            "autosize": True
        },
        "cooling_storage": None,
        "heating_storage": {
            "type": "citylearn.energy_model.StorageTank",
            "autosize": True
        },
        "dhw_storage": None,
        "electrical_storage": {
            "type": "citylearn.energy_model.Battery",
            "autosize": True
        },
        "pv": {
            "type": "citylearn.energy_model.PV",
            "autosize": True,
            "autosize_attributes": {
                "epw_filepath": "weather.epw",
                "roof_area": roof_area
            }
        },
        "dynamics": {
            "type": "citylearn.dynamics.LSTMDynamics",
            "attributes": {
                "input_size": None,
                "hidden_size": 8,
                "num_layers": 2,
                "lookback": 13,
                "filename": pth_file,
                "input_normalization_minimum": [
                    -1.0, -1.0, -1.0, -1.0, -1.0, -1.0,
                    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 9.0
                ],
                "input_normalization_maximum": [
                    1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
                    15.0, 15.0, 1007.5, 465.5, 28.9, 4.0, 35.0
                ],
                "input_observation_names": [
                    "month_sin", "month_cos", "day_type_sin", "day_type_cos",
                    "hour_sin", "hour_cos", "cooling_demand", "heating_demand",
                    "direct_solar_irradiance", "diffuse_solar_irradiance",
                    "outdoor_dry_bulb_temperature", "occupant_count",
                    "indoor_dry_bulb_temperature"
                ]
            }
        }
    }

    return config


def update_schema(schema_path, buildings_folder, output_path=None):
    """
    Update the schema file with buildings from the folder

    Args:
        schema_path: Path to the existing schema JSON file
        buildings_folder: Path to folder containing building CSV and PTH files
        output_path: Path for output file (if None, overwrites schema_path)
    """
    # Load existing schema
    with open(schema_path, 'r') as f:
        schema = json.load(f)

    # Get building files from folder
    building_files = get_building_files(buildings_folder)

    print(f"Found {len(building_files)} complete buildings (with both CSV and PTH files)")

    # Create new buildings dictionary
    new_buildings = {}
    for building_id, files in building_files.items():
        print(f"Processing: {building_id}")
        new_buildings[building_id] = create_building_config(
            building_id,
            files['csv'],
            files['pth']
        )

    # Update schema
    schema['buildings'] = new_buildings

    # Write output
    output_file = output_path if output_path else schema_path
    with open(output_file, 'w') as f:
        json.dump(schema, f, indent=2)

    print(f"\nSchema updated successfully!")
    print(f"Output written to: {output_file}")
    print(f"Total buildings: {len(new_buildings)}")


# Example usage
if __name__ == "__main__":
    # Update these paths according to your setup
    BUILDINGS_FOLDER = "data/CA_20_dynamics"
    SCHEMA_FILE = join_path(BUILDINGS_FOLDER,  "schema.json")
    OUTPUT_FILE = join_path(BUILDINGS_FOLDER,  "schema_updated.json")  # Set to None to overwrite original

    update_schema(SCHEMA_FILE, BUILDINGS_FOLDER, OUTPUT_FILE)