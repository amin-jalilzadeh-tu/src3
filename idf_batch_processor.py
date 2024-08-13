from geomeppy import IDF
import os
import pandas as pd
import psycopg2
import numpy as np
import shutil
import subprocess
from config import get_conn_params, get_idf_config
from concurrent.futures import ThreadPoolExecutor

# Use centralized configurations
config = get_idf_config()
conn_params = get_conn_params()

# Database connection and building data fetching
def fetch_buildings_data(table_name, conn_params):
    conn = psycopg2.connect(conn_params)
    query = f"SELECT * FROM {table_name};"
    buildings_df = pd.read_sql_query(query, conn)
    conn.close()
    return buildings_df

IDF.setiddname(config['iddfile'])
idf = IDF(config['idf_file_path'])

# Directory setup
if not os.path.exists(config['output_dir']):
    os.makedirs(config['output_dir'])

# Define a function to remove existing building objects from the IDF
def remove_building_object(idf):
    """Remove all 'Building' objects in the given IDF to prevent conflicts."""
    building_objects = idf.idfobjects['BUILDING']
    for building in building_objects:
        idf.removeidfobject(building)

# Execute the function to clean up the IDF file
remove_building_object(idf)

# Save changes to the IDF file
idf.save()

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
    idf.newidfobject("BUILDING", Name="New Building Block", North_Axis=orientation)
    idf.add_block(name='BuildingBlock1', coordinates=coordinates, height=facade_height, num_stories=num_stories)

## Construction Materials


def update_construction_materials(idf, building_row):
    # Step 1: Reset existing materials and constructions
    for obj_type in ['MATERIAL', 'MATERIAL:NOMASS', 'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM', 'CONSTRUCTION']:
        objs = idf.idfobjects[obj_type]
        for obj in objs:
            idf.removeidfobject(obj)

    # Step 2: Define new materials
    # Ground floor - Changing to MATERIAL for thermal mass
    idf.newidfobject('MATERIAL', Name='Groundfloor1', 
                     Roughness='MediumRough',
                     Thickness=0.15,  
                     Conductivity=1.4,  
                     Density=2300,  
                     Specific_Heat=1000)  

    # External walls - Changing to MATERIAL for thermal mass
    idf.newidfobject('MATERIAL', Name='Ext_Walls1', 
                     Roughness='MediumRough',
                     Thickness=0.2,  # Adjust thickness based on your design
                     Conductivity=1.4,  # Concrete, adjust accordingly
                     Density=2300,  # Concrete, adjust accordingly
                     Specific_Heat=1000)  # Concrete, adjust accordingly

    # Roof - Keeping as MATERIAL:NOMASS for simplicity
    idf.newidfobject('MATERIAL:NOMASS', Name='Roof1', 
                     Thermal_Resistance=building_row['flat_pitched_roof_rc'],
                     Roughness='MediumRough')

    # Windows (using a simple glazing system for example)
    idf.newidfobject("WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM", 
                     Name='Windowglass', 
                     UFactor=building_row['glazing_u_value'], 
                     Solar_Heat_Gain_Coefficient=0.7)

    # Internal Walls - Keeping as MATERIAL:NOMASS for simplicity
    idf.newidfobject('MATERIAL:NOMASS', Name='Int_Walls1', 
                     Thermal_Resistance=building_row.get('int_wall_rc', 0.2), 
                     Roughness='MediumRough')

    # Internal Floors/Ceilings - Keeping as MATERIAL:NOMASS for simplicity
    idf.newidfobject('MATERIAL:NOMASS', Name='Int_Floors1', 
                     Thermal_Resistance=building_row.get('int_floor_rc', 0.2), 
                     Roughness='MediumRough')
    

    # Step 3: Define new constructions
    # Ground floor construction
    idf.newidfobject('CONSTRUCTION', Name='GroundFloor1C', Outside_Layer='Groundfloor1')
    # External walls construction
    idf.newidfobject('CONSTRUCTION', Name='Ext_Walls1C', Outside_Layer='Ext_Walls1')
    # Roof construction
    idf.newidfobject('CONSTRUCTION', Name='Roof1C', Outside_Layer='Roof1')
    # Windows construction
    idf.newidfobject('CONSTRUCTION', Name='Window1C', Outside_Layer='Windowglass')
    # Internal Walls construction
    idf.newidfobject('CONSTRUCTION', Name='Int_Walls1C', Outside_Layer='Int_Walls1')
    # Internal Floors/Ceilings construction
    idf.newidfobject('CONSTRUCTION', Name='Int_Floors1C', Outside_Layer='Int_Floors1')




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
                surface.Construction_Name = 'Ext_Walls1C'
            else:  # It's an internal wall
                surface.Construction_Name = 'Int_Walls1C'
                
        elif surface_type == 'ROOF':
            # Assign construction to roofs
            surface.Construction_Name = 'Roof1C'
            
        elif surface_type == 'FLOOR':
            # Assign construction to floors
            # If the name convention includes "ground" for ground floors, adjust as needed
            if 'ground' in surface.Name.lower():
                surface.Construction_Name = 'GroundFloor1C'
            else:
                surface.Construction_Name = 'Int_Floors1C'  # This is new
            
        elif surface_type == 'CEILING':
            # Assign construction to ceilings
            surface.Construction_Name = 'Int_Floors1C'  # Ceilings use the same construction as internal floors
    


