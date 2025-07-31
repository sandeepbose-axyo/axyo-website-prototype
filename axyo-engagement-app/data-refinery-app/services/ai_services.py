# filename: refinery_app/services/ai_services.py
import json
import asyncio
import aiohttp
from services.core_utils import PromptManager, LLMServiceWrapper

# ==============================================================================
# Service 8: SemanticDescriptionGenerator (Optimized with Async)
# ==============================================================================

class SemanticDescriptionGenerator:
    """
    Uses an LLM to generate a business-friendly description for schema columns.
    Optimized to run API calls concurrently for much faster performance.
    """
    def __init__(self, prompt_manager: PromptManager, llm_wrapper: LLMServiceWrapper):
        self.prompt_manager = prompt_manager
        self.llm_wrapper = llm_wrapper

    async def _get_single_description_async(self, session, column_name: str, data_type: str) -> dict:
        """
        Asynchronously generates a description for a single column.
        """
        prompt = self.prompt_manager.get_prompt(
            "generate_semantic_description",
            variables={"column_name": column_name, "data_type": data_type}
        )
        
        # Use the async call method from the wrapper
        response = await self.llm_wrapper.call_llm_async(session, prompt)
        
        description = f"Error: {response.get('error')}"
        if response.get("success"):
            try:
                description = response["data"].get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '').strip()
            except (IndexError, KeyError, TypeError):
                description = "Error parsing LLM response."

        return {"name": column_name, "description": description}

    async def enrich_schema_async(self, schema: list[dict]) -> list[dict]:
        """
        Takes a schema and adds an AI-generated description to each column concurrently.
        """
        async with aiohttp.ClientSession() as session:
            tasks = [self._get_single_description_async(session, col["name"], col["type"]) for col in schema]
            results = await asyncio.gather(*tasks)

        description_map = {result["name"]: result["description"] for result in results}

        enriched_schema = [{**col, "description": description_map.get(col["name"])} for col in schema]
        return enriched_schema

# ==============================================================================
# Service 9: MappingSuggester
# ==============================================================================

class MappingSuggester:
    """
    Uses an LLM to suggest 1:1 mappings between a source and target schema.
    """
    def __init__(self, prompt_manager: PromptManager, llm_wrapper: LLMServiceWrapper):
        self.prompt_manager = prompt_manager
        self.llm_wrapper = llm_wrapper

    def suggest_mappings(self, source_schema: list[dict], target_schema: list[dict]) -> dict:
        """
        Generates a dictionary of suggested mappings.
        """
        prompt = self.prompt_manager.get_prompt(
            "suggest_schema_mapping",
            variables={
                "source_schema": json.dumps(source_schema, indent=2),
                "target_schema": json.dumps(target_schema, indent=2)
            }
        )
        
        response = self.llm_wrapper.call_llm(prompt)
        
        if response.get("success"):
            try:
                llm_output_str = response["data"].get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                cleaned_str = llm_output_str.strip().replace('```json', '').replace('```', '')
                return json.loads(cleaned_str)
            except (json.JSONDecodeError, IndexError, KeyError, TypeError) as e:
                print(f"ERROR: Could not parse LLM response for mapping: {e}")
                return {"error": "Failed to parse LLM response."}
        else:
            return {"error": f"LLM call failed: {response.get('error', 'Unknown error')}"}
