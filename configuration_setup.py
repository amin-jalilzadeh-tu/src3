# configuration_setup.py
import json

def initialize_data_structure():
    return {
        "Building Functions": {
            "Residential": {
                "Building Types": {}
            },
            "Industrial": {
                "Building Types": {}
            },
            "Commercial": {
                "Building Types": {}
            }
        }
    }

def add_building_type(data_structure, function, building_type, age_range, niveau, object_group, object_type, object_name, parameters):
    # Navigate to the appropriate function
    function_dict = data_structure["Building Functions"].setdefault(function, {"Building Types": {}})
    
    # Navigate to the building type
    building_type_dict = function_dict["Building Types"].setdefault(building_type, {})
    
    # Navigate to the age range
    age_range_dict = building_type_dict.setdefault(age_range, {"niveaux": {}})
    
    # Navigate to the niveau
    niveau_dict = age_range_dict["niveaux"].setdefault(niveau, {})
    
    # Navigate to the object group
    object_group_dict = niveau_dict.setdefault(object_group, {})
    
    # Navigate to the object type
    object_type_dict = object_group_dict.setdefault(object_type, {})
    
    # Finally, add the object name and parameters
    object_type_dict[object_name] = parameters


def setup_hvac_configurations(data_structure):
    # Define the HVAC configurations by niveau for each combination
    hvac_by_niveau = {
        "niveau 0": {
            "Residential": {
                "Terraced housing": ["V1", "H2", "DHV1"],
                "Apartment": ["V1", "H1", "DHV1"],
                "Semi Detached": ["V1", "H2", "DHV1"],
                "Detached": ["V1", "H3", "DHV1"]
            },
            "Industrial": {
                "Other": ["V2", "H2", "DHV2", "C1"]
            },
            "Commercial": {
                "Other": ["V2", "H2", "DHV2", "C1"]
            }
        },
        "niveau 1": {
            "Residential": {
                "Terraced housing": ["V2", "H1", "DHV2", "C2"],
                "Apartment": ["V2", "H2", "DHV2", "C1"],
                "Semi Detached": ["V2", "H1", "DHV2", "C2"],
                "Detached": ["V2", "H2", "DHV2", "C1"]
            },
            "Industrial": {
                "Other": ["V2", "H3", "DHV2", "C2"]
            },
            "Commercial": {
                "Other": ["V2", "H3", "DHV2", "C2"]
            }
        },
        "niveau 2": {
            "Residential": {
                "Terraced housing": ["V3", "H1", "DHV2", "C2"],
                "Apartment": ["V3", "H3", "DHV2", "C2"],
                "Semi Detached": ["V3", "H1", "DHV2", "C2"],
                "Detached": ["V3", "H2", "DHV2", "C2"]
            },
            "Industrial": {
                "Other": ["V3", "H3", "DHV2", "C2"]
            },
            "Commercial": {
                "Other": ["V3", "H3", "DHV2", "C2"]
            }
        }
    }

    # Define all functions, building types, and age ranges
    functions = ["Residential", "Industrial", "Commercial"]
    residential_building_types = ["Apartment", "Terraced housing", "Semi Detached", "Detached"]
    other_building_types = ["Other"]
    age_ranges = ["< 1945", "1965 - 1974", "1975 - 1991", "1992 - 2005", "2006 - 2014", "2015 - 2018"]

    # Add HVAC configurations for each combination
    for niveau, hvac_config in hvac_by_niveau.items():
        for function in functions:
            building_types = residential_building_types if function == "Residential" else other_building_types
            for building_type in building_types:
                for age_range in age_ranges:
                    hvac_functions = hvac_config.get(function, {}).get(building_type, [])
                    if hvac_functions:
                        for hvac_function in hvac_functions:
                            add_building_type(
                                data_structure,
                                function,
                                building_type,
                                age_range,
                                niveau,
                                "HVAC Systems",  # Treat HVAC as an object group
                                "HVAC Function",  # Treat each function as an object type
                                hvac_function,  # Function name as object name
                                None  # Parameters can be None or any specific configurations
                            )

    return data_structure