# ### 2.1 Ground Temperature
# Ref: H15 page 673 NTA8800
def add_ground_temperatures(idf):
    # Remove any existing ground temperature objects to avoid duplicates
    existing_ground_temps = idf.idfobjects["SITE:GROUNDTEMPERATURE:BUILDINGSURFACE"]
    for temp in existing_ground_temps:
        idf.removeidfobject(temp)

    # Add new ground temperature object with specified monthly values
    idf.newidfobject(
        "SITE:GROUNDTEMPERATURE:BUILDINGSURFACE",
        January_Ground_Temperature=2.61,
        February_Ground_Temperature=4.82,
        March_Ground_Temperature=5.91,
        April_Ground_Temperature=9.32,
        May_Ground_Temperature=14.73,
        June_Ground_Temperature=16.12,
        July_Ground_Temperature=18.05,
        August_Ground_Temperature=18.48,
        September_Ground_Temperature=15.63,
        October_Ground_Temperature=10.40,
        November_Ground_Temperature=7.99,
        December_Ground_Temperature=4.00,
    )


#  ### 2.2 Internal Mass


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




# ### 2.3 People

# ### Schedule based on the three functions of buildings
# ### 1. People
# ### 2. Activity
# ### 3. Lighting

def add_people_and_activity_schedules(idf, building_row):


    building_function = building_row.get('Function', 'Residential')  # Default to "Woon- en Verblijfsfuncties"  # Checks

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


# It is minimal

def add_people_to_all_zones(idf, building_row):

    # Define the people schedule
    # Define the occupancy schedule

    # The rest of the function remains unchanged
    facade_height = building_row.get('height', 10)  # Default facade height
    floor_height = building_row.get('floor height', 3)  # Default floor height
    num_stories = int(facade_height / floor_height)
    
    # Assumed or predefined values
    number_of_people_schedule_name = "PeopleSched"  # Assuming it applies to occupancy
    activity_level_schedule_name = "OccupancySched"  # Assuming a generic activity level
    number_of_people = building_row.get('number_of_people', 40) / num_stories  # Assuming a default of 40
    fraction_radiant = 0.3
    sensible_heat_fraction = 0.55  # Assuming a value for the sensible heat fraction


    for zone in idf.idfobjects["ZONE"]:
        # Assuming a simple naming convention for people objects, based on the zone name
        people_name = f"{zone.Name} People 1"
        
        idf.newidfobject("PEOPLE",
                         Name=people_name,
                         Zone_or_ZoneList_or_Space_or_SpaceList_Name=zone.Name,  # The zone the people object applies to
                         Number_of_People_Schedule_Name=number_of_people_schedule_name,
                         Number_of_People_Calculation_Method="people",  # Assuming direct specification   "Area/Person"  "People/Area"
                         Number_of_People=number_of_people,
                         #People_per_Zone_Floor_Area="",  # Left blank as per example
                         #Zone_Floor_Area_per_Person="",  # Left blank as per example
                         Fraction_Radiant=fraction_radiant,
                         Sensible_Heat_Fraction=sensible_heat_fraction,
                         Activity_Level_Schedule_Name=activity_level_schedule_name)



# ### 2.4 Lighting

def add_lights_to_all_zones(idf, building_row):

    # Assumed or predefined values
    schedule_name = "OccupancySched"  # Example, assuming it applies to all zones uniformly
    watts_per_zone_floor_area = 5.52125  # Example value, adjust based on your criteria
    
    # Assuming adjustment_factor needs to be defined or calculated somewhere above this snippet
    adjustment_factor = .9  

    base_values = {
        "Residential": 3,  # Base value for residential areas, in W/m2
        "Commercial": 4,  # Base value for commercial areas, in W/m2
        "Industrial": 5,  # Base value for industrial areas, in W/m2
    }

    # Assuming building_row is a dictionary that includes 'building_type' among its keys
    building_type = building_row.get('assignedclass', "Commercial")

    if building_type in base_values:
        base_value = base_values[building_type]
        watts_per_zone_floor_area = base_value * adjustment_factor
    else:
        # Default value if building type is not specified
        watts_per_zone_floor_area = 5 * adjustment_factor


    # Other lighting properties based on assumptions
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
                         Design_Level_Calculation_Method="Watts/Person", 
                         Watts_per_Zone_Floor_Area=watts_per_zone_floor_area,
                         Watts_per_Person= 1,
                         Fraction_Radiant=fraction_radiant,
                         Fraction_Visible=fraction_visible
                         #End_Use_Subcategory=end_use_subcategory
        )


