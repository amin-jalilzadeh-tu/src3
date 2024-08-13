# config_manager.py
import random
import pandas as pd

class ConfigurationManager:
    def __init__(self, data, user_config, default_niveau="niveau 1"):
        self.data = data
        self.user_selections = user_config.get("user_selections", {})
        self.user_modifications = user_config.get("user_modifications", {})
        self.default_niveau = default_niveau

    def get_niveau(self, function, building_type, age_range):
        # Retrieves the selected niveau for a given function, building type, and age range
        return self.user_selections.get(function, {}).get(building_type, {}).get(age_range, self.default_niveau)

    def get_parameter_values(self, function, building_type, age_range, niveau=None, object_group=None, object_type=None, object_name=None):
        # Retrieves the parameter values for a specific object
        niveau = niveau if niveau else self.default_niveau
        try:
            param_values = self.data["Building Functions"][function]["Building Types"][building_type][age_range]["niveaux"][niveau][object_group][object_type][object_name]

            # Apply user modifications if available
            if object_name in self.user_modifications:
                user_params = self.user_modifications[object_name]
                for param_name, user_value in user_params.items():
                    if user_value.get("autosize_allowed", False):
                        param_values[param_name] = "Autosize"
                    else:
                        param_values[param_name] = user_value

            return param_values

        except KeyError:
            raise ValueError(f"Configuration for {function} -> {building_type} -> {age_range} -> {niveau} -> {object_group} -> {object_type} -> {object_name} not found.")

    def get_random_value(self, min_val, max_val):
        # Generates a random value between min_val and max_val
        return random.uniform(min_val, max_val)

    def get_ground_temperatures(self):
        # Adjust ground temperatures based on user modifications
        ground_temps = self.data["Ground Temperatures"].copy()
        future_increase = self.user_modifications.get("future_increase", ground_temps.get("future_increase", 0.0))

        for month in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]:
            base_value = ground_temps[month]["base_value"]

            # Initialize user_month_config with an empty dictionary or some other default value
            user_month_config = self.user_modifications.get(month, {})

            # Apply user modifications to the base value if present
            base_value = user_month_config.get("base_value", base_value)

            # Calculate the adjusted value and ensure it is within the min and max bounds
            adjusted_value = base_value + future_increase
            min_value = user_month_config.get("min_value", ground_temps[month]["min_value"])
            max_value = user_month_config.get("max_value", ground_temps[month]["max_value"])
            adjusted_value = max(min(adjusted_value, max_value), min_value)

            ground_temps[month] = adjusted_value

        return ground_temps


def preprocess_building_data(buildings_df, config_manager):
    """
    Preprocesses the building data and applies the configurations based on user selections and modifications.
    
    This is where the configuration logic is applied to each building based on the provided DataFrame.
    """
    merged_data = []

    for _, building_row in buildings_df.iterrows():
        function = building_row["function"]
        building_type = building_row["building_type"]
        age_range = building_row["age_range"]

        # Determine the appropriate niveau
        niveau = config_manager.get_niveau(function, building_type, age_range)
        building_data = building_row.to_dict()

        # Apply configurations to the building data
        for object_group in ["envelop parameters"]:
            for object_type in ["material", "material:nomass", "windowmaterial:simpleglazingsystem"]:
                if object_type in config_manager.data["Building Functions"][function]["Building Types"][building_type][age_range]["niveaux"][niveau][object_group]:
                    for object_name in config_manager.data["Building Functions"][function]["Building Types"][building_type][age_range]["niveaux"][niveau][object_group][object_type].keys():
                        param_values = config_manager.get_parameter_values(function, building_type, age_range, niveau, object_group=object_group, object_type=object_type, object_name=object_name)
                        building_data[object_name] = param_values

        merged_data.append(building_data)

    merged_df = pd.DataFrame(merged_data)
    return merged_df


def map_roughness_value(numeric_value):
    """Map numeric roughness values to valid EnergyPlus roughness strings."""
    if numeric_value <= 0.2:
        return "VerySmooth"
    elif numeric_value <= 0.4:
        return "Smooth"
    elif numeric_value <= 0.6:
        return "MediumSmooth"
    elif numeric_value <= 0.8:
        return "MediumRough"
    elif numeric_value <= 1.0:
        return "Rough"
    else:
        return "VeryRough"


def extract_value(param, config_manager):
    """
    Extracts a specific value from the configuration parameters, potentially applying user-specified modifications.
    """
    if isinstance(param, dict):
        min_val = param.get("min_value")
        max_val = param.get("max_value")
        if min_val is not None and max_val is not None:
            if "autosize_allowed" in param and param["autosize_allowed"]:
                return "Autosize"
            return config_manager.get_random_value(min_val, max_val)
        else:
            raise KeyError(f"Missing 'min_value' or 'max_value' in parameter configuration: {param}")
    return param











# "filter_criteria": {
#    "postcode6": "1234AB"
#    // OR
#    // "ids": ["NL.IMBAG.Pand.0363100012240688", "NL.IMBAG.Pand.1955100000022664", "NL.IMBAG.Pand.0363100012237464"]
  