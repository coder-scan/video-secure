from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RiskEvaluation:
    risk_score: int
    risk_level: str  # LOW, MEDIUM, HIGH, VERY_HIGH
    triggers: List[str] = field(default_factory=list)
    action_recommended: str = "ALLOW"  # ALLOW, VERIFY_OTP, RESTRICT_SESSION


class RiskEngine:
    """
    Explainable Security Risk Engine that evaluates streaming signals,
    concurrency patterns, device shifts, and player tamper events.
    """

    @staticmethod
    def evaluate(
        concurrent_streams: int = 1,
        max_allowed_streams: int = 1,
        is_ip_anomaly: bool = False,
        is_tamper_detected: bool = False,
        failed_key_requests: int = 0,
        extra_signals: Optional[Dict[str, any]] = None,
    ) -> RiskEvaluation:
        score = 0
        triggers: List[str] = []

        # 1. Concurrent playback anomaly
        if concurrent_streams > max_allowed_streams:
            excess = concurrent_streams - max_allowed_streams
            points = min(50, excess * 35)
            score += points
            triggers.append(
                f"{concurrent_streams} concurrent active streams detected (limit is {max_allowed_streams})"
            )

        # 2. IP / Geolocation anomaly
        if is_ip_anomaly:
            score += 25
            triggers.append("Abrupt IP subnet or geographical anomaly detected")

        # 3. DOM / Canvas Watermark Tampering
        if is_tamper_detected:
            score += 45
            triggers.append("Watermark Canvas tampering or style suppression detected by player watchdog")

        # 4. Repeated unauthorized key/manifest requests
        if failed_key_requests > 0:
            points = min(30, failed_key_requests * 10)
            score += points
            triggers.append(f"{failed_key_requests} unauthorized or expired license key requests")

        # Clamp score between 0 and 100
        score = min(100, max(0, score))

        # Categorize level & recommendation
        if score >= 90:
            level = "VERY_HIGH"
            action = "RESTRICT_SESSION"
        elif score >= 70:
            level = "HIGH"
            action = "RESTRICT_SESSION"
        elif score >= 40:
            level = "MEDIUM"
            action = "VERIFY_OTP"
        else:
            level = "LOW"
            action = "ALLOW"

        return RiskEvaluation(
            risk_score=score,
            risk_level=level,
            triggers=triggers,
            action_recommended=action,
        )


risk_engine = RiskEngine()