# ### 2.5 Electric Equipment

def generate_detailed_electric_equipment(idf, building_row):
    # Removed the schedule_name since it's not used in your modifications

    # Default values with updated building_type options and removed season and occupancy profile


    base_values = {
    "Residential": 2,  # Base value for residential areas, in W/m2
    "Commercial": 3,  # Base value for commercial areas, in W/m2
    "Industrial": 4,  # Base value for industrial areas, in W/m2
    }

    building_type = building_row.get('assignedclass', "Commercial")
    zone_area = building_row.get('zone_area', 50)  # Default to 50 m2 if not specified

    # Efficiency adjustment based on energy label
    efficiency_adjustment = {
        "A+": 0.8,
        "A": 0.85,
        "B": 0.9,
        "C": 0.95,
    }.get(building_row.get('energy_label', 'B'), 1)  # Default to "B" if not specified

    # Determine adjustment factor based on zone area
    if zone_area < 50:  # Small zones
        adjustment_factor = 1.1
    elif zone_area < 200:  # Medium zones
        adjustment_factor = 1.0
    else:  # Large zones
        adjustment_factor = 0.9

    # Calculate adjusted power density based on building type, zone area, and energy efficiency
    if building_type in base_values:
        base_value = base_values[building_type]
        adjusted_power_density = base_value * efficiency_adjustment * adjustment_factor
    else:
        # Default value if building type is not specified
        adjusted_power_density = 5 * efficiency_adjustment * adjustment_factor

    # Total design level calculated from the adjusted power density and the zone area
    design_level = adjusted_power_density * zone_area

    # Other electric equipment properties based on assumptions
    fraction_latent = 0.0
    fraction_radiant = 0.3
    fraction_lost = 0.0


    Wats_per_Person = 2
    
    for zone in idf.idfobjects["ZONE"]:
        # Assuming a simple naming convention for lights objects
        electric_eq_name = f"electric_eq_{zone.Name}"
        
    
        idf.newidfobject('ELECTRICEQUIPMENT',
                        Name=electric_eq_name,
                        Zone_or_ZoneList_or_Space_or_SpaceList_Name= zone.Name,
                        Schedule_Name='OccupancySched',  # Assuming this schedule still applies
                        Design_Level_Calculation_Method='Watts/Person',
                        Design_Level=design_level,  # Using the calculated design level
                        Watts_per_Person= 1, #Wats_per_Person,
                        Fraction_Latent=fraction_latent,
                        Fraction_Radiant=fraction_radiant,
                        Fraction_Lost=fraction_lost,
                        # End_Use_Subcategory can be uncommented or adjusted as needed
                        # End_Use_Subcategory='Computers'
                )



# # 3. Sizing

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


# # Hvac

# ### 1. Thermal zones and the overall building layout
# 
# 
# ### 2. Thermostat and Setpoint Definitions
# 
# - **HVACTEMPLATE:THERMOSTAT** and **THERMOSTATSETPOINT:DUALSETPOINT**: These components are essential for controlling the environment within each zone, setting the groundwork for detailed HVAC operation.
# 
# ### 3. Detailed HVAC Components
# 
# With the decision to model a detailed HVAC system, each component needs to be defined explicitly, considering their role in heating, cooling, air distribution, and ventilation.
# 
# - **COIL:HEATING:GAS:MULTISTAGE**: Define this for detailed modeling of the heating system, particularly if you're looking at gas heating options with multiple stages for efficiency and control.
# - **COIL:COOLING:DX:SINGLESPEED**: For the cooling system, detailing the capacity and efficiency of direct expansion cooling equipment.
# - **Boiler:HotWater**: If your system includes hydronic heating, specifying the boiler details is essential for accurate energy modeling.
# 
# ### 4. Air Distribution System
# 
# - **FAN:SYSTEMMODEL**: Given your choice, this model will represent the fan component of your HVAC system, which can be tailored to match specific system characteristics and operational strategies.
# - **AIRLOOPHVAC**: Integrates the various components of the air distribution system, including the fans, coils, and any additional air handling units.
# - **ZONEHVAC:EQUIPMENTLIST**: Organize the HVAC equipment within each zone, ensuring the sequence of operation is defined to meet the zones' heating and cooling demands efficiently.
# 
# ### 5. Ventilation and Air Quality Control
# 
# - **CONTROLLER:OUTDOORAIR** and **CONTROLLER:MECHANICALVENTILATION**: These are critical for ensuring adequate outdoor air intake and mechanical ventilation, maintaining indoor air quality and adhering to health and comfort standards.
# 
# ### 6. Energy Recovery
# 
# - **HEATEXCHANGER:AIRTOAIR:SENSIBLEANDLATENT**: Including an air-to-air heat exchanger can significantly improve system efficiency by recovering energy from exhaust air streams.
# 
# ### 7. Plant Equipment

