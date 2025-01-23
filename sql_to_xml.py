import warnings
warnings.filterwarnings("ignore")

import sqlglot
import xml.etree.ElementTree as ET
from lxml import etree
from xmlschema import XMLSchema
import os
import pandas as pd
from openai import OpenAI
import xml.dom.minidom as minidom
import json

mapping_sql_xmlschema = {'select': 'SqlFunctions', 'all_tables': 'TableObjects', 'all_joins': 'StaticJoinOptions', 'individual_joins': 'Joins', 'where': 'ValueFilters', 'order': 'SortOptions', 'group': 'AggregateOptions'}
api_key = ''
client = OpenAI(api_key=api_key)

def ask_gpt(sys_msg):
    completion = client.chat.completions.create(model="gpt-4o",messages=[{"role": "user", "content": sys_msg}])
    result = completion.choices[0].message.content.split(",")
    return result[0]

def get_sql(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        return "The file could not be found."
    except Exception as e:
        return f"An error occurred: {str(e)}"
    
def get_view_details():
    with open("config/view.json", 'r') as json_file:
        data = json.load(json_file)
        return data['viewName'], data['viewDesc']

def is_well_formed(xml_text):
    try:
        ET.fromstring(xml_text)
        return True
    except ET.ParseError as e:
        print(f"Regenerating Bad xml \n" + xml_text)
        return False
    
def get_selects(vals):
    if vals is None:
        return 'NA'
    select_xsd = components_schema[mapping_sql_xmlschema['select']]
    msg = f'''For a given SQL SELECT clause and xsd definition as json
    {select_xsd}
    write the xml entries only with case sensitive tags. Please do not provide any explanations. Do not specify xml anywhere.
    
    {vals}
    '''
    resp = ask_gpt(msg)
    return resp

def get_distincts(vals):
    if vals is None:
        return False
    return True

def get_TableObjects(vals):
    if vals is None:
        return False
    TableObjects_xsd = components_schema[mapping_sql_xmlschema['all_tables']]
    msg = f'''For a given table names: {vals.split(' ')}.
    And xsd definition as json
    {TableObjects_xsd}
    write the xml entries only with case sensitive tags. Please do not provide any explanations. Do not specify xml anywhere.
    '''
    resp = ask_gpt(msg)
    return resp

def get_joins(vals):
    if vals is None:
        return False
    staticJoin_xsd = components_schema[mapping_sql_xmlschema['all_joins']]
    individual_xsd = components_schema[mapping_sql_xmlschema['individual_joins']]
    msg = f'''For a given SQL JOIN clauses and xsd definition as json
    {staticJoin_xsd} and {individual_xsd}
    write the xml entries only with case sensitive tags. Please do not provide any explanations. Do not specify xml anywhere.
    
    {vals}
    '''
    resp = ask_gpt(msg)
    return resp

def get_where(vals):
    if vals is None:
        return False
    where_xsd = components_schema[mapping_sql_xmlschema['where']]
    msg = f'''For a given SQL WHERE clause and xsd definition as json
    {where_xsd}
    write the xml entries only with case sensitive tags. Please do not provide any explanations. Do not specify xml anywhere.
    
    {vals}
    '''
    resp = ask_gpt(msg)
    return resp

def get_order(vals):
    if vals is None:
        return False
    order_xsd = components_schema[mapping_sql_xmlschema['order']]
    msg = f'''For a given SQL ORDER BY clause and xsd definition as json
    {order_xsd}
    write the xml entries only with case sensitive tags. Please do not provide any explanations. Do not specify xml anywhere.
    
    {vals}
    '''
    resp = ask_gpt(msg)
    return resp

def get_group(vals):
    if vals is None:
        return False
    group_xsd = components_schema[mapping_sql_xmlschema['group']]
    msg = f'''For a given SQL GROUP BY clause and xsd definition as json
    {group_xsd}
    write the xml entries only with case sensitive tags. Please do not provide any explanations. Do not specify xml anywhere.
    
    {vals}
    '''
    resp = ask_gpt(msg)
    return resp

def generate_child_xmls(sql):
    parsed = sqlglot.parse_one(sql)
    parsed_dict = parsed.args
    components = {}
    
    flag = True
    resp = None
    while flag:
        resp = get_selects(parsed_dict['expressions']).replace("```","").replace("xml","")
        if is_well_formed(resp):
            flag = False
            components['select'] = resp
    
    components['distinct'] = False if parsed_dict['distinct'] is None else True
    
    qsn = f"List all tables used in this sql :{sql}. Return only table names separated by single whitespace in that same order mentioned. Do not provide any explanations."
    all_tables_involved = ask_gpt(qsn)
    flag = True
    resp = None
    while flag:
        resp = get_TableObjects(all_tables_involved).replace("```","").replace("xml","")
        if is_well_formed(resp):
            flag = False
            components['all_tables'] = resp 
    
    flag = True
    resp = None
    while flag:
        if 'joins' not in parsed_dict.keys():
            flag = False
            continue
        resp = get_joins(parsed_dict['joins']).replace("```","").replace("xml","")
        if is_well_formed(resp):
            flag = False
            components['staticJoinOption'] = resp
    
    flag = True
    resp = None
    while flag:
        if 'where' not in parsed_dict.keys():
            flag = False
            continue
        resp = get_where(parsed_dict['where']).replace("```","").replace("xml","")
        if is_well_formed(resp):
            flag = False
            components['where'] = resp
    
    flag = True
    resp = None
    while flag:
        if 'order' not in parsed_dict.keys():
            flag = False
            continue
        resp = get_order(parsed_dict['order']).replace("```","").replace("xml","")
        if is_well_formed(resp):
            flag = False
            components['order'] = resp
            
    flag = True
    resp = None
    while flag:
        if 'group' not in parsed_dict.keys():
            flag = False
            continue
        resp = get_group(parsed_dict['group']).replace("```","").replace("xml","")
        if is_well_formed(resp):
            flag = False
            components['group'] = resp
    
    return components

def pp(root):
    xml_string = ET.tostring(root, encoding="unicode")
    pretty_xml = minidom.parseString(xml_string).toprettyxml(indent="  ")
    print(pretty_xml)
    
def convert_to_xml(xml_string):
    tree = ET.fromstring(xml_string)
    return tree

def create_final_xml(sql, schema_dict, child_xml):
    ns = schema_dict['@xmlns:xs']
    ET.register_namespace("@xmlns:xs", ns)
    if 'join' not in sql.lower():
        root = ET.Element("BusinessObjectSingle")
    else:
        root = ET.Element("BusinessObjectJoined")
    
    # Get view detail from user input saved in view.json
    viewName, viewDesc = get_view_details()
    # Add elements now
    BusinessObjectName = viewName
    BusinessObjectType = 'JOINED' if 'join' in sql.lower() else 'SINGLE'
    BusinessObjectDescription = viewDesc
    iso_lang = ['de', 'en', 'es', 'fr', 'pt']
    IsoText = {}
    IsoText['en'] = BusinessObjectDescription
    for i in iso_lang:
        msg = f"Translate this text into {i} language as it is without extra explanation. Provide only the translation and not other description or explanation.\n{BusinessObjectDescription}"
        IsoText[i] = ask_gpt(msg)
        
    BusinessObjectInMenue = 'true'
    ModuleName = 'FI-AP'
    viewReferenceName = BusinessObjectName
    viewReferenceTargetUrl = f"https://wef2025.cloud.jivs.com/jivs/getSearchForm.do?viewName={BusinessObjectName}&packageName=sap.ecc60kjl"
    viewReferenceTargetViewName = f'viewName={BusinessObjectName}'
    UseTheDistinctClauseInSqlSelectQuery = str(child_xml['distinct']).lower()
    
    # Create the Tree now
    ET.SubElement(root, "BusinessObjectName").text = BusinessObjectName
    ET.SubElement(root, "BusinessObjectType").text = BusinessObjectType
    bot = ET.SubElement(root, "BusinessObjectText")
    for i in iso_lang:
        isotext = ET.SubElement(bot, "IsoText")
        ET.SubElement(isotext, "IsoCode").text = i
        ET.SubElement(isotext, "Text").text = IsoText[i]
        
    bost = ET.SubElement(root, "BusinessObjectShortText")
    for i in iso_lang:
        isotext = ET.SubElement(bost, "IsoText")
        ET.SubElement(isotext, "IsoCode").text = i
        ET.SubElement(isotext, "Text").text = IsoText[i]
        
    bodesc = ET.SubElement(root, "BusinessObjectDescr")
    for i in iso_lang:
        isotext = ET.SubElement(bodesc, "IsoText")
        ET.SubElement(isotext, "IsoCode").text = i
        ET.SubElement(isotext, "Text").text = IsoText[i]
        
    ET.SubElement(root, "BusinessObjectInMenue").text = BusinessObjectInMenue
    ET.SubElement(root, "ModuleName").text = ModuleName
    
    vr = ET.SubElement(root, "viewReference")
    ET.SubElement(vr, "viewReferenceName").text = viewReferenceName
    vrt = ET.SubElement(vr, "viewReferenceText")
    for i in iso_lang:
        isotext = ET.SubElement(vrt, "IsoText")
        ET.SubElement(isotext, "IsoCode").text = i
        ET.SubElement(isotext, "Text").text = IsoText[i]
    vrd = ET.SubElement(vr, "viewReferenceDescription")
    for i in iso_lang:
        isotext = ET.SubElement(vrd, "IsoText")
        ET.SubElement(isotext, "IsoCode").text = i
        ET.SubElement(isotext, "Text").text = IsoText[i]
    ET.SubElement(vr, "viewReferenceTargetUrl").text = viewReferenceTargetUrl
    ET.SubElement(vr, "viewReferenceTargetViewName").text = viewReferenceTargetViewName
    
    sqlFunction = ET.fromstring(child_xml['select'].replace('\n', '').strip())
    root.append(sqlFunction)
    
    ET.SubElement(root, "UseTheDistinctClauseInSqlSelectQuery").text = UseTheDistinctClauseInSqlSelectQuery
    
    TableObjects = ET.fromstring(child_xml['all_tables'].replace('\n', '').strip())
    root.append(TableObjects)
    
    if BusinessObjectType == 'JOINED':
        staticJoinOptions = ET.fromstring(child_xml['staticJoinOption'].replace('\n', '').strip())
        root.append(staticJoinOptions)
    
    if 'where' in child_xml.keys():
        valueFilters = ET.fromstring(child_xml['where'].replace('\n', '').strip())
        root.append(valueFilters)
    
    if 'order' in child_xml.keys():
        sortOptions = ET.fromstring(child_xml['order'].replace('\n', '').strip())
        root.append(sortOptions)
        
    if 'group' in child_xml.keys():
        aggregateOptions = ET.fromstring(child_xml['group'].replace('\n', '').strip())
        root.append(aggregateOptions)
    
    return root

sql_filepath = "data/sample.sql"
xsd_file = "config/standard.xsd"
schema_dict = XMLSchema.meta_schema.decode(xsd_file)
components_schema = {}
for i, sch in enumerate(schema_dict['xs:complexType']):
    components_schema[sch['@name']] = schema_dict['xs:complexType'][i]

sql = get_sql(sql_filepath)

child_xml_dict = generate_child_xmls(sql)
rt = create_final_xml(sql, schema_dict, child_xml_dict)
tree = ET.ElementTree(rt)
viewName, viewDesc = get_view_details() 
output_xml_file = f"config/{viewName}.xml"
tree.write(output_xml_file, encoding="utf-8", xml_declaration=True)