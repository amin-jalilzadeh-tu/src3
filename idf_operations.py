from config_manager import extract_value, map_roughness_value  # Import extract_value function
from geomeppy import IDF




# Define a function to remove existing building objects from the IDF
def remove_building_object(idf):
    """Remove all 'Building' objects in the given IDF to prevent conflicts."""
    building_objects = idf.idfobjects['BUILDING']
    for building in building_objects:
        idf.removeidfobject(building)

# Execute the function to clean up the IDF file
################################################################                remove_building_object(idf)

# Save changes to the IDF file
################################################################                idf.save()

# Define a function to create a new building block in the IDF
def create_building_block(idf, building_row):
    """Create a building block in the IDF based on DataFrame row information."""
    perimeter = building_row['perimeter']
    area = building_row['area']
    
    # Calculate building dimensions
    width = max(area / (perimeter / 4), area**0.5)  # Ensure width is reasonable
    length = area / width
    facade_height = building_row.get('height', 10)
    floor_height = building_row.get('floor height', 3)
    num_stories = int(facade_height / floor_height)
    
    # Prepare building orientation
    orientation = building_row.get('orientation', 0)
    coordinates = [(0, 0), (width, 0), (width, length), (0, length)]
    if orientation != 0:
        from math import radians, cos, sin
        orientation_rad = radians(orientation)
        rotated_coordinates = [
            (cos(orientation_rad) * x - sin(orientation_rad) * y,
             sin(orientation_rad) * x + cos(orientation_rad) * y)
            for x, y in coordinates
        ]
        coordinates = rotated_coordinates

    # Add the building block to the IDF
        # Add the building block to the IDF
    idf.newidfobject("BUILDING", 
                     Name="New Building Block", 
                     North_Axis=orientation,
                     Terrain="Suburbs",                      # Assuming suburban terrain
                     Loads_Convergence_Tolerance_Value=0.04,  # Default values for convergence
                     Temperature_Convergence_Tolerance_Value=0.4,
                     Solar_Distribution="FullExterior",      # Default solar distribution
                     Maximum_Number_of_Warmup_Days=150,       # Set maximum warmup days to 50
                     Minimum_Number_of_Warmup_Days=1)        # Set minimum warmup days to 1

    # Add the building block to the IDF with the given parameters
    idf.add_block(name='BuildingBlock1', 
                  coordinates=coordinates, 
                  height=facade_height, 
                  num_stories=num_stories)

def update_construction_materials(idf, building_row, config_manager):
    """Update construction materials in the IDF based on the building's parameters."""

    # Step 1: Reset existing materials and constructions
    for obj_type in ['MATERIAL', 'MATERIAL:NOMASS', 'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM', 'CONSTRUCTION']:
        objs = idf.idfobjects[obj_type]
        for obj in objs:
            idf.removeidfobject(obj)

    function = building_row["function"]
    building_type = building_row["building_type"]
    age_range = building_row["age_range"]
    niveau = config_manager.get_niveau(function, building_type, age_range)

    # Process Groundfloor
    groundfloor_params = config_manager.get_parameter_values(function, building_type, age_range, niveau, object_group="envelop parameters", object_type="material", object_name="groundfloor")
    idf.newidfobject('MATERIAL', Name='Groundfloor', 
                     Roughness=map_roughness_value(extract_value(groundfloor_params.get("roughness", 0.7), config_manager)),
                     Thickness=extract_value(groundfloor_params.get("thickness", 0.15), config_manager),  
                     Conductivity=extract_value(groundfloor_params.get("thermal conductivity", 1.4), config_manager),  
                     Density=extract_value(groundfloor_params.get("density", 2300), config_manager),  
                     Specific_Heat=extract_value(groundfloor_params.get("specific heat", 1000), config_manager))

    # Process External Walls
    ext_walls_params = config_manager.get_parameter_values(function, building_type, age_range, niveau, object_group="envelop parameters", object_type="material", object_name="ext_walls")
    idf.newidfobject('MATERIAL', Name='Ext_Walls', 
                     Roughness=map_roughness_value(extract_value(ext_walls_params.get("surface roughness", 0.7), config_manager)),
                     Thickness=extract_value(ext_walls_params.get("thickness", 0.2), config_manager),  
                     Conductivity=extract_value(ext_walls_params.get("thermal conductivity", 1.4), config_manager),  
                     Density=extract_value(ext_walls_params.get("density", 2300), config_manager),  
                     Specific_Heat=extract_value(ext_walls_params.get("specific heat", 1000), config_manager))

    # Process Roof
    roof_params = config_manager.get_parameter_values(function, building_type, age_range, niveau, object_group="envelop parameters", object_type="material:nomass", object_name="roof")
    idf.newidfobject('MATERIAL:NOMASS', Name='Roof', 
                     Thermal_Resistance=extract_value(roof_params.get("thermal resistance", 0.2), config_manager),
                     Roughness='MediumRough')

    # Process Windows
    windows_params = config_manager.get_parameter_values(function, building_type, age_range, niveau, object_group="envelop parameters", object_type="windowmaterial:simpleglazingsystem", object_name="windows")
    idf.newidfobject("WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM", 
                     Name='Windowglass', 
                     UFactor=extract_value(windows_params.get("u_factor", 2.0), config_manager), 
                     Solar_Heat_Gain_Coefficient=0.7)

    # Process Internal Walls
    int_walls_params = config_manager.get_parameter_values(function, building_type, age_range, niveau, object_group="envelop parameters", object_type="material:nomass", object_name="int_walls")
    idf.newidfobject('MATERIAL:NOMASS', Name='Int_Walls', 
                     Thermal_Resistance=extract_value(int_walls_params.get("thermal resistance", 0.2), config_manager), 
                     Roughness='MediumRough')

    # Process Internal Floors/Ceilings
    int_floors_params = config_manager.get_parameter_values(function, building_type, age_range, niveau, object_group="envelop parameters", object_type="material:nomass", object_name="int_floors")
    idf.newidfobject('MATERIAL:NOMASS', Name='Int_Floors', 
                     Thermal_Resistance=extract_value(int_floors_params.get("thermal resistance", 0.2), config_manager), 
                     Roughness='MediumRough')


    # Step 3: Define new constructions
    # Ground floor construction
    idf.newidfobject('CONSTRUCTION', Name='GroundFloorC', Outside_Layer='Groundfloor')
    # External walls construction
    idf.newidfobject('CONSTRUCTION', Name='Ext_WallsC', Outside_Layer='Ext_Walls')
    # Roof construction
    idf.newidfobject('CONSTRUCTION', Name='RoofC', Outside_Layer='Roof')
    # Windows construction
    idf.newidfobject('CONSTRUCTION', Name='Window1C', Outside_Layer='Windowglass')
    # Internal Walls construction
    idf.newidfobject('CONSTRUCTION', Name='Int_WallsC', Outside_Layer='Int_Walls')
    # Internal Floors/Ceilings construction
    idf.newidfobject('CONSTRUCTION', Name='Int_FloorsC', Outside_Layer='Int_Floors')



# # Define Fenestration and Façade

def update_idf_for_fenestration(idf, building_row):
    # Step 1: Correct the geometry intersections for better accuracy in simulations.
    IDF.intersect_match(idf)
    
    # Step 2: Clear existing fenestration details to start fresh.
    fenestrations = idf.idfobjects['FENESTRATIONSURFACE:DETAILED']
    del fenestrations[:]
    
    # Step 3: Set the new window-to-wall ratio (WWR).

    wwr =  building_row.get('average_wwr', .2)

    IDF.set_wwr(idf, wwr=wwr, force=True, construction='Window1C')
    
    
# idf.intersect_match()




# # Assign Constructions to Surfaces

def assign_constructions_to_surfaces(idf):
    # Retrieve lists of all detailed building surfaces from the IDF file
    surfaces = idf.idfobjects['BUILDINGSURFACE:DETAILED']
    
    # Iterate over each surface to determine its type and assign the appropriate construction
    for surface in surfaces:
        surface_type = surface.Surface_Type.upper()

        # Determine if the surface is a wall, roof, floor, or ceiling and assign the construction
        if surface_type == 'WALL':
            # Check if the wall is an external wall
            if surface.Outside_Boundary_Condition.upper() == 'OUTDOORS':
                surface.Construction_Name = 'Ext_WallsC'
            else:  # It's an internal wall
                surface.Construction_Name = 'Int_WallsC'
                
        elif surface_type == 'ROOF':
            # Assign construction to roofs
            surface.Construction_Name = 'RoofC'
            
        elif surface_type == 'FLOOR':
            # Assign construction to floors
            # If the name convention includes "ground" for ground floors, adjust as needed
            if 'ground' in surface.Name.lower():
                surface.Construction_Name = 'GroundFloorC'
            else:
                surface.Construction_Name = 'Int_FloorsC'  # This is new
            
        elif surface_type == 'CEILING':
            # Assign construction to ceilings
            surface.Construction_Name = 'Int_FloorsC'  # Ceilings use the same construction as internal floors
    



def add_ground_temperatures(idf, config_manager):
    # Remove any existing ground temperature objects to avoid duplicates
    existing_ground_temps = idf.idfobjects["SITE:GROUNDTEMPERATURE:BUILDINGSURFACE"]
    for temp in existing_ground_temps:
        idf.removeidfobject(temp)


    ground_temps = config_manager.get_ground_temperatures()

    idf.newidfobject(
        "SITE:GROUNDTEMPERATURE:BUILDINGSURFACE",
        January_Ground_Temperature=ground_temps["January"],
        February_Ground_Temperature=ground_temps["February"],
        March_Ground_Temperature=ground_temps["March"],
        April_Ground_Temperature=ground_temps["April"],
        May_Ground_Temperature=ground_temps["May"],
        June_Ground_Temperature=ground_temps["June"],
        July_Ground_Temperature=ground_temps["July"],
        August_Ground_Temperature=ground_temps["August"],
        September_Ground_Temperature=ground_temps["September"],
        October_Ground_Temperature=ground_temps["October"],
        November_Ground_Temperature=ground_temps["November"],
        December_Ground_Temperature=ground_temps["December"],
    )




# Internal Mass
def add_internal_mass_to_all_zones_with_first_construction(idf, building_row):

   surface_area = building_row['area']   # check

   # InternalMass Construction
   idf.newidfobject('CONSTRUCTION', Name='FurnitureConstruction', Outside_Layer='FurnitureMaterial')


   # Internal Mass - Keeping as MATERIAL:NOMASS for simplicity
   idf.newidfobject('MATERIAL', Name='FurnitureMaterial', 
                    Roughness='MediumSmooth',
                    Thickness=0.15,  # Adjust thickness based on your design
                    Conductivity=1.4,  # Concrete, adjust accordingly
                    Density=1210,  # Concrete, adjust accordingly
                    Specific_Heat=1000,
                    Thermal_Absorptance=.9,
                    Solar_Absorptance =.78,
                    Visible_Absorptance =.78)  # Concrete, adjust accordingly
   



   # Create INTERNALMASS objects for each zone
   for zone in idf.idfobjects["ZONE"]:
       internal_mass_name = f"InternalMass_{zone.Name}"
       idf.newidfobject("INTERNALMASS",
                        Name=internal_mass_name,
                        Construction_Name="FurnitureConstruction",
                        Zone_or_ZoneList_Name=zone.Name,
                        Surface_Area=surface_area)
# Zone



def add_people_and_activity_schedules(idf, building_row):


    building_function = building_row.get('function', 'Residential')  # Default to "Woon- en Verblijfsfuncties"  # Checks

    idf.newidfobject(
        "SCHEDULETYPELIMITS",
        Name="Fraction",
        Lower_Limit_Value=0.0,
        Upper_Limit_Value=1.0,
        Numeric_Type="Continuous",
        Unit_Type="Dimensionless",
    )

    idf.newidfobject(
        "SCHEDULETYPELIMITS",
        Name="Any Number",
        Numeric_Type="Continuous",
    )


     # Residential and Accommodation Functions
    if building_function == "Residential":
        # People schedule for residential
        idf.newidfobject(
            "SCHEDULE:COMPACT",
            Name="PeopleSched",
            Schedule_Type_Limits_Name="Fraction",
            Field_1="Through: 12/31",
            Field_2="For: Weekdays",
            Field_3="Until: 6:00,0.4",  
            Field_4="Until: 6:30,0.45",
            Field_5="Until: 7:00,0.5",  
            Field_6="Until: 7:30,0.55",
            Field_7="Until: 8:00,0.6",  
            Field_8="Until: 17:00,0.3",  
            Field_9="Until: 17:30,0.35",
            Field_10="Until: 22:00,0.8",  
            Field_11="Until: 22:30,0.7",
            Field_12="Until: 24:00,0.5",  
            Field_13="For: Weekends",
            Field_14="Until: 8:00,0.6",  
            Field_15="Until: 22:00,0.9",  
            Field_16="Until: 24:00,0.6",
            # Assuming holidays have a similar pattern to weekends but with a distinct identifier
            Field_17="For: Holidays",
            Field_18="Until: 8:00,0.6",
            Field_19="Until: 22:00,0.9",
            Field_20="Until: 24:00,0.6",
            # For design days and custom days, assuming minimal occupancy
            Field_21="For: SummerDesignDay",
            Field_22="Until: 24:00,0.1",
            Field_23="For: WinterDesignDay",
            Field_24="Until: 24:00,0.1",
            Field_25="For: CustomDay1",
            Field_26="Until: 24:00,0.1",
            Field_27="For: CustomDay2",
            Field_28="Until: 24:00,0.1"
        )

        # Activity schedule for residential
        idf.newidfobject(
            "SCHEDULE:COMPACT",
            Name="OccupancySched",
            Schedule_Type_Limits_Name="Any Number",
            Field_1="Through: 12/31",
            Field_2="For: AllDays",
            Field_3="Until: 7:00,120",  
            Field_4="Until: 7:30,130",
            Field_5="Until: 12:00,200",  
            Field_6="Until: 12:30,190",
            Field_7="Until: 17:00,150",  
            Field_8="Until: 17:30,160",
            Field_9="Until: 22:00,220",  
            Field_10="Until: 22:30,180",
            Field_11="Until: 24:00,120")

    # Commercial and Institutional Functions
    elif building_function == "Commercial":
        # People schedule for commercial
        idf.newidfobject(
            "SCHEDULE:COMPACT",
            Name="PeopleSched",
            Schedule_Type_Limits_Name="Fraction",
            Field_1="Through: 12/31",
            Field_2="For: Weekdays",
            Field_3="Until: 7:00,0.05",
            Field_4="Until: 7:30,0.1",
            Field_5="Until: 8:00,0.2",
            Field_6="Until: 18:00,1.0",  # Full occupancy during working hours
            Field_7="Until: 18:30,0.75",
            Field_8="Until: 20:00,0.5",
            Field_9="Until: 20:30,0.25",
            Field_10="Until: 24:00,0.1",
            Field_11="For: Weekends",
            Field_12="Until: 24:00,0.05",  # Minimal occupancy
            # Assuming minimal occupancy on holidays similar to weekends
            Field_13="For: Holidays",
            Field_14="Until: 24:00,0.05",
            # For design days and custom days, assuming slightly higher occupancy than holidays to account for potential special activities
            Field_15="For: SummerDesignDay",
            Field_16="Until: 24:00,0.1",
            Field_17="For: WinterDesignDay",
            Field_18="Until: 24:00,0.1",
            Field_19="For: CustomDay1",
            Field_20="Until: 24:00,0.1",
            Field_21="For: CustomDay2",
            Field_22="Until: 24:00,0.1"
        )

        # Activity schedule for commercial
        idf.newidfobject(
            "SCHEDULE:COMPACT",
            Name="OccupancySched",
            Schedule_Type_Limits_Name="Any Number",
            Field_1="Through: 12/31",
            Field_2="For: Weekdays",
            Field_3="Until: 8:00,100",  # Early arrivals
            Field_4="Until: 8:30,150",
            Field_5="Until: 18:00,200",  # Core hours
            Field_6="Until: 18:30,175",
            Field_7="Until: 20:00,150",  # Late stays
            Field_8="Until: 20:30,125",
            Field_9="Until: 24:00,100",  # Minimal activities
            Field_10="For: Weekends",
            Field_11="Until: 24:00,100",  # Uniform low activity level
            # Assuming the same level of activity on Holidays, SummerDesignDay, WinterDesignDay, CustomDay1, and CustomDay2 as on weekends
            Field_12="For: Holidays",
            Field_13="Until: 24:00,100",
            Field_14="For: SummerDesignDay",
            Field_15="Until: 24:00,100",
            Field_16="For: WinterDesignDay",
            Field_17="Until: 24:00,100",
            Field_18="For: CustomDay1",
            Field_19="Until: 24:00,100",
            Field_20="For: CustomDay2",
            Field_21="Until: 24:00,100"
        )

    # Industrial and Special Functions
    elif building_function == "Industrial":
        # People schedule for industrial
        idf.newidfobject(
            "SCHEDULE:COMPACT",
            Name="PeopleSched",
            Schedule_Type_Limits_Name="Fraction",
            Field_1="Through: 12/31",
            Field_2="For: AllDays",
            Field_3="Until: 5:00,0.2",  # Early shift start
            Field_4="Until: 5:30,0.25",
            Field_5="Until: 6:00,0.3",
            Field_6="Until: 14:00,1.0",  # Main shift
            Field_7="Until: 14:30,0.95",
            Field_8="Until: 20:00,0.9",  # Second shift
            Field_9="Until: 20:30,0.85",
            Field_10="Until: 22:00,0.8",
            Field_11="Until: 22:30,0.5",
            Field_12="Until: 24:00,0.3",  # Wind down
            # Assuming holidays have reduced occupancy, reflecting minimal staffing for essential operations
            Field_13="For: Holidays",
            Field_14="Until: 24:00,0.1",
            # For design days, assuming standard operation as industrial processes often need to continue regardless of external conditions
            Field_15="For: SummerDesignDay",
            Field_16="Until: 24:00,1.0",
            Field_17="For: WinterDesignDay",
            Field_18="Until: 24:00,1.0",
            Field_19="For: CustomDay1",
            Field_20="Until: 24:00,1.0",
            Field_21="For: CustomDay2",
            Field_22="Until: 24:00,1.0"
        )

        # Activity schedule for industrial
        idf.newidfobject(
            "SCHEDULE:COMPACT",
            Name="OccupancySched",
            Schedule_Type_Limits_Name="Any Number",
            Field_1="Through: 12/31",
            Field_2="For: AllDays",
            Field_3="Until: 6:00,100",  # Preparation for the day's operations
            Field_4="Until: 6:30,150",
            Field_5="Until: 14:00,300",  # Peak industrial activity
            Field_6="Until: 14:30,275",
            Field_7="Until: 20:00,250",  # Continuing operations
            Field_8="Until: 20:30,225",
            Field_9="Until: 22:00,150",  # Decrease towards end of shift
            Field_10="Until: 22:30,125",
            Field_11="Until: 24:00,100",  # Nighttime low activity
            # Assuming the same activity levels on Holidays, SummerDesignDay, WinterDesignDay, CustomDay1, and CustomDay2 as operational needs dictate consistent production
            Field_12="For: Holidays",
            Field_13="Until: 24:00,100",
            Field_14="For: SummerDesignDay",
            Field_15="Until: 24:00,300",
            Field_16="For: WinterDesignDay",
            Field_17="Until: 24:00,300",
            Field_18="For: CustomDay1",
            Field_19="Until: 24:00,300",
            Field_20="For: CustomDay2",
            Field_21="Until: 24:00,300"
        )

    else:
        print("Unknown building function")





