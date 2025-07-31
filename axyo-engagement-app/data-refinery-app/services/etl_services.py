# ==============================================================================
# File 6 of 8: services/etl_services.py
# Location: refinery_app/services/etl_services.py
# ==============================================================================

import pandas as pd

class RecipeCompiler:
    def compile_script(self, mapping_config: dict, code_snippets: list[str]) -> str:
        rename_dict = {source: target for target, source in mapping_config.items()}
        rename_str = f"df = df.rename(columns={rename_dict})"
        
        full_script = "# --- Auto-generated ETL Script ---\n\n"
        full_script += "# Step 1: Rename columns based on mapping\n"
        full_script += rename_str + "\n\n"
        full_script += "# Step 2: Apply user-defined transformations\n"
        full_script += "\n".join(code_snippets)
        return full_script

class AsyncFullETLRunner:
    def run_etl(self, final_etl_script: str, connector, output_path: str) -> (bool, str):
        try:
            df = connector.get_data()
            local_scope = {'df': df, 'pd': pd}
            exec(final_etl_script, {}, local_scope)
            final_df = local_scope['df']
            final_df.to_csv(output_path, index=False)
            return True, f"Successfully processed {len(final_df)} rows and saved to {output_path}"
        except Exception as e:
            return False, f"ETL process failed: {e}"