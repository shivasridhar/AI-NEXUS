from typing import Any, Dict

from app.services.connectors.base_connector import BaseConnector
from app.services.connectors.connector_registry import ConnectorRegistry


class ConnectorConfigurationError(Exception):
    """Raised when a connector is missing required configuration or cannot be instantiated."""


class ConnectorFactory:
    """
    Factory for instantiating registered connectors using dependency injection.
    Follows the Open/Closed Principle: requires no modification to support new connectors.
    """

    @classmethod
    def create(cls, name: str, config: Dict[str, Any]) -> BaseConnector:
        """
        Instantiate a connector by name, injecting the provided configuration dictionary.
        The factory does not know any specific concrete class, only the BaseConnector interface.

        Args:
            name: The registered string identifier of the connector.
            config: A dictionary containing initialization arguments (e.g., api_keys, urls).

        Raises:
            ConnectorNotFoundError: If the requested connector is not registered.
            ConnectorConfigurationError: If the connector fails to initialize with the given config.
        """
        # Resolve the class strictly through the registry (no hardcoded imports/branches)
        connector_class = ConnectorRegistry.get(name)

        try:
            # Instantiate via dependency injection of the config dictionary
            return connector_class(**config)
        except TypeError as e:
            # This catches mismatched constructor arguments for the specific connector
            raise ConnectorConfigurationError(
                f"Failed to configure connector '{name}': {str(e)}"
            )
        except Exception as e:
            # Catching other potential runtime initialization errors
            raise ConnectorConfigurationError(
                f"Unexpected error initializing connector '{name}': {str(e)}"
            )