def add_lights_to_all_zones(idf, building_row):
    # Assumed or predefined values
    schedule_name = "OccupancySched"  # Example, assuming it applies to all zones uniformly
    adjustment_factor = 0.9  # Adjusted based on desired criteria
    
    # Base lighting levels (in W/m2 or as needed) by function, type, and age
    lighting_levels = {
        "Residential": {
            "<1945": 2.5,
            "1945 - 1964": 3.0,
            "1965 - 1974": 2.8,
            "1975 - 1991": 2.6,
            "1992 - 2005": 2.4,
            "2006 - 2014": 2.2,
            "2015 and later": 2.0
        },
        "Commercial": {
            "<1945": 4.0,
            "1945 - 1964": 3.8,
            "1965 - 1974": 3.6,
            "1975 - 1991": 3.4,
            "1992 - 2005": 3.2,
            "2006 - 2014": 3.0,
            "2015 and later": 2.8
        },
        "Industrial": {
            "<1945": 5.0,
            "1945 - 1964": 4.8,
            "1965 - 1974": 4.6,
            "1975 - 1991": 4.4,
            "1992 - 2005": 4.2,
            "2006 - 2014": 4.0,
            "2015 and later": 3.8
        }
    }
    
    # Extract building details
    building_function = building_row.get('function', "Commercial")
    building_type = building_row.get('building_type', "Other")
    building_age = building_row.get('age_range', "2006 - 2014")
    
    # Determine the lighting level based on building function, type, and age
    if building_function in lighting_levels:
        age_group = lighting_levels[building_function]
        if building_age in age_group:
            lighting_level = age_group[building_age] * adjustment_factor
        else:
            lighting_level = age_group["2006 - 2014"] * adjustment_factor  # Default age group
    else:
        # Default lighting level if function is not specified
        lighting_level = 3.0 * adjustment_factor

    # Other lighting properties
    fraction_radiant = 0.37
    fraction_visible = 0.18
    end_use_subcategory = "GeneralLights"  # Example subcategory

    for zone in idf.idfobjects["ZONE"]:
        # Assuming a simple naming convention for lights objects
        lights_name = f"Lights_{zone.Name}"
        
        idf.newidfobject("LIGHTS",
                         Name=lights_name,
                         Zone_or_ZoneList_or_Space_or_SpaceList_Name=zone.Name,
                         Schedule_Name=schedule_name,
                         Design_Level_Calculation_Method="LightingLevel",
                         Lighting_Level=lighting_level,
                         Fraction_Radiant=fraction_radiant,
                         Fraction_Visible=fraction_visible,
                         EndUse_Subcategory=end_use_subcategory
        )



def generate_detailed_electric_equipment(idf, building_row):
    # Default values with updated building_type options and removed dependency on area and people
    base_values = {
        "Residential": {
            "<1945": 1.5,
            "1945 - 1964": 1.8,
            "1965 - 1974": 1.7,
            "1975 - 1991": 1.6,
            "1992 - 2005": 1.5,
            "2006 - 2014": 1.4,
            "2015 and later": 1.3
        },
        "Commercial": {
            "<1945": 2.5,
            "1945 - 1964": 2.8,
            "1965 - 1974": 2.7,
            "1975 - 1991": 2.6,
            "1992 - 2005": 2.5,
            "2006 - 2014": 2.4,
            "2015 and later": 2.3
        },
        "Industrial": {
            "<1945": 3.5,
            "1945 - 1964": 3.8,
            "1965 - 1974": 3.7,
            "1975 - 1991": 3.6,
            "1992 - 2005": 3.5,
            "2006 - 2014": 3.4,
            "2015 and later": 3.3
        }
    }
    
    # Extract building details
    building_function = building_row.get('function', "Commercial")
    building_type = building_row.get('building_type', "Other")
    building_age = building_row.get('age_range', "2006 - 2014")
    
    # Determine the electric equipment load based on building function, type, and age
    if building_function in base_values:
        age_group = base_values[building_function]
        if building_age in age_group:
            electric_load = age_group[building_age]
        else:
            electric_load = age_group["2006 - 2014"]  # Default age group
    else:
        # Default electric load value if function is not specified
        electric_load = 2.5  # Conservative value to avoid high electricity use

    # Other electric equipment properties
    fraction_latent = 0.0
    fraction_radiant = 0.3
    fraction_lost = 0.0

    for zone in idf.idfobjects["ZONE"]:
        # Assuming a simple naming convention for electric equipment objects
        electric_eq_name = f"electric_eq_{zone.Name}"
        
        idf.newidfobject('ELECTRICEQUIPMENT',
                        Name=electric_eq_name,
                        Zone_or_ZoneList_or_Space_or_SpaceList_Name=zone.Name,
                        Schedule_Name='OccupancySched',  # Assuming this schedule still applies
                        Design_Level_Calculation_Method='EquipmentLevel',  # Using direct equipment load
                        Design_Level=electric_load,  # Using the calculated electric load
                        Fraction_Latent=fraction_latent,
                        Fraction_Radiant=fraction_radiant,
                        Fraction_Lost=fraction_lost,
                        # End_Use_Subcategory can be uncommented or adjusted as needed
                        EndUse_Subcategory='General'
                )


# ### 3.1 RUNPERIOD

def add_year_long_run_period(idf):

    idf.newidfobject(
        "RUNPERIOD",
        Name="RUNPERIOD 1",
        Begin_Month=1,
        Begin_Day_of_Month=1,
        End_Month=12,
        End_Day_of_Month=31,
        Day_of_Week_for_Start_Day="Sunday",
        Use_Weather_File_Holidays_and_Special_Days="Yes",
        Use_Weather_File_Daylight_Saving_Period="No",
        Apply_Weekend_Holiday_Rule="Yes",
        Use_Weather_File_Rain_Indicators="Yes",
        Use_Weather_File_Snow_Indicators="Yes"
    )


# ### 3.2 SIZING:SYSTEM and SIZING:ZONE

def add_outdoor_air_and_zone_sizing_to_all_zones(idf):
    for zone in idf.idfobjects["ZONE"]:
        # Construct the names based on the zone name
        dsoa_name = f"DSOA {zone.Name}"
        dszado_name = f"DSZADO {zone.Name}"

        # Create the DESIGNSPECIFICATION:OUTDOORAIR object
        idf.newidfobject(
            "DESIGNSPECIFICATION:OUTDOORAIR",
            Name=dsoa_name,
            Outdoor_Air_Method="SUM",
            Outdoor_Air_Flow_per_Person=0.00236,
            Outdoor_Air_Flow_per_Zone_Floor_Area=0.000305
        )

        # Create the SIZING:ZONE object
        idf.newidfobject(
            "SIZING:ZONE",
            Zone_or_ZoneList_Name=zone.Name,
            Zone_Cooling_Design_Supply_Air_Temperature=14,
            Zone_Heating_Design_Supply_Air_Temperature=50,
            Zone_Cooling_Design_Supply_Air_Humidity_Ratio=0.009,
            Zone_Heating_Design_Supply_Air_Humidity_Ratio=0.004,
            Design_Specification_Outdoor_Air_Object_Name=dsoa_name,
            Zone_Cooling_Sizing_Factor=0.0,
            Zone_Heating_Sizing_Factor=0.0,
            Cooling_Design_Air_Flow_Method="designdaywithlimit",
            Heating_Design_Air_Flow_Method="designday",
            Design_Specification_Zone_Air_Distribution_Object_Name=dszado_name,
            Account_for_Dedicated_Outdoor_Air_System="Yes",
            Dedicated_Outdoor_Air_System_Control_Strategy="ColdSupplyAir",
            Dedicated_Outdoor_Air_Low_Setpoint_Temperature_for_Design=12.2,
            Dedicated_Outdoor_Air_High_Setpoint_Temperature_for_Design=14.4,
            Zone_Load_Sizing_Method="Sensible And Latent Load",
            Zone_Latent_Cooling_Design_Supply_Air_Humidity_Ratio_Input_Method="HumidityRatioDifference",
            #Zone_Cooling_Design_Supply_Air_Humidity_Ratio_Difference=0.005,
            Zone_Latent_Heating_Design_Supply_Air_Humidity_Ratio_Input_Method="HumidityRatioDifference",
            #Zone_Heating_Design_Supply_Air_Humidity_Ratio_Difference=0.005
        )

        # Create the DesignSpecification:ZoneAirDistribution object
        idf.newidfobject(
            "DESIGNSPECIFICATION:ZONEAIRDISTRIBUTION",
            Name=dszado_name,
            Zone_Air_Distribution_Effectiveness_in_Cooling_Mode=1.0,
            Zone_Air_Distribution_Effectiveness_in_Heating_Mode=1.0,
            Zone_Secondary_Recirculation_Fraction=0.3
        )


def add_door_to_wall(idf):
    # Define Door Material and Construction
    idf.newidfobject(
        'MATERIAL', Name='DoorMaterial',
        Roughness='Smooth',
        Thickness=0.05,  # Typical door thickness
        Conductivity=0.15,  # Wood or similar material
        Density=800,
        Specific_Heat=2100
    )
    
    idf.newidfobject(
        'CONSTRUCTION', Name='DoorConstruction',
        Outside_Layer='DoorMaterial'
    )

    # Find a suitable wall to place the door
    walls = [wall for wall in idf.idfobjects['BUILDINGSURFACE:DETAILED'] if wall.Surface_Type.upper() == 'WALL' and wall.Outside_Boundary_Condition.upper() == 'OUTDOORS']
    
    if walls:
        # For simplicity, we choose the first exterior wall
        chosen_wall = walls[0]
        
        # Door dimensions
        door_height = 2.1  # Typical door height
        door_width = 0.9   # Typical door width
        
        # Assuming the door starts from the bottom left of the wall
        base_height = 0.0  # Bottom of the wall

        # Add the door as a subsurface to the chosen wall
        idf.newidfobject(
            'FENESTRATIONSURFACE:DETAILED', Name='MainDoor',
            Surface_Type='DOOR',
            Construction_Name='DoorConstruction',
            Building_Surface_Name=chosen_wall.Name,
            Number_of_Vertices=4,
            Vertex_1_Xcoordinate=chosen_wall.Vertex_1_Xcoordinate,
            Vertex_1_Ycoordinate=chosen_wall.Vertex_1_Ycoordinate,
            Vertex_1_Zcoordinate=base_height,
            Vertex_2_Xcoordinate=chosen_wall.Vertex_1_Xcoordinate + door_width,
            Vertex_2_Ycoordinate=chosen_wall.Vertex_1_Ycoordinate,
            Vertex_2_Zcoordinate=base_height,
            Vertex_3_Xcoordinate=chosen_wall.Vertex_1_Xcoordinate + door_width,
            Vertex_3_Ycoordinate=chosen_wall.Vertex_1_Ycoordinate,
            Vertex_3_Zcoordinate=base_height + door_height,
            Vertex_4_Xcoordinate=chosen_wall.Vertex_1_Xcoordinate,
            Vertex_4_Ycoordinate=chosen_wall.Vertex_1_Ycoordinate,
            Vertex_4_Zcoordinate=base_height + door_height
        )
    else:
        print("No suitable exterior wall found to place a door.")





