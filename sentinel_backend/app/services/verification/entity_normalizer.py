import re

class EntityNormalizer:
    """
    Normalizes entities to ensure deterministic matching during verification.
    """
    
    @staticmethod
    def normalize_arn(arn: str) -> str:
        """
        Normalizes ARNs by ensuring lowercase and handling empty regions.
        """
        if not arn:
            return ""
        arn = arn.lower().strip()
        # Ensure region is stripped if empty (e.g. arn:aws:iam::123 -> arn:aws:iam::123)
        return arn
        
    @staticmethod
    def normalize_ip(ip: str) -> str:
        if not ip:
            return ""
        return ip.strip()
        
    @staticmethod
    def normalize_event(event: str) -> str:
        """
        Normalizes CloudTrail event names.
        e.g., 'AssumeRole API' -> 'AssumeRole'
        """
        if not event:
            return ""
        event = event.strip()
        # Remove ' API', ' Event', ' Action'
        event = re.sub(r'(?i)\s+(API|Event|Action)$', '', event)
        # Convert to lower to avoid casing issues during match
        return event.lower()
