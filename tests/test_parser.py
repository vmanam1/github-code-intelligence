import pytest
from parser.tree_sitter_parser import CodeParser

def test_language_detection():
    parser = CodeParser()
    assert parser.get_language_from_ext(".py") == "python"
    assert parser.get_language_from_ext(".ts") == "typescript"
    assert parser.get_language_from_ext(".go") == "go"
    assert parser.get_language_from_ext(".txt") is None

def test_parse_python_code():
    code = """
import os
from datetime import datetime as dt

class Calculator:
    \"\"\"A simple calculator class\"\"\"
    
    def add(self, a, b):
        \"\"\"Return the sum of a and b\"\"\"
        return a + b

def global_helper():
    return True
"""
    parser = CodeParser()
    # Write code to a dummy file name to trigger python mapping
    res = parser.parse_file("dummy.py", code)
    
    # Assert imports
    assert len(res["imports"]) == 2
    assert res["imports"][0]["name"] == "os"
    assert res["imports"][1]["source"] == "datetime"
    assert res["imports"][1]["name"] == "datetime"
    assert res["imports"][1]["alias"] == "dt"
    
    # Assert classes
    assert len(res["classes"]) == 1
    assert res["classes"][0]["name"] == "Calculator"
    assert res["classes"][0]["docstring"] == "A simple calculator class"
    
    # Assert functions
    assert len(res["functions"]) == 2
    # Method
    methods = [f for f in res["functions"] if f["class_name"] == "Calculator"]
    assert len(methods) == 1
    assert methods[0]["name"] == "add"
    assert methods[0]["docstring"] == "Return the sum of a and b"
    
    # Global function
    globals_ = [f for f in res["functions"] if f["class_name"] is None]
    assert len(globals_) == 1
    assert globals_[0]["name"] == "global_helper"

def test_parse_javascript_code():
    code = """
import { useState } from 'react';
import * as React from 'react';

// A greet function
function greet(name) {
    return `Hello, ${name}`;
}

const add = (a, b) => a + b;
"""
    parser = CodeParser()
    res = parser.parse_file("dummy.js", code)
    
    # Assert imports
    assert len(res["imports"]) >= 2
    
    # Assert functions
    funcs = {f["name"]: f for f in res["functions"]}
    assert "greet" in funcs
    assert funcs["greet"]["docstring"] == "A greet function"
    
    # Arrow function
    assert "add" in funcs