def add_hvac_schedules(idf, building_row):
          


     building_function = building_row['function'] #, 'Residential')  # Default to "Woon- en Verblijfsfuncties"  # Checks

     idf.newidfobject(
          "SCHEDULETYPELIMITS",
          Name="CONTROL TYPE",
          Lower_Limit_Value=0,
          Upper_Limit_Value=2,  # Assuming 0 to 2 covers all your control types.
          Numeric_Type="Discrete",  # Use "Discrete" for integer values.
          )


     # Residential and Accommodation Functions
     if building_function == "Residential":
        # Heating Setpoint Schedule for residential
          idf.newidfobject("SCHEDULE:COMPACT",
                 Name="Heating Setpoint Schedule",
                 Schedule_Type_Limits_Name="Temperature",
                 Field_1="Through: 12/31",
                 Field_2="For: Weekdays",
                 Field_3="Until: 06:00,16.0",  # Lower temperature for sleeping hours
                 Field_4="Until: 08:00,20.0",  # Warm up for morning routine
                 Field_5="Until: 09:00,18.0",  # Lower while the house is likely empty
                 Field_6="Until: 17:00,18.0",  # Continue lower temperature during typical work/school hours
                 Field_7="Until: 18:00,20.0",  # Warm up for evening activities
                 Field_8="Until: 22:00,21.0",  # Comfortable for evening relaxation
                 Field_9="Until: 24:00,16.0",  # Lower for sleeping hours
                 Field_10="For: Saturday",
                 Field_11="Until: 08:00,18.0", # Slightly warmer for weekend mornings
                 Field_12="Until: 23:00,21.0", # Keep comfortable for weekend day
                 Field_13="Until: 24:00,16.0", # Lower for sleeping
                 Field_14="For: Sunday",
                 Field_15="Until: 08:00,18.0", # Similar pattern to Saturday for consistency
                 Field_16="Until: 23:00,21.0",
                 Field_17="Until: 24:00,16.0",
                 Field_18="For: SummerDesignDay",
                 Field_19="Until: 24:00,24.0", # Adjust for desired summer design conditions
                 Field_20="For: WinterDesignDay",
                 Field_21="Until: 24:00,21.5", # Ensure comfort during colder days
                 Field_22="For: Holidays",
                 Field_23="Until: 24:00,18.0", # Slightly warmer for holidays when occupants are likely home
                 Field_24="For: AllOtherDays",
                 Field_25="Until: 06:00,16.0",
                 Field_26="Until: 22:00,20.0", # Comfortable for typical home activities
                 Field_27="Until: 24:00,16.0") # Lower for nighttime
        # Cooling Setpoint Schedule for residential
          idf.newidfobject("SCHEDULE:COMPACT",
                 Name="Cooling Return Air Setpoint Schedule",
                 Schedule_Type_Limits_Name="Temperature",
                 Field_1="Through: 12/31",
                 Field_2="For: Weekdays",
                 Field_3="Until: 06:00,26.0",  # Higher setpoint during sleeping hours for energy savings
                 Field_4="Until: 08:00,24.0",  # Begin to cool down as residents wake up and get ready for the day
                 Field_5="Until: 18:00,28.0",  # Higher setpoint during the day when the house is likely unoccupied
                 Field_6="Until: 22:00,24.0",  # Lower setpoint during the evening for comfort
                 Field_7="Until: 24:00,26.0",  # Increase setpoint during sleeping hours
                 Field_8="For: Saturday",
                 Field_9="Until: 09:00,26.0",  # Residents likely to sleep in, so keep setpoint higher for longer
                 Field_10="Until: 23:00,24.0",  # Lower setpoint throughout the day for weekend comfort
                 Field_11="Until: 24:00,26.0",  # Prepare for bedtime with a higher setpoint
                 Field_12="For: Sunday",
                 Field_13="Until: 09:00,26.0",
                 Field_14="Until: 23:00,24.0",
                 Field_15="Until: 24:00,26.0",
                 Field_16="For: SummerDesignDay",
                 Field_17="Until: 24:00,24.0",  # Consistently lower setpoint to combat higher outside temperatures
                 Field_18="For: WinterDesignDay",
                 Field_19="Until: 24:00,28.0",  # Potentially higher setpoint as cooling may not be needed
                 Field_20="For: Holidays",
                 Field_21="Until: 24:00,26.0",  # Assuming less occupancy or activity, allowing for energy savings
                 Field_22="For: AllOtherDays",
                 Field_23="Until: 06:00,26.0",
                 Field_24="Until: 18:00,28.0",
                 Field_25="Until: 22:00,24.0",
                 Field_26="Until: 24:00,26.0"
                 )  # Adjust based on special events or unusually hot days
        # Zone Control Type Schedule for residential
            # Higher cooling demand with more people in the house
            # Fan and Coil Availability Schedule for residential
          idf.newidfobject("SCHEDULE:COMPACT",
                 Name="FanAndCoilAvailSchedule",
                 Schedule_Type_Limits_Name="Fraction",
                 Field_1="Through: 12/31",
                 Field_2="For: Weekdays",
                 Field_3="Until: 06:00,0.0",
                 Field_4="Until: 22:00,1.0",
                 Field_5="Until: 24:00,0.0",
                 Field_6="For: Weekend",
                 Field_7="Until: 07:00,0.0",
                 Field_8="Until: 23:00,1.0",
                 Field_9="Until: 24:00,0.0",
                 Field_10="For: Holidays",
                 Field_11="Until: 24:00,0.0",
                 Field_12="For: SummerDesignDay",
                 Field_13="Until: 24:00,1.0",
                 Field_14="For: WinterDesignDay",
                 Field_15="Until: 24:00,1.0",
                 Field_16="For: AllOtherDays",
                 Field_17="Until: 24:00,1.0")
          # Residential System Availability Schedule
          idf.newidfobject("SCHEDULE:COMPACT",
                 Name="System Availability Schedule",
                 Schedule_Type_Limits_Name="Fraction",
                 Field_1="Through: 12/31",
                 Field_2="For: Weekdays",
                 Field_3="Until: 06:00,0.0",
                 Field_4="Until: 22:00,1.0",
                 Field_5="Until: 24:00,0.0",
                 Field_6="For: Weekend",
                 Field_7="Until: 08:00,0.0",
                 Field_8="Until: 23:00,1.0",
                 Field_9="Until: 24:00,0.0",
                 Field_10="For: Holidays",
                 Field_11="Until: 24:00,0.0",
                 Field_12="For: SummerDesignDay",
                 Field_13="Until: 24:00,1.0",
                 Field_14="For: WinterDesignDay",
                 Field_15="Until: 24:00,1.0",
                 Field_16="For: AllOtherDays",
                 Field_17="Until: 24:00,1.0")
          # Residential Fan Schedule
          idf.newidfobject("SCHEDULE:COMPACT",
                 Name="Fan Schedule",
                 Schedule_Type_Limits_Name="Fraction",
                 Field_1="Through: 12/31",
                 Field_2="For: Weekdays",
                 Field_3="Until: 06:00,0.0",
                 Field_4="Until: 22:00,1.0",
                 Field_5="Until: 24:00,0.0",
                 Field_6="For: Weekend",
                 Field_7="Until: 08:00,0.0",
                 Field_8="Until: 23:00,1.0",
                 Field_9="Until: 24:00,0.0",
                 Field_10="For: Holidays",
                 Field_11="Until: 24:00,0.0",
                 Field_12="For: SummerDesignDay",
                 Field_13="Until: 24:00,1.0",
                 Field_14="For: WinterDesignDay",
                 Field_15="Until: 24:00,1.0",
                 Field_16="For: AllOtherDays",
                 Field_17="Until: 24:00,1.0")

          idf.newidfobject("SCHEDULE:COMPACT",
                 Name="Sales Schedule",
                 Schedule_Type_Limits_Name="Fraction",
                 Field_1="Through: 12/31",
                 Field_2="For: Weekdays",
                 Field_3="Until: 06:00,0.0",
                 Field_4="Until: 08:00,0.5",
                 Field_5="Until: 18:00,1.0",
                 Field_6="Until: 22:00,0.5",
                 Field_7="Until: 24:00,0.0",
                 Field_8="For: Weekend",
                 Field_9="Until: 08:00,0.0",
                 Field_10="Until: 12:00,0.5",
                 Field_11="Until: 20:00,1.0",
                 Field_12="Until: 24:00,0.0",
                 Field_13="For: Holidays",
                 Field_14="Until: 24:00,0.0",
                 Field_15="For: SummerDesignDay",
                 Field_16="Until: 24:00,1.0",
                 Field_17="For: WinterDesignDay",
                 Field_18="Until: 24:00,1.0",
                 Field_19="For: AllOtherDays",
                 Field_20="Until: 24:00,0.5")


    # Commercial and Institutional Functions
     elif building_function == "Commercial":
        # Heating Setpoint Schedule for commercial
                idf.newidfobject("SCHEDULE:COMPACT",
                 Name="Heating Setpoint Schedule",
                 Schedule_Type_Limits_Name="Temperature",
                 Field_1="Through: 12/31",
                 Field_2="For: Weekdays",
                 Field_3="Until: 06:00,16.0",  # Pre-business hours, lower heating to save energy
                 Field_4="Until: 08:00,20.0",  # Gradual heating up before employees arrive
                 Field_5="Until: 09:00,21.5",  # Comfortable start of business day
                 Field_6="Until: 12:00,21.5",  # Stable temperature through the morning
                 Field_7="Until: 13:00,21.0",  # Slight reduction during typical lunch hour
                 Field_8="Until: 17:00,21.5",  # Resume comfortable temperature for the afternoon
                 Field_9="Until: 18:00,21.0",  # Begin to lower temperature towards end of day
                 Field_10="Until: 20:00,19.0", # Further reduced heating as people leave
                 Field_11="Until: 24:00,16.0", # Minimum heating overnight
                 Field_12="For: Saturday",
                 Field_13="Until: 08:00,16.0", # Lower heating as occupancy is unpredictable
                 Field_14="Until: 14:00,20.0", # Increased heating during possible activity hours
                 Field_15="Until: 24:00,16.0", # Return to minimum heating
                 Field_16="For: Sunday",
                 Field_17="Until: 24:00,16.0", # Consistent minimum heating as building is likely unoccupied
                 Field_18="For: SummerDesignDay",
                 Field_19="Until: 24:00,24.0", # Adjust for desired summer design conditions
                 Field_20="For: WinterDesignDay",
                 Field_21="Until: 24:00,21.5", # Ensure comfort during the coldest part of the year
                 Field_22="For: Holidays",
                 Field_23="Until: 24:00,16.0", # Reduced heating to save energy during holidays
                 Field_24="For: AllOtherDays",
                 Field_25="Until: 06:00,16.0",
                 Field_26="Until: 22:00,20.0", # Slightly increased heating for potential occasional use
                 Field_27="Until: 24:00,16.0") # Energy saving overnight setting
        # Cooling Setpoint Schedule for commercial
                idf.newidfobject("SCHEDULE:COMPACT",
                 Name="Cooling Return Air Setpoint Schedule",
                 Schedule_Type_Limits_Name="Temperature",
                 Field_1="Through: 12/31",
                 Field_2="For: Weekdays",
                 Field_3="Until: 06:00,55.0",  # Adjust for minimal operations or maintenance periods
                 Field_4="Until: 07:00,54.0",  # Begin cooling down before first shift starts
                 Field_5="Until: 19:00,52.0",  # Lower setpoint during main operational hours for equipment and process cooling
                 Field_6="Until: 21:00,54.0",  # Begin to increase setpoint as operations wind down
                 Field_7="Until: 24:00,55.0",  # Higher setpoint during off-shift hours for energy savings
                 Field_8="For: Saturday",
                 Field_9="Until: 06:00,56.0",  # Assume limited operations or maintenance
                 Field_10="Until: 18:00,54.0",  # Some operations may continue into the weekend
                 Field_11="Until: 24:00,56.0",  # Higher setpoint assuming reduced activity
                 Field_12="For: Sunday",
                 Field_13="Until: 24:00,57.0",  # Higher setpoint assuming minimal or no operations
                 Field_14="For: SummerDesignDay",
                 Field_15="Until: 24:00,52.0",  # Lower setpoint to accommodate increased cooling needs
                 Field_16="For: WinterDesignDay",
                 Field_17="Until: 24:00,54.0",  # Potential for slightly higher setpoint if cooling demands are lower
                 Field_18="For: Holidays",
                 Field_19="Until: 24:00,57.0",  # Assuming the building is largely unoccupied
                 Field_20="For: AllOtherDays",
                 Field_21="Until: 06:00,55.0",
                 Field_22="Until: 19:00,52.0",
                 Field_23="Until: 24:00,55.0")  # Higher setpoint during maintenance periods for energy efficiency


          
               #
                idf.newidfobject("SCHEDULE:COMPACT",
                 Name="System Availability Schedule",
                 Schedule_Type_Limits_Name="Fraction",
                 Field_1="Through: 12/31",
                 Field_2="For: Weekdays",
                 Field_3="Until: 05:00,0.0",
                 Field_4="Until: 21:00,1.0",
                 Field_5="Until: 24:00,0.0",
                 Field_6="For: Weekend",
                 Field_7="Until: 24:00,0.0",
                 Field_8="For: Holidays",
                 Field_9="Until: 24:00,0.0",
                 Field_10="For: SummerDesignDay",
                 Field_11="Until: 24:00,1.0",
                 Field_12="For: WinterDesignDay",
                 Field_13="Until: 24:00,1.0",
                 Field_14="For: AllOtherDays",
                 Field_15="Until: 24:00,1.0")
                # Commercial Fan Schedule
                idf.newidfobject("SCHEDULE:COMPACT",
                 Name="Fan Schedule",
                 Schedule_Type_Limits_Name="Fraction",
                 Field_1="Through: 12/31",
                 Field_2="For: Weekdays",
                 Field_3="Until: 05:00,0.0",
                 Field_4="Until: 21:00,1.0",
                 Field_5="Until: 24:00,0.0",
                 Field_6="For: Weekend",
                 Field_7="Until: 24:00,0.0",
                 Field_8="For: Holidays",
                 Field_9="Until: 24:00,0.0",
                 Field_10="For: SummerDesignDay",
                 Field_11="Until: 24:00,1.0",
                 Field_12="For: WinterDesignDay",
                 Field_13="Until: 24:00,1.0",
                 Field_14="For: AllOtherDays",
                 Field_15="Until: 24:00,1.0")

                idf.newidfobject("SCHEDULE:COMPACT",
                 Name="Sales Schedule",
                 Schedule_Type_Limits_Name="Fraction",
                 Field_1="Through: 12/31",
                 Field_2="For: Weekdays",
                 Field_3="Until: 05:00,0.0",
                 Field_4="Until: 07:00,0.5",
                 Field_5="Until: 19:00,1.0",
                 Field_6="Until: 21:00,0.5",
                 Field_7="Until: 24:00,0.0",
                 Field_8="For: Weekend",
                 Field_9="Until: 24:00,0.0",
                 Field_10="For: Holidays",
                 Field_11="Until: 24:00,0.0",
                 Field_12="For: SummerDesignDay",
                 Field_13="Until: 24:00,1.0",
                 Field_14="For: WinterDesignDay",
                 Field_15="Until: 24:00,0.5",
                 Field_16="For: AllOtherDays",
                 Field_17="Until: 24:00,1.0")
                idf.newidfobject("SCHEDULE:COMPACT",
                 Name="FanAndCoilAvailSchedule",
                 Schedule_Type_Limits_Name="Fraction",
                 Field_1="Through: 12/31",
                 Field_2="For: Weekdays",
                 Field_3="Until: 06:00,0.0",
                 Field_4="Until: 22:00,1.0",
                 Field_5="Until: 24:00,0.0",
                 Field_6="For: Weekend",
                 Field_7="Until: 07:00,0.0",
                 Field_8="Until: 23:00,1.0",
                 Field_9="Until: 24:00,0.0",
                 Field_10="For: Holidays",
                 Field_11="Until: 24:00,0.0",
                 Field_12="For: SummerDesignDay",
                 Field_13="Until: 24:00,1.0",
                 Field_14="For: WinterDesignDay",
                 Field_15="Until: 24:00,1.0",
                 Field_16="For: AllOtherDays",
                 Field_17="Until: 24:00,1.0")
    # Industrial and Special Functions
     elif building_function == "Industrial":
            idf.newidfobject("SCHEDULE:COMPACT",
                 Name="Heating Setpoint Schedule",
                 Schedule_Type_Limits_Name="Temperature",
                 Field_1="Through: 12/31",
                 Field_2="For: Weekdays",
                 Field_3="Until: 06:00,15.0",  # Lower temperature for non-operational hours
                 Field_4="Until: 07:00,18.0",  # Gradual warm-up before the first shift starts
                 Field_5="Until: 19:00,20.0",  # Maintain comfortable temperature during operating hours
                 Field_6="Until: 20:00,18.0",  # Begin to lower temperature as operations wind down
                 Field_7="Until: 24:00,15.0",  # Lower temperature for non-operational evening hours
                 Field_8="For: Saturday",
                 Field_9="Until: 24:00,15.0",  # Maintain a lower temperature if the facility is less active
                 Field_10="For: Sunday",
                 Field_11="Until: 24:00,15.0",  # Similar to Saturday, assuming non-operational
                 Field_12="For: SummerDesignDay",
                 Field_13="Until: 24:00,20.0",  # Maintain a stable temperature, considering summer conditions
                 Field_14="For: WinterDesignDay",
                 Field_15="Until: 24:00,20.0",  # Ensure a slightly higher temperature for comfort and equipment
                 Field_16="For: Holidays",
                 Field_17="Until: 24:00,15.0",  # Reduced temperature during holidays
                 Field_18="For: AllOtherDays",
                 Field_19="Until: 06:00,15.0",
                 Field_20="Until: 19:00,20.0",  # Similar pattern to weekdays for consistency
                 Field_21="Until: 24:00,15.0")  # Lowest setting during prolonged non-use periods
            
            # Cooling Setpoint Schedule for industrial
            idf.newidfobject("SCHEDULE:COMPACT",
                 Name="Cooling Return Air Setpoint Schedule",
                 Schedule_Type_Limits_Name="Temperature",
                 Field_1="Through: 12/31",
                 Field_2="For: Weekdays",
                 Field_3="Until: 06:00,55.0",  # Adjust for minimal operations or maintenance periods
                 Field_4="Until: 07:00,54.0",  # Begin cooling down before first shift starts
                 Field_5="Until: 19:00,52.0",  # Lower setpoint during main operational hours for equipment and process cooling
                 Field_6="Until: 21:00,54.0",  # Begin to increase setpoint as operations wind down
                 Field_7="Until: 24:00,55.0",  # Higher setpoint during off-shift hours for energy savings
                 Field_8="For: Saturday",
                 Field_9="Until: 06:00,56.0",  # Assume limited operations or maintenance
                 Field_10="Until: 18:00,54.0",  # Some operations may continue into the weekend
                 Field_11="Until: 24:00,56.0",  # Higher setpoint assuming reduced activity
                 Field_12="For: Sunday",
                 Field_13="Until: 24:00,57.0",  # Higher setpoint assuming minimal or no operations
                 Field_14="For: SummerDesignDay",
                 Field_15="Until: 24:00,52.0",  # Lower setpoint to accommodate increased cooling needs
                 Field_16="For: WinterDesignDay",
                 Field_17="Until: 24:00,54.0",  # Potential for slightly higher setpoint if cooling demands are lower
                 Field_18="For: Holidays",
                 Field_19="Until: 24:00,57.0",  # Assuming the building is largely unoccupied
                 Field_20="For: AllOtherDays",
                 Field_21="Until: 06:00,55.0",
                 Field_22="Until: 19:00,52.0",
                 Field_23="Until: 24:00,55.0")  # Higher setpoint during maintenance periods for energy efficiency

           
            
            # System Availability Schedule for industrial
            idf.newidfobject("SCHEDULE:COMPACT",
                 Name="System Availability Schedule",
                 Schedule_Type_Limits_Name="Fraction",
                 Field_1="Through: 12/31",
                 Field_2="For: Weekdays",
                 Field_3="Until: 04:00,0.0",
                 Field_4="Until: 23:00,1.0",
                 Field_5="Until: 24:00,0.0",
                 Field_6="For: Weekend",
                 Field_7="Until: 24:00,0.0",
                 Field_8="For: Holidays",
                 Field_9="Until: 24:00,0.0",
                 Field_10="For: SummerDesignDay",
                 Field_11="Until: 24:00,1.0",
                 Field_12="For: WinterDesignDay",
                 Field_13="Until: 24:00,1.0",
                 Field_14="For: AllOtherDays",
                 Field_15="Until: 24:00,1.0")
               # Industrial Fan Schedule
            idf.newidfobject("SCHEDULE:COMPACT",
                 Name="Fan Schedule",
                 Schedule_Type_Limits_Name="Fraction",
                 Field_1="Through: 12/31",
                 Field_2="For: Weekdays",
                 Field_3="Until: 04:00,0.0",
                 Field_4="Until: 23:00,1.0",
                 Field_5="Until: 24:00,0.0",
                 Field_6="For: Weekend",
                 Field_7="Until: 24:00,0.0",
                 Field_8="For: Holidays",
                 Field_9="Until: 24:00,0.0",
                 Field_10="For: SummerDesignDay",
                 Field_11="Until: 24:00,1.0",
                 Field_12="For: WinterDesignDay",
                 Field_13="Until: 24:00,1.0",
                 Field_14="For: AllOtherDays",
                 Field_15="Until: 24:00,1.0")
            

            idf.newidfobject("SCHEDULE:COMPACT",
                 Name="Sales Schedule",
                 Schedule_Type_Limits_Name="Fraction",
                 Field_1="Through: 12/31",
                 Field_2="For: Weekdays",
                 Field_3="Until: 04:00,0.0",
                 Field_4="Until: 06:00,0.5",
                 Field_5="Until: 22:00,1.0",
                 Field_6="Until: 24:00,0.5",
                 Field_7="For: Weekend",
                 Field_8="Until: 24:00,0.0",
                 Field_9="For: Holidays",
                 Field_10="Until: 24:00,0.0",
                 Field_11="For: SummerDesignDay",
                 Field_12="Until: 24:00,1.0",
                 Field_13="For: WinterDesignDay",
                 Field_14="Until: 24:00,1.0",
                 Field_15="For: AllOtherDays",
                 Field_16="Until: 24:00,1.0")
            idf.newidfobject("SCHEDULE:COMPACT",
                 Name="FanAndCoilAvailSchedule",
                 Schedule_Type_Limits_Name="Fraction",
                 Field_1="Through: 12/31",
                 Field_2="For: Weekdays",
                 Field_3="Until: 06:00,0.0",
                 Field_4="Until: 22:00,1.0",
                 Field_5="Until: 24:00,0.0",
                 Field_6="For: Weekend",
                 Field_7="Until: 07:00,0.0",
                 Field_8="Until: 23:00,1.0",
                 Field_9="Until: 24:00,0.0",
                 Field_10="For: Holidays",
                 Field_11="Until: 24:00,0.0",
                 Field_12="For: SummerDesignDay",
                 Field_13="Until: 24:00,1.0",
                 Field_14="For: WinterDesignDay",
                 Field_15="Until: 24:00,1.0",
                 Field_16="For: AllOtherDays",
                 Field_17="Until: 24:00,1.0")

     else:
        print("Unknown building function")










