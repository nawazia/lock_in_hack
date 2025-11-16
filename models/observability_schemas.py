"""Observability schemas for hallucination detection and monitoring."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class EvidenceData(BaseModel):
    """Evidence used for extraction."""

    search_query: str = Field(..., description="Query used to search")
    raw_results_count: int = Field(..., description="Number of raw search results")
    raw_results: List[Dict[str, Any]] = Field(default_factory=list, description="Raw search results")
    formatted_evidence: str = Field(..., description="Formatted evidence text used for validation")
    evidence_length: int = Field(..., description="Character length of evidence")


class ExtractionData(BaseModel):
    """Data extracted by LLM."""

    extracted_items: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted items as dicts")
    item_count: int = Field(..., description="Number of items extracted")
    extraction_prompt: Optional[str] = Field(None, description="Prompt used for extraction")
    llm_output_raw: Optional[str] = Field(None, description="Raw LLM output")


class HallucinationMetrics(BaseModel):
    """EDFL hallucination detection metrics."""

    validation_type: str = Field(..., description="Type of validation (evidence_based, closed_book, etc.)")
    edfl_decision: str = Field(..., description="PASS, FAIL, or ERROR")
    risk_of_hallucination: float = Field(..., description="Risk of hallucination (RoH) bound, 0-1")
    confidence: str = Field(..., description="high, medium, or low")

    # EDFL technical metrics
    delta_bar: float = Field(..., description="Information gain (Δ̄) in nats")
    isr: float = Field(..., description="Information sufficiency ratio (ISR)")
    b2t: float = Field(..., description="Bits-to-trust (B2T) threshold in nats")
    p_answer: float = Field(..., description="Probability of 'answer' in full prompt")
    q_avg: float = Field(..., description="Average probability of 'answer' in skeletons")
    q_lo: float = Field(..., description="Minimum probability of 'answer' in skeletons")

    n_samples: int = Field(..., description="Number of samples per prompt")
    m_skeletons: int = Field(..., description="Number of skeleton prompts")

    rationale: str = Field(..., description="Human-readable explanation")

    # Optional error info
    error: Optional[str] = Field(None, description="Error message if validation failed")

    # Evidence checking
    evidence_items_checked: Optional[Dict[str, int]] = Field(None, description="Count of evidence items checked")


class PipelineStep(BaseModel):
    """Single step in the travel planning pipeline."""

    step_name: str = Field(..., description="Name of the step (e.g., 'flight_search', 'hotel_search')")
    step_type: str = Field(..., description="Type of step (search, extraction, validation, etc.)")
    timestamp: datetime = Field(default_factory=datetime.now, description="When this step executed")
    duration_seconds: Optional[float] = Field(None, description="How long this step took")

    # Evidence
    evidence: Optional[EvidenceData] = Field(None, description="Evidence data for this step")

    # Extraction
    extraction: Optional[ExtractionData] = Field(None, description="Extraction data for this step")

    # Hallucination metrics
    hallucination_metrics: Optional[HallucinationMetrics] = Field(None, description="EDFL validation metrics")

    # Status
    status: str = Field("success", description="success, failed, or skipped")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional step metadata")


class ObservabilityReport(BaseModel):
    """Complete observability report for a travel planning query."""

    # Query info
    query_id: str = Field(..., description="Unique identifier for this query")
    user_query: str = Field(..., description="Original user query")
    timestamp: datetime = Field(default_factory=datetime.now, description="When query was received")

    # Pipeline execution
    steps: List[PipelineStep] = Field(default_factory=list, description="All pipeline steps")
    total_duration_seconds: Optional[float] = Field(None, description="Total pipeline duration")

    # Final output
    final_itinerary: Optional[Dict[str, Any]] = Field(None, description="Final itinerary output")

    # Overall metrics
    overall_hallucination_risk: float = Field(..., description="Maximum RoH across all steps")
    overall_confidence: str = Field(..., description="Overall confidence level")

    # Step summary
    steps_completed: int = Field(0, description="Number of steps completed")
    steps_failed: int = Field(0, description="Number of steps that failed")
    validation_passes: int = Field(0, description="Number of validations that passed")
    validation_failures: int = Field(0, description="Number of validations that failed")

    # Hallucination flags
    hallucination_flags: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of flagged hallucinations with details"
    )


class HallucinationFlag(BaseModel):
    """A flagged hallucination with details."""

    step_name: str = Field(..., description="Which step flagged this")
    severity: str = Field(..., description="high, medium, or low")
    risk_of_hallucination: float = Field(..., description="RoH score")

    item_type: str = Field(..., description="Type of item (flight, hotel, activity, etc.)")
    item_name: Optional[str] = Field(None, description="Name/identifier of the item")

    issue_description: str = Field(..., description="What was flagged")
    evidence_snippet: Optional[str] = Field(None, description="Relevant evidence snippet")
    extracted_claim: Optional[str] = Field(None, description="What was extracted")

    recommendation: str = Field(..., description="What to do about it")


def calculate_overall_confidence(steps: List[PipelineStep]) -> str:
    """Calculate overall confidence from all steps.

    Args:
        steps: List of pipeline steps

    Returns:
        Overall confidence: high, medium, or low
    """
    confidences = []
    for step in steps:
        if step.hallucination_metrics:
            confidences.append(step.hallucination_metrics.confidence)

    if not confidences:
        return "unknown"

    # If any step is low confidence, overall is low
    if "low" in confidences:
        return "low"

    # If all high, return high
    if all(c == "high" for c in confidences):
        return "high"

    # Otherwise medium
    return "medium"


def calculate_overall_risk(steps: List[PipelineStep]) -> float:
    """Calculate overall hallucination risk (max RoH).

    Args:
        steps: List of pipeline steps

    Returns:
        Maximum risk of hallucination across all steps
    """
    risks = []
    for step in steps:
        if step.hallucination_metrics:
            risks.append(step.hallucination_metrics.risk_of_hallucination)

    return max(risks) if risks else 0.0


def extract_hallucination_flags(steps: List[PipelineStep], threshold: float = 0.3) -> List[HallucinationFlag]:
    """Extract hallucination flags from pipeline steps.

    Args:
        steps: List of pipeline steps
        threshold: RoH threshold above which to flag (default 0.3)

    Returns:
        List of hallucination flags
    """
    flags = []

    for step in steps:
        if not step.hallucination_metrics:
            continue

        metrics = step.hallucination_metrics

        # Flag if RoH above threshold
        if metrics.risk_of_hallucination >= threshold:
            severity = "high" if metrics.risk_of_hallucination >= 0.7 else \
                      "medium" if metrics.risk_of_hallucination >= 0.5 else "low"

            flag = HallucinationFlag(
                step_name=step.step_name,
                severity=severity,
                risk_of_hallucination=metrics.risk_of_hallucination,
                item_type=step.step_name.replace("_search", "").replace("_", " "),
                issue_description=f"High hallucination risk detected ({metrics.risk_of_hallucination:.1%})",
                recommendation=f"Review extracted {step.step_name} data carefully. "
                              f"EDFL validation suggests potential hallucinations. "
                              f"Confidence: {metrics.confidence}, ISR: {metrics.isr:.3f}"
            )

            # Add evidence and extraction snippets if available
            if step.evidence:
                flag.evidence_snippet = step.evidence.formatted_evidence[:200] + "..."

            if step.extraction and step.extraction.extracted_items:
                flag.extracted_claim = str(step.extraction.extracted_items[0])[:200] + "..."

            flags.append(flag)

    return flags
