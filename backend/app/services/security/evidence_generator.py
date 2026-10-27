import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict


class EvidenceGenerator:
    """
    Compiles structured, cryptographic evidence packages for piracy incidents,
    enabling creators to investigate leaks and file takedown notices.
    """

    @staticmethod
    def generate_package(
        incident_number: str,
        video_id: str,
        video_title: str,
        source_url: str,
        similarity_score: float,
        suspected_user_email: str = None,
        suspected_session_id: str = None,
        watermark_data: Dict[str, Any] = None,
        audit_trail: list = None,
    ) -> Dict[str, Any]:
        now_str = datetime.now(timezone.utc).isoformat()

        package = {
            "evidence_package_version": "1.0",
            "generated_at": now_str,
            "incident_number": incident_number,
            "protected_content": {
                "video_id": video_id,
                "title": video_title,
                "protection_mode": "HLS AES-128 Zero-Trust",
            },
            "leak_detection": {
                "source_url": source_url,
                "similarity_score_pct": round(similarity_score * 100, 2),
                "detection_method": "Perceptual Visual Hash & Audio Acoustic Fingerprinting",
            },
            "source_attribution": {
                "suspected_viewer_email": suspected_user_email or "Unknown",
                "suspected_session_id": suspected_session_id or "Unknown",
                "watermark_recovered_payload": watermark_data or {},
            },
            "forensic_audit_trail": audit_trail or [],
        }

        # Calculate cryptographic package signature hash
        serialized = json.dumps(package, sort_keys=True)
        package["package_sha256_checksum"] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return package

    @staticmethod
    def export_csv(package: Dict[str, Any]) -> str:
        """Exports key evidence elements to CSV format."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Field", "Value"])
        writer.writerow(["Incident Number", package.get("incident_number")])
        writer.writerow(["Generated At", package.get("generated_at")])
        writer.writerow(["Video ID", package.get("protected_content", {}).get("video_id")])
        writer.writerow(["Video Title", package.get("protected_content", {}).get("title")])
        writer.writerow(["Source URL", package.get("leak_detection", {}).get("source_url")])
        writer.writerow(["Similarity Score %", package.get("leak_detection", {}).get("similarity_score_pct")])
        writer.writerow(["Suspected Viewer", package.get("source_attribution", {}).get("suspected_viewer_email")])
        writer.writerow(["Suspected Session", package.get("source_attribution", {}).get("suspected_session_id")])
        writer.writerow(["Cryptographic Checksum", package.get("package_sha256_checksum")])
        return output.getvalue()


evidence_generator = EvidenceGenerator()
