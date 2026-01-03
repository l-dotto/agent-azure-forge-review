"""
Finding data model - Single source of truth for finding structure
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class Finding:
    """Structured finding from a review agent"""
    agent: str
    severity: str
    category: str
    title: str
    file_path: str
    line_number: Optional[int]
    description: str
    recommendation: str
    exploit_scenario: Optional[str] = None
    confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        return {k: v for k, v in asdict(self).items() if v is not None}
