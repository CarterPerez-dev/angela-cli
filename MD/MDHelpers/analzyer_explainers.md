**File 1: `angela/ai/analyzer.py` (ErrorAnalyzer)**

**Class: `ErrorAnalyzer`**

1.  **`def _extract_key_error(self, error: str) -> str:`**
    *   **Name:** `_extract_key_error`
    *   **Purpose:** This function attempts to distill a potentially long and verbose error message string down to its most salient line or part. It prioritizes lines containing "error", lines matching known error patterns, or falls back to the first line.
    *   **Snippets:**
        ```python
        lines = [line.strip() for line in error.splitlines() if line.strip()]
        if not lines:
            return "Unknown error"
        ```
        ```python
        for line in lines[:3]:
            if "error" in line.lower():
                return line
            for pattern, _, _ in self.ERROR_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    return line
        return lines[0] # Fallback
        ```

2.  **`def _match_error_pattern(self, error: str) -> Optional[Tuple[str, str, List[str]]]:`**
    *   **Name:** `_match_error_pattern`
    *   **Purpose:** It iterates through a predefined list of common error regular expression patterns (`self.ERROR_PATTERNS`). If the input `error` string matches one of these patterns, it returns a tuple containing the matched pattern, a human-readable explanation of the error, and a list of potential fix suggestions.
    *   **Snippets:**
        ```python
        for pattern, explanation, fixes in self.ERROR_PATTERNS:
            if re.search(pattern, error, re.IGNORECASE):
                return (pattern, explanation, fixes)
        return None
        ```
        *Self.ERROR\_PATTERNS example:*
        ```python
        # (r'No such file or directory', 'The specified file or directory does not exist', ['Check path', ...])
        ```

3.  **`def _analyze_command_structure(self, command: str) -> List[str]:`**
    *   **Name:** `_analyze_command_structure`
    *   **Purpose:** This function performs a basic structural analysis of the input `command` string to identify common syntactical issues. It uses `shlex.split` for tokenization and checks for problems like empty commands, redirects/pipes used as commands, or missing arguments for common utilities (e.g., `cp`, `grep`).
    *   **Snippets:**
        ```python
        if not command.strip():
            issues.append("Command is empty")
        ```
        ```python
        tokens = shlex.split(command)
        base_cmd = tokens[0]
        if base_cmd in ['>', '>>', '<', '|']:
            issues.append(f"{base_cmd} symbol used as command")
        ```
        ```python
        if base_cmd in ['cp', 'mv'] and len(tokens) == 1:
            issues.append(f"{base_cmd} requires source and destination arguments")
        ```

4.  **`def _check_file_references(self, command: str, error: str) -> List[Dict[str, Any]]:`**
    *   **Name:** `_check_file_references`
    *   **Purpose:** It attempts to identify file or directory paths mentioned in the `command` string. For each potential path, it checks if it exists. If not, it suggests this as an issue and may even look for similarly named files in the parent directory as typo suggestions. It also checks for permission issues if "Permission denied" is in the `error` string.
    *   **Snippets:**
        ```python
        tokens = shlex.split(command)
        for token in tokens[1:]: # Iterate over arguments
            if token.startswith('-'): continue # Skip options
            potential_paths.append(token)
        ```
        ```python
        path = Path(path_str)
        if not path.exists():
            issue["exists"] = False
            issue["suggestion"] = f"File/directory does not exist: {path_str}"
            # ... (logic for similar_files) ...
        elif "Permission denied" in error and not os.access(path, os.R_OK):
            issue["permission"] = False
        ```

---

**File 2: `angela/ai/intent_analyzer.py` (IntentAnalyzer)**

**Class: `IntentAnalyzer`**