def setup_configurations():
    data_structure = initialize_data_structure()

    # Define parameters for different niveau levels
    parameters_by_niveau = {
        "niveau 0": {
            "groundfloor": {
                "roughness": {"min_value": 0.5, "max_value": 1.5, "autosize_allowed": False, "min_value_allowed": 0.4, "max_value_allowed": 1.6},
                "thickness": {"min_value": 0.15, "max_value": 0.25, "autosize_allowed": False, "min_value_allowed": 0.1, "max_value_allowed": 0.3},
                "thermal conductivity": {"min_value": 1.2, "max_value": 2.0, "autosize_allowed": False, "min_value_allowed": 1.0, "max_value_allowed": 2.5},
                "density": {"min_value": 2200, "max_value": 2500, "autosize_allowed": False, "min_value_allowed": 2000, "max_value_allowed": 2600},
                "specific heat": {"min_value": 800, "max_value": 1200, "autosize_allowed": False, "min_value_allowed": 700, "max_value_allowed": 1300}
            },
            "ext_walls": {
                "surface roughness": {"min_value": 0.3, "max_value": 1.0, "autosize_allowed": False, "min_value_allowed": 0.2, "max_value_allowed": 1.2},
                "thickness": {"min_value": 0.2, "max_value": 0.35, "autosize_allowed": False, "min_value_allowed": 0.15, "max_value_allowed": 0.4},
                "thermal conductivity": {"min_value": 1.1, "max_value": 2.2, "autosize_allowed": False, "min_value_allowed": 1.0, "max_value_allowed": 2.5},
                "density": {"min_value": 2100, "max_value": 2400, "autosize_allowed": False, "min_value_allowed": 2000, "max_value_allowed": 2500},
                "specific heat": {"min_value": 800, "max_value": 1200, "autosize_allowed": False, "min_value_allowed": 700, "max_value_allowed": 1300}
            },
            "roof": {
                "thermal resistance": {"min_value": 0.5, "max_value": 2.0, "autosize_allowed": False, "min_value_allowed": 0.3, "max_value_allowed": 2.5}
            },
            "windows": {
                "u_factor": {"min_value": 2.5, "max_value": 3.5, "autosize_allowed": False, "min_value_allowed": 2.0, "max_value_allowed": 4.0}
            },
            "int_walls": {
                "thermal resistance": {"min_value": 0.2, "max_value": 1.0, "autosize_allowed": False, "min_value_allowed": 0.15, "max_value_allowed": 1.2}
            },
            "int_floors": {
                "thermal resistance": {"min_value": 0.2, "max_value": 1.0, "autosize_allowed": False, "min_value_allowed": 0.15, "max_value_allowed": 1.2}
            }
        },
        "niveau 1": {
            "groundfloor": {
                "roughness": {"min_value": 0.6, "max_value": 1.4, "autosize_allowed": False, "min_value_allowed": 0.5, "max_value_allowed": 1.7},
                "thickness": {"min_value": 0.18, "max_value": 0.28, "autosize_allowed": False, "min_value_allowed": 0.12, "max_value_allowed": 0.32},
                "thermal conductivity": {"min_value": 1.1, "max_value": 2.1, "autosize_allowed": False, "min_value_allowed": 1.0, "max_value_allowed": 2.6},
                "density": {"min_value": 2100, "max_value": 2400, "autosize_allowed": False, "min_value_allowed": 1900, "max_value_allowed": 2500},
                "specific heat": {"min_value": 800, "max_value": 1200, "autosize_allowed": False, "min_value_allowed": 700, "max_value_allowed": 1300}
            },
            "ext_walls": {
                "surface roughness": {"min_value": 0.4, "max_value": 1.2, "autosize_allowed": False, "min_value_allowed": 0.3, "max_value_allowed": 1.3},
                "thickness": {"min_value": 0.25, "max_value": 0.4, "autosize_allowed": False, "min_value_allowed": 0.2, "max_value_allowed": 0.45},
                "thermal conductivity": {"min_value": 1.3, "max_value": 2.5, "autosize_allowed": False, "min_value_allowed": 1.2, "max_value_allowed": 2.7},
                "density": {"min_value": 2200, "max_value": 2500, "autosize_allowed": False, "min_value_allowed": 2000, "max_value_allowed": 2600},
                "specific heat": {"min_value": 800, "max_value": 1200, "autosize_allowed": False, "min_value_allowed": 700, "max_value_allowed": 1300}
            },
            "roof": {
                "thermal resistance": {"min_value": 0.7, "max_value": 2.5, "autosize_allowed": False, "min_value_allowed": 0.4, "max_value_allowed": 2.8}
            },
            "windows": {
                "u_factor": {"min_value": 2.0, "max_value": 3.0, "autosize_allowed": False, "min_value_allowed": 1.5, "max_value_allowed": 3.5}
            },
            "int_walls": {
                "thermal resistance": {"min_value": 0.3, "max_value": 1.2, "autosize_allowed": False, "min_value_allowed": 0.2, "max_value_allowed": 1.3}
            },
            "int_floors": {
                "thermal resistance": {"min_value": 0.3, "max_value": 1.2, "autosize_allowed": False, "min_value_allowed": 0.2, "max_value_allowed": 1.3}
            }
        },
        "niveau 2": {
            "groundfloor": {
                "roughness": {"min_value": 0.7, "max_value": 1.3, "autosize_allowed": False, "min_value_allowed": 0.6, "max_value_allowed": 1.8},
                "thickness": {"min_value": 0.2, "max_value": 0.3, "autosize_allowed": False, "min_value_allowed": 0.15, "max_value_allowed": 0.35},
                "thermal conductivity": {"min_value": 1.0, "max_value": 2.0, "autosize_allowed": False, "min_value_allowed": 0.9, "max_value_allowed": 2.3},
                "density": {"min_value": 2000, "max_value": 2300, "autosize_allowed": False, "min_value_allowed": 1900, "max_value_allowed": 2400},
                "specific heat": {"min_value": 850, "max_value": 1100, "autosize_allowed": False, "min_value_allowed": 750, "max_value_allowed": 1250}
            },
            "ext_walls": {
                "surface roughness": {"min_value": 0.5, "max_value": 1.1, "autosize_allowed": False, "min_value_allowed": 0.4, "max_value_allowed": 1.4},
                "thickness": {"min_value": 0.3, "max_value": 0.5, "autosize_allowed": False, "min_value_allowed": 0.25, "max_value_allowed": 0.55},
                "thermal conductivity": {"min_value": 1.2, "max_value": 2.4, "autosize_allowed": False, "min_value_allowed": 1.1, "max_value_allowed": 2.6},
                "density": {"min_value": 2150, "max_value": 2450, "autosize_allowed": False, "min_value_allowed": 2050, "max_value_allowed": 2550},
                "specific heat": {"min_value": 820, "max_value": 1180, "autosize_allowed": False, "min_value_allowed": 720, "max_value_allowed": 1280}
            },
            "roof": {
                "thermal resistance": {"min_value": 0.8, "max_value": 2.8, "autosize_allowed": False, "min_value_allowed": 0.5, "max_value_allowed": 3.0}
            },
            "windows": {
                "u_factor": {"min_value": 1.8, "max_value": 2.8, "autosize_allowed": False, "min_value_allowed": 1.4, "max_value_allowed": 3.2}
            },
            "int_walls": {
                "thermal resistance": {"min_value": 0.4, "max_value": 1.5, "autosize_allowed": False, "min_value_allowed": 0.3, "max_value_allowed": 1.6}
            },
            "int_floors": {
                "thermal resistance": {"min_value": 0.4, "max_value": 1.5, "autosize_allowed": False, "min_value_allowed": 0.3, "max_value_allowed": 1.6}
            }
        }
    }

    # Define all functions, building types, age ranges, and object groups
    functions = ["Residential", "Industrial", "Commercial"]
    residential_building_types = ["Apartment", "Terraced housing", "Semi Detached", "Detached"]
    other_building_types = ["Other"]
    age_ranges = ["< 1945", "1945 - 1964", "1965 - 1974", "1975 - 1991", "1992 - 2005", "2006 - 2014", "2015 - 2018"]
    object_names = ["groundfloor", "ext_walls", "roof", "windows", "int_walls", "int_floors"]

    for function in functions:
        building_types = residential_building_types if function == "Residential" else other_building_types
        for building_type in building_types:
            for age_range in age_ranges:
                for niveau, parameters in parameters_by_niveau.items():
                    for object_name in object_names:
                        object_group = "envelop parameters"
                        object_type = "material" if object_name in ["groundfloor", "ext_walls"] else "material:nomass" if object_name in ["roof", "int_walls", "int_floors"] else "windowmaterial:simpleglazingsystem"
                        add_building_type(data_structure, function, building_type, age_range, niveau, object_group, object_type, object_name, parameters[object_name])

    # Ground Temperatures
    parameters_ground_temperatures = {
        "January": {"base_value": 2.61, "min_value": 2.0, "max_value": 3.0},
        "February": {"base_value": 4.82, "min_value": 4.0, "max_value": 5.0},
        "March": {"base_value": 5.91, "min_value": 5.0, "max_value": 6.5},
        "April": {"base_value": 9.32, "min_value": 8.0, "max_value": 10.0},
        "May": {"base_value": 14.73, "min_value": 13.0, "max_value": 16.0},
        "June": {"base_value": 16.12, "min_value": 15.0, "max_value": 17.5},
        "July": {"base_value": 18.05, "min_value": 17.0, "max_value": 19.0},
        "August": {"base_value": 18.48, "min_value": 17.5, "max_value": 19.5},
        "September": {"base_value": 15.63, "min_value": 14.5, "max_value": 16.5},
        "October": {"base_value": 10.40, "min_value": 9.0, "max_value": 11.0},
        "November": {"base_value": 7.99, "min_value": 7.0, "max_value": 9.0},
        "December": {"base_value": 4.00, "min_value": 3.0, "max_value": 5.0},
        "future_increase": 0.0  # Default is no increase, can be adjusted in user configuration
    }

    # Add Ground Temperatures to data structure
    data_structure["Ground Temperatures"] = parameters_ground_temperatures


    # Add HVAC configurations
    data_structure = setup_hvac_configurations(data_structure)



    return data_structure

# Running the configuration setup and displaying the result
#config = setup_configurations()

# Print the resulting data structure as a formatted JSON
#print(json.dumps(config, indent=4))