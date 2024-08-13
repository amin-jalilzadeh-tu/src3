import pandas as pd
import psycopg2
from config import get_conn_params

def create_engine_and_load_data(filter_criteria):
    # Get connection string using the config function
    conn_string = get_conn_params()

    # Establish a connection to the database
    conn = psycopg2.connect(conn_string)
    
    # Cursor to execute the query
    cursor = conn.cursor()

    # Build the SQL query based on filter criteria
    base_query = """
    SELECT 
        nummeraanduiding_id, 
        meestvoorkomendepostcode, 
        function,
        building_type,
        age_range,
        height,
        area,
        perimeter,
        average_wwr
    FROM 
        amin.buildings_1
    """

    # Add conditions to the query based on filter criteria
    conditions = []
    if 'postcode6' in filter_criteria:
        conditions.append(f"meestvoorkomendepostcode = '{filter_criteria['postcode6']}'")
    if 'ids' in filter_criteria:
        ids_list = ', '.join([f"'{id}'" for id in filter_criteria['ids']])
        conditions.append(f"nummeraanduiding_id IN ({ids_list})")

    if conditions:
        query = f"{base_query} WHERE {' AND '.join(conditions)};"
    else:
        query = base_query + ";"

    # Execute the query
    cursor.execute(query)
    
    # Fetch the results and convert to a DataFrame
    colnames = [desc[0] for desc in cursor.description]
    data = cursor.fetchall()
    buildings_df = pd.DataFrame(data, columns=colnames)
    
    # Close the cursor and connection
    cursor.close()
    conn.close()
    
    return buildings_df