1.  **`def _extract_entities(self, normalized: str, intent_type: str) -> Dict[str, Any]:`**
    *   **Name:** `_extract_entities`
    *   **Purpose:** Based on the determined `intent_type` (e.g., "file\_search", "file\_operation"), this function uses regular expressions to parse the `normalized` request string and extract relevant entities. For example, for "file\_search", it tries to find patterns and directory names.
    *   **Snippets:**
        ```python
        if intent_type == "file_search":
            pattern_match = re.search(r'matching (.+?)(?: in | with | containing |$)', normalized)
            if pattern_match:
                entities["pattern"] = pattern_match.group(1)
        ```
        ```python
        elif intent_type == "file_operation":
            path_match = re.search(r'(?:file|directory|folder) (?:called |named |)["\'"]?([\w\./]+)["\'"]?', normalized)
            if path_match:
                entities["path"] = path_match.group(1)
        ```

2.  **`def _get_intent_description(self, intent_type: str, entities: Dict[str, Any]) -> str:`**
    *   **Name:** `_get_intent_description`
    *   **Purpose:** Generates a human-readable string describing a potential intent, often incorporating the extracted `entities`. This is used when presenting disambiguation options to the user.
    *   **Snippets:**
        ```python
        if intent_type == "file_search":
            pattern = entities.get("pattern", "files")
            directory = entities.get("directory", "current directory")
            return f"Search for {pattern} in {directory}"
        ```
        ```python
        elif intent_type == "file_operation":
            path = entities.get("path", "a file")
            return f"Perform operation on file: {path}"
        ```

---

**File 3: `angela/ai/content_analyzer_extensions.py` (EnhancedContentAnalyzer)**

**Class: `EnhancedContentAnalyzer` (inherits from `ContentAnalyzer`)**

1.  **`async def _analyze_python(self, file_path, request=None):`**
    *   **Name:** `_analyze_python`
    *   **Purpose:** A specialized analyzer for Python files. It uses Python's `ast` (Abstract Syntax Tree) module to parse the code and extract structural information like class definitions, function definitions (including parameters and methods within classes), and import statements.
    *   **Snippets:**
        ```python
        import ast
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append({"name": node.name, "line": node.lineno, ...})
            elif isinstance(node, ast.FunctionDef):
                functions.append({"name": node.name, "line": node.lineno, ...})
        ```
        ```python
        return {
            "classes": classes,
            "functions": functions,
            "imports": self._extract_python_imports(content)
        }
        ```

2.  **`def _extract_python_imports(self, content):`**
    *   **Name:** `_extract_python_imports`
    *   **Purpose:** This helper function is used by `_analyze_python` to specifically parse Python code content (as a string) using regular expressions to find and list all `import` and `from ... import ...` statements.
    *   **Snippets:**
        ```python
        import_pattern = r'^(?:from\s+(\S+)\s+)?import\s+(.+)$'
        for line in content.splitlines():
            match = re.match(import_pattern, line.strip())
            if match:
                from_module, imported = match.groups()
                imports.append({"from_module": from_module, "imported": [...]})
        ```

3.  **`async def _analyze_typescript(self, file_path, request=None):`**
    *   **Name:** `_analyze_typescript`
    *   **Purpose:** A specialized analyzer for TypeScript files. It first uses a helper `_extract_typescript_types` for basic type/interface extraction via regex. Then, for more comprehensive analysis, it prepares a prompt with the TypeScript code and sends it to an AI model (Gemini) to identify interfaces, types, classes, functions, design patterns, and dependencies.
    *   **Snippets:**
        ```python
        types = self._extract_typescript_types(content) # Regex-based
        ```
        ```python
        prompt = f"""
Analyze this TypeScript file and extract key information:
```typescript
{content[:20000]}
```
Identify and describe: ...
"""
        response = await self._get_ai_analysis(prompt) # AI-based
        return {"types": types, "ai_analysis": response}
        ```

