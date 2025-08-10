# filename: refinery_app/services/data_services.py
import json
import pandas as pd
import numpy as np

class BlueprintLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path
    def get_schema(self) -> list[dict]:
        try:
            with open(self.file_path, 'r') as f:
                blueprint_data = json.load(f)
                if isinstance(blueprint_data, list):
                    return blueprint_data
                return blueprint_data.get("schema", [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading blueprint: {e}")
            return []

class DataSourceConnector:
    def __init__(self, source_path: str):
        self.source_path = source_path
        self._df = None
    def get_dataframe(self) -> pd.DataFrame:
        if self._df is None:
            try:
                self._df = pd.read_csv(self.source_path, delimiter=',', engine='python')
            except FileNotFoundError:
                raise FileNotFoundError(f"Source data file not found at {self.source_path}")
            except Exception as e:
                raise IOError(f"Error reading or parsing CSV file: {e}")
        return self._df

class SchemaExtractor:
    def __init__(self, connector: DataSourceConnector):
        self.connector = connector
    def get_schema(self) -> list[dict]:
        df = self.connector.get_dataframe()
        return [{"name": col, "type": str(dtype), "description": ""} for col, dtype in df.dtypes.items()]

class DataSampler:
    def __init__(self, connector: DataSourceConnector):
        self.connector = connector
    def get_sample(self, num_rows: int = 200) -> pd.DataFrame:
        return self.connector.get_dataframe().head(num_rows)

class InitialProfiler:
    def __init__(self, df: pd.DataFrame):
        self.df = df
    def get_profile(self) -> dict:
        return {
            "total_rows": len(self.df), "total_columns": len(self.df.columns),
            "null_counts": self.df.isnull().sum().to_dict(),
            "data_types": {col: str(dtype) for col, dtype in self.df.dtypes.items()}
        }

def convert_to_json_safe(obj):
    """
    Recursively converts an object to be JSON serializable, correctly handling NaN.
    """
    # First, handle collections by recursively calling this function.
    if isinstance(obj, dict):
        return {k: convert_to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, np.ndarray)):
        return [convert_to_json_safe(i) for i in obj]

    # --- THIS IS THE FIX ---
    # Now, handle scalar (single) values. The isna() check is safe here.
    if pd.isna(obj):
        return None  # Convert numpy's NaN to Python's None, which becomes JSON's null
    
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    
    # Handle other types like strings, booleans, etc.
    return obj