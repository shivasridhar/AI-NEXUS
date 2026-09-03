import os
from functools import lru_cache

class PromptManager:
    """
    Enterprise prompt management system.
    Loads prompts from disk and caches them in memory.
    Supports versioning by dynamically resolving template paths.
    """
    
    def __init__(self, templates_dir: str = None):
        if not templates_dir:
            # Default to the templates directory alongside this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.templates_dir = os.path.join(current_dir, "templates")
        else:
            self.templates_dir = templates_dir
            
    @lru_cache(maxsize=32)
    def load_prompt(self, name: str) -> str:
        """
        Loads a prompt template from disk by filename.
        Uses lru_cache to prevent repeated disk I/O.
        """
        file_path = os.path.join(self.templates_dir, name)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Prompt template '{name}' not found at {file_path}")
            
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def get_system_prompt(self, version: str = "v1") -> str:
        """Helper to get the core system prompt."""
        return self.load_prompt(f"system_{version}.md")
        
    def get_prompt_version(self, prompt_base_name: str, version: str = "v1") -> str:
        """Generic helper to load a specific version of a prompt."""
        return self.load_prompt(f"{prompt_base_name}_{version}.md")