def add_water_heating(idf):

    # Add Schedule:Compact objects
    idf.newidfobject("SCHEDULE:COMPACT",
        Name="ZN_1_FLR_1_SEC_1SHW_DEFAULT Latent fract sched",
        Schedule_Type_Limits_Name="Fraction",
        Field_1="Through: 12/31",
        Field_2="For: AllDays",
        Field_3="Until: 24:00,0.05"
    )

    idf.newidfobject("SCHEDULE:COMPACT",
        Name="ZN_1_FLR_1_SEC_1SHW_DEFAULT Sensible fract sched",
        Schedule_Type_Limits_Name="Fraction",
        Field_1="Through: 12/31",
        Field_2="For: AllDays",
        Field_3="Until: 24:00,0.2"
    )

    idf.newidfobject("SCHEDULE:COMPACT",
        Name="ZN_1_FLR_1_SEC_1SHW_DEFAULT Temp Sched",
        Schedule_Type_Limits_Name="Temperature",
        Field_1="Through: 12/31",
        Field_2="For: AllDays",
        Field_3="Until: 24:00,40"
    )

    idf.newidfobject("SCHEDULE:COMPACT",
        Name="ZN_1_FLR_1_SEC_1SHW_DEFAULTHot Supply Temp Sched",
        Schedule_Type_Limits_Name="Temperature",
        Field_1="Through: 12/31",
        Field_2="For: AllDays",
        Field_3="Until: 24:00,55"
    )

    idf.newidfobject(
          "SCHEDULETYPELIMITS",
          Name="On/Off",
          Lower_Limit_Value=0,
          Upper_Limit_Value=1,  # Assuming 0 to 2 covers all your control types.
          Numeric_Type="Discrete",  # Use "Discrete" for integer values.
          )    

    idf.newidfobject("SCHEDULE:COMPACT",
        Name="PlantOnSched",
        Schedule_Type_Limits_Name="On/Off",
        Field_1="Through: 12/31",
        Field_2="For: AllDays",
        Field_3="Until: 24:00,1.0"
    )

    # Add SetpointManager:Scheduled object
    idf.newidfobject("SETPOINTMANAGER:SCHEDULED",
        Name="SHWSys1_Loop_Setpoint_Manager",
        Control_Variable="Temperature",
        Schedule_Name="SHWSys1_Loop_Temp_Schedule",
        Setpoint_Node_or_NodeList_Name="SHWSys1_Supply_Outlet_Node"
    )

    # Add PlantEquipmentOperationSchemes object
    idf.newidfobject("PLANTEQUIPMENTOPERATIONSCHEMES",
        Name="SHWSys1_Loop_Operation_Scheme_List",
        Control_Scheme_1_Object_Type="PlantEquipmentOperation:HeatingLoad",
        Control_Scheme_1_Name="SHWSys1_Operation_Scheme",
        Control_Scheme_1_Schedule_Name="PlantOnSched"
    )

    # Add PlantEquipmentOperation:HeatingLoad object
    idf.newidfobject("PLANTEQUIPMENTOPERATION:HEATINGLOAD",
        Name="SHWSys1_Operation_Scheme",
        Load_Range_1_Lower_Limit=0.0,
        Load_Range_1_Upper_Limit=1000000000000000,
        Range_1_Equipment_List_Name="SHWSys1_Equipment_List"
    )

    # Add Schedule:Compact objects
    idf.newidfobject("SCHEDULE:COMPACT",
        Name="SHWSys1_Loop_Temp_Schedule",
        Schedule_Type_Limits_Name="Temperature",
        Field_1="Through: 12/31",
        Field_2="For: AllDays",
        Field_3="Until: 24:00,60"
    )

    idf.newidfobject("SCHEDULE:COMPACT",
        Name="SHWSys1_Water_Heater_Setpoint_Temperature_Schedule",
        Schedule_Type_Limits_Name="Temperature",
        Field_1="Through: 12/31",
        Field_2="For: AllDays",
        Field_3="Until: 24:00,60.0"
    )

    idf.newidfobject("SCHEDULE:COMPACT",
        Name="SHWSys1_Water_Heater_Ambient_Temperature_Schedule",
        Schedule_Type_Limits_Name="Temperature",
        Field_1="Through: 12/31",
        Field_2="For: AllDays",
        Field_3="Until: 24:00,22.0"
    )

    idf.newidfobject("SCHEDULE:COMPACT",
        Name="ZN_1_FLR_1_SEC_5SHW_Default_Latent_Fract_Sched",
        Schedule_Type_Limits_Name="Fraction",
        Field_1="Through: 12/31",
        Field_2="For: AllDays",
        Field_3="Until: 24:00,0.05"
    )

    idf.newidfobject("SCHEDULE:COMPACT",
        Name="ZN_1_FLR_1_SEC_5SHW_Default_Sensible_Fract_Sched",
        Schedule_Type_Limits_Name="Fraction",
        Field_1="Through: 12/31",
        Field_2="For: AllDays",
        Field_3="Until: 24:00,0.2"
    )

    idf.newidfobject("SCHEDULE:COMPACT",
        Name="ZN_1_FLR_1_SEC_5SHW_Default_Temp_Sched",
        Schedule_Type_Limits_Name="Temperature",
        Field_1="Through: 12/31",
        Field_2="For: AllDays",
        Field_3="Until: 24:00,40"
    )

    idf.newidfobject("SCHEDULE:COMPACT",
        Name="ZN_1_FLR_1_SEC_5SHW_Default_Hot_Supply_Temp_Sched",
        Schedule_Type_Limits_Name="Temperature",
        Field_1="Through: 12/31",
        Field_2="For: AllDays",
        Field_3="Until: 24:00,55"
    )

    idf.newidfobject("SCHEDULE:COMPACT",
        Name="BLDG_SWH_SCH",
        Schedule_Type_Limits_Name="Fraction",
        Field_1="Through: 12/31",
        Field_2="For: AllDays",
        Field_3="Until: 24:00,1.0"
    )

    # ================================== # 


    # Add Pump:VariableSpeed object
    idf.newidfobject("PUMP:VARIABLESPEED",
        Name="SHWSys1_Pump",
        Inlet_Node_Name="SHWSys1_Supply_Inlet_Node",
        Outlet_Node_Name="SHWSys1_Pump_Water_Heater_NodeviaConnector",
        Design_Maximum_Flow_Rate="AUTOSIZE",
        Design_Pump_Head=50000,
        Design_Power_Consumption="AUTOSIZE",
        Motor_Efficiency=.88,
        Fraction_of_Motor_Inefficiencies_to_Fluid_Stream=0.0,
        Coefficient_1_of_the_Part_Load_Performance_Curve=0.1,
        Coefficient_2_of_the_Part_Load_Performance_Curve=0.9,
        Coefficient_3_of_the_Part_Load_Performance_Curve=0,
        Coefficient_4_of_the_Part_Load_Performance_Curve=0,
        Design_Minimum_Flow_Rate=0.001,
        Pump_Control_Type="INTERMITTENT"
    )

    # Add WaterHeater:Mixed object
    idf.newidfobject("WATERHEATER:MIXED",
        Name="SHWSys1_Water_Heater",
        Tank_Volume=3,
        Setpoint_Temperature_Schedule_Name="SHWSys1_Water_Heater_Setpoint_Temperature_Schedule",
        Deadband_Temperature_Difference=2.0,
        Maximum_Temperature_Limit=82.2222,
        Heater_Control_Type="CYCLE",
        Heater_Maximum_Capacity=845000,
        Heater_Minimum_Capacity="",
        Heater_Ignition_Minimum_Flow_Rate="",
        Heater_Ignition_Delay="",
        Heater_Fuel_Type="NATURALGAS",
        Heater_Thermal_Efficiency=0.8,
        Part_Load_Factor_Curve_Name="",
        Off_Cycle_Parasitic_Fuel_Consumption_Rate=20,
        Off_Cycle_Parasitic_Fuel_Type="NATURALGAS",
        Off_Cycle_Parasitic_Heat_Fraction_to_Tank=0.8,
        On_Cycle_Parasitic_Fuel_Consumption_Rate="",
        On_Cycle_Parasitic_Fuel_Type="NATURALGAS",
        On_Cycle_Parasitic_Heat_Fraction_to_Tank="",
        Ambient_Temperature_Indicator="SCHEDULE",
        Ambient_Temperature_Schedule_Name="SHWSys1_Water_Heater_Ambient_Temperature_Schedule",
        Ambient_Temperature_Zone_Name="",
        Ambient_Temperature_Outdoor_Air_Node_Name="",
        Off_Cycle_Loss_Coefficient_to_Ambient_Temperature=6.0,
        Off_Cycle_Loss_Fraction_to_Zone="",
        On_Cycle_Loss_Coefficient_to_Ambient_Temperature=6.0,
        On_Cycle_Loss_Fraction_to_Zone="",
        Peak_Use_Flow_Rate="",
        Use_Flow_Rate_Fraction_Schedule_Name="",
        Cold_Water_Supply_Temperature_Schedule_Name="",
        Use_Side_Inlet_Node_Name="SHWSys1_Pump_Water_Heater_Node",
        Use_Side_Outlet_Node_Name="SHWSys1_Supply_Equipment_Outlet_Node",
        Use_Side_Effectiveness=1.0,
        Source_Side_Inlet_Node_Name="",
        Source_Side_Outlet_Node_Name="",
        Source_Side_Effectiveness=1.0,
        Use_Side_Design_Flow_Rate="AUTOSIZE",
        Source_Side_Design_Flow_Rate="AUTOSIZE",
        Indirect_Water_Heating_Recovery_Time=1.5
    )

    # Add PlantLoop object
    idf.newidfobject("PLANTLOOP",
        Name="SHWSys1",
        Fluid_Type="WATER",
        User_Defined_Fluid_Type="",
        Plant_Equipment_Operation_Scheme_Name="SHWSys1_Loop_Operation_Scheme_List",
        Loop_Temperature_Setpoint_Node_Name="SHWSys1_Supply_Outlet_Node",
        Maximum_Loop_Temperature=60.0,
        Minimum_Loop_Temperature=10.0,
        Maximum_Loop_Flow_Rate="AUTOSIZE",
        Minimum_Loop_Flow_Rate=0.0,
        Plant_Loop_Volume="AUTOSIZE",
        Plant_Side_Inlet_Node_Name="SHWSys1_Supply_Inlet_Node",
        Plant_Side_Outlet_Node_Name="SHWSys1_Supply_Outlet_Node",
        Plant_Side_Branch_List_Name="SHWSys1_Supply_Branches",
        Plant_Side_Connector_List_Name="SHWSys1_Supply_Connectors",
        Demand_Side_Inlet_Node_Name="SHWSys1_Demand_Inlet_Node",
        Demand_Side_Outlet_Node_Name="SHWSys1_Demand_Outlet_Node",
        Demand_Side_Branch_List_Name="SHWSys1_Demand_Branches",
        Demand_Side_Connector_List_Name="SHWSys1_Demand_Connectors",
        Load_Distribution_Scheme="OPTIMAL"
    )

    # Add Sizing:Plant object
    idf.newidfobject("SIZING:PLANT",
        Plant_or_Condenser_Loop_Name="SHWSys1",
        Loop_Type="HEATING",
        Design_Loop_Exit_Temperature=60,
        Loop_Design_Temperature_Difference=5.0
    )



    # Add PlantEquipmentList object
    idf.newidfobject("PLANTEQUIPMENTLIST",
        Name="SHWSys1_Equipment_List",
        Equipment_1_Object_Type="WaterHeater:Mixed",
        Equipment_1_Name="SHWSys1_Water_Heater"
    )

    # Add BranchList objects
    idf.newidfobject("BRANCHLIST",
        Name="SHWSys1_Supply_Branches",
        Branch_1_Name="SHWSys1_Supply_Inlet_Branch",
        Branch_2_Name="SHWSys1_Supply_Equipment_Branch",
        Branch_3_Name="SHWSys1_Supply_Equipment_Bypass_Branch",
        Branch_4_Name="SHWSys1_Supply_Outlet_Branch"
    )

    

    # Add ConnectorList objects
    idf.newidfobject("CONNECTORLIST",
        Name="SHWSys1_Supply_Connectors",
        Connector_1_Object_Type="Connector:Splitter",
        Connector_1_Name="SHWSys1_Supply_Splitter",
        Connector_2_Object_Type="Connector:Mixer",
        Connector_2_Name="SHWSys1_Supply_Mixer"
    )

    idf.newidfobject("CONNECTORLIST",
        Name="SHWSys1_Demand_Connectors",
        Connector_1_Object_Type="Connector:Splitter",
        Connector_1_Name="SHWSys1_Demand_Splitter",
        Connector_2_Object_Type="Connector:Mixer",
        Connector_2_Name="SHWSys1_Demand_Mixer"
    )

    # Add Connector:Splitter objects
    idf.newidfobject("CONNECTOR:SPLITTER",
        Name="SHWSys1_Supply_Splitter",
        Inlet_Branch_Name="SHWSys1_Supply_Inlet_Branch",
        Outlet_Branch_1_Name="SHWSys1_Supply_Equipment_Branch",
        Outlet_Branch_2_Name="SHWSys1_Supply_Equipment_Bypass_Branch"
    )

    

    # Add Connector:Mixer objects
    idf.newidfobject("CONNECTOR:MIXER",
        Name="SHWSys1_Supply_Mixer",
        Outlet_Branch_Name="SHWSys1_Supply_Outlet_Branch",
        Inlet_Branch_1_Name="SHWSys1_Supply_Equipment_Branch",
        Inlet_Branch_2_Name="SHWSys1_Supply_Equipment_Bypass_Branch"
    )

    

    # Add Branch objects
    idf.newidfobject("BRANCH",
        Name="SHWSys1_Supply_Inlet_Branch",
        Component_1_Object_Type="Pump:VariableSpeed",
        Component_1_Name="SHWSys1_Pump",
        Component_1_Inlet_Node_Name="SHWSys1_Supply_Inlet_Node",
        Component_1_Outlet_Node_Name="SHWSys1_Pump_Water_Heater_NodeviaConnector"
    )

    idf.newidfobject("BRANCH",
        Name="SHWSys1_Supply_Equipment_Branch",
        Component_1_Object_Type="WaterHeater:Mixed",
        Component_1_Name="SHWSys1_Water_Heater",
        Component_1_Inlet_Node_Name="SHWSys1_Pump_Water_Heater_Node",
        Component_1_Outlet_Node_Name="SHWSys1_Supply_Equipment_Outlet_Node"
    )

    idf.newidfobject("BRANCH",
        Name="SHWSys1_Supply_Equipment_Bypass_Branch",
        Component_1_Object_Type="Pipe:Adiabatic",
        Component_1_Name="SHWSys1_Supply_Equipment_Bypass_Pipe",
        Component_1_Inlet_Node_Name="SHWSys1_Supply_Equip_Bypass_Inlet_Node",
        Component_1_Outlet_Node_Name="SHWSys1_Supply_Equip_Bypass_Outlet_Node"
    )

    idf.newidfobject("PIPE:ADIABATIC",
        Name="SHWSys1_Supply_Equipment_Bypass_Pipe",
        Inlet_Node_Name="SHWSys1_Supply_Equip_Bypass_Inlet_Node",
        Outlet_Node_Name="SHWSys1_Supply_Equip_Bypass_Outlet_Node"
    )

    idf.newidfobject("BRANCH",
        Name="SHWSys1_Supply_Outlet_Branch",
        Component_1_Object_Type="Pipe:Adiabatic",
        Component_1_Name="SHWSys1_Supply_Outlet_Pipe",
        Component_1_Inlet_Node_Name="SHWSys1_Supply_Mixer_Outlet_Pipe",
        Component_1_Outlet_Node_Name="SHWSys1_Supply_Outlet_Node"
    )

    idf.newidfobject("PIPE:ADIABATIC",
        Name="SHWSys1_Supply_Outlet_Pipe",
        Inlet_Node_Name="SHWSys1_Supply_Mixer_Outlet_Pipe",
        Outlet_Node_Name="SHWSys1_Supply_Outlet_Node"
    )

    idf.newidfobject("BRANCH",
        Name="SHWSys1_Demand_Inlet_Branch",
        Component_1_Object_Type="Pipe:Adiabatic",
        Component_1_Name="SHWSys1_Demand_Inlet_Pipe",
        Component_1_Inlet_Node_Name="SHWSys1_Demand_Inlet_Node",
        Component_1_Outlet_Node_Name="SHWSys1_Demand_Inlet_Pipe_Mixer_Node"
    )

    idf.newidfobject("PIPE:ADIABATIC",
        Name="SHWSys1_Demand_Inlet_Pipe",
        Inlet_Node_Name="SHWSys1_Demand_Inlet_Node",
        Outlet_Node_Name="SHWSys1_Demand_Inlet_Pipe_Mixer_Node"
    )

    idf.newidfobject("BRANCH",
        Name="SHWSys1_Demand_Bypass_Branch",
        Component_1_Object_Type="Pipe:Adiabatic",
        Component_1_Name="SHWSys1_Demand_Bypass_Pipe",
        Component_1_Inlet_Node_Name="SHWSys1_Demand_Bypass_Pipe_Inlet_Node",
        Component_1_Outlet_Node_Name="SHWSys1_Demand_Bypass_Pipe_Outlet_Node"
    )

    idf.newidfobject("PIPE:ADIABATIC",
        Name="SHWSys1_Demand_Bypass_Pipe",
        Inlet_Node_Name="SHWSys1_Demand_Bypass_Pipe_Inlet_Node",
        Outlet_Node_Name="SHWSys1_Demand_Bypass_Pipe_Outlet_Node"
    )

    idf.newidfobject("BRANCH",
        Name="SHWSys1_Demand_Outlet_Branch",
        Component_1_Object_Type="Pipe:Adiabatic",
        Component_1_Name="SHWSys1_Demand_Outlet_Pipe",
        Component_1_Inlet_Node_Name="SHWSys1_Demand_Mixer_Outlet_Pipe",
        Component_1_Outlet_Node_Name="SHWSys1_Demand_Outlet_Node"
    )

    idf.newidfobject("PIPE:ADIABATIC",
        Name="SHWSys1_Demand_Outlet_Pipe",
        Inlet_Node_Name="SHWSys1_Demand_Mixer_Outlet_Pipe",
        Outlet_Node_Name="SHWSys1_Demand_Outlet_Node"
    )


    demand_branches = []
    # Define WaterUse:Connections and WaterUse:Equipment objects for each zone
    for i, zone in enumerate(idf.idfobjects['ZONE']):
        # Unique identifiers for each zone's components
        water_use_connections_name = f"{zone.Name}_WaterUse_Connections"
        water_use_equipment_name = f"{zone.Name}_WaterUse_Equipment"
        branch_name = f"SHWSys1_Demand_Load_Branch_{i+1}"

        # Define WaterUse:Connections object for each zone
        idf.newidfobject("WATERUSE:CONNECTIONS",
            Name=water_use_connections_name,
            Inlet_Node_Name=f"{zone.Name}_Water_Inlet_Node",
            Outlet_Node_Name=f"{zone.Name}_Water_Outlet_Node",
            Water_Use_Equipment_1_Name=water_use_equipment_name
        )

        # Define WaterUse:Equipment object for each zone
        idf.newidfobject("WATERUSE:EQUIPMENT",
            Name=water_use_equipment_name,
            EndUse_Subcategory="SHW_Default",
            Peak_Flow_Rate=2.77777777777778E-6,
            Flow_Rate_Fraction_Schedule_Name="BLDG_SWH_SCH",
            Target_Temperature_Schedule_Name="ZN_1_FLR_1_SEC_1SHW_DEFAULT Temp Sched",
            Hot_Water_Supply_Temperature_Schedule_Name="ZN_1_FLR_1_SEC_1SHW_DEFAULTHot Supply Temp Sched",
            Cold_Water_Supply_Temperature_Schedule_Name="",
            Zone_Name=zone.Name,
            Sensible_Fraction_Schedule_Name="ZN_1_FLR_1_SEC_1SHW_DEFAULT Sensible fract sched",
            Latent_Fraction_Schedule_Name="ZN_1_FLR_1_SEC_1SHW_DEFAULT Latent fract sched"
        )

        # Define Branch object for each zone
        idf.newidfobject("BRANCH",
            Name=branch_name,
            Component_1_Object_Type="WaterUse:Connections",
            Component_1_Name=water_use_connections_name,
            Component_1_Inlet_Node_Name=f"{zone.Name}_Water_Inlet_Node",
            Component_1_Outlet_Node_Name=f"{zone.Name}_Water_Outlet_Node"
        )

        # Collect demand branch names
        demand_branches.append(branch_name)
    

    # Prepare the list of branches in the required format for BRANCHLIST
    branch_list_fields = {
        "Branch_1_Name": "SHWSys1_Demand_Inlet_Branch",
        **{f"Branch_{i+2}_Name": name for i, name in enumerate(demand_branches)},
        f"Branch_{len(demand_branches) + 2}_Name": "SHWSys1_Demand_Bypass_Branch",
        f"Branch_{len(demand_branches) + 3}_Name": "SHWSys1_Demand_Outlet_Branch"
    }

    # Add BranchList for demand branches
    idf.newidfobject("BRANCHLIST",
        Name="SHWSys1_Demand_Branches",
        **branch_list_fields
    )

    # Prepare the list of branches in the required format for CONNECTOR:SPLITTER
    splitter_fields = {
        "Inlet_Branch_Name": "SHWSys1_Demand_Inlet_Branch",
        **{f"Outlet_Branch_{i+1}_Name": name for i, name in enumerate(demand_branches)},
        f"Outlet_Branch_{len(demand_branches) + 1}_Name": "SHWSys1_Demand_Bypass_Branch"
    }

    # Add Connector:Splitter for demand branches
    idf.newidfobject("CONNECTOR:SPLITTER",
        Name="SHWSys1_Demand_Splitter",
        **splitter_fields
    )


    # Prepare the list of branches in the required format for CONNECTOR:MIXER
    mixer_fields = {
        "Outlet_Branch_Name": "SHWSys1_Demand_Outlet_Branch",
        **{f"Inlet_Branch_{i+1}_Name": name for i, name in enumerate(demand_branches)},
        f"Inlet_Branch_{len(demand_branches) + 1}_Name": "SHWSys1_Demand_Bypass_Branch"
    }

    # Add Connector:Mixer for demand branches
    idf.newidfobject("CONNECTOR:MIXER",
        Name="SHWSys1_Demand_Mixer",
        **mixer_fields
    )

