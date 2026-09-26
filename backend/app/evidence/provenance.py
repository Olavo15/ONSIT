from datetime import datetime
from app.models.models import DisplayPolicy, VerificationStatus

class ProvenanceRecord:
    """
    Standard Provenance Metadata Structure (Section 20 & 21)
    Ensures every OSINT finding is traceable and auditable.
    """
    def __init__(
        self,
        field: str,
        value: str,
        source_name: str,
        source_reference: str = None,
        verification_status: VerificationStatus = VerificationStatus.SOURCE_CONFIRMED,
        display_policy: DisplayPolicy = DisplayPolicy.FULL,
        retrieved_at: datetime = None
    ):
        self.field = field
        self.value = value
        self.source_name = source_name
        self.source_reference = source_reference
        self.verification_status = verification_status
        self.display_policy = display_policy
        self.retrieved_at = retrieved_at or datetime.utcnow()

    def format_value_for_display(self) -> str:
        if self.display_policy == DisplayPolicy.HIDDEN:
            return "[DADO PROTEGIDO POR REGRA DE PRIVACIDADE]"
        elif self.display_policy == DisplayPolicy.MASKED:
            if "@" in self.value:
                parts = self.value.split("@")
                return f"{parts[0][:2]}***@{parts[1]}"
            elif len(self.value) >= 11 and self.value.isdigit(): # CPF/CNPJ
                return f"***.{self.value[3:6]}.***-**"
            else:
                return f"{self.value[:3]}***"
        return self.value

    def to_dict(self):
        return {
            "field": self.field,
            "value": self.format_value_for_display(),
            "source": self.source_name,
            "source_reference": self.source_reference,
            "retrieved_at": self.retrieved_at.isoformat(),
            "verification": self.verification_status.value,
            "display_policy": self.display_policy.value
        }
