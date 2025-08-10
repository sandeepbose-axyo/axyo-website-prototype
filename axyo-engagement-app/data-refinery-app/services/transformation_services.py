import json
import pandas as pd
import numpy as np
import ast
from multiprocessing import Process, Queue
from .core_utils import PromptManager, LLMServiceWrapper

class TransformationSuggester:
    """Uses an LLM to suggest transformations based on a profile, schema, and data sample."""
    def __init__(self, prompt_manager: PromptManager, llm_wrapper: LLMServiceWrapper):
        self.prompt_manager = prompt_manager
        self.llm_wrapper = llm_wrapper

    def suggest_transformations(self, profile_report: dict, df_sample: pd.DataFrame) -> list:
        schema_str = str(df_sample.dtypes.to_dict())
        sample_data_str = df_sample.head(3).to_json(orient='records', indent=2)
        prompt = self.prompt_manager.get_prompt(
            "suggest_data_transformations",
            variables={
                "profile_report": json.dumps(profile_report, indent=2),
                "data_schema": schema_str,
                "sample_data": sample_data_str
            }
        )
        response = self.llm_wrapper.call_llm(prompt)
        if response.get("success"):
            try:
                raw_text = response["data"].get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '[]')
                cleaned_text = raw_text.replace('```json', '').replace('```', '').strip()
                return json.loads(cleaned_text)
            except Exception as e:
                raise Exception(f"Failed to parse LLM response for transformations: {e}")
        else:
            raise Exception(f"LLM call failed: {response.get('error', 'Unknown error')}")

class NaturalLanguageToCode:
    """Converts a natural language command into pandas code."""
    def __init__(self, prompt_manager: PromptManager, llm_wrapper: LLMServiceWrapper):
        self.prompt_manager = prompt_manager
        self.llm_wrapper = llm_wrapper

    def generate_code(self, command: str, df_sample: pd.DataFrame) -> str:
        schema_str = str(df_sample.dtypes.to_dict())
        relevant_cols = [col for col in df_sample.columns if f"`{col}`" in command or f"'{col}'" in command]
        if not relevant_cols: relevant_cols = df_sample.columns[:2].tolist()
        sample_data_dict = {
            col: df_sample[col].dropna().head(3).tolist()
            for col in relevant_cols if col in df_sample.columns
        }
        sample_data_str = json.dumps(sample_data_dict, indent=2)
        prompt = self.prompt_manager.get_prompt(
            "generate_pandas_code",
            variables={ "data_schema": schema_str, "sample_data": sample_data_str, "command": command }
        )
        response = self.llm_wrapper.call_llm(prompt)
        if response.get("success"):
            try:
                code = response["data"].get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                return code.strip().replace('```python', '').replace('```', '')
            except (IndexError, KeyError, TypeError):
                raise Exception("Failed to parse code from LLM response.")
        else:
            raise Exception(f"LLM call failed: {response.get('error', 'Unknown error')}")

class CodeValidator:
    """Performs static analysis on generated code to ensure it's safe."""
    def __init__(self):
        self.allowed_names = {'pd', 'np', 'df', 'str', 'True', 'False'}
        self.allowed_attributes = {
            'to_datetime', 'fillna', 'astype', 'mean', 'median', 'mode', 'apply', 'str', 
            'replace', 'lower', 'upper', 'strip', 'split', 'to_numeric', 'round', 'dt', 'map'
        }

    def validate(self, code_snippet: str) -> tuple[bool, list]:
        errors = []
        try:
            tree = ast.parse(code_snippet)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    errors.append("Forbidden 'import' statement found.")
                if isinstance(node, ast.Attribute):
                    if node.attr not in self.allowed_attributes:
                        errors.append(f"Disallowed attribute or function: '{node.attr}'")
                if isinstance(node, ast.Name) and node.id not in self.allowed_names:
                    errors.append(f"Disallowed variable or function name: '{node.id}'")
        except SyntaxError as e:
            errors.append(f"Invalid Python syntax: {e}")
        
        forbidden_keywords = ['open(', 'eval(', 'exec(', 'os.', 'sys.', 'subprocess.']
        errors.extend([f"Forbidden keyword '{kw}' found." for kw in forbidden_keywords if kw in code_snippet])
        return not errors, list(set(errors))

class SandboxedCodeExecutor:
    """Executes a snippet of code in a separate, sandboxed process with a timeout."""
    def _worker(self, queue, code_snippet, df_copy):
        try:
            sandbox_globals = {'pd': pd, 'np': np, 'df': df_copy}
            exec(code_snippet, sandbox_globals)
            queue.put({'success': True, 'data': sandbox_globals['df']})
        except Exception as e:
            queue.put({'success': False, 'error': str(e)})

    def execute(self, code_snippet: str, df_sample: pd.DataFrame, timeout_seconds: int = 5) -> tuple[pd.DataFrame, str]:
        df_copy = df_sample.copy()
        q = Queue()
        process = Process(target=self._worker, args=(q, code_snippet, df_copy))
        process.start()
        process.join(timeout=timeout_seconds)

        if process.is_alive():
            process.terminate()
            process.join()
            return df_sample, "Code execution timed out after 5 seconds."

        if q.empty():
            return df_sample, "Execution process failed without a clear error."

        result = q.get()
        if result['success']:
            return result['data'], None
        else:
            return df_sample, result['error']
