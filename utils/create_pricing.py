import pandas as pd

rho_fuel = 0.671  # kg/Sm3
LHV_fuel = 13.889  # kWh/kg

def _open_data_txt(file: str,
                   name: str,
                   origin_time: str = '2023-01-01 00:00:00',
                   sim_timestep: int = 1):
    data = pd.read_csv(file, sep='\s+', header=None, names=['time', name], skiprows=2)

    # Create datetime columns
    data['datetime'] = pd.to_datetime(data['time'], unit='s', origin=origin_time)

    # rescale data
    if name == 'ng_price':
        data[name] = data[name] / (rho_fuel * LHV_fuel)  # from price per Sm3 to price per kWh
        # Crea il nuovo DataFrame con shift
        new_df = pd.DataFrame({
            'fuel_pricing': data['ng_price'],
            'fuel_pricing_predicted_1': data['ng_price'].shift(-1),
            'fuel_pricing_predicted_2': data['ng_price'].shift(-2),
            'fuel_pricing_predicted_3': data['ng_price'].shift(-3)
        })

    elif name == 'el_price':
        # Crea il nuovo DataFrame con shift
        new_df = pd.DataFrame({
            'electricity_pricing': data['el_price'],
            'electricity_pricing_predicted_1': data['el_price'].shift(-1),
            'electricity_pricing_predicted_2': data['el_price'].shift(-2),
            'electricity_pricing_predicted_3': data['el_price'].shift(-3)
        })
    else:
        new_df = pd.DataFrame({})
        raise ValueError("Nome non riconosciuto. Usa 'ng_price' o 'el_price'.")

    # Riempi i NaN con l'ultimo valore disponibile (backward fill per gli shift negativi)
    new_df = new_df.fillna(method='bfill')

    return new_df


price_ng_file = "C:/Users/GiacomoBuscemi/OneDrive - Politecnico di Torino/PycharmProjects/CCHP/data/price/ng_price_2023.txt"
price_el_file= "C:/Users/GiacomoBuscemi/OneDrive - Politecnico di Torino/PycharmProjects/CCHP/data/price/price_el_2023.txt"

# Open the txt files
ng_data = _open_data_txt(price_ng_file, 'ng_price')
el_data = _open_data_txt(price_el_file, 'el_price')

# cbind this two dataframes
pricing_data = pd.concat([ng_data, el_data], axis=1)

# Save to csv
pricing_data.to_csv("data/pricing_2023.csv", index=False)