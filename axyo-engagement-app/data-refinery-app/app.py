# ==============================================================================
# File: app.py (Complete Production Version with Final Fix)
# Location: refinery_app/app.py
# ==============================================================================

import os
import asyncio
from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template
import pandas as pd

# --- Load environment variables from .env file at the very top ---
load_dotenv()

# --- Import all your micro-services ---
from services.core_utils import PromptManager, LLMServiceWrapper
from services.data_services import (
    BlueprintLoader, DataSourceConnector, SchemaExtractor, 
    DataSampler, InitialProfiler, convert_to_json_safe
)
from services.ai_services import SemanticDescriptionGenerator, MappingSuggester
from services.transformation_services import TransformationSuggester, NaturalLanguageToCode, CodeValidator, SandboxedCodeExecutor
from services.etl_services import RecipeCompiler, AsyncFullETLRunner

# --- Initialize the Flask Application ---
app = Flask(__name__)

# --- Application Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"

SOURCE_DATA_PATH = 'real_source_data.csv'
BLUEPRINT_PATH = 'real_blueprint.json'
OUTPUT_MRD_PATH = 'model_ready_dataset.csv'

# --- API Endpoints ---

@app.route('/')
def home():
    """Serves the main HTML user interface."""
    return render_template('refinery_ui.html')
    
@app.route('/api/load-and-profile', methods=['POST'])
def load_and_profile_api():
    try:
        blueprint_loader = BlueprintLoader(BLUEPRINT_PATH)
        target_schema = blueprint_loader.get_schema()
        connector = DataSourceConnector(SOURCE_DATA_PATH)
        schema_extractor = SchemaExtractor(connector)
        source_schema = schema_extractor.get_schema()
        sampler = DataSampler(connector)
        data_sample_df = sampler.get_sample()
        profiler = InitialProfiler(data_sample_df)
        profile_report = profiler.get_profile()

        final_payload = {
            "success": True, "targetSchema": target_schema, "sourceSchema": source_schema,
            "dataSample": data_sample_df.to_dict(orient='records'), "profileReport": profile_report
        }
        return jsonify(convert_to_json_safe(final_payload))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/generate-descriptions', methods=['POST'])
def generate_descriptions_api():
    """Generates all semantic descriptions concurrently on the server."""
    data = request.get_json()
    prompt_manager = PromptManager('prompts.yaml')
    llm_wrapper = LLMServiceWrapper(api_key=GEMINI_API_KEY, api_url=GEMINI_API_URL)
    desc_generator = SemanticDescriptionGenerator(prompt_manager, llm_wrapper=llm_wrapper)
    
    try:
        # Use asyncio.run to execute the async function from a sync context
        enriched_source = asyncio.run(desc_generator.enrich_schema_async(data.get('sourceSchema')))
        enriched_target = asyncio.run(desc_generator.enrich_schema_async(data.get('targetSchema')))
        return jsonify({"success": True, "sourceSchema": enriched_source, "targetSchema": enriched_target})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/suggest-mappings', methods=['POST'])
def suggest_mappings_api():
    data = request.get_json()
    prompt_manager = PromptManager('prompts.yaml')
    llm_wrapper = LLMServiceWrapper(api_key=GEMINI_API_KEY, api_url=GEMINI_API_URL)
    mapping_suggester = MappingSuggester(prompt_manager, llm_wrapper=llm_wrapper)
    try:
        suggestions = mapping_suggester.suggest_mappings(data.get('sourceSchema'), data.get('targetSchema'))
        return jsonify({"success": True, "suggestedMappings": suggestions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/suggest-transformations', methods=['POST'])
def suggest_transformations_api():
    data = request.get_json()
    prompt_manager = PromptManager('prompts.yaml')
    llm_wrapper = LLMServiceWrapper(api_key=GEMINI_API_KEY, api_url=GEMINI_API_URL)
    suggester = TransformationSuggester(prompt_manager, llm_wrapper=llm_wrapper)
    try:
        suggestions = suggester.suggest_transformations(data.get('profileReport'))
        return jsonify({"success": True, "suggestions": suggestions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/apply-transformation', methods=['POST'])
def apply_transformation_api():
    data = request.get_json()
    df_sample = pd.DataFrame(data.get('dataSample'))
    prompt_manager = PromptManager('prompts.yaml')
    llm_wrapper = LLMServiceWrapper(api_key=GEMINI_API_KEY, api_url=GEMINI_API_URL)
    code_generator = NaturalLanguageToCode(prompt_manager, llm_wrapper=llm_wrapper)
    code_validator = CodeValidator()
    code_executor = SandboxedCodeExecutor()
    try:
        code_snippet = code_generator.generate_code(data.get('command'), df_sample)
        is_safe, errors = code_validator.validate(code_snippet)
        if not is_safe:
            raise Exception(f"Generated code is not safe: {', '.join(errors)}")
        transformed_df, error = code_executor.execute(code_snippet, df_sample)
        if error:
            raise Exception(f"Code execution failed: {error}")
        return jsonify({"success": True, "transformedSample": convert_to_json_safe(transformed_df.to_dict(orient='records')), "codeSnippet": code_snippet})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/run-full-etl', methods=['POST'])
def run_full_etl_api():
    data = request.get_json()
    compiler = RecipeCompiler()
    runner = AsyncFullETLRunner()
    connector = DataSourceConnector(SOURCE_DATA_PATH)
    try:
        final_script = compiler.compile_script(data.get('mappingConfig'), data.get('recipe'))
        success, message = runner.run_etl(final_script, connector, OUTPUT_MRD_PATH)
        if not success:
            raise Exception(message)
        return jsonify({"success": True, "message": message})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
