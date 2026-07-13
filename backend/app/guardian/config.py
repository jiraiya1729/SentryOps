from pydantic_settings import BaseSettings

class GuardianConfig(BaseSettings):


    
    GUARDIAN_MODEL: str = "claude-sonnet-4-6-20250514"
    GUARDIAN_MAX_TOKENS: int = 4096

    
    MAX_EVIDENCE_ITEMS: int = 20
    MAX_INVESTIGATION_DURATION_MINUTES: int = 10
    MAX_CONCURRENT_INVESTIGATIONS: int = 5

    
    CPU_SPIKE_THRESHOLD: float = 0.8  
    MEMORY_SPIKE_THRESHOLD: float = 0.85  
    RESTART_COUNT_THRESHOLD: int = 3
    ERROR_RATE_THRESHOLD: float = 0.1  

    
    ANOMALY_CHECK_INTERVAL_SECONDS: int = 60
    INVESTIGATION_COOLDOWN_MINUTES: int = 15  

    
    AUTO_REMEDIATION_ENABLED: bool = False  
    REQUIRE_HUMAN_APPROVAL: bool = True

    model_config = {"env_prefix": "GUARDIAN_", "extra": "ignore"}


guardian_config = GuardianConfig()
