"""필수 영역을 원자적으로 다루는 내부 근거 묶음. HTTP DTO/승인 정책은 바꾸지 않는다."""

from dataclasses import dataclass
from pathlib import Path

from app.rag.loader import digest
from app.rag.pipeline import canonical
from app.rag.quality_checks import safe_child
from app.schemas.common import Source
from app.services.generation import Evidence


class BundleError(ValueError):
    pass


@dataclass(frozen=True)
class EvidenceBundle:
    target_id: str
    parts: tuple[Evidence, ...]
    required_ids: tuple[str, ...]
    usage_scope: str
    unresolved_issues: tuple[str, ...] = ()

    def check(self, *, max_sources=10):
        ids = [p.evidence_id for p in self.parts]
        if (
            not ids
            or len(ids) != len(set(ids))
            or set(ids) != set(self.required_ids)
            or len(ids) != len(self.required_ids)
        ):
            raise BundleError("REQUIRED_CONTEXT_MISSING")
        for part in self.parts:
            if part.bundle_id != self.target_id or set(part.required_ids) != set(
                self.required_ids
            ):
                raise BundleError("BUNDLE_IDENTITY_MISMATCH")
            if digest(part.content.encode()) != (part.metadata or {}).get("textHash"):
                raise BundleError("CONTEXT_CONTENT_CHANGED")
            if (part.metadata or {}).get("usageScope") != self.usage_scope:
                raise BundleError("BUNDLE_SCOPE_MISMATCH")
        if len(self.display_sources()) > max_sources:
            raise BundleError("SOURCE_LIMIT_WHOLE_BUNDLE_HELD")
        return self

    def display_sources(self):
        sources = {}
        for part in self.parts:
            sources[canonical(part.source.model_dump(by_alias=True))] = part.source
        return tuple(sources.values())

    def prompt_parts(self):
        self.check()
        return [
            {
                "citationId": f"E{i}",
                "evidenceId": p.evidence_id,
                "content": p.content,
                "source": p.source.model_dump(by_alias=True),
                "context": p.metadata,
            }
            for i, p in enumerate(self.parts, 1)
        ]


def _source(region, url, *, year=None, verified=False, effective=None):
    return Source(
        chunkId=region["chunkId"],
        documentVersion=region["documentVersion"],
        documentTitle=region["documentTitle"],
        article=region.get("article"),
        sourceFile=region["sourceFile"],
        sourceUrl=url,
        pageStart=region["pageStart"],
        pageEnd=region["pageEnd"],
        effectiveDate=effective,
        applicableTaxYear=year,
        applicabilityVerified=verified,
    )