4.  **`def _extract_typescript_types(self, content: str) -> List[Dict[str, Any]]:`**
    *   **Name:** `_extract_typescript_types`
    *   **Purpose:** This helper function uses regular expressions to perform a basic extraction of `interface` and `type` definitions from TypeScript code content.
    *   **Snippets:**
        ```python
        interface_pattern = r'interface\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{([^}]*)\}'
        for match in re.finditer(interface_pattern, content, re.DOTALL):
            # ... extract name, extends, properties ...
            interfaces.append(...)
        ```
        ```python
        type_pattern = r'type\s+(\w+)\s*=\s*(.+?);'
        for match in re.finditer(type_pattern, content, re.DOTALL):
            types.append(...)
        ```

5.  **`async def _analyze_javascript(self, file_path, request=None):`**
    *   **Name:** `_analyze_javascript`
    *   **Purpose:** Placeholder for a specialized JavaScript analyzer. The comment indicates it would be similar to TypeScript but without type information. The actual implementation is `pass`.
    *   **Snippets:**
        ```python
        # Similar implementation to TypeScript but without type information
        pass
        ```

6.  **`async def _analyze_json(self, file_path, request=None):`**
    *   **Name:** `_analyze_json`
    *   **Purpose:** A specialized analyzer for JSON files. It reads the file, parses it using `json.loads()`, and then attempts to infer a basic schema for the JSON data using `_infer_json_schema`. It also provides keys (if it's an object) or length (if it's an array) and a preview.
    *   **Snippets:**
        ```python
        data = json.loads(content)
        schema = self._infer_json_schema(data)
        return {
            "schema": schema,
            "keys": list(data.keys()) if isinstance(data, dict) else [], ...
        }
        ```

7.  **`def _infer_json_schema(self, data):`**
    *   **Name:** `_infer_json_schema`
    *   **Purpose:** This recursive helper function takes a piece of parsed JSON data (a dictionary, list, or primitive) and tries to determine its basic schema structure (e.g., "object" with properties, "array" with item types, "string", "number").
    *   **Snippets:**
        ```python
        if isinstance(data, dict):
            schema = {}
            for key, value in data.items():
                schema[key] = self._get_type(value) # Recursive call
            return {"type": "object", "properties": schema}
        elif isinstance(data, list):
            # ... logic to determine item type, possibly "mixed" ...
            return {"type": "array", "items": item_type_schema}
        ```

8.  **`def _get_type(self, value):`**
    *   **Name:** `_get_type`
    *   **Purpose:** A helper for `_infer_json_schema`. Given a single JSON value, it returns a dictionary describing its basic JSON type (e.g., `{"type": "string"}`, `{"type": "integer"}`). For nested objects/arrays, it makes recursive calls.
    *   **Snippets:**
        ```python
        if isinstance(value, bool):
            return {"type": "boolean"}
        elif isinstance(value, str):
            return {"type": "string"}
        elif isinstance(value, dict): # Recursive part
            schema = {}
            for key, val in value.items():
                schema[key] = self._get_type(val)
            return {"type": "object", "properties": schema}
        ```

9.  **`async def _analyze_yaml(self, ...)`**, **`async def _analyze_markdown(self, ...)`**, **`async def _analyze_html(self, ...)`**, **`async def _analyze_css(self, ...)`**, **`async def _analyze_sql(self, ...)`**
    *   **Name(s):** `_analyze_yaml`, `_analyze_markdown`, etc.
    *   **Purpose:** These are placeholders for specialized analyzers for various other file types (YAML, Markdown, HTML, CSS, SQL). The comments suggest what they might extract (e.g., headings for Markdown, selectors for CSS). The actual implementations are `pass`.
    *   **Snippets (Example from `_analyze_markdown`):**
        ```python
        # Extract headings, links, etc.
        pass
        ```

10. **`async def _get_ai_analysis(self, prompt):`**
    *   **Name:** `_get_ai_analysis`
    *   **Purpose:** A utility function to send a given `prompt` to the AI service (Gemini) and return the text response. This is used by other `_analyze_XYZ` methods that leverage AI for deeper analysis (like `_analyze_typescript`).
    *   **Snippets:**
        ```python
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=4000
        )
        response = await gemini_client.generate_text(api_request)
        return response.text
        ```

