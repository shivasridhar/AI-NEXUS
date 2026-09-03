from app.services.parsers.base import BaseEventParser
from app.services.parsers.wazuh_parser import WazuhParser
from app.services.parsers.suricata_parser import SuricataParser
from app.services.parsers.openvas_parser import OpenVASParser

class ParserFactory:
    """
    Factory for retrieving the appropriate event parser based on the source tool.
    """
    _parsers = {
        "wazuh": WazuhParser(),
        "suricata": SuricataParser(),
        "openvas": OpenVASParser(),
        # cloudtrail is intentionally not here yet, as requested, to avoid refactoring it now.
    }
    
    @classmethod
    def get_parser(cls, source_tool: str) -> BaseEventParser:
        source_lower = source_tool.strip().lower()
        parser = cls._parsers.get(source_lower)
        if not parser:
            raise ValueError(f"No parser registered for source tool: {source_tool}")
        return parser
