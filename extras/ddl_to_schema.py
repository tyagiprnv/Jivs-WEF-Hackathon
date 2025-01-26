import os

def merge_sql_files(input_directory, output_file):
    try:
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for filename in os.listdir(input_directory):
                if filename.endswith('.sql'):
                    file_path = os.path.join(input_directory, filename)
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        content = infile.read()
                    outfile.write(content)
                    outfile.write("\n")

    except Exception as e:
        print(f"An error occurred: {e}")

input_directory = "data/ddl" 
output_file = "schema.txt"
merge_sql_files(input_directory, output_file)