def add_v2_fan_natural_ventilation(idf):
    # ScheduleTypeLimits for Temperature
    idf.newidfobject(
        "SCHEDULETYPELIMITS",
        Name="Temperature",
        Lower_Limit_Value=-60,  # Adjust these values based on your requirements
        Upper_Limit_Value=200,
        Numeric_Type="Continuous",
        Unit_Type="Temperature"
    )


    idf.newidfobject(
        "SCHEDULE:COMPACT",
        Name="Sliding_Doors_Ventilation_Availability_SCH",
        Schedule_Type_Limits_Name="Fraction",
        Field_1="Through: 12/31",
        Field_2="For: WinterDesignDay",
        Field_3="Until: 24:00,0",
        Field_4="For: SummerDesignDay",
        Field_5="Until: 24:00,0",
        Field_6="For: AllOtherDays",
        Field_7="Until: 6:00,0",
        Field_8="Until: 22:00,1",
        Field_9="Until: 24:00,0"
    )

    idf.newidfobject("SCHEDULE:COMPACT",
                     Name="Zone Control Type Schedule",
                     Schedule_Type_Limits_Name="Any Number",
                     Field_1="Through: 12/31",
                     Field_2="For: AllDays",
                     Field_3="Until: 24:00,4")
    
    # Supply Air Setpoint Schedule
    idf.newidfobject("SCHEDULE:COMPACT",
                     Name="Supply Air Setpoint Schedule",
                     Schedule_Type_Limits_Name="Temperature",
                     Field_1="Through: 12/31",
                     Field_2="For: AllDays",
                     Field_3="Until: 24:00,14.0")  # Ensure this is realistic and matches your cooling setpoint

    # Always On Schedule
    idf.newidfobject("SCHEDULE:COMPACT",
                     Name="Always On",
                     Schedule_Type_Limits_Name="Any Number",
                     Field_1="Through: 12/31",
                     Field_2="For: AllDays",
                     Field_3="Until: 24:00,1")

    # Night Ventilation Schedule
    idf.newidfobject("SCHEDULE:COMPACT",
                     Name="NightVentSched",
                     Schedule_Type_Limits_Name="Fraction",
                     Field_1="Through: 12/31",
                     Field_2="For: AllDays",
                     Field_3="Until: 6:00,1",
                     Field_4="Until: 22:00,0",
                     Field_5="Until: 24:00,1")

    current_floor = 0

    for zone in idf.idfobjects['ZONE']:
        # Define unique names for each component based on the zone name
        base_name = zone.Name #.replace(" ", "_")
        
        outdoor_air_mixer_name = f"{base_name}_OutdoorAirMixer"
        mixed_air_node_name = f"{base_name}_MixedAirNode"
        outdoor_air_stream_node_name = f"{base_name}_OutdoorAirStreamNode"
        return_air_node_name = f"{base_name}_ReturnAirNode"
        zone_exhaust_node_name = f"{base_name}_ExhaustNode"
        ptac_name = f"{base_name}_PTAC"
        zone_supply_air_node_name = f"{base_name}_SupplyAirNode"
        fan_name = f"{base_name}_VariableSpeedFan"
        coil_nameh = f"{base_name}_MultiStageGasHeatingCoil"
        equipment_list_name = f"{zone.Name} Eq"
        coil_name = f"{base_name}_DXCoolingCoil"
        supply_air_node_list_name = f"{zone.Name} In Nodes"
        air_outlet_node_name = f"{base_name}_CoolingCoilAirOutletNode"
        air_inlet_node_nameh = f"{base_name}_HeatingCoilAirInletNode"
        relief_air_stream_node_name = f"{base_name}_ReliefAirStreamNode"
        zone_air_node_name = f"{zone.Name} Node"
        zone_return_air_node_name = f"{zone.Name} Out Node"
        air_loop_name = f"{base_name}_AirLoopHVAC"
        air_terminal_name = f"{base_name}_AirTerminal"
        thermostat_name = f"{base_name}_Thermostat"
        thermostat_control_name = f"{base_name}_ThermostatControl"
        exhaust_air_node_list_name = f"{base_name}_ExhaustAirNodeList"
        exhaust_fan_name = f"{base_name}_ExhaustFan"

        # Define the OutdoorAir:Mixer
        idf.newidfobject("OUTDOORAIR:MIXER",
                         Name=outdoor_air_mixer_name,
                         Mixed_Air_Node_Name=mixed_air_node_name,
                         Outdoor_Air_Stream_Node_Name=outdoor_air_stream_node_name,
                         Relief_Air_Stream_Node_Name=relief_air_stream_node_name,
                         Return_Air_Stream_Node_Name=return_air_node_name)

        # OutdoorAir:Node - Defines the conditions of the outdoor air entering the mixer
        idf.newidfobject("OUTDOORAIR:NODE",
                         Name=outdoor_air_stream_node_name,
                         Height_Above_Ground=current_floor + 2)
        current_floor += 3

        # Define Zone HVAC Equipment List
        #idf.newidfobject("ZONEHVAC:EQUIPMENTLIST",
        #                 Name=equipment_list_name,
        #                 Zone_Equipment_1_Object_Type="FAN:ZONEEXHAUST",
        #                 Zone_Equipment_1_Name=exhaust_fan_name,
        #                 Zone_Equipment_1_Cooling_Sequence=1,
        #                 Zone_Equipment_1_Heating_or_NoLoad_Sequence=1)

        # Define Zone HVAC Equipment Connections
        idf.newidfobject("ZONEHVAC:EQUIPMENTCONNECTIONS",
                         Zone_Name=zone.Name,
                         Zone_Conditioning_Equipment_List_Name=equipment_list_name,
                         Zone_Air_Inlet_Node_or_NodeList_Name=supply_air_node_list_name,
                         Zone_Air_Exhaust_Node_or_NodeList_Name=zone_exhaust_node_name,
                         Zone_Air_Node_Name=zone_air_node_name,
                         Zone_Return_Air_Node_or_NodeList_Name=zone_return_air_node_name)

        # NodeList for Supply Air Nodes (if you have multiple supply air inlets to a zone)
        idf.newidfobject("NODELIST",
                         Name=supply_air_node_list_name,
                         Node_1_Name=zone_supply_air_node_name)

        # NodeList for Exhaust Air Nodes (if you have multiple exhaust nodes from a zone)
        idf.newidfobject("NODELIST",
                         Name=zone_exhaust_node_name,
                         Node_1_Name=return_air_node_name)

        # Fan:ZoneExhaust for mechanical exhaust
        idf.newidfobject("FAN:ZONEEXHAUST",
                         Name=exhaust_fan_name,
                         Availability_Schedule_Name="Always On",
                         Fan_Total_Efficiency=0.7,
                         Pressure_Rise=200,
                         Maximum_Flow_Rate=0.05,
                         Air_Inlet_Node_Name=return_air_node_name,
                         Air_Outlet_Node_Name=zone_supply_air_node_name)

        # Thermostat Setpoint Dual Setpoint
        idf.newidfobject("THERMOSTATSETPOINT:DUALSETPOINT",
                         Name=thermostat_name,
                         Cooling_Setpoint_Temperature_Schedule_Name="Cooling Return Air Setpoint Schedule",
                         Heating_Setpoint_Temperature_Schedule_Name="Heating Setpoint Schedule")

        # Zone Control Thermostat
        idf.newidfobject("ZONECONTROL:THERMOSTAT",
                         Name=thermostat_control_name,
                         Zone_or_ZoneList_Name=zone.Name,
                         Control_Type_Schedule_Name="Zone Control Type Schedule",
                         Control_1_Object_Type="ThermostatSetpoint:DualSetpoint",
                         Control_1_Name=thermostat_name)

        # ZoneVentilation:DesignFlowRate for mechanical exhaust
        idf.newidfobject(
            "ZONEVENTILATION:DESIGNFLOWRATE",
            Name=f"{base_name}_Exhaust_DesignFlowRate",
            Zone_or_ZoneList_or_Space_or_SpaceList_Name=zone.Name,
            Schedule_Name="OccupancySched",
            Design_Flow_Rate_Calculation_Method="Flow/Zone",
            Design_Flow_Rate=0.05295,
            Ventilation_Type="Exhaust",
            Fan_Pressure_Rise=67.0,
            Fan_Total_Efficiency=0.7,
            Constant_Term_Coefficient=1,
            Temperature_Term_Coefficient=0,
            Velocity_Term_Coefficient=0,
            Velocity_Squared_Term_Coefficient=0,
            Minimum_Indoor_Temperature=18,
            Maximum_Indoor_Temperature=100,
            Delta_Temperature=2.0,
            Minimum_Outdoor_Temperature=-100,
            Maximum_Outdoor_Temperature=100,
            Maximum_Wind_Speed=40
        )

        # ZoneVentilation:DesignFlowRate for natural intake
        idf.newidfobject(
            "ZONEVENTILATION:DESIGNFLOWRATE",
            Name=f"{base_name}_NaturalIntake_DesignFlowRate",
            Zone_or_ZoneList_or_Space_or_SpaceList_Name=zone.Name,
            Schedule_Name="NightVentSched",
            Design_Flow_Rate_Calculation_Method="Flow/Zone",
            Design_Flow_Rate=0.05295,
            Ventilation_Type="Natural",
            Fan_Pressure_Rise=0.0,  # Not applicable for Natural
            Fan_Total_Efficiency=0.50,  # Not applicable for Natural
            Constant_Term_Coefficient=1,
            Temperature_Term_Coefficient=0,
            Velocity_Term_Coefficient=0,
            Velocity_Squared_Term_Coefficient=0,
            Minimum_Indoor_Temperature=18,
            Maximum_Indoor_Temperature=100,
            Delta_Temperature=2.0,
            Minimum_Outdoor_Temperature=-100,
            Maximum_Outdoor_Temperature=100,
            Maximum_Wind_Speed=40
        )

        # Define parameters for the ventilation objects
        opening_area = 0.0374
        height_difference = 6.0957
        min_indoor_temp = 18.89
        max_indoor_temp = 25.56
        delta_temp = -100
        min_outdoor_temp = 15.56
        max_outdoor_temp = 26.67
        max_wind_speed = 40

        # Effective angles for different orientations
        orientations = {
            "North": 0,
            "East": 90,
            "South": 180,
            "West": 270
        }

        for direction, angle in orientations.items():
            idf.newidfobject(
                "ZONEVENTILATION:WINDANDSTACKOPENAREA",
                Name=f"{base_name}_{direction}_Ventilation",
                Zone_or_Space_Name=zone.Name,
                Opening_Area=opening_area,
                Opening_Area_Fraction_Schedule_Name="Sliding_Doors_Ventilation_Availability_SCH",
                Opening_Effectiveness="autocalculate",
                Effective_Angle=angle,
                Height_Difference=height_difference,
                Discharge_Coefficient_for_Opening="autocalculate",
                Minimum_Indoor_Temperature=min_indoor_temp,
                Minimum_Indoor_Temperature_Schedule_Name="",
                Maximum_Indoor_Temperature=max_indoor_temp,
                Maximum_Indoor_Temperature_Schedule_Name="",
                Delta_Temperature=delta_temp,
                Delta_Temperature_Schedule_Name="",
                Minimum_Outdoor_Temperature=min_outdoor_temp,
                Minimum_Outdoor_Temperature_Schedule_Name="",
                Maximum_Outdoor_Temperature=max_outdoor_temp,
                Maximum_Outdoor_Temperature_Schedule_Name="",
                Maximum_Wind_Speed=max_wind_speed
            )

