import os
import re
from typing import Dict, List, Any, Optional
from tree_sitter import Parser, Node
import tree_sitter_languages

class CodeParser:
    """
    Robust code parser using tree-sitter.
    Extracts class, function, and import metadata from files in multiple programming languages.
    """
    
    # Map file extensions to tree-sitter language identifiers
    LANGUAGE_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".h": "cpp",
        ".hpp": "cpp",
        ".java": "java",
    }

    def __init__(self):
        self._parsers = {}

    def _get_parser(self, language_name: str) -> Optional[Parser]:
        """Lazy load tree-sitter parser for a specific language."""
        if language_name not in self._parsers:
            try:
                lang = tree_sitter_languages.get_language(language_name)
                try:
                    parser = Parser()
                    parser.set_language(lang)
                except (AttributeError, TypeError):
                    parser = Parser(lang)
                self._parsers[language_name] = parser
            except Exception as e:
                print(f"Failed to load tree-sitter parser for {language_name}: {e}")
                return None
        return self._parsers[language_name]

    def get_language_from_ext(self, ext: str) -> Optional[str]:
        return self.LANGUAGE_MAP.get(ext.lower())

    def parse_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Parses the code content of a file and returns extracted features.
        """
        _, ext = os.path.splitext(file_path)
        lang_name = self.get_language_from_ext(ext)
        
        result = {
            "classes": [],
            "functions": [],
            "imports": [],
            "lines_count": len(content.splitlines()),
            "language": lang_name or "text"
        }

        if not lang_name or not content.strip():
            return result

        parser = self._get_parser(lang_name)
        if not parser:
            return result

        try:
            tree = parser.parse(bytes(content, "utf8"))
            root_node = tree.root_node
            
            # Extract features depending on the language
            self._walk_and_parse(root_node, content, result, lang_name)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error parsing file {file_path}: {e}")
            
        return result

    def _walk_and_parse(self, root_node: Node, content: str, result: Dict[str, Any], lang_name: str):
        """Walk the AST and parse entities."""
        content_bytes = bytes(content, "utf8")
        
        def traverse(node: Node):
            # 1. Parse Imports
            self._parse_import_node(node, content_bytes, result["imports"], lang_name)
            
            # 2. Parse Classes
            self._parse_class_node(node, content_bytes, result["classes"], lang_name)
            
            # 3. Parse Functions (including methods)
            self._parse_function_node(node, content_bytes, result["functions"], lang_name)
            
            for child in node.children:
                traverse(child)

        traverse(root_node)

    def _get_node_text(self, node: Node, content_bytes: bytes) -> str:
        """Helper to get text of a node."""
        return content_bytes[node.start_byte:node.end_byte].decode("utf8", errors="ignore")

    def _parse_import_node(self, node: Node, content_bytes: bytes, imports: List[Dict[str, Any]], lang_name: str):
        """Extract imports from imports nodes."""
        node_type = node.type
        line_num = node.start_point[0] + 1
        
        if lang_name == "python":
            if node_type == "import_statement":
                # import a, b as c
                # Children usually include dotted_name or aliased_import
                for child in node.children:
                    if child.type == "dotted_name":
                        name = self._get_node_text(child, content_bytes)
                        imports.append({"source": "", "name": name, "alias": None, "line_number": line_num})
                    elif child.type == "aliased_import":
                        dotted = child.child_by_field_name("name")
                        alias = child.child_by_field_name("alias")
                        if dotted:
                            name = self._get_node_text(dotted, content_bytes)
                            alias_str = self._get_node_text(alias, content_bytes) if alias else None
                            imports.append({"source": "", "name": name, "alias": alias_str, "line_number": line_num})
            elif node_type == "import_from_statement":
                # from a import b as c, d
                source_node = node.child_by_field_name("module_name")
                source = self._get_node_text(source_node, content_bytes) if source_node else ""
                
                # Check children for imports, skip the source_node itself
                for child in node.children:
                    if child == source_node:
                        continue
                    if child.type == "dotted_name":
                        name = self._get_node_text(child, content_bytes)
                        imports.append({"source": source, "name": name, "alias": None, "line_number": line_num})
                    elif child.type == "aliased_import":
                        dotted = child.child_by_field_name("name")
                        alias = child.child_by_field_name("alias")
                        if dotted:
                            name = self._get_node_text(dotted, content_bytes)
                            alias_str = self._get_node_text(alias, content_bytes) if alias else None
                            imports.append({"source": source, "name": name, "alias": alias_str, "line_number": line_num})
                    elif child.type == "wildcard_import":
                        imports.append({"source": source, "name": "*", "alias": None, "line_number": line_num})
                        
        elif lang_name in ("javascript", "typescript"):
            if node_type == "import_statement":
                # Find source
                source = ""
                source_node = node.child_by_field_name("source")
                if source_node:
                    source = self._get_node_text(source_node, content_bytes).strip("'\"")
                else:
                    for c in node.children:
                        if c.type == "string":
                            source = self._get_node_text(c, content_bytes).strip("'\"")
                            break
                
                # Find import_clause
                clause = None
                for c in node.children:
                    if c.type == "import_clause":
                        clause = c
                        break
                
                if clause:
                    for child in clause.children:
                        if child.type == "identifier":
                            # default import: import React from 'react'
                            name = "default"
                            alias = self._get_node_text(child, content_bytes)
                            imports.append({"source": source, "name": name, "alias": alias, "line_number": line_num})
                        elif child.type == "namespace_import":
                            # namespace import: import * as React from 'react'
                            alias = ""
                            for sub in child.children:
                                if sub.type == "identifier":
                                    alias = self._get_node_text(sub, content_bytes)
                            imports.append({"source": source, "name": "*", "alias": alias if alias else None, "line_number": line_num})
                        elif child.type == "named_imports":
                            # named imports: import { useState as state } from 'react'
                            for spec in child.children:
                                if spec.type == "import_specifier":
                                    idents = [sub for sub in spec.children if sub.type == "identifier"]
                                    if len(idents) == 1:
                                        name = self._get_node_text(idents[0], content_bytes)
                                        imports.append({"source": source, "name": name, "alias": None, "line_number": line_num})
                                    elif len(idents) == 2:
                                        name = self._get_node_text(idents[0], content_bytes)
                                        alias = self._get_node_text(idents[1], content_bytes)
                                        imports.append({"source": source, "name": name, "alias": alias, "line_number": line_num})

        elif lang_name == "go":
            if node_type == "import_declaration":
                # import "fmt" or import ( "fmt"; "os" )
                for child in node.children:
                    if child.type == "import_spec":
                        path_node = child.child_by_field_name("path")
                        name_node = child.child_by_field_name("name")
                        if path_node:
                            source = self._get_node_text(path_node, content_bytes).strip("'\"")
                            alias = self._get_node_text(name_node, content_bytes) if name_node else None
                            imports.append({"source": "", "name": source, "alias": alias, "line_number": line_num})

        elif lang_name == "cpp":
            if node_type == "preproc_include":
                # #include <vector> or #include "header.h"
                for child in node.children:
                    if child.type in ("system_lib_string", "string_literal"):
                        name = self._get_node_text(child, content_bytes).strip('<>"')
                        imports.append({"source": "", "name": name, "alias": None, "line_number": line_num})

    def _parse_class_node(self, node: Node, content_bytes: bytes, classes: List[Dict[str, Any]], lang_name: str):
        """Extract classes from class nodes."""
        node_type = node.type
        is_class = False
        name = ""
        
        if lang_name == "python" and node_type == "class_definition":
            is_class = True
            name_node = node.child_by_field_name("name")
            name = self._get_node_text(name_node, content_bytes) if name_node else "UnknownClass"
            
        elif lang_name in ("javascript", "typescript") and node_type in ("class_declaration", "class"):
            is_class = True
            name_node = node.child_by_field_name("name")
            name = self._get_node_text(name_node, content_bytes) if name_node else "AnonymousClass"
            
        elif lang_name == "go" and node_type == "type_declaration":
            # Go: type MyStruct struct { ... }
            # Let's extract structs as classes
            for child in node.children:
                if child.type == "type_spec":
                    name_node = child.child_by_field_name("name")
                    type_node = child.child_by_field_name("type")
                    if type_node and type_node.type == "struct_type" and name_node:
                        is_class = True
                        name = self._get_node_text(name_node, content_bytes)
                        
        elif lang_name == "cpp" and node_type in ("class_specifier", "struct_specifier"):
            is_class = True
            name_node = node.child_by_field_name("name")
            name = self._get_node_text(name_node, content_bytes) if name_node else "AnonymousClass"

        elif lang_name == "java" and node_type == "class_declaration":
            is_class = True
            name_node = node.child_by_field_name("name")
            name = self._get_node_text(name_node, content_bytes) if name_node else "UnknownClass"

        if is_class and name:
            body = self._get_node_text(node, content_bytes)
            docstring = self._extract_docstring(node, content_bytes, lang_name)
            classes.append({
                "name": name,
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
                "body": body,
                "docstring": docstring
            })

    def _parse_function_node(self, node: Node, content_bytes: bytes, functions: List[Dict[str, Any]], lang_name: str):
        """Extract functions and methods from function nodes."""
        node_type = node.type
        is_func = False
        name = ""
        signature = ""
        
        if lang_name == "python" and node_type == "function_definition":
            is_func = True
            name_node = node.child_by_field_name("name")
            name = self._get_node_text(name_node, content_bytes) if name_node else "anonymous_func"
            params_node = node.child_by_field_name("parameters")
            params = self._get_node_text(params_node, content_bytes) if params_node else "()"
            signature = f"def {name}{params}"
            
        elif lang_name in ("javascript", "typescript"):
            if node_type in ("function_declaration", "method_definition"):
                is_func = True
                name_node = node.child_by_field_name("name")
                name = self._get_node_text(name_node, content_bytes) if name_node else "anonymous_func"
                params_node = node.child_by_field_name("parameters")
                params = self._get_node_text(params_node, content_bytes) if params_node else "()"
                signature = f"function {name}{params}"
            elif node_type == "arrow_function":
                # Parent might be a variable declarator with a name
                parent = node.parent
                if parent and parent.type == "variable_declarator":
                    is_func = True
                    name_node = parent.child_by_field_name("name")
                    name = self._get_node_text(name_node, content_bytes) if name_node else "anonymous_arrow"
                    params_node = node.child_by_field_name("parameters")
                    params = self._get_node_text(params_node, content_bytes) if params_node else "()"
                    signature = f"const {name} = {params} => ..."

        elif lang_name == "go":
            if node_type == "function_declaration":
                is_func = True
                name_node = node.child_by_field_name("name")
                name = self._get_node_text(name_node, content_bytes) if name_node else "anonymous_func"
                params_node = node.child_by_field_name("parameters")
                params = self._get_node_text(params_node, content_bytes) if params_node else "()"
                signature = f"func {name}{params}"
            elif node_type == "method_declaration":
                is_func = True
                name_node = node.child_by_field_name("name")
                name = self._get_node_text(name_node, content_bytes) if name_node else "anonymous_func"
                receiver_node = node.child_by_field_name("receiver")
                receiver = self._get_node_text(receiver_node, content_bytes) if receiver_node else ""
                params_node = node.child_by_field_name("parameters")
                params = self._get_node_text(params_node, content_bytes) if params_node else "()"
                signature = f"func {receiver} {name}{params}"

        elif lang_name == "cpp" and node_type == "function_definition":
            is_func = True
            declarator = node.child_by_field_name("declarator")
            if declarator:
                # Find inner name
                name = self._extract_cpp_func_name(declarator, content_bytes)
                signature = self._get_node_text(declarator, content_bytes)
            else:
                name = "anonymous_func"
                signature = "void func()"

        elif lang_name == "java" and node_type == "method_declaration":
            is_func = True
            name_node = node.child_by_field_name("name")
            name = self._get_node_text(name_node, content_bytes) if name_node else "anonymous_func"
            params_node = node.child_by_field_name("parameters")
            params = self._get_node_text(params_node, content_bytes) if params_node else "()"
            signature = f"{name}{params}"

        if is_func and name:
            body = self._get_node_text(node, content_bytes)
            docstring = self._extract_docstring(node, content_bytes, lang_name)
            
            # Find class context (is this node inside a class?)
            class_name = self._find_parent_class_name(node, lang_name)
            
            functions.append({
                "name": name,
                "signature": signature,
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
                "body": body,
                "docstring": docstring,
                "class_name": class_name
            })

    def _extract_cpp_func_name(self, declarator_node: Node, content_bytes: bytes) -> str:
        """Traverse down C++ declarator to find the function name identifier."""
        if declarator_node.type == "identifier":
            return self._get_node_text(declarator_node, content_bytes)
        for child in declarator_node.children:
            name = self._extract_cpp_func_name(child, content_bytes)
            if name != "anonymous_func":
                return name
        return "anonymous_func"

    def _find_parent_class_name(self, node: Node, lang_name: str) -> Optional[str]:
        """Traverse upwards to see if this function is a method inside a class."""
        curr = node.parent
        while curr:
            if lang_name == "python" and curr.type == "class_definition":
                name_node = curr.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode("utf8", errors="ignore")
            elif lang_name in ("javascript", "typescript") and curr.type in ("class_declaration", "class"):
                name_node = curr.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode("utf8", errors="ignore")
            elif lang_name == "cpp" and curr.type in ("class_specifier", "struct_specifier"):
                name_node = curr.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode("utf8", errors="ignore")
            elif lang_name == "java" and curr.type == "class_declaration":
                name_node = curr.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode("utf8", errors="ignore")
            curr = curr.parent
        return None

    def _extract_docstring(self, node: Node, content_bytes: bytes, lang_name: str) -> Optional[str]:
        """Extract first docstring/comment associated with classes or functions."""
        if lang_name == "python":
            # For Python, check the first expression inside the body block
            body_node = node.child_by_field_name("body")
            if body_node and body_node.type == "block" and len(body_node.children) > 0:
                first_stmt = body_node.children[0]
                if first_stmt.type == "expression_statement":
                    expr = first_stmt.children[0]
                    if expr.type == "string":
                        doc = self._get_node_text(expr, content_bytes)
                        # Clean docstring quotes
                        doc = doc.strip(" \n\t'\"")
                        return doc
        else:
            # For JS/TS, Go, CPP, Java, look for leading comments right before the node
            # Let's check sibling nodes or parent's child prior to this node
            parent = node.parent
            if parent:
                siblings = parent.children
                try:
                    idx = siblings.index(node)
                    if idx > 0:
                        prev_sibling = siblings[idx - 1]
                        if prev_sibling.type in ("comment", "line_comment", "block_comment"):
                            text = self._get_node_text(prev_sibling, content_bytes)
                            # Clean comment symbols
                            text = re.sub(r'^//|^\/\*|\*\/$', '', text).strip()
                            return text
                except ValueError:
                    pass
        return None
