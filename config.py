# config.py

import json
import os

def get_db_config():
    return {
        "dbname": os.getenv('DB_NAME', "research"),
        "user": os.getenv('DB_USER', "postgres"),
        "password": os.getenv('DB_PASSWORD', "mypassword"),
        "host": os.getenv('DB_HOST', "leda.geodan.nl")
    }

def get_conn_params():
    config = get_db_config()
    return f"dbname='{config['dbname']}' user='{config['user']}' password='{config['password']}' host='{config['host']}'"

#def get_idf_config():
#    return {
#        "iddfile": os.getenv('IDDFILE'),
#        "idf_file_path": os.getenv('IDFFILE'),
#        "epwfile": os.getenv('EPWFILE'),
#        "output_dir": os.getenv('OUTPUT_DIR')    }
#  for SQLALchemy

def get_idf_config():
    return {
        "iddfile": os.getenv('IDDFILE', "/usr/local/EnergyPlus-22.2.0-c249759bad-Linux-Ubuntu20.04-x86_64/Energy+.idd"),
        "idf_file_path": os.getenv('IDFFILE', "/app/data/Minimal.idf"),
        "epwfile": os.getenv('EPWFILE', "/app/data/weather/NLD_Amsterdam.062400_IWEC.epw"),
        "output_dir": os.getenv('OUTPUT_DIR', "/app/output")
    }


#def get_idf_config():
#    return {
#        "iddfile": os.getenv('IDDFILE', "D:/EnergyPlus/Energy+.idd"),
#        "idf_file_path": os.getenv('IDFFILE', "C:/Users/aminj/OneDrive/Desktop/EnergyPlus/Minimal.idf"),
#        "epwfile": os.getenv('EPWFILE', "C:/Users/aminj/OneDrive/Desktop/EnergyPlus/Weather/NLD_Amsterdam.062400_IWEC.epw"),  # Add default if needed
#        "output_dir": os.getenv('OUTPUT_DIR', "D:/EnergyPlusOutput")
#    }

# relevant tables   pg_dump

#  -h leda.geodan.nl -U postgres -d Dataless -t all_databases_columns > table.sql
#  -h leda.geodan.nl -U postgres -d research -t nldata.gebouw > gebouw.sql
#  -h leda.geodan.nl -U postgres -d maquette_nl -t bag_latest.adres_plus > adres_plus.sql
#  -h leda.geodan.nl -U postgres -d research -t tomahawk.energypoint > energypoint.sql
#  -h leda.geodan.nl -U postgres -d research -t tomahawk.adres > adres.sql
#  -h leda.geodan.nl -U postgres -d maquette_nl -t dt_heerlen.cesium_buildings > cesium_buildings.sql
# maquette_nl cesium.bag3d_v20231008