---

**File 4: `angela/ai/semantic_analyzer.py` (SemanticAnalyzer)**

**Class: `SemanticAnalyzer`**

1.  **`def _get_extensions_for_language(self, language: str) -> List[str]:`**
    *   **Name:** `_get_extensions_for_language`
    *   **Purpose:** A helper method that returns a list of common file extensions associated with a given programming `language` string (e.g., ".py", ".pyi" for "python").
    *   **Snippets:**
        ```python
        extensions_map = {
            "python": [".py", ".pyi", ".pyx"],
            "javascript": [".js", ".jsx", ".mjs"],
            # ...
        }
        return extensions_map.get(language.lower(), [])
        ```

2.  **`def _matches_glob_pattern(self, path: str, pattern: str) -> bool:`**
    *   **Name:** `_matches_glob_pattern`
    *   **Purpose:** A utility to check if a given file `path` matches a `glob` (shell-style wildcard) `pattern`. It uses the `fnmatch` module. This is used for excluding certain directories/files (like `node_modules`) from project-wide analysis.
    *   **Snippets:**
        ```python
        import fnmatch
        return fnmatch.fnmatch(path, pattern)
        ```

3.  **`def _analyze_python_file(self, file_path: Path, module: Module) -> bool:`**
    *   **Name:** `_analyze_python_file`
    *   **Purpose:** This is the core Python file analyzer. It reads the file, parses it into an Abstract Syntax Tree (AST) using Python's `ast` module, and then walks this tree to extract detailed semantic information. It populates the provided `Module` object with `Import`, `Function`, `Class`, and `Variable` entities, including details like parameters, docstrings, base classes, decorators, called functions, and basic code metrics (line counts, complexity).
    *   **Snippets:**
        ```python
        tree = ast.parse(content, filename=str(file_path))
        module.docstring = ast.get_docstring(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # ... create Import object and add to module.imports ...
            elif isinstance(node, ast.FunctionDef):
                # ... create Function object, calculate complexity, find called functions ...
                # ... add to module.functions or class.methods ...
            elif isinstance(node, ast.ClassDef):
                # ... create Class object, find attributes ...
                # ... add to module.classes ...
        ```
        ```python
        module.code_metrics = { "total_lines": ..., "complexity": ..., ... }
        ```

4.  **`def _get_type_annotation(self, annotation) -> Optional[str]:`**
    *   **Name:** `_get_type_annotation`
    *   **Purpose:** A helper for `_analyze_python_file`. Given an AST node representing a type annotation (e.g., from a function parameter or return type), it attempts to convert it into a string representation of that type (e.g., "str", "List[int]").
    *   **Snippets:**
        ```python
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Attribute): # e.g., typing.List
            return f"{annotation.value.id}.{annotation.attr}"
        elif isinstance(annotation, ast.Subscript): # e.g., List[int]
            # ... logic to format subscripted types ...
        ```

5.  **`def _get_last_line(self, node) -> int:`**
    *   **Name:** `_get_last_line`
    *   **Purpose:** A helper for `_analyze_python_file`. It determines the last line number occupied by a given AST `node`. It uses `node.end_lineno` if available (Python 3.8+) or recursively finds the maximum line number among the node and its children.
    *   **Snippets:**
        ```python
        if hasattr(node, 'end_lineno'):
            return node.end_lineno
        max_lineno = node.lineno
        for child in ast.iter_child_nodes(node):
            max_lineno = max(max_lineno, self._get_last_line(child))
        return max_lineno
        ```

