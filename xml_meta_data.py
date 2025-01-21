from lxml import etree
import os
import json

def extract_metadata(xml_path):
    tree = etree.parse(xml_path)
    root = tree.getroot()

    table_objects = []
    for table in root.xpath(".//TableObjects/TableObject"):
        table_name = table.find("TableName").text
        position = table.find("Position").text
        table_objects.append({"TableName": table_name, "Position": position})

    static_joins = []
    for join_option in root.xpath(".//staticJoinOptions/staticJoinOption"):
        join_table = join_option.find("joinTable").text
        join_type = join_option.find("joinType").text
        joins = []
        for join in join_option.xpath(".//joins/join"):
            source_table = join.find("sourceTable").text
            source_field = join.find("sourceFieldName").text
            join_table_field = join.find("joinTable").text
            join_field = join.find("joinFieldName").text
            operator = join.find("operator").text
            joins.append({
                "SourceTable": source_table,
                "SourceField": source_field,
                "JoinTable": join_table_field,
                "JoinField": join_field,
                "Operator": operator
            })
        static_joins.append({
            "JoinTable": join_table,
            "JoinType": join_type,
            "Joins": joins
        })

    value_filters = []
    for filter in root.xpath(".//valueFilters/valueFilter"):
        logical_operator = filter.find("logicalOperator").text
        table_name = filter.find("tableName").text
        field_name = filter.find("fieldName").text
        operator = filter.find("operator").text
        value = filter.find("value").text
        value_filters.append({
            "LogicalOperator": logical_operator,
            "TableName": table_name,
            "FieldName": field_name,
            "Operator": operator,
            "Value": value
        })

    sort_options = []
    for sort in root.xpath(".//sortOptions/sortOption"):
        source_table = sort.find("sourceTable").text
        source_field = sort.find("sourceField").text
        sorting = sort.find("sorting").text
        sort_options.append({
            "SourceTable": source_table,
            "SourceField": source_field,
            "Sorting": sorting
        })

    return {
        "TableObjects": table_objects,
        "StaticJoinOptions": static_joins,
        "ValueFilters": value_filters,
        "SortOptions": sort_options
    }


def process_xml_directory(directory_path):
    for file_name in os.listdir(directory_path):
        if file_name.endswith(".xml"):
            xml_path = os.path.join(directory_path, file_name)
            try:
                metadata = extract_metadata(xml_path)
                
                json_file_name = os.path.splitext(file_name)[0] + ".json"
                json_path = os.path.join(directory_path, json_file_name)
                
                with open(json_path, "w", encoding="utf-8") as json_file:
                    json.dump(metadata, json_file, indent=4)
                
                print(f"Processed: {file_name}")
                print("TableObjects:", metadata.get("TableObjects"))
                print("StaticJoinOptions:", metadata.get("StaticJoinOptions"))
                print("ValueFilters:", metadata.get("ValueFilters"))
                print("SortOptions:", metadata.get("SortOptions"))
            except Exception as e:
                print(f"Error processing {file_name}: {e}")

directory_path = "data/"
process_xml_directory(directory_path)