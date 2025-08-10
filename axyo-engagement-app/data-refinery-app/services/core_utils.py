# filename: services/core_utils.py
import yaml
import os
import json
import aiohttp
import requests

class PromptManager:
    """
    Manages and formats prompts. Prompts are stored directly in a dictionary.
    """
    def __init__(self, file_path: str = None):
        self._prompts = {
            'generate_simple_description': """Analyze the following database column name and data type, and provide a single, concise, one-sentence business description of its likely purpose.

**CRITICAL RULES:**
1. Respond with ONLY the raw sentence.
2. Do NOT include any preamble.
---
COLUMN NAME: {column_name}
DATA TYPE: {data_type}
---
DESCRIPTION:""",

            'suggest_schema_mapping': """You are an expert data analyst. Your task is to map columns from a source schema to a target schema based on their names and business descriptions.
Provide only the most logical 1:1 mappings. If a target column has no direct match in the source, do not include it in the output.

**CRITICAL RULES:**
1. Respond with ONLY a valid JSON object.
2. Do NOT include any text, explanations, or markdown like ```json before or after the JSON object.
3. The keys of the JSON object must be target column names, and the values must be the corresponding source column names.
---
SOURCE SCHEMA:
{source_schema}
---
TARGET SCHEMA:
{target_schema}
---
JSON RESPONSE:""",

            'suggest_data_transformations': """You are an expert data analyst. Based on the data quality report, schema, and sample data below, provide a list of specific, actionable data cleaning or feature engineering steps.

**CRITICAL RULES:**
1. Respond with ONLY a valid JSON array of objects.
2. Do NOT include any text before or after the JSON array.
3. Each object in the array must have "title", "context", and "action" keys.
4. The "action" string should always begin with "Action:".
---
DATA QUALITY REPORT:
{profile_report}
---
DATA SCHEMA:
{data_schema}
---
SAMPLE DATA:
{sample_data}
---
JSON RESPONSE:""",
            
            'generate_pandas_code': """You are an expert Python programmer specializing in the pandas library.
Your task is to convert a natural language command into a single, executable line or block of Python code that transforms a pandas DataFrame named 'df'.

**GOOD CODE EXAMPLE (for cleaning and converting a column):**
```python
# First, ensure the column is a string, then remove non-numeric characters
df['column_name'] = df['column_name'].astype(str).str.replace(r'[^0-9.-]', '', regex=True)
# Then, convert to a numeric type, turning errors into NaN
df['column_name'] = pd.to_numeric(df['column_name'], errors='coerce')
# Finally, impute the median of the now-numeric column
df['column_name'].fillna(df['column_name'].median(), inplace=True)
```

**CRITICAL RULES:**
1. The DataFrame is ALWAYS named 'df'.
2. The final output MUST be only the raw Python code. Do NOT include any explanations, comments, or markdown.
3. NEVER include an `import` statement. The pandas library (`pd`) is already available.
4. When using `pd.to_numeric` or `pd.to_datetime`, ALWAYS use `errors='coerce'`. Do NOT use it for other type conversions like `.astype(bool)`.
5. All operations must be performed on a DataFrame column (e.g., `df['col'] = ...`). Do not operate on raw lists of values.
6. Do not use any functions that access the file system, network, or external libraries.
7. Focus on column-level transformations. Do NOT perform table-level operations like `pd.merge` or `df.join`.
---
DATA SCHEMA (column_name: dtype):
{data_schema}
---
SAMPLE DATA (first 3 non-null rows of relevant columns):
{sample_data}
---
USER COMMAND:
"{command}"
---
PYTHON CODE:"""
        }

    def get_prompt(self, key: str, variables: dict = None) -> str:
        prompt_template = self._prompts.get(key)
        if not prompt_template:
            raise KeyError(f"Prompt key '{key}' not found in the internal dictionary.")
        if variables:
            try:
                return prompt_template.format(**variables)
            except KeyError as e:
                raise KeyError(f"Missing variable {e} for prompt key '{key}'")
        return prompt_template

class LLMServiceWrapper:
    def __init__(self, api_key: str, api_url: str):
        if not api_key or not api_url:
            raise ValueError("API key and URL are required for LLMServiceWrapper")
        self.api_key = api_key
        self.api_url = f"{api_url}?key={api_key}"
        self.headers = {'Content-Type': 'application/json'}

    async def call_llm_async(self, session, prompt: str) -> dict:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            async with session.post(self.api_url, headers=self.headers, json=payload) as response:
                response.raise_for_status()
                return {"success": True, "data": await response.json()}
        except aiohttp.ClientError as e:
            return {"success": False, "error": f"API call failed with status: {e.status}"}

    def call_llm(self, prompt: str) -> dict:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.exceptions.RequestException as e:
            error_message = "API call failed. Check server logs for details."
            if e.response is not None:
                error_message = f"API call failed with status: {e.response.status_code}"
            return {"success": False, "error": error_message}
