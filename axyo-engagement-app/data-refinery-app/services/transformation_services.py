# filename: refinery_app/services/transformation_services.py
import pandas as pd
import json
from services.core_utils import PromptManager, LLMServiceWrapper

# ==============================================================================
# Service 10: TransformationSuggester
# ==============================================================================

class TransformationSuggester:
    """
    Proactively suggests data transformations based on a data profile.
    """
    def __init__(self, prompt_manager: PromptManager, llm_wrapper: LLMServiceWrapper):
        self.prompt_manager = prompt_manager
        self.llm_wrapper = llm_wrapper

    def suggest_transformations(self, profile_report: dict) -> list[str]:
        """
        Generates a list of suggested transformation commands using an LLM.
        """
        prompt = self.prompt_manager.get_prompt(
            "suggest_data_transformations",
            variables={"profile_report": json.dumps(profile_report, indent=2, default=str)}
        )
        response = self.llm_wrapper.call_llm(prompt)
        if response["success"]:
            try:
                # BUG FIX: Correctly parse the Gemini API response structure
                suggestions_text = response["data"].get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                # Split suggestions by newline and filter out any empty lines
                return [line.strip("-* ").strip() for line in suggestions_text.split('\n') if line.strip()]
            except (IndexError, KeyError, TypeError) as e:
                print(f"ERROR parsing transformation suggestions: {e}")
                return []
        else:
            print(f"ERROR from LLM: {response['error']}")
            return []

# ==============================================================================
# Service 11: NaturalLanguageToCode
# ==============================================================================

class NaturalLanguageToCode:
    """
    Converts a natural language command into executable Python (pandas) code.
    """
    def __init__(self, prompt_manager: PromptManager, llm_wrapper: LLMServiceWrapper):
        self.prompt_manager = prompt_manager
        self.llm_wrapper = llm_wrapper

    def generate_code(self, command: str, df_sample: pd.DataFrame) -> str:
        """
        Generates a pandas code snippet from a user command.
        """
        schema = df_sample.dtypes.to_string()
        prompt = self.prompt_manager.get_prompt(
            "generate_pandas_code",
            variables={"command": command, "data_schema": schema}
        )
        response = self.llm_wrapper.call_llm(prompt)
        if response["success"]:
            try:
                # BUG FIX: Correctly parse the Gemini API response structure
                code_text = response["data"].get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                # Clean up markdown code blocks if the LLM adds them
                cleaned_code = code_text.strip().replace('```python', '').replace('```', '').strip()
                return cleaned_code
            except (IndexError, KeyError, TypeError) as e:
                 raise Exception(f"Error parsing generated code: {e}")
        else:
            raise Exception(f"Failed to generate code: {response['error']}")

# ==============================================================================
# Service 12 & 13: CodeValidator & SandboxedCodeExecutor
# ==============================================================================
class CodeValidator:
    def __init__(self):
        self.disallowed_keywords = ['import ', 'open(', 'eval(', 'exec(', 'input(', '__', '.py', 'requests.', 'urllib.', 'socket.', 'os.', 'sys.']

    def validate(self, code_snippet: str) -> (bool, list):
        found_issues = [f"Disallowed keyword '{kw}' found." for kw in self.disallowed_keywords if kw in code_snippet]
        return len(found_issues) == 0, found_issues

class SandboxedCodeExecutor:
    def execute(self, code_snippet: str, df: pd.DataFrame) -> (pd.DataFrame, str):
        df_copy = df.copy()
        local_scope = {'df': df_copy, 'pd': pd}
        try:
            exec(code_snippet, {}, local_scope)
            return local_scope['df'], None
        except Exception as e:
            return None, str(e)
