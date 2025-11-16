"""EDFL-based validation for travel agent LLM responses.

This module uses the hallbayes library to provide mathematically grounded
hallucination detection for LLM outputs in the travel planning pipeline.

Based on: Expectation-level Decompression Law (EDFL) framework
Paper: https://arxiv.org/abs/2509.11208
"""

import logging
import sys
import os
from typing import Tuple, Optional

# Add hallbayes to path if needed
hallbayes_path = "/Users/paul/Desktop/Hackathon_UCL_great_agent_hack/hallbayes"
if hallbayes_path not in sys.path:
    sys.path.insert(0, hallbayes_path)

logger = logging.getLogger(__name__)

# Lazy imports to avoid import errors if hallbayes not available
_OpenAIPlanner = None
_OpenAIItem = None

def _ensure_hallbayes():
    """Lazy import of hallbayes components."""
    global _OpenAIPlanner, _OpenAIItem
    if _OpenAIPlanner is None:
        try:
            from hallbayes.hallucination_toolkit import OpenAIPlanner, OpenAIItem
            _OpenAIPlanner = OpenAIPlanner
            _OpenAIItem = OpenAIItem
        except ImportError as e:
            logger.error(f"Failed to import hallbayes: {e}")
            raise ImportError("hallbayes library not found. Install from /hallbayes directory") from e