def add_hvac_schedules(idf, building_row):
          


     building_function = building_row['assignedclass'] #, 'Residential')  # Default to "Woon- en Verblijfsfuncties"  # Checks

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
                 Field_3="Until: 06:00,26.0",  # Higher setpoint during early morning for energy savings
                 Field_4="Until: 08:00,24.0",  # Begin to cool down before occupants arrive
                 Field_5="Until: 18:00,23.0",  # Comfortable setpoint during occupied hours
                 Field_6="Until: 22:00,26.0",  # Increase setpoint after most occupants leave
                 Field_7="Until: 24:00,28.0",  # Higher setpoint during late night for maximum energy savings
                 Field_8="For: Saturday",
                 Field_9="Until: 24:00,28.0",  # Higher setpoint assuming lower occupancy
                 Field_10="For: Sunday",
                 Field_11="Until: 24:00,28.0",  # Same as Saturday
                 Field_12="For: SummerDesignDay",
                 Field_13="Until: 24:00,29.0",  # Lower setpoint to manage higher outdoor temperatures
                 Field_14="For: WinterDesignDay",
                 Field_15="Until: 24:00,26.0",  # Setpoint might be higher if cooling is less of a concern
                 Field_16="For: Holidays",
                 Field_17="Until: 24:00,28.0",  # Assuming building is unoccupied or minimally occupied
                 Field_18="For: AllOtherDays",
                 Field_19="Until: 06:00,26.0",
                 Field_20="Until: 18:00,23.0",
                 Field_21="Until: 22:00,26.0",
                 Field_22="Until: 24:00,28.0"
                                  )  # Adjust for special circumstances, potentially more occupancy or events


          
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
                 Field_3="Until: 06:00,25.0",  # Adjust for minimal operations or maintenance periods
                 Field_4="Until: 07:00,24.0",  # Begin cooling down before first shift starts
                 Field_5="Until: 19:00,22.0",  # Lower setpoint during main operational hours for equipment and process cooling
                 Field_6="Until: 21:00,24.0",  # Begin to increase setpoint as operations wind down
                 Field_7="Until: 24:00,25.0",  # Higher setpoint during off-shift hours for energy savings
                 Field_8="For: Saturday",
                 Field_9="Until: 06:00,26.0",  # Assume limited operations or maintenance
                 Field_10="Until: 18:00,24.0",  # Some operations may continue into the weekend
                 Field_11="Until: 24:00,26.0",  # Higher setpoint assuming reduced activity
                 Field_12="For: Sunday",
                 Field_13="Until: 24:00,27.0",  # Higher setpoint assuming minimal or no operations
                 Field_14="For: SummerDesignDay",
                 Field_15="Until: 24:00,22.0",  # Lower setpoint to accommodate increased cooling needs
                 Field_16="For: WinterDesignDay",
                 Field_17="Until: 24:00,24.0",  # Potential for slightly higher setpoint if cooling demands are lower
                 Field_18="For: Holidays",
                 Field_19="Until: 24:00,27.0",  # Assuming the building is largely unoccupied
                 Field_20="For: AllOtherDays",
                 Field_21="Until: 06:00,25.0",
                 Field_22="Until: 19:00,22.0",
                 Field_23="Until: 24:00,25.0")  # Higher setpoint during maintenance periods for energy efficiency

           
            
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

