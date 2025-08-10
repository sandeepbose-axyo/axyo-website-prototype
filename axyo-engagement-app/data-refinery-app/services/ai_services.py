import json
import asyncio
import aiohttp
import pandas as pd
from services.core_utils import PromptManager, LLMServiceWrapper

class SemanticDescriptionGenerator:
    def __init__(self, prompt_manager: PromptManager, llm_wrapper: LLMServiceWrapper):
        self.prompt_manager = prompt_manager
        self.llm_wrapper = llm_wrapper

    async def _get_single_description_async(self, session, column: dict) -> dict:
        column_name, data_type = column['name'], column['type']
        try:
            prompt = self.prompt_manager.get_prompt("generate_simple_description", variables={"column_name": column_name, "data_type": data_type})
            response = await self.llm_wrapper.call_llm_async(session, prompt)
            if not response.get("success"): raise Exception(response.get('error', 'Unknown LLM error'))
            description = response["data"].get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '').strip()
        except Exception as e:
            description = f"Error generating description for {column_name}: {e}"
        return {"name": column_name, "description": description}

    async def enrich_schema_async(self, schema: list[dict], **kwargs) -> list[dict]:
        async with aiohttp.ClientSession() as session:
            tasks = [self._get_single_description_async(session, col) for col in schema]
            results = await asyncio.gather(*tasks)
        description_map = {result["name"]: result["description"] for result in results}
        return [{**col, "description": description_map.get(col["name"], col.get("description"))} for col in schema]

class MappingSuggester:
    def __init__(self, prompt_manager: PromptManager, llm_wrapper: LLMServiceWrapper):
        self.prompt_manager = prompt_manager
        self.llm_wrapper = llm_wrapper

    def suggest_mappings(self, source_schema: list[dict], target_schema: list[dict]) -> dict:
        prompt = self.prompt_manager.get_prompt("suggest_schema_mapping", variables={"source_schema": json.dumps(source_schema, indent=2), "target_schema": json.dumps(target_schema, indent=2)})
        response = self.llm_wrapper.call_llm(prompt)
        if response.get("success"):
            try:
                llm_output_str = response["data"].get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                cleaned_str = llm_output_str.strip().replace('```json', '').replace('```', '')
                return json.loads(cleaned_str)
            except Exception as e:
                return {"error": f"Failed to parse LLM response: {e}"}
        else:
            return {"error": f"LLM call failed: {response.get('error', 'Unknown error')}"}