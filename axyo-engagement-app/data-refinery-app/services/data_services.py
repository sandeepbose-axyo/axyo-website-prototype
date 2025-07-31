# ==============================================================================
# File 3 of 8: services/data_services.py
# Location: refinery_app/services/data_services.py
# ==============================================================================

import json
import pandas as pd
import numpy as np

def convert_to_json_safe(obj):
    """
    Recursively traverses a dictionary or list and converts any non-JSON-serializable
    data types to standard Python types.
    """
    if isinstance(obj, dict):
        return {k: convert_to_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_safe(i) for i in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, (np.floating, float)):
        if pd.isna(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif pd.isna(obj):
        return None
    return obj

class BlueprintLoader:
    def __init__(self, blueprint_path: str):
        self.blueprint_path = blueprint_path

    def get_schema(self) -> list[dict]:
        try:
            with open(self.blueprint_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"ERROR loading blueprint: {e}")
            raise

class DataSourceConnector:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def get_data(self) -> pd.DataFrame:
        try:
            return pd.read_csv(self.file_path)
        except Exception as e:
            print(f"ERROR reading data source: {e}")
            raise

class SchemaExtractor:
    def __init__(self, connector: DataSourceConnector):
        self.connector = connector

    def get_schema(self) -> list[dict]:
        df = self.connector.get_data()
        schema = []
        for col_name, dtype in df.dtypes.items():
            schema.append({"name": col_name, "type": str(dtype)})
        return schema

class DataSampler:
    def __init__(self, connector: DataSourceConnector, sample_size: int = 100):
        self.connector = connector
        self.sample_size = sample_size

    def get_sample(self) -> pd.DataFrame:
        df = self.connector.get_data()
        return df.head(self.sample_size)

class InitialProfiler:
    def __init__(self, data_sample_df: pd.DataFrame):
        self.df = data_sample_df

    def get_profile(self) -> dict:
        if self.df.empty:
            return {"error": "DataFrame is empty."}
        
        return {
            "total_rows": len(self.df),
            "total_columns": len(self.df.columns),
            "null_counts": self.df.isnull().sum().to_dict(),
            "numeric_stats": self.df.describe().to_dict()
        }