def add_H21_RadiantConvective_heating(idf):

    # ===================================
    idf.newidfobject("SETPOINTMANAGER:SCHEDULED",
        Name="Hot Water Loop Setpoint Manager",
        Control_Variable="Temperature",
        Schedule_Name="SHWSys1_Loop_Temp_Schedule",
        Setpoint_Node_or_NodeList_Name="Hot Water Loop Setpoint Node List"
    )


    idf.newidfobject("CURVE:QUADRATIC",
        Name="BoilerEfficiency",
        Coefficient1_Constant=1.0,
        Coefficient2_x=0.0,
        Coefficient3_x2=0.0,
        Minimum_Value_of_x=0,
        Maximum_Value_of_x=1
    )
    
    idf.newidfobject("NODELIST",
        Name="Hot Water Loop Setpoint Node List",
        Node_1_Name="HW Supply Outlet Node"
    )

    idf.newidfobject("BRANCHLIST",
        Name="Heating Supply Side Branches",
        Branch_1_Name="Heating Supply Inlet Branch",
        Branch_2_Name="Central Boiler Branch",
        Branch_3_Name="Heating Supply Bypass Branch",
        Branch_4_Name="Heating Supply Outlet Branch"
    )

    idf.newidfobject("BRANCH",
        Name="Heating Supply Inlet Branch",
        Component_1_Object_Type="Pump:VariableSpeed",
        Component_1_Name="HW Circ Pump",
        Component_1_Inlet_Node_Name="HW Supply Inlet Node",
        Component_1_Outlet_Node_Name="HW Pump Outlet Node"
    )

    idf.newidfobject("PUMP:VARIABLESPEED",
        Name="HW Circ Pump",
        Inlet_Node_Name="HW Supply Inlet Node",
        Outlet_Node_Name="HW Pump Outlet Node",
        Pump_Control_Type="INTERMITTENT"
    )

    idf.newidfobject("BRANCH",
        Name="Central Boiler Branch",
        Component_1_Object_Type="Boiler:HotWater",
        Component_1_Name="Central Boiler",
        Component_1_Inlet_Node_Name="Central Boiler Inlet Node",
        Component_1_Outlet_Node_Name="Central Boiler Outlet Node"
    )

    idf.newidfobject("BRANCH",
        Name="Heating Supply Bypass Branch",
        Component_1_Object_Type="Pipe:Adiabatic",
        Component_1_Name="Heating Supply Side Bypass",
        Component_1_Inlet_Node_Name="Heating Supply Bypass Inlet Node",
        Component_1_Outlet_Node_Name="Heating Supply Bypass Outlet Node"
    )

    idf.newidfobject("PIPE:ADIABATIC",
        Name="Heating Supply Side Bypass",
        Inlet_Node_Name="Heating Supply Bypass Inlet Node",
        Outlet_Node_Name="Heating Supply Bypass Outlet Node"
    )

    idf.newidfobject("BRANCH",
        Name="Heating Supply Outlet Branch",
        Component_1_Object_Type="Pipe:Adiabatic",
        Component_1_Name="Heating Supply Outlet",
        Component_1_Inlet_Node_Name="Heating Supply Exit Pipe Inlet Node",
        Component_1_Outlet_Node_Name="HW Supply Outlet Node"
    )

    idf.newidfobject("PIPE:ADIABATIC",
        Name="Heating Supply Outlet",
        Inlet_Node_Name="Heating Supply Exit Pipe Inlet Node",
        Outlet_Node_Name="HW Supply Outlet Node"
    )

    idf.newidfobject("CONNECTOR:SPLITTER",
        Name="Heating Supply Splitter",
        Inlet_Branch_Name="Heating Supply Inlet Branch",
        Outlet_Branch_1_Name="Central Boiler Branch",
        Outlet_Branch_2_Name="Heating Supply Bypass Branch"
    )

    idf.newidfobject("CONNECTOR:MIXER",
        Name="Heating Supply Mixer",
        Outlet_Branch_Name="Heating Supply Outlet Branch",
        Inlet_Branch_1_Name="Central Boiler Branch",
        Inlet_Branch_2_Name="Heating Supply Bypass Branch"
    )

    idf.newidfobject("CONNECTORLIST",
        Name="Heating Supply Side Connectors",
        Connector_1_Object_Type="Connector:Splitter",
        Connector_1_Name="Heating Supply Splitter",
        Connector_2_Object_Type="Connector:Mixer",
        Connector_2_Name="Heating Supply Mixer"
    )

    idf.newidfobject("PLANTEQUIPMENTLIST",
        Name="heating plant",
        Equipment_1_Object_Type="Boiler:HotWater",
        Equipment_1_Name="Central Boiler"
    )

    idf.newidfobject("PLANTEQUIPMENTOPERATIONSCHEMES",
        Name="Hot Loop Operation",
        Control_Scheme_1_Object_Type="PlantEquipmentOperation:HeatingLoad",
        Control_Scheme_1_Name="Central Boiler Only",
        Control_Scheme_1_Schedule_Name="PlantOnSched"
    )    

    # ===================================
    # Adding global objects
    idf.newidfobject("PLANTLOOP",
        Name="Hot Water Loop",
        Fluid_Type="Water",
        Plant_Equipment_Operation_Scheme_Name="Hot Loop Operation",
        Loop_Temperature_Setpoint_Node_Name="HW Supply Outlet Node",
        Plant_Side_Inlet_Node_Name="HW Supply Inlet Node",
        Plant_Side_Outlet_Node_Name="HW Supply Outlet Node",
        Plant_Side_Branch_List_Name="Heating Supply Side Branches",
        Plant_Side_Connector_List_Name="Heating Supply Side Connectors",
        Demand_Side_Inlet_Node_Name="HW Demand Inlet Node",
        Demand_Side_Outlet_Node_Name="HW Demand Outlet Node",
        Demand_Side_Branch_List_Name="Heating Demand Side Branches",
        Demand_Side_Connector_List_Name="Heating Demand Side Connectors",
        Load_Distribution_Scheme="SequentialLoad",
        Maximum_Loop_Flow_Rate="autosize",  # or a specific value, e.g., 0.1
        Maximum_Loop_Temperature=100,       # or a specific value as required
        Minimum_Loop_Temperature=5
    )

    idf.newidfobject("SIZING:PLANT",
        Plant_or_Condenser_Loop_Name="Hot Water Loop",
        Loop_Type="heating",
        Design_Loop_Exit_Temperature=82,
        Loop_Design_Temperature_Difference=11
    )



    idf.newidfobject("BOILER:HOTWATER",
        Name="Central Boiler",
        Fuel_Type="NaturalGas",
        Nominal_Capacity="autosize",
        Nominal_Thermal_Efficiency=0.8,
        Efficiency_Curve_Temperature_Evaluation_Variable="LeavingBoiler",
        Normalized_Boiler_Efficiency_Curve_Name="BoilerEfficiency",
        Design_Water_Flow_Rate="autosize",
        Minimum_Part_Load_Ratio=0.0,
        Maximum_Part_Load_Ratio=1.2,
        Optimum_Part_Load_Ratio=1.0,
        Boiler_Water_Inlet_Node_Name="Central Boiler Inlet Node",
        Boiler_Water_Outlet_Node_Name="Central Boiler Outlet Node",
        Water_Outlet_Upper_Temperature_Limit=100.0,
        Boiler_Flow_Mode="LeavingSetpointModulated"
    )



    idf.newidfobject("PLANTEQUIPMENTOPERATION:HEATINGLOAD",
        Name="Central Boiler Only",
        Load_Range_1_Lower_Limit=0,
        Load_Range_1_Upper_Limit=1000000,
        Range_1_Equipment_List_Name="heating plant"
    )


    idf.newidfobject(
        "ZONEHVAC:BASEBOARD:RADIANTCONVECTIVE:WATER:DESIGN",
        Name="Baseboard Design",                               # Name
        Heating_Design_Capacity_Method="HeatingDesignCapacity", # Heating Design Capacity Method
        Heating_Design_Capacity_Per_Floor_Area="",              # Heating Design Capacity Per Floor Area {W/m2}
        Fraction_of_Autosized_Heating_Design_Capacity="",       # Fraction of Autosized Heating Design Capacity
        Convergence_Tolerance=0.001,                            # Convergence Tolerance
        Fraction_Radiant=0.3,                                   # Fraction Radiant
        Fraction_of_Radiant_Energy_Incident_on_People=0.03       # Fraction of Radiant Energy Incident on People
    )



    # Define RadiantConvective components for each zone
    surfaces = idf.idfobjects['BUILDINGSURFACE:DETAILED']
    demand_branches = []
    # Define RadiantConvective components for each zone
    for i, zone in enumerate(idf.idfobjects['ZONE']):
        # Unique identifiers for each zone's components
        radiant_name = f"{zone.Name} Baseboard"
        design_name =    "Baseboard Design"
        inlet_node = f"{zone.Name} Zone Coil Water In Node"
        outlet_node = f"{zone.Name} Zone Coil Water Out Node"

        # Assigning two surfaces to each radiant component
        zone_surfaces = [s for s in surfaces if s.Zone_Name == zone.Name][:2]

        idf.newidfobject("ZONEHVAC:BASEBOARD:RADIANTCONVECTIVE:WATER",
            Name=radiant_name,
            Design_Object=design_name,
            Availability_Schedule_Name="Fan Schedule",
            Inlet_Node_Name=inlet_node,
            Outlet_Node_Name=outlet_node,
            Surface_1_Name=zone_surfaces[0].Name if len(zone_surfaces) > 0 else "",
            Surface_2_Name=zone_surfaces[1].Name if len(zone_surfaces) > 1 else "",
            Rated_Average_Water_Temperature=87.78,
            Rated_Water_Mass_Flow_Rate=0.063,
            Heating_Design_Capacity="autosize",
            Maximum_Water_Flow_Rate="autosize",
            Fraction_of_Radiant_Energy_to_Surface_1=0.4
        )
