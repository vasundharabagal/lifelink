"""First-aid protocol library loader and schema definitions (Spec §5.5, TRIAGE-01).

Loads pre-reviewed clinical protocol definitions from `shared/protocols/*.json`.
Protocols cite official public first-aid guidelines (IFRC, AHA) and include
explicit contraindications (`do_not`) and unreviewed demo disclaimers.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ProtocolId

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_PROTOCOLS_DIR = _PROJECT_ROOT / "shared" / "protocols"


class ProtocolStep(BaseModel):
    """An individual numbered imperative action in an emergency protocol."""
    n: int
    text_key: str
    icon: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class ProtocolDefinition(BaseModel):
    """Clinical first-aid protocol schema matching Spec §5.5."""
    id: ProtocolId
    version: str
    title: str
    applies_to: List[str]
    status: str = "demo_unreviewed"
    source_citation: str
    reviewed_by: Optional[str] = None
    reviewed_on: Optional[str] = None
    call_emergency_first: bool = True
    steps: List[ProtocolStep] = Field(min_length=1)
    do_not: List[str] = Field(default_factory=list)
    disclaimer_key: str = "demo_unreviewed_guidance"

    model_config = ConfigDict(extra="forbid")


class ProtocolLibrary:
    """In-memory cache and registry for version-controlled first-aid protocols."""

    def __init__(self, protocols_dir: Optional[Path] = None) -> None:
        self.protocols_dir = protocols_dir or _PROTOCOLS_DIR
        self._protocols: Dict[str, ProtocolDefinition] = {}
        self.reload()

    def reload(self) -> None:
        """Scan directory and parse all protocol JSON files."""
        self._protocols.clear()
        if not self.protocols_dir.exists():
            logger.warning("Protocols directory not found: %s", self.protocols_dir)
            return

        for json_path in sorted(self.protocols_dir.glob("*.json")):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                protocol = ProtocolDefinition.model_validate(data)
                self._protocols[protocol.id.value] = protocol
            except Exception as e:
                logger.error("Failed to load protocol from %s: %s", json_path, e)
                raise ValueError(f"Invalid protocol definition at {json_path}: {e}") from e

        # Validate that all 7 MVP protocols are present
        for pid in ProtocolId:
            if pid.value not in self._protocols:
                raise ValueError(f"Missing required MVP protocol in library: {pid.value}")

    def get_protocol(self, protocol_id: str) -> Optional[ProtocolDefinition]:
        """Fetch protocol by identifier."""
        return self._protocols.get(protocol_id)

    def list_protocols(self) -> List[ProtocolDefinition]:
        """Return all loaded protocols."""
        return list(self._protocols.values())

    def __len__(self) -> int:
        return len(self._protocols)


# Process-wide singleton
protocol_library = ProtocolLibrary()
