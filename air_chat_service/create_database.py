from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document

import os
import json
from clang.cindex import CursorKind, Index, Cursor

#should connect all that code to ProjectParser class
class ProjectParser():
    def __init__(self, 
                 path: str,
                 embedder: OllamaEmbeddings, 
                 clang_args: list):
        
        self.embeddings = embedder
        self.path = path
        self.args = clang_args
        self.all_chunks = []

    def get_source_code(self, cursor):
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

    def get_namespace(self, cursor):
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

    def collect_called_functions(self, cursor: Cursor):
        called_functions = []
        for node in cursor.walk_preorder():
            if node.kind == CursorKind.CALL_EXPR:
                ref = node.referenced  # ссылка на объявление вызываемой функции
                if ref:
                    called_functions.append({
                        "name": ref.spelling,
                        "namespace": self.get_namespace(ref)[-1] if self.get_namespace(ref) else None,
                        "file": ref.location.file.name if ref.location.file else None
                    })
        return called_functions

    def parse_file(self, path: str):
        index = Index.create()
        tu = index.parse(path, args=self.args)
        cursors = tu.cursor.get_children()
        chunks = []
        for cursor in cursors:
            if cursor.location.file.name == path:
                common_data = {
                    "name": cursor.spelling,
                    "full_name": path,
                    "code_snippet": self.get_source_code(cursor)[:500],
                    "full_code": self.get_source_code(cursor),
                    "file_path": path,
                    "namespace_path": self.get_namespace(cursor),
                    "parent": cursor.semantic_parent.spelling if cursor.semantic_parent else None,
                    "called_functions": self.collect_called_functions(cursor)
                }

                if cursor.kind == CursorKind.FUNCTION_DECL and cursor.is_definition():
                    chunks.append({
                        "type": "function",
                        **common_data
                    })

                elif cursor.kind == CursorKind.CLASS_DECL:
                    chunks.append({
                        "type": "class",
                        **common_data
                    })

                elif cursor.kind == CursorKind.STRUCT_DECL:
                    chunks.append({
                        "type": "struct",
                        **common_data
                    })

                elif cursor.kind == CursorKind.CXX_METHOD:
                    chunks.append({
                        "type": "method",
                        **common_data,
                        "kind_specifics": {
                            "is_static": cursor.is_static_method(),
                            "access": str(cursor.access_specifier.name)  # public/protected/private
                        }
                    })

        return chunks

    def parse_project(self, directory): 
        for root, _, files in os.walk(directory):
            for file in files:
                path = os.path.join(root, file)
                chunks_to_add = []
                if file.endswith(".cpp") or file.endswith(".c") or file.endswith(".h") or file.endswith(".hpp"):
                    chunks_to_add = self.parse_file(path)
                try:
                    print(path)
                    self.all_chunks.extend(chunks_to_add)
                except Exception as e:
                    print(f"Error reading {path}: {e}")
    

    def process_project(self, dir: str):
        self.parse_project(dir)
        documents = [
            Document(page_content=
                f"File path: {chunk['file_path']}\n"
                f"Namespace path: {'::'.join(chunk.get('namespace_path', []))}\n"
                f"Name: {chunk['name']}\n"
                f"Code:\n{chunk['code_snippet']}"
            ,
            metadata={
                "type": chunk.get("type"),
                "file_path": chunk.get("file_path"),
                "name": chunk.get("name"),
                "full_code": chunk.get("full_code"),
                "namespace_path": chunk.get("namespace_path", []),
                "parent": chunk.get("parent"),
                "called_functions": chunk.get( "called_functions")
            }
            ) for chunk in self.all_chunks
        ]
        self.vectorstore = FAISS.from_documents(documents, self.embeddings)
        self.vectorstore.save_local("code_vector_db")

        print(f"Всего документов в базе: {len(self.vectorstore.index_to_docstore_id)}")
        print(f"Всего документов в базе: {len(self.vectorstore.docstore.__dict__)}")
        print("Количество векторов в FAISS:", self.vectorstore.index.ntotal)

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
    DIRECTORY = "../../LTE"

    parser = ProjectParser(DIRECTORY, embeddings, ['-x', 'c++', '-std=c++14', '-DNO_SYSTEM_HEADERS'])
 
    parser.process_project(DIRECTORY)


if __name__ == "__main__":
    all_namespaces = set()
    main()