# ===========================================================
        branch_name = f"{zone.Name} Baseboard Branch"

        idf.newidfobject("BRANCH",
            Name=branch_name,
            Component_1_Object_Type="ZoneHVAC:Baseboard:RadiantConvective:Water",
            Component_1_Name=radiant_name,
            Component_1_Inlet_Node_Name=inlet_node,
            Component_1_Outlet_Node_Name=outlet_node
        )

       
            # Create a new ZoneHVAC:EquipmentList
        #idf.newidfobject("ZONEHVAC:EQUIPMENTLIST",
        #        Name=f"{zone.Name} Eq",
        #        Load_Distribution_Scheme="SequentialLoad",
        #        Zone_Equipment_1_Object_Type="ZoneHVAC:Baseboard:RadiantConvective:Water",
        #        Zone_Equipment_1_Name=radiant_name,
        #        Zone_Equipment_1_Cooling_Sequence=1,
        #        Zone_Equipment_1_Heating_or_NoLoad_Sequence=1
        #    )

        # Check if ZoneHVAC:EquipmentConnections already exists for the zone
        existing_equip_connection = None
        for equip_connection in idf.idfobjects['ZONEHVAC:EQUIPMENTCONNECTIONS']:
            if equip_connection.Zone_Name == zone.Name:
                existing_equip_connection = equip_connection
                break

        if not existing_equip_connection:
            # Create a new ZoneHVAC:EquipmentConnections
            idf.newidfobject("ZONEHVAC:EQUIPMENTCONNECTIONS",
                Zone_Name=zone.Name,
                Zone_Conditioning_Equipment_List_Name=f"{zone.Name} Eq",
                Zone_Air_Inlet_Node_or_NodeList_Name=f"{zone.Name} In Nodes",
                Zone_Air_Node_Name=f"{zone.Name} Node",
                Zone_Return_Air_Node_or_NodeList_Name=f"{zone.Name} Out Node"
            )

        # Create NodeList if not exists
        if not any(nodelist.Name == f"{zone.Name} In Nodes" for nodelist in idf.idfobjects['NODELIST']):
            idf.newidfobject("NODELIST",
                Name=f"{zone.Name} In Nodes",
                Node_1_Name=f"{zone.Name} In Node"
            )

        demand_branches.append(branch_name)

    # Define demand side branches and connectors
    branch_list_fields = {
        "Branch_1_Name": "Heating Demand Inlet Branch",
        **{f"Branch_{i+2}_Name": name for i, name in enumerate(demand_branches)},
        f"Branch_{len(demand_branches) + 2}_Name": "Heating Demand Bypass Branch",
        f"Branch_{len(demand_branches) + 3}_Name": "Heating Demand Outlet Branch"
    }

    idf.newidfobject("BRANCHLIST",
        Name="Heating Demand Side Branches",
        **branch_list_fields
    )

    splitter_fields = {
        "Inlet_Branch_Name": "Heating Demand Inlet Branch",
        **{f"Outlet_Branch_{i+1}_Name": name for i, name in enumerate(demand_branches)},
        f"Outlet_Branch_{len(demand_branches) + 1}_Name": "Heating Demand Bypass Branch"
    }

    idf.newidfobject("CONNECTOR:SPLITTER",
        Name="Heating Demand Splitter",
        **splitter_fields
    )

    mixer_fields = {
        "Outlet_Branch_Name": "Heating Demand Outlet Branch",
        **{f"Inlet_Branch_{i+1}_Name": name for i, name in enumerate(demand_branches)},
        f"Inlet_Branch_{len(demand_branches) + 1}_Name": "Heating Demand Bypass Branch"
    }

    idf.newidfobject("CONNECTOR:MIXER",
        Name="Heating Demand Mixer",
        **mixer_fields
    )

    idf.newidfobject("CONNECTORLIST",
        Name="Heating Demand Side Connectors",
        Connector_1_Object_Type="CONNECTOR:SPLITTER",
        Connector_1_Name="Heating Demand Splitter",
        Connector_2_Object_Type="CONNECTOR:MIXER",
        Connector_2_Name="Heating Demand Mixer"
    )

    idf.newidfobject("BRANCH",
        Name="Heating Demand Inlet Branch",
        Component_1_Object_Type="PIPE:ADIABATIC",
        Component_1_Name="Heating Demand Inlet Pipe",
        Component_1_Inlet_Node_Name="HW Demand Inlet Node",
        Component_1_Outlet_Node_Name="HW Demand Entrance Pipe Outlet Node"
    )

    idf.newidfobject("PIPE:ADIABATIC",
        Name="Heating Demand Inlet Pipe",
        Inlet_Node_Name="HW Demand Inlet Node",
        Outlet_Node_Name="HW Demand Entrance Pipe Outlet Node"
    )

    idf.newidfobject("BRANCH",
        Name="Heating Demand Bypass Branch",
        Component_1_Object_Type="PIPE:ADIABATIC",
        Component_1_Name="Heating Demand Bypass",
        Component_1_Inlet_Node_Name="Heating Demand Bypass Inlet Node",
        Component_1_Outlet_Node_Name="Heating Demand Bypass Outlet Node"
    )

    idf.newidfobject("PIPE:ADIABATIC",
        Name="Heating Demand Bypass",
        Inlet_Node_Name="Heating Demand Bypass Inlet Node",
        Outlet_Node_Name="Heating Demand Bypass Outlet Node"
    )

    idf.newidfobject("BRANCH",
        Name="Heating Demand Outlet Branch",
        Component_1_Object_Type="PIPE:ADIABATIC",
        Component_1_Name="Heating Demand Outlet Pipe",
        Component_1_Inlet_Node_Name="HW Demand Exit Pipe Inlet Node",
        Component_1_Outlet_Node_Name="HW Demand Outlet Node"
    )

    idf.newidfobject("PIPE:ADIABATIC",
        Name="Heating Demand Outlet Pipe",
        Inlet_Node_Name="HW Demand Exit Pipe Inlet Node",
        Outlet_Node_Name="HW Demand Outlet Node"
    )

    # Call the function with an IDF object
    # add_RadiantConvective_heating(idf)


