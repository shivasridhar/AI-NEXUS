import os
from abc import ABC, abstractmethod
from typing import IO, Union
from pathlib import Path

class StorageProvider(ABC):
    @abstractmethod
    def save(self, path: str, content: Union[bytes, str]) -> str:
        """Saves content to the given path and returns the URI/URL."""

    @abstractmethod
    def get(self, path: str) -> bytes:
        """Retrieves content from the given path."""

    @abstractmethod
    def get_uri(self, path: str) -> str:
        """Returns the fully qualified URI for the file."""

class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: str = "storage"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, path: str, content: Union[bytes, str]) -> str:
        full_path = self.base_dir / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        mode = "wb" if isinstance(content, bytes) else "w"
        if isinstance(content, str):
            with open(full_path, mode, encoding="utf-8") as f:
                f.write(content)
        else:
            with open(full_path, mode) as f:
                f.write(content)
            
        return self.get_uri(path)

    def get(self, path: str) -> bytes:
        full_path = self.base_dir / path
        if not full_path.exists():
            raise FileNotFoundError(f"File {path} not found in storage.")
        with open(full_path, "rb") as f:
            return f.read()

    def get_uri(self, path: str) -> str:
        # For local storage, we return the path with forward slashes for URLs
        return f"{self.base_dir}/{path}".replace('\\', '/')