def add_detailed_Hvac_system_to_zones(idf):   # base sample: 1ZoneDataCenterCRAC_wApproachTemp.idf

    idf.newidfobject(
        "SCHEDULETYPELIMITS",
        Name="Temperature",
        Lower_Limit_Value=-60,  # Adjust these values based on your requirements
        Upper_Limit_Value=200,
        Numeric_Type="Continuous",
        Unit_Type="Temperature"
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
                 Schedule_Type_Limits_Name="Any Number",
                 Field_1="Through: 12/31",
                 Field_2="For: AllDays",
                 Field_3="Until: 24:00,10.0")





    # Define the first curve: Total Cooling Capacity Function of Flow Fraction
    idf.newidfobject("CURVE:QUADRATIC",
                    Name="TotalHPACCoolCapFFF",
                    Coefficient1_Constant=0.8,
                    Coefficient2_x=0.2,
                    Coefficient3_x2=0.0,
                    Minimum_Value_of_x=0.5,
                    Maximum_Value_of_x=1.5)

    # Define the second curve: Part Load Fraction Correlation Curve
    idf.newidfobject("CURVE:QUADRATIC",
                    Name="PartHPACCOOLPLFFPLR",
                    Coefficient1_Constant=0.85,
                    Coefficient2_x=0.15,
                    Coefficient3_x2=0.0,
                    Minimum_Value_of_x=0.0,
                    Maximum_Value_of_x=1.0)

    # Define the third curve: Energy Input Ratio Function of Flow Fraction
    idf.newidfobject("CURVE:QUADRATIC",
                    Name="EnergyHPACCOOLEIRFFF",
                    Coefficient1_Constant=0.85,
                    Coefficient2_x=.1,
                    Coefficient3_x2=0.05,
                    Minimum_Value_of_x=0.5,
                    Maximum_Value_of_x=1.5)




        # Curve:Quadratic for Part Load Fraction Correlation
    idf.newidfobject("CURVE:QUADRATIC",
                    Name="HPACCOOLPLFFPLR 1",
                    Coefficient1_Constant=0.95,
                    Coefficient2_x=0.15,
                    Coefficient3_x2=0.0,
                    Minimum_Value_of_x=0.0,
                    Maximum_Value_of_x=1.0)




    # Curve:Cubic for Energy Input Ratio Function of Flow Fraction
    idf.newidfobject("CURVE:BIQUADRATIC",
                 Name="HPACCOOLEIRFF 2",
                 Coefficient1_Constant=0.85,
                 Coefficient2_x=0.02,
                 Coefficient3_x2=0.0001,
                 Coefficient4_y=-0.003,
                 Coefficient5_y2=0.00001,
                 Coefficient6_xy=-0.0001,
                 Minimum_Value_of_x=17.0,
                 Maximum_Value_of_x=22.0,
                 Minimum_Value_of_y=10.0,
                 Maximum_Value_of_y=25.0,
                 Minimum_Curve_Output=0.7,
                 Maximum_Curve_Output=1.2)

    # Another Curve:Cubic for Cooling Capacity Function of Flow Fraction


    idf.newidfobject("CURVE:BIQUADRATIC",
                 Name="HPACCoolCapFF 3",
                 Coefficient1_Constant=0.93,
                 Coefficient2_x=0.009543347,
                 Coefficient3_x2=0.000683770,
                 Coefficient4_y=-0.011042676,
                 Coefficient5_y2=0.000005249,
                 Coefficient6_xy=-0.000009720,
                 Minimum_Value_of_x=17.0,
                 Maximum_Value_of_x=22.0,
                 Minimum_Value_of_y=10.0,
                 Maximum_Value_of_y=25.0,
                 Minimum_Curve_Output=0.5,
                 Maximum_Curve_Output=1.5)


    idf.newidfobject("CURVE:CUBIC",
                Name="DOAS Heating Coil PLF-FPLR",
                Coefficient1_Constant=0.8,
                Coefficient2_x=0.2,
                Coefficient3_x2=0,
                Coefficient4_x3=0,
                Minimum_Value_of_x=0,
                Maximum_Value_of_x=1)

    current_floor = 0

    for zone in idf.idfobjects['ZONE']:
        # Keep the original unique identifiers for the zone's components
        outdoor_air_mixer_name = f"{zone.Name}_OutdoorAirMixer" # ###
        mixed_air_node_name = f"{zone.Name}_MixedAirNode" # $
        outdoor_air_stream_node_name = f"{zone.Name}_OutdoorAirStreamNode" # $$
        return_air_node_name = f"{zone.Name}_ReturnAirNode"  #
        zone_exhaust_node_name = f"{zone.Name}_ExhaustNode" # $$$
        ptac_name = f"{zone.Name}_PTAC" # +++
        zone_supply_air_node_name = f"{zone.Name}_SupplyAirNode"   ##
        fan_name = f"{zone.Name}_VariableSpeedFan" ####
        coil_nameh = f"{zone.Name}_MultiStageGasHeatingCoil" #####
        equipment_list_name = f"{zone.Name}_EquipmentList" # +
        coil_name = f"{zone.Name}_DXCoolingCoil" ######
        supply_air_node_list_name = f"{zone.Name}_SupplyAirNodeList" # ***
        air_outlet_node_name = f"{zone.Name}_CoolingCoilAirOutletNode" # *
        air_inlet_node_nameh = f"{zone.Name}_HeatingCoilAirInletNode" # +++++

        relief_air_stream_node_name = f"{zone.Name}_ReliefAirStreamNode"
        zone_air_node_name = f"{zone.Name}_ZoneAirNode"
        zone_return_air_node_name = f"{zone.Name}_ReturnAirNodeZZ"


        #################################################
        air_loop_name = f"{zone.Name}_AirLoopHVAC"
        air_terminal_name = f"{zone.Name}_AirTerminal"
        thermostat_name = f"{zone.Name}_Thermostat"
        thermostat_control_name = f"{zone.Name}_ThermostatControl"
        #################################################

        # New Nodes and Lists
        exhaust_air_node_list_name = f"{zone.Name}_ExhaustAirNodeList"

        # Define the OutdoorAir:Mixer
        idf.newidfobject("OUTDOORAIR:MIXER",
                        Name=outdoor_air_mixer_name, ###
                        Mixed_Air_Node_Name=mixed_air_node_name, # $
                        Outdoor_Air_Stream_Node_Name=outdoor_air_stream_node_name, # $$
                        Relief_Air_Stream_Node_Name=relief_air_stream_node_name,
                        Return_Air_Stream_Node_Name=return_air_node_name) # 

        # OutdoorAir:Node - Defines the conditions of the outdoor air entering the mixer

        height_above_ground = current_floor + 2
        idf.newidfobject("OUTDOORAIR:NODE",
                        Name=outdoor_air_stream_node_name, # $$
                        Height_Above_Ground=1)
        current_floor += 3
        
        # Define the PTAC with the updated connection including Outdoor Air Mixer
        idf.newidfobject("ZONEHVAC:PACKAGEDTERMINALAIRCONDITIONER",
                        Name=ptac_name,   # +++
                        Availability_Schedule_Name="Sales Schedule",
                        Cooling_Supply_Air_Flow_Rate="Autosize",
                        Heating_Supply_Air_Flow_Rate="Autosize",
                        No_Load_Supply_Air_Flow_Rate="Autosize",
                        Cooling_Coil_Object_Type="COIL:COOLING:DX:SINGLESPEED",
                        Supply_Air_Fan_Object_Type="FAN:ONOFF",
                        Heating_Coil_Object_Type="COIL:HEATING:FUEL",
                        Cooling_Outdoor_Air_Flow_Rate = "autosize",
                        Heating_Outdoor_Air_Flow_Rate = "autosize",
                        Air_Inlet_Node_Name=return_air_node_name,   # 
                        Air_Outlet_Node_Name=zone_supply_air_node_name, ##
                        Outdoor_Air_Mixer_Object_Type="OutdoorAir:Mixer",
                        Outdoor_Air_Mixer_Name=outdoor_air_mixer_name,###
                        Cooling_Coil_Name=coil_name, ######
                        Supply_Air_Fan_Name=fan_name,  ####
                        Heating_Coil_Name=coil_nameh) #####

        # Define Zone HVAC Equipment List
        idf.newidfobject("ZONEHVAC:EQUIPMENTLIST",
                        Name=equipment_list_name, # +
                        Zone_Equipment_1_Object_Type="ZONEHVAC:PACKAGEDTERMINALAIRCONDITIONER",
                        Zone_Equipment_1_Name=ptac_name, # +++
                        Zone_Equipment_1_Cooling_Sequence=1,
                        Zone_Equipment_1_Heating_or_NoLoad_Sequence=1)





        # Define Zone HVAC Equipment Connections
        idf.newidfobject("ZONEHVAC:EQUIPMENTCONNECTIONS",
                        Zone_Name=zone.Name,
                        Zone_Conditioning_Equipment_List_Name=equipment_list_name, # +
                        Zone_Air_Inlet_Node_or_NodeList_Name=supply_air_node_list_name, # ***
                        Zone_Air_Exhaust_Node_or_NodeList_Name=zone_exhaust_node_name, # $$$
                        Zone_Air_Node_Name=zone_air_node_name,
                        Zone_Return_Air_Node_or_NodeList_Name=zone_return_air_node_name)

        # Additional objects like COIL:HEATING:GAS:MULTISTAGE and COIL:COOLING:DX:SINGLESPEED are defined as you originally described.


        # NodeList for Supply Air Nodes (if you have multiple supply air inlets to a zone)
        idf.newidfobject("NODELIST",
                        Name=supply_air_node_list_name, # ***
                        Node_1_Name=zone_supply_air_node_name) ##

        # NodeList for Exhaust Air Nodes (if you have multiple exhaust nodes from a zone)
        idf.newidfobject("NODELIST",
                        Name=zone_exhaust_node_name,  # $$$
                        Node_1_Name=return_air_node_name) #


        # Variable Speed Fan (On/Off)
        idf.newidfobject("FAN:ONOFF",
                        Name=fan_name,  ####
                        Availability_Schedule_Name="Fan Schedule",
                        Fan_Total_Efficiency=0.7,
                        Pressure_Rise=500,
                        Maximum_Flow_Rate="Autosize",
                        Motor_Efficiency=0.9,
                        Motor_In_Airstream_Fraction=1,
                        Air_Inlet_Node_Name=air_outlet_node_name, # * 
                        Air_Outlet_Node_Name=zone_supply_air_node_name) ##



        
        idf.newidfobject("COIL:HEATING:FUEL",
                Name=coil_nameh, #####,
                Availability_Schedule_Name="FanAndCoilAvailSchedule",  # Leave blank or specify a schedule name
                Fuel_Type="NaturalGas",
                Burner_Efficiency=0.8,
                Nominal_Capacity="autosize",  # EnergyPlus will determine the capacity
                Air_Inlet_Node_Name=air_inlet_node_nameh, # +++++,
                Air_Outlet_Node_Name=air_outlet_node_name, # *
                Temperature_Setpoint_Node_Name=air_outlet_node_name,
                #Parasitic_Electric_Load=0.0,
                Part_Load_Fraction_Correlation_Curve_Name="DOAS Heating Coil PLF-FPLR",
                #Parasitic_Fuel_Load=0
                )


        # DX Cooling Coil
        idf.newidfobject("COIL:COOLING:DX:SINGLESPEED",
                        Name=coil_name, ######
                        Air_Inlet_Node_Name=mixed_air_node_name, # $
                        Air_Outlet_Node_Name=air_inlet_node_nameh,  # +++++
                        Availability_Schedule_Name="System Availability Schedule",
                        Gross_Rated_Total_Cooling_Capacity="Autosize",
                        Gross_Rated_Cooling_COP=3.5,
                        Rated_Air_Flow_Rate="Autosize",
                        Gross_Rated_Sensible_Heat_Ratio=0.75,
                        Total_Cooling_Capacity_Function_of_Temperature_Curve_Name="HPACCoolCapFF 3",
                        Total_Cooling_Capacity_Function_of_Flow_Fraction_Curve_Name="TotalHPACCoolCapFFF",
                        Energy_Input_Ratio_Function_of_Temperature_Curve_Name="HPACCOOLEIRFF 2",
                        Energy_Input_Ratio_Function_of_Flow_Fraction_Curve_Name="EnergyHPACCOOLEIRFFF",
                        Part_Load_Fraction_Correlation_Curve_Name="PartHPACCOOLPLFFPLR")






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

                # Heating coil (Gas Multi-Stage)
        #idf.newidfobject("COIL:HEATING:GAS:MULTISTAGE",
                       # Name=coil_nameh, #####
                       # Air_Inlet_Node_Name=air_inlet_node_nameh, # +++++
                       # Air_Outlet_Node_Name=air_outlet_node_name, # *
                       # Availability_Schedule_Name="FanAndCoilAvailSched",
                       # Number_of_Stages=2,
                       # Stage_1_Gas_Burner_Efficiency=0.92,
                       # Stage_1_Nominal_Capacity="Autosize",
                       # Stage_2_Gas_Burner_Efficiency=0.90,
                       # Stage_2_Nominal_Capacity="Autosize")


            # Air Terminal - Uncontrolled
            #air_terminal = idf.newidfobject("AirTerminal:",
                                            
            
            # Connection of components and zones might require additional steps, including specifying
            # zone equipment lists and air loop connections, which are not fully detailed here.
            


