import xml.etree.ElementTree as ET
from typing import List, Dict
import os
from sentence_transformers import SentenceTransformer
import chromadb
import pandas as pd

def parse_excel(excel_file: str) -> Dict[str, str]:
    df = pd.read_excel(excel_file)
    return dict(zip(df['ObjectName'], df['Description']))

def parse_view(xml_content: str, descriptions: Dict[str, str]) -> Dict:
    root = ET.fromstring(xml_content)
    viewname = root.findtext("viewName")
    view_name = viewname.split('.')[1]

    view_data = {
        "view_name": view_name,
        "description": descriptions.get(view_name, ""), 
        "fields": []
    }

    # Use a set to track unique fields
    unique_fields = set()

    for field in root.findall(".//searchField"):
        field_name = field.findtext("fieldName")
        table_name = field.findtext("tableName")
        datatype = field.find("dataType/dataTypeName").text if field.find("dataType/dataTypeName") is not None else ""

        # Create a unique key for the field
        field_key = (field_name, table_name, datatype)

        if field_key not in unique_fields:
            unique_fields.add(field_key)
            field_data = {
                "field_name": field_name,
                "table_name": table_name,
                "datatype": datatype
            }
            view_data["fields"].append(field_data)
    
    print(view_data['description'])

    return view_data

def load_all_views_from_directory(directory: str, excel_file: str) -> List[Dict]:
    descriptions = parse_excel(excel_file)
    views = []

    unique_views = set()

    for filename in os.listdir(directory):
        if filename.endswith(".xml"):
            xml_path = os.path.join(directory, filename)
            with open(xml_path, "r", encoding="utf-8") as file:
                xml_content = file.read()
                view = parse_view(xml_content, descriptions)
                view_key = (view["view_name"], str(view["fields"]))
                if view_key not in unique_views:
                    unique_views.add(view_key)
                    views.append(view)
    return views

def create_search_documents(views: List[Dict]) -> List[str]:
    documents = []
    for view in views:
        doc = f"View {view['view_name']} ({view['description']}) contains: "
        doc += ". ".join([f"{field['field_name']} ({field['table_name']}, {field['datatype']})" 
                        for field in view['fields']])
        documents.append(doc)
    return documents

def setup_chroma_db(views: List[Dict], documents: List[str], embeddings: List[List[float]], persist_dir: str = "chroma_db"):
    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_or_create_collection(name="views")
    
    print(f"Adding {len(documents)} documents to the collection.")
    
    collection.add(
        ids=[str(i) for i in range(len(documents))],
        embeddings=embeddings,
        documents=documents,
        metadatas=[{
            "view_name": view["view_name"],
            "description": view.get("description", "No description available"),  # Include description
            "fields": str(view["fields"])
        } for view in views]
    )
    print(f"Database setup complete. Persisted to {persist_dir}")

def main():
    xml_directory = "data_task_1"
    excel_file = "data/SAP_ECC60_ReleaseSubset_FI-AP.xls"
    views = load_all_views_from_directory(xml_directory, excel_file)
    
    documents = create_search_documents(views)
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(documents).tolist()
    
    setup_chroma_db(views, documents, embeddings)

if __name__ == "__main__":
    main()