import pandas as pd
import os

def infer_sql_datatype(dtype):
    if "int" in dtype:
        return "INT"
    elif "float" in dtype:
        return "FLOAT"
    elif "bool" in dtype:
        return "BOOLEAN"
    elif "datetime" in dtype:
        return "DATETIME"
    else:
        return "VARCHAR(255)"

def generate_create_table_statement(file_path):
    # Read the CSV file
    df = pd.read_csv(file_path, delimiter=";")
    
    # Get the filename without extension to use as table name
    table_name = file_path.split('/')[-1].split('.')[0]
    
    # Start creating the SQL statement
    sql = f"CREATE TABLE {table_name} (\n"
    
    # Iterate through columns to add them to the SQL statement
    for column in df.columns:
        # Infer data type from the column data
        sql_type = infer_sql_datatype(df[column].dtype.name)
        sql += f"    {column} {sql_type},\n"
    
    # Remove the last comma and add closing parenthesis
    sql = sql.rstrip(',\n') + '\n);'
    
    return table_name, sql

def write_sql_to_file(table_name, sql):
    # Check if the directory exists, if not create it
    fname = f"data/{table_name}.sql"
    directory = os.path.dirname(fname)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Write the SQL string to the specified file
    with open(fname, 'w') as file:
        file.write(sql)

# Example usage
lis = ['/Users/sidpai/Desktop/ddl/ADR6.csv', '/Users/sidpai/Desktop/ddl/BKPF.csv', '/Users/sidpai/Desktop/ddl/BNKA.csv', '/Users/sidpai/Desktop/ddl/BSAK.csv', '/Users/sidpai/Desktop/ddl/BSEG.csv', '/Users/sidpai/Desktop/ddl/BSIK.csv', '/Users/sidpai/Desktop/ddl/CDHDR.csv', '/Users/sidpai/Desktop/ddl/CDPOS.csv', '/Users/sidpai/Desktop/ddl/KNVK.csv', '/Users/sidpai/Desktop/ddl/LFA1.csv', '/Users/sidpai/Desktop/ddl/LFAS.csv', '/Users/sidpai/Desktop/ddl/LFB1.csv', '/Users/sidpai/Desktop/ddl/LFB5.csv', '/Users/sidpai/Desktop/ddl/LFBK.csv', '/Users/sidpai/Desktop/ddl/LFBW.csv', '/Users/sidpai/Desktop/ddl/LFC1.csv', '/Users/sidpai/Desktop/ddl/LFC3.csv', '/Users/sidpai/Desktop/ddl/LFM1.csv', '/Users/sidpai/Desktop/ddl/LFM2.csv', '/Users/sidpai/Desktop/ddl/T001.csv', '/Users/sidpai/Desktop/ddl/T014.csv', '/Users/sidpai/Desktop/ddl/TIBAN.csv']
for l in lis:
    table_name, create_statement = generate_create_table_statement(l)
    write_sql_to_file(table_name, create_statement)
    print("Done with " + l)