# # Output

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



from geomeppy import IDF

# Load the IDF file 

def update_idf_and_save(buildings_df, output_dir=config['output_dir']):
    base_idf_path = config['idf_file_path']
    idd_path = config['iddfile']
    # Iterate over each row in the DataFrame
    # Define a function to process each building
    def process_building(row):
        idf = IDF(base_idf_path)

        
        # Apply modifications using the refactored functions
        remove_building_object(idf)
        create_building_block(idf, row)
        update_construction_materials(idf, row)
        update_idf_for_fenestration(idf, row)
        assign_constructions_to_surfaces(idf)
        add_ground_temperatures(idf)
        add_internal_mass_to_all_zones_with_first_construction(idf, row)
        add_people_and_activity_schedules(idf, row)
        add_people_to_all_zones(idf, row)
        add_lights_to_all_zones(idf, row)
        generate_detailed_electric_equipment(idf, row)
        add_year_long_run_period(idf)
        add_hvac_schedules(idf, row)
        add_outdoor_air_and_zone_sizing_to_all_zones(idf)
        add_detailed_Hvac_system_to_zones(idf)
        check_and_add_idfobject(idf)
        
     
        
        # Save the modified IDF file with a new name to indicate it's modified
        modified_idf_path = os.path.join(output_dir, f"modified_building_{row['ogc_fid']}.idf")
        print(f"Saving IDF to: {modified_idf_path}")  # This will show the full path being used

        idf.save(modified_idf_path)
        
        print(f"Saved modified IDF for building {row['ogc_fid']}.")


    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all jobs to the executor
        executor.map(process_building, buildings_df.to_dict('records'))
    







