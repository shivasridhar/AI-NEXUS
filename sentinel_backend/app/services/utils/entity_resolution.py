def resolve_actor_identifier(raw_identifier: str, source: str) -> str:
    """
    Resolves a raw hostname, username, or IP from non-AWS sources 
    to a canonical actor identifier.
    
    This operates separately from the MachineIdentity ARN-based resolution.
    """
    if not raw_identifier:
        return "unknown"
        
    # Standardize the format, e.g., prefix with source or keep it simple
    return raw_identifier.strip().lower()
