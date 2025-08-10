# filename: services/etl_services.py
import pandas as pd
import numpy as np
from multiprocessing import Process, Queue
from services.data_services import DataSourceConnector

class RecipeCompiler:
    """Compiles the final Python script from mappings and transformation steps."""
    def compile_script(self, mapping_config: dict, recipe_steps: list[str]) -> str:
        script_parts = [
            "# --- Auto-generated ETL Script ---",
            "import pandas as pd", "import numpy as np\n"
        ]
        if mapping_config:
            rename_dict_str = "{\n" + ",\n".join([f"    '{source}': '{target}'" for target, source in mapping_config.items()]) + "\n}"
            script_parts.append("# Step 1: Apply column mappings")
            script_parts.append(f"df = df.rename(columns={rename_dict_str})\n")
        if recipe_steps:
            script_parts.append("# Step 2: Apply transformation recipe")
            script_parts.extend(recipe_steps)
        return "\n".join(script_parts)

class AsyncFullETLRunner:
    """Executes the full ETL script in a sandboxed process."""
    def _worker(self, queue, script, connector, output_path):
        try:
            df = connector.get_dataframe()
            initial_rows = len(df)
            exec_globals = {'pd': pd, 'np': np, 'df': df}
            exec(script, exec_globals)
            final_df = exec_globals['df']
            final_df.to_csv(output_path, index=False)
            message = f"Successfully processed {initial_rows} rows and saved to {output_path}."
            queue.put({'success': True, 'message': message})
        except Exception as e:
            queue.put({'success': False, 'message': f"ETL script failed: {e}"})

    def run_etl(self, script: str, connector: DataSourceConnector, output_path: str, timeout_seconds: int = 60) -> tuple[bool, str]:
        q = Queue()
        process = Process(target=self._worker, args=(q, script, connector, output_path))
        process.start()
        process.join(timeout=timeout_seconds)

        if process.is_alive():
            process.terminate()
            process.join()
            return False, "Full ETL process timed out after 60 seconds."
        
        if q.empty():
            return False, "ETL process failed without returning a message."

        result = q.get()
        return result['success'], result['message']