6.  **`def _calculate_complexity(self, node) -> int:`**
    *   **Name:** `_calculate_complexity`
    *   **Purpose:** A helper for `_analyze_python_file`. It calculates a simplified cyclomatic complexity for a given function AST `node` by counting branching statements (if, while, for, try/except) and boolean operators (and, or).
    *   **Snippets:**
        ```python
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.Try)):
                complexity += 1
            elif isinstance(child, ast.BoolOp) and isinstance(child.op, (ast.And, ast.Or)):
                complexity += len(child.values) - 1
        return complexity
        ```

7.  **`async def _analyze_javascript_file(self, file_path: Path, module: Module) -> bool:`**
    *   **Name:** `_analyze_javascript_file`
    *   **Purpose:** Analyzes JavaScript files. This implementation uses a simpler, regex-based approach to extract imports/requires, functions, and classes. It's less robust than AST parsing but provides a basic level of analysis. It also calculates simple code metrics.
    *   **Snippets:**
        ```python
        # Regex for imports
        import_patterns = [ r'import\s+{([^}]+)}\s+from\s+[\'"]([^\'"]+)[\'"]', ... ]
        for line in content.splitlines():
            for pattern in import_patterns:
                for match in re.finditer(pattern, line):
                    # ... create Import object ...
        ```
        ```python
        # Regex for functions
        function_patterns = [ r'function\s+(\w+)\s*\(([^)]*)\)', ... ]
        for pattern in function_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                # ... create Function object ...
        ```

8.  **`async def _analyze_typescript_file(self, file_path: Path, module: Module) -> bool:`**
    *   **Name:** `_analyze_typescript_file`
    *   **Purpose:** Analyzes TypeScript files. It first leverages the `_analyze_javascript_file` for common JS constructs and then adds regex-based extraction for TypeScript-specific features like `interface` and `type` definitions. It also attempts to find return type annotations for functions.
    *   **Snippets:**
        ```python
        js_result = await self._analyze_javascript_file(file_path, module) # Base analysis
        ```
        ```python
        # Regex for interfaces
        interface_pattern = r'interface\s+(\w+)(?:\s+extends\s+(\w+))?\s*{'
        for match in re.finditer(interface_pattern, content, re.MULTILINE):
            # ... create Class object (treating interface as class) ...
        ```
        ```python
        # Regex for types
        type_pattern = r'type\s+(\w+)\s*=\s*\{[^}]*\}'
        for match in re.finditer(type_pattern, content, re.MULTILINE):
            # ... create Variable object (treating type as variable) ...
        ```

