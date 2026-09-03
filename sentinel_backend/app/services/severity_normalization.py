import logging

logger = logging.getLogger(__name__)

def normalize_wazuh_severity(level: int) -> int:
    """
    Normalizes Wazuh rule level (0-15) to a 0-100 scale.
    Formula: (level / 15) * 100
    """
    try:
        level = int(level)
    except (ValueError, TypeError):
        logger.warning(f"Invalid Wazuh severity level: {level}. Defaulting to 0.")
        return 0
        
    if level < 0:
        return 0
    if level > 15:
        level = 15
        
    return int((level / 15.0) * 100)

def normalize_openvas_severity(label: str) -> int:
    """
    Normalizes OpenVAS risk labels to a 0-100 scale.
    Critical: 95, High: 80, Medium: 50, Low: 20
    """
    if not label:
        return 0
        
    label_lower = str(label).strip().lower()
    mapping = {
        "critical": 95,
        "high": 80,
        "medium": 50,
        "low": 20
    }
    
    if label_lower in mapping:
        return mapping[label_lower]
        
    logger.warning(f"Unknown OpenVAS severity label: {label}. Defaulting to 0.")
    return 0
