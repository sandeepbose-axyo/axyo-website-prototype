# ==============================================================================
# File: core_utils.py (Complete & Corrected Version)
# Location: refinery_app/services/core_utils.py
# ==============================================================================

import yaml
import time
import requests
import json
import aiohttp 
import asyncio

class PromptManager:
    """
    A robust service to load and format prompts from an external YAML file.
    """
    def __init__(self, prompt_file_path: str):
        self.prompt_file_path = prompt_file_path
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> dict:
        try:
            with open(self.prompt_file_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            print(f"ERROR: Prompt file not found at '{self.prompt_file_path}'")
            return {}
        except yaml.YAMLError as e:
            print(f"ERROR: Could not parse YAML file '{self.prompt_file_path}': {e}")
            return {}

    def get_prompt(self, prompt_name: str, variables: dict = None) -> str:
        if not self.prompts:
            return "Error: Prompt dictionary is empty. Check file path and format."
        prompt_template = self.prompts.get(prompt_name)
        if not prompt_template:
            return f"Error: Prompt '{prompt_name}' not found in '{self.prompt_file_path}'."
        if variables:
            try:
                return prompt_template.format(**variables)
            except KeyError as e:
                return f"Error: Missing variable {e} for prompt '{prompt_name}'."
        return prompt_template

class LLMServiceWrapper:
    """
    A stateless wrapper for making calls to the Gemini API, with support for both
    synchronous and asynchronous (concurrent) requests.
    """
    def __init__(self, api_key: str, api_url: str):
        if not api_key:
            print("WARNING: No API key found. LLMServiceWrapper will run in mock mode.")
        self.api_key = api_key
        self.api_url = api_url

    def call_llm(self, prompt: str, max_retries: int = 3, timeout: int = 60) -> dict:
        """
        Calls the LLM API (synchronously) and returns the full JSON response.
        """
        if not self.api_key:
            mock_response = {"candidates": [{"content": {"parts": [{"text": "This is a mock LLM response."}]}}]}
            return {"success": True, "data": mock_response}

        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        full_url = f"{self.api_url}?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        
        for attempt in range(max_retries):
            try:
                response = requests.post(full_url, headers=headers, json=payload, timeout=timeout)
                response.raise_for_status()
                return {"success": True, "data": response.json()}
            except requests.exceptions.RequestException as e:
                print(f"ERROR: API request failed on attempt {attempt + 1}/{max_retries}. Error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return {"success": False, "error": f"API request failed after {max_retries} attempts: {e}"}
        return {"success": False, "error": "An unknown error occurred after all retries."}

    async def call_llm_async(self, session: aiohttp.ClientSession, prompt: str) -> dict:
        """
        Calls the LLM API asynchronously. Used for making many calls at once.
        """
        if not self.api_key:
            await asyncio.sleep(0.1) # Simulate network delay
            mock_response = {"candidates": [{"content": {"parts": [{"text": "This is a mock async description."}]}}]}
            return {"success": True, "data": mock_response}

        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        full_url = f"{self.api_url}?key={self.api_key}"
        headers = {"Content-Type": "application/json"}

        try:
            async with session.post(full_url, headers=headers, json=payload) as response:
                response.raise_for_status()
                return {"success": True, "data": await response.json()}
        except Exception as e:
            print(f"ERROR: Async API call failed for prompt '{prompt[:30]}...': {e}")
            return {"success": False, "error": str(e)}