# Call the function with the DataFrame, output directory, and the path to the IDD file

# update_idf_and_save(buildings_df, base_idf_path, OUTPUT_DIR, iddfile)














































# # 2. General info 

# ### # design day defined manually in idf file: 
# 

# 
# Site:Location,
#     Amsterdam_Netherlands,    !- Name
#     52.37,                    !- Latitude
#     4.89,                  !- Longitude
#     1,                       !- Time Zone
#     -2;                     !- Elevation
# 
# GlobalGeometryRules,
#     UpperLeftCorner,         !- Starting Vertex Position
#     CounterClockWise,        !- Vertex Entry Direction
#     Relative;                !- Coordinate System
# 
# 
# SizingPeriod:DesignDay,
#     Netherlands Ann Htg 99.6% Condns DB,    !- Name
#     1,                        !- Month
#     21,                       !- Day of Month
#     WinterDesignDay,          !- Day Type
#     -5,                       !- Maximum DryBulb Temperature
#     0,                        !- Daily DryBulb Temperature Range
#     ,                         !- DryBulb Temperature Range Modifier Type
#     ,                         !- DryBulb Temperature Range Modifier Day Schedule Name
#     Wetbulb,                  !- Humidity Condition Type
#     -5,                       !- Wetbulb or DewPoint at Maximum DryBulb
#     ,                         !- Humidity Condition Day Schedule Name
#     ,                         !- Humidity Ratio at Maximum DryBulb
#     ,                         !- Enthalpy at Maximum DryBulb
#     ,                         !- Daily WetBulb Temperature Range
#     102000,                   !- Barometric Pressure
#     4,                        !- Wind Speed
#     270,                      !- Wind Direction
#     No,                       !- Rain Indicator
#     No,                       !- Snow Indicator
#     No,                       !- Daylight Saving Time Indicator
#     ASHRAEClearSky,           !- Solar Model Indicator
#     ,                         !- Beam Solar Day Schedule Name
#     ,                         !- Diffuse Solar Day Schedule Name
#     ,                         !- ASHRAE Clear Sky Optical Depth for Beam Irradiance taub
#     ,                         !- ASHRAE Clear Sky Optical Depth for Diffuse Irradiance taud
#     0;                        !- Sky Clearness
# 
# SizingPeriod:DesignDay,
#     Netherlands Ann Clg 1% Condns DB=>MWB,    !- Name
#     7,                        !- Month
#     21,                       !- Day of Month
#     SummerDesignDay,          !- Day Type
#     28,                       !- Maximum DryBulb Temperature
#     10,                       !- Daily DryBulb Temperature Range
#     ,                         !- DryBulb Temperature Range Modifier Type
#     ,                         !- DryBulb Temperature Range Modifier Day Schedule Name
#     Wetbulb,                  !- Humidity Condition Type
#     17,                       !- Wetbulb or DewPoint at Maximum DryBulb
#     ,                         !- Humidity Condition Day Schedule Name
#     ,                         !- Humidity Ratio at Maximum DryBulb
#     ,                         !- Enthalpy at Maximum DryBulb
#     ,                         !- Daily WetBulb Temperature Range
#     102000,                   !- Barometric Pressure
#     3.5,                      !- Wind Speed
#     90,                       !- Wind Direction
#     No,                       !- Rain Indicator
#     No,                       !- Snow Indicator
#     No,                       !- Daylight Saving Time Indicator
#     ASHRAEClearSky,           !- Solar Model Indicator
#     ,                         !- Beam Solar Day Schedule Name
#     ,                         !- Diffuse Solar Day Schedule Name
#     ,			              !- ASHRAE Clear Sky Optical Depth for Beam Irradiance taub
#     ,        			      !- ASHRAE Clear Sky Optical Depth for Diffuse Irradiance taud
#     1;                        !- Sky Clearness
# 

# For test
#if __name__ == "__main__":
    # Assuming get_conn_params and get_idf_config are correctly defined in config.py
 #   from config import get_conn_params, get_idf_config
 #   conn_params = get_conn_params()
 #   output_dir = get_idf_config()['output_dir']
 #   table_name = "test_pc6"

    # Fetch building data
 #   buildings_df = fetch_buildings_data(table_name, conn_params)
 #   if not buildings_df.empty:
 #       print("Successfully fetched building data:")
 #       print(buildings_df.head())  # Display the first few rows of the DataFrame

    # Run update_idf_and_save
 #   update_idf_and_save(buildings_df, output_dir)
 #   print(f"Check the output directory for modified IDF files: {output_dir}")