class EDFLValidator:
    """Validates LLM responses using Expectation-level Decompression Law.

    This validator provides mathematically bounded hallucination risk assessment
    for LLM outputs in the travel planning pipeline.

    Usage:
        validator = EDFLValidator(llm_backend, h_star=0.05)
        should_use, risk, rationale = validator.validate_evidence_based(
            task="Extract flights",
            evidence=search_results,
            llm_output=extracted_flights
        )
    """

    def __init__(self, llm_backend, h_star: float = 0.05, enable_validation: bool = True, use_aligned: bool = True):
        """Initialize EDFL validator.

        Args:
            llm_backend: LLM backend compatible with hallbayes (must support chat_create and multi_choice)
            h_star: Target hallucination rate (default 5%)
            enable_validation: If False, always returns (True, 0.0, "validation_disabled")
            use_aligned: If True, uses aligned Δ̄ computation (recommended)
        """
        self.enable_validation = enable_validation
        self.h_star = h_star
        self.use_aligned = use_aligned

        if not enable_validation:
            logger.info("EDFL validation disabled - all validations will pass")
            self.planner = None
            return

        try:
            _ensure_hallbayes()

            # Check if we need to adapt BedrockProxyLLM
            adapted_backend = self._adapt_backend_if_needed(llm_backend)

            # Use aligned validator if requested
            if use_aligned:
                logger.info("Using ALIGNED EDFL validator (fixes Δ̄/q/B2T mismatch)")
                from config.edfl_aligned_validator import AlignedEDFLValidator
                self._aligned_validator = AlignedEDFLValidator(
                    llm_backend=llm_backend,
                    h_star=h_star,
                    enable_validation=True
                )
                self.planner = None  # Use aligned validator instead
            else:
                # Use standard hallbayes planner
                logger.info("Using STANDARD EDFL validator (may have Δ̄=0 issues)")
                self.planner = _OpenAIPlanner(
                    adapted_backend,
                    temperature=0.2,  # Lower for consistency
                    max_tokens_decision=32  # Higher for Bedrock
                )
                self._aligned_validator = None

            logger.info(f"EDFL validator initialized with h_star={h_star}")
        except Exception as e:
            logger.warning(f"Failed to initialize EDFL validator: {e}")
            logger.warning("Validation will be disabled")
            self.enable_validation = False
            self.planner = None
            self._aligned_validator = None

    def _adapt_backend_if_needed(self, llm_backend):
        """Adapt backend if it's not compatible with hallbayes.

        Args:
            llm_backend: Original LLM backend

        Returns:
            Compatible backend (possibly wrapped with adapter)
        """
        # Check if backend already has the required methods
        if hasattr(llm_backend, 'chat_create') and hasattr(llm_backend, 'multi_choice'):
            return llm_backend

        # Check if it's BedrockProxyLLM (by class name to avoid import issues)
        backend_class_name = type(llm_backend).__name__
        if backend_class_name == 'BedrockProxyLLM':
            logger.info("Detected BedrockProxyLLM - applying adapter for hallbayes compatibility")
            from config.bedrock_hallbayes_adapter import create_bedrock_adapter
            return create_bedrock_adapter(llm_backend)

        # If it's a LangChain BaseLLM or BaseChatModel, try to adapt it
        logger.warning(f"Backend type {backend_class_name} may not be fully compatible with hallbayes")
        logger.warning("Attempting to use as-is - validation may fail")
        return llm_backend

    def validate_evidence_based(
        self,
        task_description: str,
        evidence: str,
        llm_output: str,
        n_samples: int = 3,  # Reduced for speed with Bedrock
        m: int = 4  # Reduced for speed
    ) -> Tuple[bool, float, str]:
        """Validate LLM output against provided evidence.

        Uses EDFL framework with evidence-based skeleton policy to determine
        if the LLM output is grounded in the provided evidence.

        Args:
            task_description: Description of the extraction task
            evidence: Source evidence (e.g., search results)
            llm_output: LLM's extracted output to validate
            n_samples: Number of samples per prompt (default 5)
            m: Number of skeleton prompts (default 6)

        Returns:
            Tuple of (should_use, risk_bound, rationale):
                - should_use: True if output passes validation
                - risk_bound: Upper bound on hallucination risk (0-1)
                - rationale: Human-readable explanation
        """
        if not self.enable_validation:
            return True, 0.0, "validation_disabled"

        # Use aligned validator if available
        if self._aligned_validator is not None:
            result = self._aligned_validator.validate_evidence_based(
                task_description=task_description,
                evidence=evidence,
                llm_output=llm_output,
                n_samples=n_samples,
                m=m
            )
            # Propagate detailed metrics for observability
            if hasattr(self._aligned_validator, '_last_detailed_metrics'):
                self._last_detailed_metrics = self._aligned_validator._last_detailed_metrics
            return result

        # Fallback to standard validator
        if self.planner is None:
            return True, 0.0, "validation_disabled"

        try:
            # NO truncation - pass all evidence to maximize Δ̄
            # More evidence = higher information gain when it supports the claim

            # Structure evidence as bullet points for better information gain
            # This increases Δ̄ by making evidence directly support the predicate
            print(f"""VERIFICATION TASK: {task_description}

SOURCE EVIDENCE (from web search results):
{evidence}

EXTRACTED CLAIMS TO VERIFY:
{llm_output}

INSTRUCTIONS:
1. Check if EACH extracted claim is explicitly stated in the source evidence
2. Verify prices, names, dates, and URLs match the source
3. Answer "yes" ONLY if ALL claims are supported by the evidence above
4. Answer "no" if ANY claim is unsupported, hallucinated, or contradicts evidence

QUESTION: Are ALL extracted claims fully supported by the source evidence?
Answer: yes or no""")
            prompt = f"""VERIFICATION TASK: {task_description}

SOURCE EVIDENCE (from web search results):
{evidence}

EXTRACTED CLAIMS TO VERIFY:
{llm_output}

INSTRUCTIONS:
1. Check if EACH extracted claim is explicitly stated in the source evidence
2. Verify prices, names, dates, and URLs match the source
3. Answer "yes" ONLY if ALL claims are supported by the evidence above
4. Answer "no" if ANY claim is unsupported, hallucinated, or contradicts evidence

QUESTION: Are ALL extracted claims fully supported by the source evidence?
Answer: yes or no"""

            item = _OpenAIItem(
                prompt=prompt,
                n_samples=n_samples,
                m=m,
                fields_to_erase=["Evidence"],
                skeleton_policy="evidence_erase"
            )

            metrics = self.planner.run(
                [item],
                h_star=self.h_star,
                isr_threshold=1.0,
                margin_extra_bits=0.2,  # Reduced margin for Bedrock
                B_clip=12.0,
                clip_mode="one-sided"
            )

            m = metrics[0]

            decision = "ANSWER" if m.decision_answer else "REFUSE"
            logger.info(f"EDFL Evidence Validation: {decision}, RoH={m.roh_bound:.3f}, ISR={m.isr:.3f}")

            return m.decision_answer, m.roh_bound, m.rationale

        except Exception as e:
            logger.error(f"EDFL validation failed: {e}")
            # Fail open: allow output but log the error
            return True, 1.0, f"validation_error: {str(e)}"

    def validate_closed_book(
        self,
        question: str,
        llm_output: str,
        n_samples: int = 3,  # Reduced for speed with Bedrock
        m: int = 4  # Reduced for speed
    ) -> Tuple[bool, float, str]:
        """Validate LLM output without external evidence (consistency check).

        Uses EDFL framework with closed-book skeleton policy to check if
        the output is internally consistent and coherent.

        Args:
            question: Question or task description
            llm_output: LLM's output to validate
            n_samples: Number of samples per prompt (default 7)
            m: Number of skeleton prompts (default 6)

        Returns:
            Tuple of (should_use, risk_bound, rationale):
                - should_use: True if output passes validation
                - risk_bound: Upper bound on hallucination risk (0-1)
                - rationale: Human-readable explanation
        """
        if not self.enable_validation:
            return True, 0.0, "validation_disabled"

        # Use aligned validator if available
        if self._aligned_validator is not None:
            return self._aligned_validator.validate_closed_book(
                question=question,
                llm_output=llm_output,
                n_samples=n_samples,
                m=m
            )

        # Fallback to standard validator
        if self.planner is None:
            return True, 0.0, "validation_disabled"

        try:
            # NO truncation - pass full output for maximum information

            # Structured prompt for closed-book validation
            prompt = f"""{question}

Proposed answer:
{llm_output}

INSTRUCTIONS:
1. Check if the answer is internally consistent (no contradictions)
2. Verify dates, locations, and numbers are logically coherent
3. Answer "yes" if the answer is consistent and plausible
4. Answer "no" if there are internal contradictions or implausible claims

QUESTION: Is this answer internally consistent and coherent?
Answer: yes or no"""

            item = _OpenAIItem(
                prompt=prompt,
                n_samples=n_samples,
                m=m,
                skeleton_policy="closed_book"
            )

            metrics = self.planner.run(
                [item],
                h_star=self.h_star,
                isr_threshold=1.0,
                margin_extra_bits=0.2,
                B_clip=12.0,
                clip_mode="one-sided"
            )

            m = metrics[0]

            decision = "ANSWER" if m.decision_answer else "REFUSE"
            logger.info(f"EDFL Closed-book Validation: {decision}, RoH={m.roh_bound:.3f}, ISR={m.isr:.3f}")

            return m.decision_answer, m.roh_bound, m.rationale

        except Exception as e:
            logger.error(f"EDFL validation failed: {e}")
            # Fail open: allow output but log the error
            return True, 1.0, f"validation_error: {str(e)}"

    def validate_extraction_batch(
        self,
        task_description: str,
        evidence: str,
        extracted_items: list,
        item_type: str = "items"
    ) -> Tuple[bool, float, str, int]:
        """Validate a batch of extracted items against evidence.

        Args:
            task_description: Description of extraction task
            evidence: Source evidence
            extracted_items: List of extracted items (dicts or objects)
            item_type: Type of items for logging (e.g., "flights", "hotels")

        Returns:
            Tuple of (should_use, risk_bound, rationale, valid_count)
        """
        if not extracted_items:
            return True, 0.0, "no_items_to_validate", 0

        # Use aligned validator if available
        if self._aligned_validator is not None:
            result = self._aligned_validator.validate_extraction_batch(
                task_description=task_description,
                evidence=evidence,
                extracted_items=extracted_items,
                item_type=item_type
            )
            # Propagate detailed metrics for observability
            if hasattr(self._aligned_validator, '_last_detailed_metrics'):
                self._last_detailed_metrics = self._aligned_validator._last_detailed_metrics
            return result

        import json

        # Convert items to JSON string
        try:
            if hasattr(extracted_items[0], 'dict'):
                items_json = json.dumps([item.dict() for item in extracted_items], indent=2)
            else:
                items_json = json.dumps(extracted_items, indent=2)
        except Exception as e:
            logger.warning(f"Failed to serialize items: {e}")
            items_json = str(extracted_items)

        should_use, risk, rationale = self.validate_evidence_based(
            task_description=f"{task_description}\n\nExtracted {len(extracted_items)} {item_type}.",
            evidence=evidence,
            llm_output=items_json
        )

        valid_count = len(extracted_items) if should_use else 0

        logger.info(f"Batch validation for {len(extracted_items)} {item_type}: "
                   f"{'PASS' if should_use else 'FAIL'} (risk={risk:.3f})")

        return should_use, risk, rationale, valid_count