def assemble_evaluation_bundle(record, chunks, indexed_documents, evidence_root: Path):
    """v3 초안을 검토 완료로 바꾸지 않고 추출·공식 증거 일치만 검사한다."""
    required = tuple(record.required_region_ids)
    if set(required) != {r.region_id for r in record.regions} or len(required) != len(
        record.regions
    ):
        raise BundleError("REQUIRED_CONTEXT_MISSING")
    if any(c.region_id not in required for c in record.legal_conditions):
        raise BundleError("LEGAL_CONDITION_REGION_MISSING")
    parts = []
    for region in record.regions:
        chunk = chunks.get(region.chunk_id)
        indexed = indexed_documents.get(region.chunk_id)
        if not chunk or not indexed:
            raise BundleError("REQUIRED_CONTEXT_NOT_IN_INDEX")
        if (chunk.document_version, chunk.content_hash, chunk.config_hash) != (
            region.document_version,
            region.content_hash,
            region.config_hash,
        ):
            raise BundleError("REGION_SOURCE_CHANGED")
        if (
            indexed["documentVersion"] != chunk.document_version
            or indexed["contentHash"] != chunk.content_hash
            or indexed["content"] != chunk.content
        ):
            raise BundleError("INDEX_SOURCE_MISMATCH")
        if (
            indexed.get("usageScope") != "EVALUATION_ONLY"
            or indexed.get("verificationStatus") != "UNVERIFIED"
        ):
            raise BundleError("EVALUATION_SCOPE_REQUIRED")
        spans = [s for s in chunk.source_spans if s.line_id in region.line_ids]
        if not spans or [s.line_id for s in spans] != region.line_ids:
            raise BundleError("INVALID_REGION_LINES")
        positions = [chunk.source_spans.index(s) for s in spans]
        if positions != list(range(positions[0], positions[-1] + 1)):
            raise BundleError("NONCONTIGUOUS_REGION")
        original = "\n".join(s.text for s in spans)
        end = region.end_offset if region.end_offset is not None else len(original)
        if not 0 <= region.start_offset < end <= len(original):
            raise BundleError("INVALID_REGION_OFFSETS")
        text = original[region.start_offset : end]
        if digest(text.encode()) != region.text_hash:
            raise BundleError("REGION_HASH_CHANGED")
        evidence = [
            e for e in record.official_evidence if region.region_id in e.region_ids
        ]
        if not evidence:
            raise BundleError("OFFICIAL_EVIDENCE_MISSING")
        for item in evidence:
            snapshot = safe_child(evidence_root, item.snapshot_file).read_bytes()
            if (
                digest(snapshot) != item.snapshot_hash
                or digest(item.excerpt.encode()) != item.excerpt_hash
                or item.excerpt != text
                or text not in snapshot.decode("utf-8")
            ):
                raise BundleError("OFFICIAL_SNAPSHOT_MISMATCH")
        conditions = [
            c.model_dump(by_alias=True)
            for c in record.legal_conditions
            if c.region_id == region.region_id
        ]
        if any(c["text"] not in text for c in conditions):
            raise BundleError("LEGAL_CONDITION_NOT_PRESERVED")
        origin = {
            "chunkId": chunk.chunk_id,
            "documentVersion": chunk.document_version,
            "documentTitle": chunk.document_title,
            "article": chunk.article,
            "sourceFile": chunk.source_file,
            "pageStart": min(s.page for s in spans),
            "pageEnd": max(s.page for s in spans),
        }
        metadata = {
            "usageScope": "EVALUATION_ONLY",
            "verificationStatus": "UNVERIFIED",
            "approvalStatus": record.usage.status,
            "locator": region.locator,
            "role": region.role,
            "textHash": region.text_hash,
            "sourceKind": indexed.get("sourceKind"),
            "officialLawId": region.official_law_id,
            "officialLawVersion": region.official_law_version,
            "legalConditions": conditions,
            "officialEvidence": [
                {
                    "id": e.evidence_id,
                    "url": e.url,
                    "accessedAt": e.accessed_at,
                    "snapshotHash": e.snapshot_hash,
                    "versionEffectiveDate": e.effective_date,
                    "reviewed": e.reviewed,
                }
                for e in evidence
            ],
            "legalCompletenessVerified": False,
        }
        parts.append(
            Evidence(
                text,
                _source(origin, evidence[0].url, effective=chunk.effective_date),
                record.approval_target_id,
                required,
                region.region_id,
                metadata,
            )
        )
    return EvidenceBundle(
        record.approval_target_id,
        tuple(parts),
        required,
        "EVALUATION_ONLY",
        tuple(record.unresolved_issues),
    ).check()


def bundle_from_approved_context(payload, revalidate_latest, tax_year):
    """향후 운영 어댑터 경계. 콜백은 최신 원장으로 기존 approve_chunk를 재실행해야 한다."""
    fresh = revalidate_latest(payload.get("approvalTargetId"))
    if fresh is None or fresh != payload:
        raise BundleError("APPROVAL_WITHDRAWN_OR_CHANGED")
    if (
        payload.get("exportSchemaVersion") != "approved-context-v3"
        or payload.get("policyVersion") != "review-policy-v3"
        or payload.get("usageScope") != "CURRENT_2026"
        or not payload.get("applicabilityVerified")
        or payload.get("applicableTaxYear") != tax_year
    ):
        raise BundleError("APPROVED_CURRENT_CONTEXT_REQUIRED")
    if digest(canonical(payload["regions"]).encode()) != payload["contentHash"]:
        raise BundleError("CONTEXT_CONTENT_CHANGED")
    required = tuple(payload["requiredRegionIds"])
    parts = []
    for region in payload["regions"]:
        official = [
            e
            for e in payload["officialEvidence"]
            if region["regionId"] in e["regionIds"]
        ]
        if not official:
            raise BundleError("OFFICIAL_EVIDENCE_MISSING")
        origin = {**region, "article": region["locator"]}
        meta = {
            "usageScope": "CURRENT_2026",
            "textHash": region["textHash"],
            "role": region["role"],
            "locator": region["locator"],
            "legalConditions": payload["legalConditions"],
            "officialEvidence": official,
        }
        parts.append(
            Evidence(
                region["content"],
                _source(origin, official[0]["url"], year=tax_year, verified=True),
                payload["approvalTargetId"],
                required,
                region["regionId"],
                meta,
            )
        )
    return EvidenceBundle(
        payload["approvalTargetId"], tuple(parts), required, "CURRENT_2026"
    ).check()
