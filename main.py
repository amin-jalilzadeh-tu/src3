from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import json
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import necessary modules
from config import get_idf_config, get_conn_params, get_db_config
from config_manager import ConfigurationManager, preprocess_building_data
from configuration_setup import setup_configurations
from idf_operations import (
    update_construction_materials, 
    add_ground_temperatures, 
    add_water_heating, 
    add_v2_fan_natural_ventilation, 
    remove_building_object, 
    create_building_block, 
    update_idf_for_fenestration,
    assign_constructions_to_surfaces, 
    add_internal_mass_to_all_zones_with_first_construction, 
    add_lights_to_all_zones, 
    generate_detailed_electric_equipment, 
    add_year_long_run_period, 
    add_outdoor_air_and_zone_sizing_to_all_zones, 
    add_door_to_wall, 
    add_hvac_schedules, 
    add_H2_RadiantConvective_heating, 
    setup_combined_hvac_equipment_V2_H2_2, 
    check_and_add_idfobject,
    add_people_and_activity_schedules
)
from runner_generator import simulate_all
from json_processor import process_output_files
from geomeppy import IDF
from database_handler_2 import create_engine_and_load_data

# Flask app setup
app = Flask(__name__)
CORS(app)

# Function to process each building and update IDF files
def process_building(row, base_idf_path, idd_path, output_dir, config_manager):
    # Set the IDD file for Eppy
    IDF.setiddname(idd_path)

    # Load the base IDF file
    idf = IDF(base_idf_path)
    
    building_id = row['nummeraanduiding_id']
    print(f"Processing building ID {building_id}...")

    # Apply modifications using the refactored functions
    remove_building_object(idf)
    create_building_block(idf, row)
    update_construction_materials(idf, row, config_manager)
    update_idf_for_fenestration(idf, row)
    assign_constructions_to_surfaces(idf)
    add_ground_temperatures(idf, config_manager)
    add_internal_mass_to_all_zones_with_first_construction(idf, row)
    add_people_and_activity_schedules(idf, row)
    add_lights_to_all_zones(idf, row)
    generate_detailed_electric_equipment(idf, row)
    add_year_long_run_period(idf)
    add_outdoor_air_and_zone_sizing_to_all_zones(idf)
    add_door_to_wall(idf)
    add_hvac_schedules(idf, row)
    add_water_heating(idf)
    add_v2_fan_natural_ventilation(idf)
    add_H2_RadiantConvective_heating(idf)
    setup_combined_hvac_equipment_V2_H2_2(idf)
    check_and_add_idfobject(idf)

    # Save the modified IDF file with a unique name
    modified_idf_filename = f"modified_building_{building_id}.idf"
    modified_idf_path = os.path.join(output_dir, modified_idf_filename)
    idf.save(modified_idf_path)
    
    print(f"Saved modified IDF for building {building_id} at {modified_idf_path}")
    return modified_idf_path

# Function to update IDF files and save them
def update_idf_and_save(buildings_df, output_dir, base_idf_path, idd_path, config_manager):
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Process each building in the DataFrame
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(process_building, row, base_idf_path, idd_path, output_dir, config_manager) for _, row in buildings_df.iterrows()]
        for future in as_completed(futures):
            try:
                future.result()  # This will re-raise any exceptions that occurred in process_building
            except Exception as e:
                print(f"Error processing building: {e}")

# API endpoint to run the analysis
@app.route('/run_analysis', methods=['GET', 'POST'])
def run_analysis():
    try:
        # Get the user configuration JSON file from the request
        user_config_file = request.files.get('user_config')
        if user_config_file:
            user_config = json.load(user_config_file)
            print("User config loaded:", user_config)  # Debug print
        else:
            return jsonify({"error": "User configuration file not provided"}), 400
        

        # Setup configurations
        print("Setting up configurations...")
        data_structure = setup_configurations()
        print("Configurations set up.")
        config_manager = ConfigurationManager(data_structure, user_config)
        print("Configuration manager created.")
        # Filter criteria for database query
        filter_criteria = user_config.get("filter_criteria", {})
        print("Filter criteria:", filter_criteria)
        # Load building data from the database using the connection parameters from config.py

        # Get database connection parameters
        print("Getting database connection parameters...")
        db_config = get_db_config()  # This line is correct and ensures that the connection parameters are loaded.
        print("Database connection parameters loaded.")

        # Load building data using the create_engine_and_load_data function
        # You don't need to pass individual db parameters anymore; the function handles connection internally
        buildings_df = create_engine_and_load_data(filter_criteria=filter_criteria)
        print(f"Building data loaded with {len(buildings_df)} records.")

        # Preprocess the building data
        merged_df = preprocess_building_data(buildings_df, config_manager)
        print(f"Merged data prepared with {len(merged_df)} records.")
        
        # Get IDF configuration paths
        idf_config = get_idf_config()
        output_dir = idf_config['output_dir']
        idf_file_path = idf_config['idf_file_path']
        iddfile = idf_config['iddfile']

        # Update the IDF files and save them
        update_idf_and_save(
            buildings_df=merged_df, 
            output_dir=output_dir, 
            base_idf_path=idf_file_path, 
            idd_path=iddfile, 
            config_manager=config_manager
        )
        print("Updated IDF and saved.")

        # Simulate all
        simulate_all()
        print("Simulation completed.")

        # Process the output files and include the building data
        json_file_path = process_output_files(output_dir, buildings_df)
        print(f"Processed output files and created JSON: {json_file_path}")

        # Send the JSON file as the response
        return send_file(json_file_path, as_attachment=True)

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": str(e)}), 500

# Run the Flask application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

# Sample curl command:
# curl -X POST -F "user_config=@path_to_your_json_file.json" http://127.0.0.1:5000/run_analysis
 