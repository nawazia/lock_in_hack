"""Observability data collector for hallucination monitoring."""

import logging
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from models.observability_schemas import (
    ObservabilityReport,
    PipelineStep,
    EvidenceData,
    ExtractionData,
    HallucinationMetrics,
    HallucinationFlag,
    calculate_overall_confidence,
    calculate_overall_risk,
    extract_hallucination_flags
)

logger = logging.getLogger(__name__)


class ObservabilityCollector:
    """Collects observability data throughout the travel planning pipeline."""

    def __init__(self, user_query: str, query_id: str = None):
        """Initialize collector.

        Args:
            user_query: The user's query
            query_id: Optional query ID (generated if not provided)
        """
        self.query_id = query_id or str(uuid.uuid4())
        self.user_query = user_query
        self.start_time = datetime.now()

        self.steps: List[PipelineStep] = []
        self.current_step_start: Optional[datetime] = None

        logger.info(f"ObservabilityCollector initialized for query: {query_id}")

    def start_step(self, step_name: str, step_type: str = "extraction"):
        """Mark the start of a pipeline step.

        Args:
            step_name: Name of the step
            step_type: Type of step
        """
        self.current_step_start = datetime.now()
        logger.debug(f"Started step: {step_name}")

    def record_step(
        self,
        step_name: str,
        step_type: str = "extraction",
        evidence: Optional[EvidenceData] = None,
        extraction: Optional[ExtractionData] = None,
        hallucination_metrics: Optional[HallucinationMetrics] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ):
        """Record a completed pipeline step.

        Args:
            step_name: Name of the step
            step_type: Type of step
            evidence: Evidence data
            extraction: Extraction data
            hallucination_metrics: EDFL metrics
            status: Status of the step
            error_message: Error message if failed
            metadata: Additional metadata
        """
        duration = None
        if self.current_step_start:
            duration = (datetime.now() - self.current_step_start).total_seconds()

        step = PipelineStep(
            step_name=step_name,
            step_type=step_type,
            timestamp=datetime.now(),
            duration_seconds=duration,
            evidence=evidence,
            extraction=extraction,
            hallucination_metrics=hallucination_metrics,
            status=status,
            error_message=error_message,
            metadata=metadata or {}
        )

        self.steps.append(step)
        logger.info(f"Recorded step: {step_name} (status={status}, duration={duration:.2f}s)")

    def generate_report(
        self,
        final_itinerary: Optional[Dict[str, Any]] = None,
        hallucination_threshold: float = 0.3
    ) -> ObservabilityReport:
        """Generate the final observability report.

        Args:
            final_itinerary: Final itinerary output
            hallucination_threshold: RoH threshold for flagging

        Returns:
            Complete observability report
        """
        total_duration = (datetime.now() - self.start_time).total_seconds()

        # Calculate summary stats
        steps_completed = sum(1 for s in self.steps if s.status == "success")
        steps_failed = sum(1 for s in self.steps if s.status == "failed")

        validation_passes = sum(
            1 for s in self.steps
            if s.hallucination_metrics and s.hallucination_metrics.edfl_decision == "PASS"
        )
        validation_failures = sum(
            1 for s in self.steps
            if s.hallucination_metrics and s.hallucination_metrics.edfl_decision == "FAIL"
        )

        # Calculate overall metrics
        overall_risk = calculate_overall_risk(self.steps)
        overall_confidence = calculate_overall_confidence(self.steps)

        # Extract hallucination flags
        hallucination_flags = extract_hallucination_flags(self.steps, hallucination_threshold)

        report = ObservabilityReport(
            query_id=self.query_id,
            user_query=self.user_query,
            timestamp=self.start_time,
            steps=self.steps,
            total_duration_seconds=total_duration,
            final_itinerary=final_itinerary,
            overall_hallucination_risk=overall_risk,
            overall_confidence=overall_confidence,
            steps_completed=steps_completed,
            steps_failed=steps_failed,
            validation_passes=validation_passes,
            validation_failures=validation_failures,
            hallucination_flags=[flag.model_dump() for flag in hallucination_flags]
        )

        logger.info(f"Generated observability report: {steps_completed} steps, "
                   f"risk={overall_risk:.3f}, confidence={overall_confidence}")

        return report

    def to_json(self, final_itinerary: Optional[Dict[str, Any]] = None, indent: int = 2) -> str:
        """Generate JSON output for frontend.

        Args:
            final_itinerary: Final itinerary
            indent: JSON indentation

        Returns:
            JSON string
        """
        report = self.generate_report(final_itinerary)
        return json.dumps(report.model_dump(), indent=indent, default=str)

    def save_report(
        self,
        output_path: str,
        final_itinerary: Optional[Dict[str, Any]] = None
    ):
        """Save observability report to file.

        Args:
            output_path: Path to save JSON file
            final_itinerary: Final itinerary
        """
        try:
            report_json = self.to_json(final_itinerary)

            with open(output_path, 'w') as f:
                f.write(report_json)

            logger.info(f"Saved observability report to {output_path}")
        except Exception as e:
            logger.error(f"Error saving report: {e}")

    def print_summary(self):
        """Print a human-readable summary."""
        print("\n" + "=" * 80)
        print("OBSERVABILITY SUMMARY")
        print("=" * 80)
        print(f"Query ID: {self.query_id}")
        print(f"User Query: {self.user_query}")
        print(f"Steps Completed: {len(self.steps)}")
        print()

        for step in self.steps:
            status_icon = "✓" if step.status == "success" else "✗"
            print(f"{status_icon} {step.step_name} ({step.duration_seconds:.2f}s)")

            if step.hallucination_metrics:
                m = step.hallucination_metrics
                print(f"    EDFL: {m.edfl_decision}, RoH={m.risk_of_hallucination:.3f}, "
                      f"Confidence={m.confidence}, ISR={m.isr:.3f}")

            if step.extraction:
                print(f"    Extracted: {step.extraction.item_count} items")

        print()

        # Overall metrics
        overall_risk = calculate_overall_risk(self.steps)
        overall_confidence = calculate_overall_confidence(self.steps)

        print(f"Overall Risk: {overall_risk:.3f}")
        print(f"Overall Confidence: {overall_confidence}")

        # Hallucination flags
        flags = extract_hallucination_flags(self.steps, threshold=0.3)
        if flags:
            print(f"\n⚠️  {len(flags)} Hallucination Flags:")
            for flag in flags:
                print(f"  - [{flag.severity.upper()}] {flag.step_name}: {flag.issue_description}")
        else:
            print("\n✓ No hallucination flags")

        print("=" * 80 + "\n")