def add_H2_RadiantConvective_heating(idf):
    # Setpoint Manager for Hot Water Loop
    idf.newidfobject("SETPOINTMANAGER:SCHEDULED",
        Name="Hot Water Loop Setpoint Manager",
        Control_Variable="Temperature",
        Schedule_Name="SHWSys1_Loop_Temp_Schedule",
        Setpoint_Node_or_NodeList_Name="Hot Water Loop Setpoint Node List"
    )

    # Define Boiler Efficiency Curve
    idf.newidfobject("CURVE:QUADRATIC",
        Name="BoilerEfficiency",
        Coefficient1_Constant=1.0,
        Coefficient2_x=0.0,
        Coefficient3_x2=0.0,
        Minimum_Value_of_x=0,
        Maximum_Value_of_x=1
    )

    # Node List for Setpoint Manager
    idf.newidfobject("NODELIST",
        Name="Hot Water Loop Setpoint Node List",
        Node_1_Name="HW Supply Outlet Node"
    )

    # Define the Supply Side of the Plant Loop
    idf.newidfobject("BRANCHLIST",
        Name="Heating Supply Side Branches",
        Branch_1_Name="Heating Supply Inlet Branch",
        Branch_2_Name="Central Boiler Branch",
        Branch_3_Name="Heating Supply Bypass Branch",
        Branch_4_Name="Heating Supply Outlet Branch"
    )

    idf.newidfobject("BRANCH",
        Name="Heating Supply Inlet Branch",
        Component_1_Object_Type="Pump:VariableSpeed",
        Component_1_Name="HW Circ Pump",
        Component_1_Inlet_Node_Name="HW Supply Inlet Node",
        Component_1_Outlet_Node_Name="HW Pump Outlet Node"
    )

    # Correctly configured pump with non-zero values
    idf.newidfobject("PUMP:VARIABLESPEED",
        Name="HW Circ Pump",
        Inlet_Node_Name="HW Supply Inlet Node",
        Outlet_Node_Name="HW Pump Outlet Node",
        Design_Maximum_Flow_Rate="AUTOSIZE",
        Design_Pump_Head=60000,  # Example value
        Design_Power_Consumption="AUTOSIZE",
        Motor_Efficiency=0.85,  # Set to a realistic value
        Fraction_of_Motor_Inefficiencies_to_Fluid_Stream=0.0,
        Coefficient_1_of_the_Part_Load_Performance_Curve=0.1,  # Example values
        Coefficient_2_of_the_Part_Load_Performance_Curve=0.9,
        Coefficient_3_of_the_Part_Load_Performance_Curve=0,
        Coefficient_4_of_the_Part_Load_Performance_Curve=0,
        Design_Minimum_Flow_Rate=0.001,  # Small positive value
        Pump_Control_Type="INTERMITTENT"
    )

    # Define the Boiler Branch
    idf.newidfobject("BRANCH",
        Name="Central Boiler Branch",
        Component_1_Object_Type="Boiler:HotWater",
        Component_1_Name="Central Boiler",
        Component_1_Inlet_Node_Name="Central Boiler Inlet Node",
        Component_1_Outlet_Node_Name="Central Boiler Outlet Node"
    )

    # Define the Bypass and Outlet Branches
    idf.newidfobject("BRANCH",
        Name="Heating Supply Bypass Branch",
        Component_1_Object_Type="Pipe:Adiabatic",
        Component_1_Name="Heating Supply Side Bypass",
        Component_1_Inlet_Node_Name="Heating Supply Bypass Inlet Node",
        Component_1_Outlet_Node_Name="Heating Supply Bypass Outlet Node"
    )

    idf.newidfobject("PIPE:ADIABATIC",
        Name="Heating Supply Side Bypass",
        Inlet_Node_Name="Heating Supply Bypass Inlet Node",
        Outlet_Node_Name="Heating Supply Bypass Outlet Node"
    )

    idf.newidfobject("BRANCH",
        Name="Heating Supply Outlet Branch",
        Component_1_Object_Type="Pipe:Adiabatic",
        Component_1_Name="Heating Supply Outlet",
        Component_1_Inlet_Node_Name="Heating Supply Exit Pipe Inlet Node",
        Component_1_Outlet_Node_Name="HW Supply Outlet Node"
    )

    idf.newidfobject("PIPE:ADIABATIC",
        Name="Heating Supply Outlet",
        Inlet_Node_Name="Heating Supply Exit Pipe Inlet Node",
        Outlet_Node_Name="HW Supply Outlet Node"
    )

    # Define the Supply Side Splitter and Mixer
    idf.newidfobject("CONNECTOR:SPLITTER",
        Name="Heating Supply Splitter",
        Inlet_Branch_Name="Heating Supply Inlet Branch",
        Outlet_Branch_1_Name="Central Boiler Branch",
        Outlet_Branch_2_Name="Heating Supply Bypass Branch"
    )

    idf.newidfobject("CONNECTOR:MIXER",
        Name="Heating Supply Mixer",
        Outlet_Branch_Name="Heating Supply Outlet Branch",
        Inlet_Branch_1_Name="Central Boiler Branch",
        Inlet_Branch_2_Name="Heating Supply Bypass Branch"
    )

    idf.newidfobject("CONNECTORLIST",
        Name="Heating Supply Side Connectors",
        Connector_1_Object_Type="Connector:Splitter",
        Connector_1_Name="Heating Supply Splitter",
        Connector_2_Object_Type="Connector:Mixer",
        Connector_2_Name="Heating Supply Mixer"
    )

    idf.newidfobject("PLANTEQUIPMENTLIST",
        Name="heating plant",
        Equipment_1_Object_Type="Boiler:HotWater",
        Equipment_1_Name="Central Boiler"
    )

    idf.newidfobject("PLANTEQUIPMENTOPERATIONSCHEMES",
        Name="Hot Loop Operation",
        Control_Scheme_1_Object_Type="PlantEquipmentOperation:HeatingLoad",
        Control_Scheme_1_Name="Central Boiler Only",
        Control_Scheme_1_Schedule_Name="PlantOnSched"
    )

    # Add the Plant Loop
    idf.newidfobject("PLANTLOOP",
        Name="Hot Water Loop",
        Fluid_Type="Water",
        Plant_Equipment_Operation_Scheme_Name="Hot Loop Operation",
        Loop_Temperature_Setpoint_Node_Name="HW Supply Outlet Node",
        Plant_Side_Inlet_Node_Name="HW Supply Inlet Node",
        Plant_Side_Outlet_Node_Name="HW Supply Outlet Node",
        Plant_Side_Branch_List_Name="Heating Supply Side Branches",
        Plant_Side_Connector_List_Name="Heating Supply Side Connectors",
        Demand_Side_Inlet_Node_Name="HW Demand Inlet Node",
        Demand_Side_Outlet_Node_Name="HW Demand Outlet Node",
        Demand_Side_Branch_List_Name="Heating Demand Side Branches",
        Demand_Side_Connector_List_Name="Heating Demand Side Connectors",
        Load_Distribution_Scheme="SequentialLoad",
        Maximum_Loop_Flow_Rate="autosize",
        Maximum_Loop_Temperature=100,
        Minimum_Loop_Temperature=5
    )

    idf.newidfobject("SIZING:PLANT",
        Plant_or_Condenser_Loop_Name="Hot Water Loop",
        Loop_Type="heating",
        Design_Loop_Exit_Temperature=82,
        Loop_Design_Temperature_Difference=11
    )

    # Define the Boiler
    idf.newidfobject("BOILER:HOTWATER",
        Name="Central Boiler",
        Fuel_Type="NaturalGas",
        Nominal_Capacity="autosize",
        Nominal_Thermal_Efficiency=0.8,
        Efficiency_Curve_Temperature_Evaluation_Variable="LeavingBoiler",
        Normalized_Boiler_Efficiency_Curve_Name="BoilerEfficiency",
        Design_Water_Flow_Rate="autosize",
        Minimum_Part_Load_Ratio=0.0,
        Maximum_Part_Load_Ratio=1.2,
        Optimum_Part_Load_Ratio=1.0,
        Boiler_Water_Inlet_Node_Name="Central Boiler Inlet Node",
        Boiler_Water_Outlet_Node_Name="Central Boiler Outlet Node",
        Water_Outlet_Upper_Temperature_Limit=100.0,
        Boiler_Flow_Mode="LeavingSetpointModulated"
    )

    # Define Plant Operation Scheme
    idf.newidfobject("PLANTEQUIPMENTOPERATION:HEATINGLOAD",
        Name="Central Boiler Only",
        Load_Range_1_Lower_Limit=0,
        Load_Range_1_Upper_Limit=1000000,
        Range_1_Equipment_List_Name="heating plant"
    )

    idf.newidfobject(
        "ZONEHVAC:BASEBOARD:RADIANTCONVECTIVE:WATER:DESIGN",
        Name="Baseboard Design",                               # Name
        Heating_Design_Capacity_Method="HeatingDesignCapacity", # Heating Design Capacity Method
        Heating_Design_Capacity_Per_Floor_Area="",              # Heating Design Capacity Per Floor Area {W/m2}
        Fraction_of_Autosized_Heating_Design_Capacity="",       # Fraction of Autosized Heating Design Capacity
        Convergence_Tolerance=0.001,                            # Convergence Tolerance
        Fraction_Radiant=0.3,                                   # Fraction Radiant
        Fraction_of_Radiant_Energy_Incident_on_People=0.03       # Fraction of Radiant Energy Incident on People
    )




    # Radiant Convective Heating Setup
    surfaces = idf.idfobjects['BUILDINGSURFACE:DETAILED']
    demand_branches = []

    for i, zone in enumerate(idf.idfobjects['ZONE']):
        radiant_name = f"{zone.Name} Baseboard"
        design_name = "Baseboard Design"
        inlet_node = f"{zone.Name} Zone Coil Water In Node"
        outlet_node = f"{zone.Name} Zone Coil Water Out Node"

        zone_surfaces = [s for s in surfaces if s.Zone_Name == zone.Name][:2]

        idf.newidfobject("ZONEHVAC:BASEBOARD:RADIANTCONVECTIVE:WATER",
            Name=radiant_name,
            Design_Object=design_name,
            Availability_Schedule_Name="Fan Schedule",
            Inlet_Node_Name=inlet_node,
            Outlet_Node_Name=outlet_node,
            Surface_1_Name=zone_surfaces[0].Name if len(zone_surfaces) > 0 else "",
            Surface_2_Name=zone_surfaces[1].Name if len(zone_surfaces) > 1 else "",
            Rated_Average_Water_Temperature=87.78,
            Rated_Water_Mass_Flow_Rate=0.063,
            Heating_Design_Capacity="autosize",
            Maximum_Water_Flow_Rate="autosize",
            Fraction_of_Radiant_Energy_to_Surface_1=0.4
        )

        branch_name = f"{zone.Name} Baseboard Branch"

        idf.newidfobject("BRANCH",
            Name=branch_name,
            Component_1_Object_Type="ZoneHVAC:Baseboard:RadiantConvective:Water",
            Component_1_Name=radiant_name,
            Component_1_Inlet_Node_Name=inlet_node,
            Component_1_Outlet_Node_Name=outlet_node
        )

        demand_branches.append(branch_name)

    # Define Demand Side Branches and Connectors
    branch_list_fields = {
        "Branch_1_Name": "Heating Demand Inlet Branch",
        **{f"Branch_{i+2}_Name": name for i, name in enumerate(demand_branches)},
        f"Branch_{len(demand_branches) + 2}_Name": "Heating Demand Bypass Branch",
        f"Branch_{len(demand_branches) + 3}_Name": "Heating Demand Outlet Branch"
    }

    idf.newidfobject("BRANCHLIST",
        Name="Heating Demand Side Branches",
        **branch_list_fields
    )

    splitter_fields = {
        "Inlet_Branch_Name": "Heating Demand Inlet Branch",
        **{f"Outlet_Branch_{i+1}_Name": name for i, name in enumerate(demand_branches)},
        f"Outlet_Branch_{len(demand_branches) + 1}_Name": "Heating Demand Bypass Branch"
    }

    idf.newidfobject("CONNECTOR:SPLITTER",
        Name="Heating Demand Splitter",
        **splitter_fields
    )

    mixer_fields = {
        "Outlet_Branch_Name": "Heating Demand Outlet Branch",
        **{f"Inlet_Branch_{i+1}_Name": name for i, name in enumerate(demand_branches)},
        f"Inlet_Branch_{len(demand_branches) + 1}_Name": "Heating Demand Bypass Branch"
    }

    idf.newidfobject("CONNECTOR:MIXER",
        Name="Heating Demand Mixer",
        **mixer_fields
    )

    idf.newidfobject("CONNECTORLIST",
        Name="Heating Demand Side Connectors",
        Connector_1_Object_Type="CONNECTOR:SPLITTER",
        Connector_1_Name="Heating Demand Splitter",
        Connector_2_Object_Type="CONNECTOR:MIXER",
        Connector_2_Name="Heating Demand Mixer"
    )

    # Define Demand Inlet and Outlet Branches
    idf.newidfobject("BRANCH",
        Name="Heating Demand Inlet Branch",
        Component_1_Object_Type="PIPE:ADIABATIC",
        Component_1_Name="Heating Demand Inlet Pipe",
        Component_1_Inlet_Node_Name="HW Demand Inlet Node",
        Component_1_Outlet_Node_Name="HW Demand Entrance Pipe Outlet Node"
    )

    idf.newidfobject("PIPE:ADIABATIC",
        Name="Heating Demand Inlet Pipe",
        Inlet_Node_Name="HW Demand Inlet Node",
        Outlet_Node_Name="HW Demand Entrance Pipe Outlet Node"
    )

    idf.newidfobject("BRANCH",
        Name="Heating Demand Bypass Branch",
        Component_1_Object_Type="PIPE:ADIABATIC",
        Component_1_Name="Heating Demand Bypass",
        Component_1_Inlet_Node_Name="Heating Demand Bypass Inlet Node",
        Component_1_Outlet_Node_Name="Heating Demand Bypass Outlet Node"
    )

    idf.newidfobject("PIPE:ADIABATIC",
        Name="Heating Demand Bypass",
        Inlet_Node_Name="Heating Demand Bypass Inlet Node",
        Outlet_Node_Name="Heating Demand Bypass Outlet Node"
    )

    idf.newidfobject("BRANCH",
        Name="Heating Demand Outlet Branch",
        Component_1_Object_Type="PIPE:ADIABATIC",
        Component_1_Name="Heating Demand Outlet Pipe",
        Component_1_Inlet_Node_Name="HW Demand Exit Pipe Inlet Node",
        Component_1_Outlet_Node_Name="HW Demand Outlet Node"
    )

    idf.newidfobject("PIPE:ADIABATIC",
        Name="Heating Demand Outlet Pipe",
        Inlet_Node_Name="HW Demand Exit Pipe Inlet Node",
        Outlet_Node_Name="HW Demand Outlet Node"
    )





def setup_combined_hvac_equipment_V2_H2_2(idf):
    for zone  in idf.idfobjects['ZONE']:
        equipment_list_name = f"{zone.Name} Eq"
        exhaust_fan_name = f"{zone.Name}_ExhaustFan"
        radiant_name = f"{zone.Name} Baseboard"

        
        idf.newidfobject(
                "ZONEHVAC:EQUIPMENTLIST",
                Name=equipment_list_name,
                Load_Distribution_Scheme="SequentialLoad",
                Zone_Equipment_1_Object_Type="FAN:ZONEEXHAUST",
                Zone_Equipment_1_Name=exhaust_fan_name,
                Zone_Equipment_1_Cooling_Sequence=1,
                Zone_Equipment_1_Heating_or_NoLoad_Sequence=1,
                Zone_Equipment_1_Sequential_Cooling_Fraction_Schedule_Name="",
                Zone_Equipment_1_Sequential_Heating_Fraction_Schedule_Name="",
                Zone_Equipment_2_Object_Type="ZoneHVAC:Baseboard:RadiantConvective:Water",
                Zone_Equipment_2_Name=radiant_name,
                Zone_Equipment_2_Cooling_Sequence=2,
                Zone_Equipment_2_Heating_or_NoLoad_Sequence=2,
                Zone_Equipment_2_Sequential_Cooling_Fraction_Schedule_Name="",
                Zone_Equipment_2_Sequential_Heating_Fraction_Schedule_Name=""
            )




def check_and_add_idfobject(idf):
    # Define a list of objects to add, each with their type and parameters
    objects_to_add = [
        # ("OUTPUT:SURFACES:DRAWING", {}), it has error of geoeppy to do ("OUTPUT:SURFACES:DRAWING", "DXF")
        # ("OUTPUT:SURFACES:LIST", {}), 
        # ("OUTPUT:VARIABLEDICTIONARY", {}),
        # ("OUTPUT:CONSTRUCTIONS", {}),
        ("OUTPUTCONTROL:TABLE:STYLE", {"Column_Separator": "HTML"}),
        ("OUTPUT:TABLE:MONTHLY", {
            "Name": "Building Loads - Heating",
            "Digits_After_Decimal": 2,
            "Variable_or_Meter_1_Name": "Zone Air System Sensible Heating Energy",
            "Aggregation_Type_for_Variable_or_Meter_1": "SumOrAverage",
            "Variable_or_Meter_2_Name": "Zone Air System Sensible Heating Rate",
            "Aggregation_Type_for_Variable_or_Meter_2": "Maximum",
            "Variable_or_Meter_3_Name": "Site Outdoor Air Drybulb Temperature",
            "Aggregation_Type_for_Variable_or_Meter_3": "ValueWhenMaximumOrMinimum"
        }),
        ("OUTPUT:TABLE:MONTHLY", {
            "Name": "Building Loads - Cooling",
            "Digits_After_Decimal": 2,
            "Variable_or_Meter_1_Name": "Zone Air System Sensible Cooling Energy",
            "Aggregation_Type_for_Variable_or_Meter_1": "SumOrAverage",
            "Variable_or_Meter_2_Name": "Zone Air System Sensible Cooling Rate",
            "Aggregation_Type_for_Variable_or_Meter_2": "Maximum",
            "Variable_or_Meter_3_Name": "Site Outdoor Air Drybulb Temperature",
            "Aggregation_Type_for_Variable_or_Meter_3": "ValueWhenMaximumOrMinimum"
        }),

        ("OUTPUT:METER", {"Key_Name": "Fans:Electricity", "Reporting_Frequency": "timestep"}),
        
        # Electrical Generation and Storage
        #("OUTPUT:METER", {"Key_Name": "Photovoltaic:Electricity", "Reporting_Frequency": "timestep"}),
        #("OUTPUT:METER", {"Key_Name": "WindTurbine:Electricity", "Reporting_Frequency": "timestep"}),
        ("OUTPUT:METER", {"Key_Name": "Gas:Facility", "Reporting_Frequency": "timestep"}),
        
        # Electricity Meters for Whole Building and Sub-Metering
        ("OUTPUT:METER", {"Key_Name": "Electricity:Facility", "Reporting_Frequency": "timestep"}),
        ("OUTPUT:METER", {"Key_Name": "Electricity:Building", "Reporting_Frequency": "timestep"}),
       # ("OUTPUT:METER", {"Key_Name": "Electricity:HVAC", "Reporting_Frequency": "timestep"}),
       # ("OUTPUT:METER", {"Key_Name": "InteriorLights:Electricity", "Reporting_Frequency": "timestep"}),
      #  ("OUTPUT:METER", {"Key_Name": "ExteriorLights:Electricity", "Reporting_Frequency": "timestep"}),
      #  ("OUTPUT:METER", {"Key_Name": "Pumps:Electricity", "Reporting_Frequency": "timestep"}),
        
        # Specific Output Variables and Meters
        ("OUTPUT:METER", {"Key_Name": "Electricity:*", "Reporting_Frequency": "timestep"}),
        


        # Summary Reports
        ("OUTPUT:TABLE:SUMMARYREPORTS", {"Report_1_Name": "AllSummary"}),

        # Additional specific meters
       # ("OUTPUT:METER", {"Key_Name": "Heating:Electricity", "Reporting_Frequency": "timestep"}),
      #  ("OUTPUT:METER", {"Key_Name": "Electricity:Building", "Reporting_Frequency": "timestep"}),


        #("OUTPUT:METER", {"Key_Name": "Gas:Building", "Reporting_Frequency": "timestep"}),
        #("OUTPUT:METER", {"Key_Name": "Gas:Facility", "Reporting_Frequency": "timestep"}),


    ]
    
    
    for object_type, parameters in objects_to_add:
        # Special handling for OUTPUT:METER to consider Key_Name
        if object_type == "OUTPUT:METER":
            key_name = parameters.get("Key_Name")
            existing_objects = [obj for obj in idf.idfobjects[object_type.upper()] if obj.Key_Name == key_name]
            for obj in existing_objects:
                idf.removeidfobject(obj)
        else:
            # Check for existing objects of this type and remove them
            existing_objects = idf.idfobjects[object_type.upper()]
            for obj in existing_objects:
                idf.removeidfobject(obj)
        
        # Add the new object with the specified parameters
        idf.newidfobject(object_type, **parameters)

