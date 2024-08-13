import os
import pandas as pd
import json
import re
from datetime import datetime

import os
import pandas as pd
import json
import re
from datetime import datetime
from decimal import Decimal

def process_output_files(output_dir, buildings_df):
    # Today's date in YYYY-MM-DD format
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"Processing output directory: {output_dir}")

    # Create a dictionary to hold all the data
    all_data = {'timeIntervals': [], 'buildings': []}

    # Define a regex to extract the building ID from filenames
    building_id_pattern = re.compile(r"modified_building_(\d+)\.csv")

    # Iterate through all files in the directory
    for filename in os.listdir(output_dir):
        if filename.startswith('modified_building') and filename.endswith('.csv'):
            print(f"Processing file: {filename}")
            building_id_match = building_id_pattern.search(filename)
            if not building_id_match:
                continue
            building_id = building_id_match.group(1)

            # Read the CSV file
            file_path = os.path.join(output_dir, filename)
            df = pd.read_csv(file_path)

            # Check if the necessary columns exist
            if 'Electricity:Facility [J](TimeStep)' not in df.columns:
                print(f"Skipping file {filename}: Missing Electricity data")
                continue

            # Handle natural gas consumption by summing relevant columns
            df['NaturalGas:Facility [J](TimeStep)'] = df.get('SHWSYS1_WATER_HEATER:Water Heater Heating Energy [J](TimeStep)', 0) + \
                                                      df.get('CENTRAL BOILER:Boiler Heating Energy [J](TimeStep)', 0)

            # Calculate total energy consumption
            df['TotalEnergy [J](TimeStep)'] = df['Electricity:Facility [J](TimeStep)'] + df['NaturalGas:Facility [J](TimeStep)']

            # Rename columns for clarity
            df.rename(columns={
                'Date/Time': 'Time',
                'NaturalGas:Facility [J](TimeStep)': 'Natural Gas Consumption (J)',
                'Electricity:Facility [J](TimeStep)': 'Electricity Consumption (J)',
                'TotalEnergy [J](TimeStep)': 'Total Energy (J)'
            }, inplace=True)

            # If time intervals are empty, fill them
            if not all_data['timeIntervals']:
                all_data['timeIntervals'] = df['Time'].tolist()

            # Get the additional building data from buildings_df
            building_info = buildings_df[buildings_df['nummeraanduiding_id'] == building_id].to_dict('records')[0]

            # Convert any Decimal values to float
            for key, value in building_info.items():
                if isinstance(value, Decimal):
                    building_info[key] = float(value)

            # Append the data
            all_data['buildings'].append({
                'buildingId': building_id,
                'Natural Gas Consumption (J)': df['Natural Gas Consumption (J)'].tolist(),
                'Electricity Consumption (J)': df['Electricity Consumption (J)'].tolist(),
                'Total Energy (J)': df['Total Energy (J)'].tolist(),
                'building_info': building_info
            })

    # Write all the data to a single JSON file
    output_file = os.path.join(output_dir, f"energy_data_{today}.json")
    print(f"Writing to file: {output_file}")
    with open(output_file, 'w') as f:
        json.dump(all_data, f, indent=4)

    return output_file




    # Save the data to JSON files with the pc6 and date in the filename
  #  with open(os.path.join(output_dir, f'{pc6}_natural_gas_{today}.json'), 'w') as f:
  #      json.dump(natural_gas_data, f, indent=4)
  #  with open(os.path.join(output_dir, f'{pc6}_electricity_{today}.json'), 'w') as f:
  #      json.dump(electricity_data, f, indent=4)
  #  with open(os.path.join(output_dir, f'{pc6}_total_energy_{today}.json'), 'w') as f:
  #      json.dump(total_energy_data, f, indent=4)


#output_dir="D:\Try21"
#pc6 = "2628zl"
#process_output_files(output_dir)