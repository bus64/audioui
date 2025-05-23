#File:  src/performances/summary.py © 2025 projectemergence. All rights reserved.
#File:  src/performances/summary.py © 2024 projectemergence. All rights reserved.
import os
import json
from datetime import datetime
import ast

def get_version_from_path(file_path):
    parts = file_path.split(os.sep)
    for part in parts:
        if part.startswith("ALLV") and part[4:].isdigit():
            return part
    return "ALLV_unknown"

def extract_function_details(file_content):
    """Extract function names, arguments, and return statements from a given file content."""
    try:
        tree = ast.parse(file_content)
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                args = [arg.arg for arg in node.args.args]
                returns = [n.value for n in ast.walk(node) if isinstance(n, ast.Return) and n.value is not None]
                return_values = [ast.dump(r) for r in returns]
                functions.append((node.name, args, return_values))
        return functions
    except SyntaxError as e:
        #print(f"Syntax error while parsing file content: {e}")
        return []

def save_folder_structure(root_folder, output_file, concatenated_output):
    file_structure = {}
    function_definitions = {}
    all_imports = set()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

    with open(concatenated_output, "w", encoding="utf-8") as concat_file:
        for dirpath, dirnames, filenames in os.walk(root_folder):
            # Skip __pycache__ directories
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]

            rel_path = os.path.relpath(dirpath, root_folder)

            # Skip the ALLVx/Reports directory
            if 'ALLV' in rel_path and 'Reports' in rel_path:
                continue
            if 'reports' in rel_path:
                continue
            if 'saves' in rel_path:
                continue

            if rel_path == ".":
                rel_path = ""
            file_structure[rel_path] = []

            for file in filenames:
                if file.endswith(".py") or file.endswith(".ini") or file.endswith(".json"):
                    file_path = os.path.join(dirpath, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            file_content = f.read()
                    except Exception as e:
                        #print(f"Error reading file {file_path}: {e}")
                        file_content = ""
                    
                    # Save file content to the main report
                    file_structure[rel_path].append({"name": file, "content": file_content, "timestamp": timestamp})

                    # Extract function details for Python files
                    if file.endswith(".py"):
                        functions = extract_function_details(file_content)
                        function_definitions[file_path] = functions

                        # Append Python file content to concatenated file
                        concat_file.write(f"# File: {file_path}\n")
                        for line in file_content.splitlines():
                            if line.startswith("import") or line.startswith("from"):
                                if line not in all_imports:
                                    concat_file.write(f"{line}\n")
                                    all_imports.add(line)
                            elif line.strip() and not line.strip().startswith("#"):  # Avoid comments and empty lines
                                concat_file.write(f"{line}\n")
                        concat_file.write("\n\n")

    # Save the main report file
    with open(output_file, "w", encoding="utf-8") as outfile:
        json.dump(file_structure, outfile, indent=4)
    
    # Save the supplementary file with directory tree and function details
    supplementary_output_file = output_file.replace(".txt", "_ProjectTree.txt")
    with open(supplementary_output_file, "w", encoding="utf-8") as sfile:
        for dirpath, dirnames, files in os.walk(root_folder):
            # Skip __pycache__ directories
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            
            rel_path = os.path.relpath(dirpath, root_folder)
            if 'reports' in rel_path:
                continue
            if 'saves' in rel_path:
                continue
            if rel_path == ".":
                rel_path = ""
            sfile.write(f"Directory: {rel_path}\n")
            for file in files:
                if file.endswith(".py") or file.endswith(".ini") or file.endswith(".json"):
                    file_path = os.path.join(dirpath, file)
                    sfile.write(f"  File: {file}\n")
                    if file_path in function_definitions:
                        sfile.write("    Functions:\n")
                        for func_name, args, return_values in function_definitions[file_path]:
                            args_str = ", ".join(args)
                            returns_str = ", ".join(return_values)
                            sfile.write(f"      {func_name}({args_str}) -> {returns_str}\n")
            sfile.write("\n")
    
    print(f"Folder structure and files saved to {output_file}")
    print(f"Supplementary file with directory tree and function details saved to {supplementary_output_file}")
    print(f"Concatenated Python file saved to {concatenated_output}")

if __name__ == "__main__":
    script_path = os.path.abspath(__file__)
    version = get_version_from_path(script_path)

    root_folder = os.path.abspath(os.path.join(script_path, "../.."))  # Adjusted to be relative to script's location
    reports_dir = os.path.join(root_folder, "Reports")
    os.makedirs(reports_dir, exist_ok=True)

    output_file = os.path.join(reports_dir, f"{version}report_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt")
    concatenated_output = os.path.join(reports_dir, f"{version}_concatenated_{datetime.now().strftime('%Y%m%d%H%M%S')}.py")

    save_folder_structure(root_folder, output_file, concatenated_output)
