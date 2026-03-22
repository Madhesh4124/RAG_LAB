import json
import os
from typing import Dict, Any

class ConfigSerializer:
    @staticmethod
    def export_to_json(config: Any) -> str:
        """
        Takes a RAGConfig object and returns a clean JSON string with all pipeline settings,
        provider names, model names, and chunking parameters.
        """
        if not hasattr(config, "config_json"):
            raise ValueError("Config object must have a 'config_json' attribute.")
            
        return json.dumps(config.config_json, indent=4)

    @staticmethod
    def import_from_json(json_str: str) -> Dict[str, Any]:
        """
        Takes a JSON string, validates it has the required keys (chunker, embedder, vectorstore),
        and returns a dict ready to pass into PipelineFactory.create_pipeline().
        Raises clear ValueError messages for missing required keys or malformed JSON.
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed JSON: {str(e)}")
            
        if not isinstance(data, dict):
            raise ValueError("JSON content must be a dictionary.")

        required_keys = {"chunker", "embedder", "vectorstore"}
        missing_keys = required_keys - set(data.keys())
        if missing_keys:
            raise ValueError(f"Missing required keys in config: {', '.join(missing_keys)}")

        return data

    @staticmethod
    def export_to_file(config: Any, file_path: str) -> None:
        """
        Takes a RAGConfig object and a file path string and writes the JSON to disk.
        """
        json_str = ConfigSerializer.export_to_json(config)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json_str)

    @staticmethod
    def import_from_file(file_path: str) -> Dict[str, Any]:
        """
        Takes a file path, reads and parses the JSON, and returns the config dict.
        """
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json_str = f.read()
        except Exception as e:
            raise ValueError(f"Error reading file: {str(e)}")
            
        return ConfigSerializer.import_from_json(json_str)
