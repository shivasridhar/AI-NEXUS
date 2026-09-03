from typing import Dict, List, Type

from app.services.connectors.base_connector import BaseConnector


class ConnectorAlreadyRegisteredError(Exception):
    """Raised when a connector name is already registered."""


class ConnectorNotFoundError(Exception):
    """Raised when an unregistered connector is requested."""


class ConnectorRegistry:
    """
    Central registry for discovering and storing connector classes.
    It maps string identifiers (e.g., 'wazuh', 'aws_iam') to connector classes.
    """

    # Shared in-memory state for registration
    _registry: Dict[str, Type[BaseConnector]] = {}

    @classmethod
    def register(cls, name: str):
        """
        Decorator to register a concrete connector class under a specific name.
        Allows for fully dynamic discovery without hardcoding imports.
        """

        def wrapper(connector_class: Type[BaseConnector]):
            if not issubclass(connector_class, BaseConnector):
                raise TypeError(
                    f"Class {connector_class.__name__} must inherit from BaseConnector"
                )
            if name in cls._registry:
                raise ConnectorAlreadyRegisteredError(
                    f"Connector '{name}' is already registered."
                )
            cls._registry[name] = connector_class
            return connector_class

        return wrapper

    @classmethod
    def get(cls, name: str) -> Type[BaseConnector]:
        """
        Retrieve a connector class by its registered name.
        """
        if name not in cls._registry:
            raise ConnectorNotFoundError(
                f"Connector '{name}' is not registered in the system."
            )
        return cls._registry[name]

    @classmethod
    def list_registered(cls) -> List[str]:
        """
        List all dynamically registered connector names.
        """
        return list(cls._registry.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        Check if a connector is known to the registry.
        """
        return name in cls._registry
