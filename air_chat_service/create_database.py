from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_core.documents import Document

import faiss
import os
import json
from clang.cindex import CursorKind, Index

#should connect all that code to ProjectParser class
#class ProjectParser(FAISS):
#    def __init__(self, path: str):
#        self.path = path
#        self.index = Index.create(),
#        self.translation_unit = self.index.parse(path, args=['-x', 'c++', '-std=c++14', '-DNO_SYSTEM_HEADERS']),
#        self.all_chunks = []

def get_source_code(cursor):
    extent = cursor.extent
    file = extent.start.file
    if not file:
        return ""
    try:
        with open(file.name, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return content[extent.start.offset:extent.end.offset]
    except Exception:
        return ""


def get_namespace(cursor):
    namespace_path = []
    parent = cursor.semantic_parent
    while parent and parent.kind != CursorKind.TRANSLATION_UNIT:
        if parent.kind == CursorKind.NAMESPACE:
            namespace_path.append(parent.spelling)
            global all_namespaces
            all_namespaces.add(parent.spelling)
        parent = parent.semantic_parent
    if namespace_path:
        return list(reversed(namespace_path))
    return []

def is_system_header(file_path):
    if not file_path:
        return True
    
    file_path = os.path.normpath(file_path)
    system_patterns = [
        "/usr/",
        "/usr/include/",
        "/usr/local/",
        "/opt/",
        "/Library/",
        "/mingw",
        "/msys64",
        "/home/linuxbrew",
        "/var/",
        "/etc/",
        "/run/",
        "/sys/",
        "/proc/",
        "/dev/",
        "/bits/",          
        "/x86_64-pc-linux-gnu/",
        "__FSID_T_TYPE",  
        "__gthrw_",
        "../"
    ]
    for pattern in system_patterns:
        if pattern in file_path:
            return True
    return False

def parse_file(path: str):
    index = Index.create()
    tu = index.parse(path, args=['-x', 'c++', '-std=c++14', '-DNO_SYSTEM_HEADERS'])
    cursors = tu.cursor.get_children()
    chunks = []
    for cursor in cursors:
        if cursor.location.file.name == path:
            namespace_path = get_namespace(cursor)
            if cursor.kind == CursorKind.FUNCTION_DECL and cursor.is_definition():
                code = get_source_code(cursor)
                chunks.append({
                    "type": "function",
                    "name": cursor.spelling,
                    "code_snippet": code[:500],
                    "full_code": code,
                    "namespace": namespace_path[-1] if namespace_path else None,
                    "namespace_path": namespace_path,
                    "file_path": cursor.location.file.name if cursor.location.file else None
                })

            elif cursor.kind == CursorKind.CLASS_DECL:
                code = get_source_code(cursor)
                chunks.append({
                    "type": "class",
                    "name": cursor.spelling,
                    "code_snippet": code[:500],
                    "full_code": code,
                    "namespace": namespace_path[-1] if namespace_path else None,
                    "namespace_path": namespace_path,
                    "file_path": cursor.location.file.name if cursor.location.file else None
                })

            elif cursor.kind == CursorKind.STRUCT_DECL:
                code = get_source_code(cursor)
                chunks.append({
                    "type": "struct",
                    "name": cursor.spelling,
                    "code_snippet": code[:500],
                    "full_code": code,
                    "namespace": namespace_path[-1] if namespace_path else None,
                    "namespace_path": namespace_path,
                    "file_path": cursor.location.file.name if cursor.location.file else None
                })
    return chunks

def parse_project(directory): 
    all_chunks = []
    namespace_map = {}
    for root, _, files in os.walk(directory):
        for file in files:
            path = os.path.join(root, file)
            chunks_to_add = []
            if file.endswith(".cpp") or file.endswith(".c") or file.endswith(".h") or file.endswith(".hpp"):
                chunks_to_add = parse_file(path)
                # Build namespace map
                for chunk in chunks_to_add:
                    ns_path = tuple(chunk.get("namespace_path", []))
                    ns_str = "::".join(ns_path) if ns_path else "<global>"
                    if ns_str not in namespace_map:
                        namespace_map[ns_str] = {"classes": [], "functions": [], "structs": []}
                    if chunk["type"] == "class":
                        namespace_map[ns_str]["classes"].append(chunk["name"])
                    elif chunk["type"] == "function":
                        namespace_map[ns_str]["functions"].append(chunk["name"])
                    elif chunk["type"] == "struct":
                        namespace_map[ns_str]["structs"].append(chunk["name"])
            try:
                print(path)
                all_chunks.extend(chunks_to_add)
            except Exception as e:
                print(f"Error reading {path}: {e}")
    # Save namespace map
    with open("namespace_map.json", "w", encoding="utf-8") as f:
        json.dump(namespace_map, f, indent=2, ensure_ascii=False)
    return all_chunks
 

def doc_to_json(docs, path):
    result = []
    for doc in docs:
        doc_dict = {
            "metadata": doc.metadata,
            "page_content": doc.page_content
        }
        result.append(doc_dict)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


def main():

    embeddings = OllamaEmbeddings(model='nomic-embed-text:latest')

    #Write dir for parse here:
    DIRECTORY = ""
 
    chunks = parse_project(DIRECTORY)

    #with open('namespaces.txt', 'w') as file:
    #    file.write(all_namespaces)

    documents = [
        Document(page_content=
            f"File path: {chunk['file_path']}\n"
            f"Namespace: {chunk['namespace']}\n"
            f"Namespace path: {'::'.join(chunk.get('namespace_path', []))}\n"
            f"Name: {chunk['name']}\n"
            f"Code:\n{chunk['code_snippet']}"
        ,
        metadata={
            "type": chunk.get("type"),
            "file_path": chunk.get("file_path"),
            "name": chunk.get("name"),
            "full_code": chunk.get("full_code"),
            "namespace": chunk.get("namespace"),
            "namespace_path": chunk.get("namespace_path", []),
        }
        ) for chunk in chunks
    ]
    #doc_to_json(documents, "code_chunks2.json")

    embeddings_dim = len(embeddings.embed_query("hello world"))

    vector_db = FAISS(
        embedding_function=embeddings,
        index=faiss.IndexFlatL2(embeddings_dim),
        docstore=InMemoryDocstore(),
        index_to_docstore_id={}
    )

    vector_db.add_documents(documents)

    #database is saved here and it would be used with another script for inference with RAG
    vector_db.save_local("code_vector_db")

    print(f"Всего документов в базе: {len(vector_db.index_to_docstore_id)}")
    print(f"Всего документов в базе: {len(vector_db.docstore.__dict__)}")
    print("Количество векторов в FAISS:", vector_db.index.ntotal)

if __name__ == "__main__":
    all_namespaces = set()
    main()