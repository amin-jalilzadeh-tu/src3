import os
import pandas as pd
from eppy.modeleditor import IDF
from multiprocessing import Pool
from config import get_idf_config  # Import configuration function
import logging

def modify_idf_for_detailed_output(idf):
    variables = [
        "Facility Total Electric Demand Power",
        "Facility Total Gas Demand Power",
        "Electricity:Building"
    ]
    for variable in variables:
        idf.newidfobject(
            'OUTPUT:VARIABLE',
            Key_Value='*',
            Variable_Name=variable,
            Reporting_Frequency='timestep'
        )

def make_eplaunch_options(idf, fname):
    filename_without_extension = os.path.splitext(os.path.basename(fname))[0]
    return {
        'output_prefix': filename_without_extension,
        'output_suffix': 'C',
        'output_directory': os.path.dirname(fname),
        'readvars': True,
        'expandobjects': True,
    }

def run_simulation(args):
    idf_path, epwfile, iddfile = args
    ###
    ###
    try:
        IDF.setiddname(iddfile)
        idf = IDF(idf_path, epwfile)
        modify_idf_for_detailed_output(idf)
        options = make_eplaunch_options(idf, idf_path)
        ####
        
        idf.run(**options)
        logging.info(f"Simulation completed for {idf_path}")
    except Exception as e:
        logging.error(f"Error during simulation for {idf_path}: {e}", exc_info=True)

def generate_simulations(idf_directory, epwfile, iddfile):
    for filename in os.listdir(idf_directory):
        if filename.endswith(".idf"):
            idf_path = os.path.join(idf_directory, filename)
            yield (idf_path, epwfile, iddfile)

def simulate_all():
    config = get_idf_config()  # Use configuration settings
    idf_directory = config['output_dir']
    epwfile = config['epwfile']
    iddfile = config['iddfile']
    num_workers = 4  

    with Pool(num_workers) as pool:
        pool.map(run_simulation, generate_simulations(idf_directory, epwfile, iddfile))

if __name__ == '__main__':
    simulate_all()