9.  **`async def _analyze_with_llm(self, file_path: Path, module: Module) -> bool:`**
    *   **Name:** `_analyze_with_llm`
    *   **Purpose:** This method is a fallback analyzer for languages where specific parsers are not implemented (e.g., Java, C#, Ruby). It reads the file content, constructs a detailed prompt asking an LLM (Gemini) to extract semantic information (imports, functions, classes, variables, metrics) in a specific JSON format, and then parses this JSON to populate the `Module` object.
    *   **Snippets:**
        ```python
        prompt = f"""
Analyze this {language} source code and extract the key semantic information:
```{language}
{content} # Truncated if too long
```
Please return a JSON response with the following structure:
# ... detailed JSON structure definition ...
"""
        ```
        ```python
        api_request = GeminiRequest(prompt=prompt, max_tokens=4000, temperature=0.1)
        response = await gemini_client.generate_text(api_request)
        data = json.loads(response_text) # Parse LLM's JSON output
        # ... populate module.imports, module.functions, etc., from 'data' ...
        ```

10. **`def _analyze_cross_module_references(self, modules: Dict[str, Module]) -> None:`**
    *   **Name:** `_analyze_cross_module_references`
    *   **Purpose:** After individual files (modules) have been analyzed, this function attempts to identify relationships *between* them. It looks at function calls and class inheritance across different modules to populate the `references` and `dependencies` lists within each `CodeEntity`.
    *   **Snippets:**
        ```python
        # Build a map of entity names to their modules
        entity_map = {func_name: module_path for module_path, module in modules.items() for func_name in module.functions}
        ```
        ```python
        for module_path, module in modules.items():
            for func_name, func in module.functions.items():
                for called_func in func.called_functions:
                    if called_func in entity_map and entity_map[called_func] != module_path:
                        target_module = modules[entity_map[called_func]]
                        target_func = target_module.functions[called_func]
                        target_func.references.append((module_path, func.line_start))
                        func.dependencies.append(called_func)
        ```

---

**File 5: `angela/ai/content_analyzer.py` (ContentAnalyzer - the base class for EnhancedContentAnalyzer)**

**Class: `ContentAnalyzer`**

1.  **`def _build_analysis_prompt(self, content: str, file_info: Dict[str, Any], request: Optional[str]) -> str:`**
    *   **Name:** `_build_analysis_prompt`
    *   **Purpose:** Constructs a prompt to send to an AI (Gemini) for analyzing the `content` of a file. The prompt is tailored based on `file_info` (like language) and an optional specific `request` from the user. It includes different "analysis focus" points depending on the language (e.g., for Python, focus on functions/classes; for documents, focus on topics/structure).
    *   **Snippets:**
        ```python
        if language == "Python":
            analysis_focus = """
- Identify main functions and classes
- Describe the overall code structure ..."""
        elif file_type == "document" or language == "Markdown":
            analysis_focus = """
- Summarize the main topics and sections ..."""
        ```
        ```python
        if request:
            prompt = f"Analyze ... with this specific request: \"{request}\"\n```{content[:50000]}```\nAnalysis:"
        else:
            prompt = f"Analyze ...\n{analysis_focus}\n```{content[:50000]}```\nAnalysis:"
        ```

2.  **`def _build_manipulation_prompt(self, content: str, file_info: Dict[str, Any], instruction: str) -> str:`**
    *   **Name:** `_build_manipulation_prompt`
    *   **Purpose:** Creates a prompt for the AI to modify file `content` based on a natural language `instruction`. The prompt includes the original content and asks the AI to return the *entire* modified content.
    *   **Snippets:**
        ```python
        prompt = f"""
You are given a {language} file and a request to modify it.
File content:
```{content}```
Request: {instruction}
Return the ENTIRE modified content...
Modified file content:
```
"""
        ```

3.  **`def _extract_modified_content(self, response: str, original_content: str) -> str:`**
    *   **Name:** `_extract_modified_content`
    *   **Purpose:** This function attempts to parse the AI's `response` (from a manipulation request) to get just the modified file content. It looks for content enclosed in triple backticks (```) or specific header patterns like "Modified file content:". It has a fallback to return the original content if extraction is unclear.
    *   **Snippets:**
        ```python
        match = re.search(r'```(?:.*?)\n(.*?)```', response, re.DOTALL)
        if match:
            return match.group(1)
        ```
        ```python
        patterns = [ r'Modified file content:\n(.*)', ... ]
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                return match.group(1).strip()
        ```

4.  **`def _parse_search_results(self, response: str, content: str, context_lines: int) -> List[Dict[str, Any]]:`**
    *   **Name:** `_parse_search_results`
    *   **Purpose:** Parses the AI's `response` (from a content search request) to identify individual search matches. It looks for line number indications (e.g., "Lines 10-15") and code blocks in the response to structure each match, including the matched content with surrounding `context_lines`.
    *   **Snippets:**
        ```python
        line_patterns = [ r'Lines? (\d+)(?:-(\d+))?', ... ]
        for section in re.split(r'\n\s*\n', response): # Process sections of response
            for pattern in line_patterns:
                line_match = re.search(pattern, section)
                if line_match:
                    line_start = int(line_match.group(1))
                    # ...
                    break
            # ... extract code_block and explanation ...
            match_content = '\n'.join(content_lines[context_start:context_end + 1])
            matches.append({"line_start": line_start, "content": match_content, ...})
        ```
