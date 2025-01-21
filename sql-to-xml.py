import sqlglot
import xml.etree.ElementTree as ET
from lxml import etree

sql = """
SELECT KNVK.*,  ADR6.*
FROM KNVK
LEFT JOIN ADR6
    ON KNVK.MANDT = ADR6.CLIENT
    AND KNVK.PRSNR = ADR6.PERSNUMBER
WHERE KNVK.LIFNR <> ''
ORDER BY KNVK.MANDT ASC, KNVK.LIFNR ASC;
"""

xsd_files = ["data/MigrationObjects.xsd", "data/ViewReferences.xsd"] 
xsd_schemas = [etree.XMLSchema(etree.parse(xsd)) for xsd in xsd_files]

def parse_sql(sql):
    parsed = sqlglot.parse_one(sql)
    components = {
        "select": [col.sql() for col in parsed.selects],
        "from": parsed.from_.sql(),
        "joins": [
            {
                "type": join.join_type,
                "table": join.this.sql(),
                "condition": join.on.sql() if join.on else None,
            }
            for join in parsed.joins
        ],
        "where": parsed.where.sql() if parsed.where else None,
        "order_by": parsed.order.sql() if parsed.order else None,
    }
    return components

def create_xml(components):
    ns = {"bo": "http://example.com/business-object"}  
    root = ET.Element("{http://example.com/business-object}BusinessObject", nsmap=ns)

    ET.SubElement(root, "{http://example.com/business-object}Name").text = "Finance_RecentOrders"
    ET.SubElement(root, "{http://example.com/business-object}Description").text = "Retrieve orders since 2023-01-01 with customer details."

    tables = ET.SubElement(root, "{http://example.com/business-object}Tables")
    tables_set = set([components["from"]] + [j["table"] for j in components["joins"]])
    for table in tables_set:
        table_name, alias = table.split() if ' ' in table else (table, table[0])
        ET.SubElement(tables, "{http://example.com/business-object}Table", Name=table_name, Alias=alias)

    joins = ET.SubElement(root, "{http://example.com/business-object}Joins")
    for join in components["joins"]:
        join_elem = ET.SubElement(joins, "{http://example.com/business-object}Join", Type=join["type"].upper())
        left_table = join["condition"].split('=')[0].split('.')[0]
        right_table = join["condition"].split('=')[1].split('.')[0]
        ET.SubElement(join_elem, "{http://example.com/business-object}LeftTable").text = left_table
        ET.SubElement(join_elem, "{http://example.com/business-object}RightTable").text = right_table
        ET.SubElement(join_elem, "{http://example.com/business-object}Condition").text = join["condition"]

    select_clause = ET.SubElement(root, "{http://example.com/business-object}SelectClause")
    for col in components["select"]:
        table_alias, col_name = col.split('.')
        ET.SubElement(select_clause, "{http://example.com/business-object}Column", Table=table_alias, Name=col_name)

    if components["where"]:
        where_clause = ET.SubElement(root, "{http://example.com/business-object}WhereClause")
        filter_elem = ET.SubElement(where_clause, "{http://example.com/business-object}Filter")
        condition = components["where"]
        if '>=' in condition:
            col, value = condition.split('>=')
            op = 'GE'
        elif '=' in condition:
            col, value = condition.split('=')
            op = 'EQ'
        else:
            raise ValueError(f"Unsupported operator in condition: {condition}")
        table_alias, col_name = col.strip().split('.')
        ET.SubElement(filter_elem, "{http://example.com/business-object}Column", Table=table_alias, Name=col_name)
        ET.SubElement(filter_elem, "{http://example.com/business-object}Operator").text = op
        ET.SubElement(filter_elem, "{http://example.com/business-object}Value", Type="Date").text = value.strip().strip("'")

    if components["order_by"]:
        order_by_clause = ET.SubElement(root, "{http://example.com/business-object}OrderByClause")
        order_by_parts = components["order_by"].split()
        col = order_by_parts[0]
        direction = order_by_parts[1] if len(order_by_parts) > 1 else "ASC"
        table_alias, col_name = col.split('.')
        ET.SubElement(order_by_clause, "{http://example.com/business-object}SortColumn", Table=table_alias, Name=col_name, Direction=direction.upper())

    return ET.tostring(root, encoding="unicode", pretty_print=True)

def validate_xml(xml_str, xsd_schemas):
    """Validate XML against XSD schemas."""
    xml_doc = etree.fromstring(xml_str.encode())
    for xsd in xsd_schemas:
        if not xsd.validate(xml_doc):
            print(f"Validation errors for {xsd}:")
            print(xsd.error_log)
            return False
    return True

components = parse_sql(sql)
xml_str = create_xml(components)
print("Generated XML:")
print(xml_str)

if validate_xml(xml_str, xsd_schemas):
    print("XML is valid against all XSD schemas.")
else:
    print("XML validation failed.")