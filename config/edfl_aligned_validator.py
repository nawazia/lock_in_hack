"""Fixed EDFL validator with aligned Δ̄ computation.

This wrapper fixes the semantic mismatch in hallbayes where:
- q/B2T measures the "answer" event
- But Δ̄ measures whatever y_label happened to be (often "refuse")

The fix: Always compute Δ̄ for the "answer" event to align with q/B2T.
"""

import logging
import sys
import os
from typing import Tuple, List, Optional

# Add hallbayes to path if needed
hallbayes_path = "/Users/paul/Desktop/Hackathon_UCL_great_agent_hack/hallbayes"
if hallbayes_path not in sys.path:
    sys.path.insert(0, hallbayes_path)

logger = logging.getLogger(__name__)

# Lazy imports
_OpenAIPlanner = None
_OpenAIItem = None
_decision_messages_evidence = None
_decision_messages_closed_book = None
_choices_to_decisions = None
_delta_bar_from_probs = None
_bits_to_trust = None
_roh_upper_bound = None
_isr = None

def _ensure_hallbayes():
    """Lazy import of hallbayes components."""
    global _OpenAIPlanner, _OpenAIItem, _decision_messages_evidence
    global _decision_messages_closed_book, _choices_to_decisions
    global _delta_bar_from_probs, _bits_to_trust, _roh_upper_bound, _isr

    if _OpenAIPlanner is None:
        try:
            import hallbayes.hallucination_toolkit as htk
            _OpenAIPlanner = htk.OpenAIPlanner
            _OpenAIItem = htk.OpenAIItem
            _decision_messages_evidence = htk.decision_messages_evidence
            _decision_messages_closed_book = htk.decision_messages_closed_book
            _choices_to_decisions = htk._choices_to_decisions
            _delta_bar_from_probs = htk.delta_bar_from_probs
            _bits_to_trust = htk.bits_to_trust
            _roh_upper_bound = htk.roh_upper_bound
            _isr = htk.isr
        except ImportError as e:
            logger.error(f"Failed to import hallbayes: {e}")
            raise ImportError("hallbayes library not found") from e


class AlignedEDFLValidator:
    """EDFL validator with aligned Δ̄/q/B2T computation.

    Fixes the semantic mismatch by always computing Δ̄ for "answer" event.
    """

    def __init__(self, llm_backend, h_star: float = 0.05, enable_validation: bool = True):
        """Initialize aligned EDFL validator.

        Args:
            llm_backend: LLM backend compatible with hallbayes
            h_star: Target hallucination rate (default 5%)
            enable_validation: If False, always returns (True, 0.0, "validation_disabled")
        """
        self.enable_validation = enable_validation
        self.h_star = h_star

        if not enable_validation:
            logger.info("EDFL validation disabled - all validations will pass")
            self.planner = None
            return

        try:
            _ensure_hallbayes()

            # Check if we need to adapt BedrockProxyLLM
            adapted_backend = self._adapt_backend_if_needed(llm_backend)

            # Create planner
            self.planner = _OpenAIPlanner(
                adapted_backend,
                temperature=0.2,
                max_tokens_decision=32
            )

            # Store backend for custom validation
            self.backend = adapted_backend

            logger.info(f"Aligned EDFL validator initialized with h_star={h_star}")
        except Exception as e:
            logger.warning(f"Failed to initialize aligned EDFL validator: {e}")
            logger.warning("Validation will be disabled")
            self.enable_validation = False
            self.planner = None

    def _adapt_backend_if_needed(self, llm_backend):
        """Adapt backend if needed."""
        if hasattr(llm_backend, 'chat_create') and hasattr(llm_backend, 'multi_choice'):
            return llm_backend

        backend_class_name = type(llm_backend).__name__
        if backend_class_name == 'BedrockProxyLLM':
            logger.info("Detected BedrockProxyLLM - applying adapter")
            from config.bedrock_hallbayes_adapter import create_bedrock_adapter
            return create_bedrock_adapter(llm_backend)

        logger.warning(f"Backend {backend_class_name} may not be fully compatible")
        return llm_backend

    def _estimate_signals_aligned(
        self,
        prompt: str,
        skeletons: List[str],
        n_samples: int,
        temperature: float,
        max_tokens: int,
        closed_book: bool
    ) -> Tuple[float, List[float], List[float], str]:
        """Estimate signals with ALIGNED Δ̄ computation.

        Key fix: Always measure probabilities for "answer" event, not y_label.

        Returns:
            P_answer: Probability of "answer" in full prompt
            S_list_answer: List of probabilities of "answer" in each skeleton
            q_list: List of "answer" rates in each skeleton (same as S_list_answer)
            y_label: Actual first decision for compatibility
        """
        # Posterior (full prompt)
        msgs = _decision_messages_closed_book(prompt) if closed_book else _decision_messages_evidence(prompt)
        choices = self.backend.multi_choice(msgs, n=n_samples, temperature=temperature, max_tokens=max_tokens)
        post_decisions = _choices_to_decisions(choices)

        y_label = post_decisions[0] if post_decisions else "refuse"

        # KEY FIX: Always measure "answer" probability, not y_label
        P_answer = sum(1 for d in post_decisions if d == "answer") / max(1, len(post_decisions))

        # Priors across skeletons - also measure "answer" for alignment
        S_list_answer: List[float] = []
        q_list: List[float] = []

        for sk in skeletons:
            msgs_k = _decision_messages_closed_book(sk) if closed_book else _decision_messages_evidence(sk)
            choices_k = self.backend.multi_choice(msgs_k, n=n_samples, temperature=temperature, max_tokens=max_tokens)
            dec_k = _choices_to_decisions(choices_k)

            # Both measure "answer" event
            qk = sum(1 for d in dec_k if d == "answer") / max(1, len(dec_k))
            sk_answer = qk  # Same value - both are "answer" rate

            q_list.append(qk)
            S_list_answer.append(sk_answer)

        # Log diagnostics
        logger.info(f"ALIGNED SIGNALS: P(answer)={P_answer:.3f}, q_avg={sum(q_list)/len(q_list):.3f}, q_lo={min(q_list):.3f}")
        logger.info(f"  S_list_answer={[f'{s:.3f}' for s in S_list_answer]}")
        logger.info(f"  y_label={y_label} (for reference, but Δ̄ computed for 'answer')")

        return P_answer, S_list_answer, q_list, y_label

    def validate_evidence_based(
        self,
        task_description: str,
        evidence: str,
        llm_output: str,
        n_samples: int = 3,
        m: int = 4
    ) -> Tuple[bool, float, str]:
        """Validate LLM output against evidence with ALIGNED computation.

        Args:
            task_description: Description of the extraction task
            evidence: Source evidence
            llm_output: LLM's extracted output to validate
            n_samples: Number of samples per prompt
            m: Number of skeleton prompts

        Returns:
            (should_use, risk_bound, rationale)
        """
        if not self.enable_validation or self.planner is None:
            return True, 0.0, "validation_disabled"

        try:
            # Build verification prompt
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

            # LOG THE FULL PROMPT FOR DEBUGGING
            logger.info("=" * 80)
            logger.info("EDFL VERIFICATION PROMPT:")
            logger.info("=" * 80)
            logger.info(prompt[:2000] + ("..." if len(prompt) > 2000 else ""))
            logger.info("=" * 80)
            logger.info(f"Full prompt length: {len(prompt)} characters")
            logger.info("=" * 80)

            # Create item
            item = _OpenAIItem(
                prompt=prompt,
                n_samples=n_samples,
                m=m,
                fields_to_erase=["Evidence"],
                skeleton_policy="evidence_erase"
            )

            # Build skeletons
            from hallbayes.hallucination_toolkit import make_skeletons_evidence_erase
            seeds = list(range(m))
            skeletons = make_skeletons_evidence_erase(
                prompt, m=m, seeds=seeds, fields_to_erase=["Evidence"]
            )

            # ALIGNED estimation: always measure "answer" event
            P_answer, S_list_answer, q_list, y_label = self._estimate_signals_aligned(
                prompt=prompt,
                skeletons=skeletons,
                n_samples=n_samples,
                temperature=0.2,
                max_tokens=32,
                closed_book=False  # Evidence-based
            )

            # Compute metrics - all aligned to "answer" event
            from hallbayes.hallucination_toolkit import q_bar, q_lo as q_lo_func

            q_avg = q_bar(q_list)
            q_cons = q_lo_func(q_list)

            # Apply floor
            floor = 1.0 / (n_samples + 2)
            q_cons = max(q_cons, floor)

            # KEY: Δ̄ now measures "answer" event, aligned with q/B2T
            dbar = _delta_bar_from_probs(P_answer, S_list_answer, B=12.0, clip_mode="one-sided")

            # Decision metrics
            b2t = _bits_to_trust(q_cons, self.h_star)
            isr_val = _isr(dbar, b2t)
            roh = _roh_upper_bound(dbar, q_avg)

            # Decision
            will_answer = (isr_val >= 1.0) and (dbar >= b2t + 0.2)

            # Build rationale
            rationale = (
                f"Δ̄={dbar:.4f} nats, B2T={b2t:.4f}, ISR={isr_val:.3f}, "
                f"P(answer)={P_answer:.3f}, q_lo={q_cons:.3f}, RoH={roh:.3f}; "
                f"y_label='{y_label}' (Δ̄ computed for 'answer' event)"
            )

            # Detailed logging
            logger.info("=" * 60)
            logger.info("ALIGNED EDFL VALIDATION:")
            logger.info(f"  P(answer) in full prompt: {P_answer:.3f}")
            logger.info(f"  q_avg (avg S[answer]):   {q_avg:.3f}")
            logger.info(f"  q_lo (min S[answer]):    {q_cons:.3f}")
            logger.info(f"  Δ̄ (for 'answer'):        {dbar:.4f} nats")
            logger.info(f"  B2T:                     {b2t:.4f} nats")
            logger.info(f"  ISR:                     {isr_val:.3f}")
            logger.info(f"  RoH bound:               {roh:.3f}")
            logger.info(f"  Decision:                {'ANSWER' if will_answer else 'REFUSE'}")
            logger.info("=" * 60)

            # Store detailed metrics for observability
            self._last_detailed_metrics = {
                "delta_bar": dbar,
                "b2t": b2t,
                "isr": isr_val,
                "p_answer": P_answer,
                "q_avg": q_avg,
                "q_lo": q_cons,
                "n_samples": n_samples,
                "m_skeletons": m,
                "y_label": y_label,
                "will_answer": will_answer
            }

            return will_answer, roh, rationale

        except Exception as e:
            logger.error(f"Aligned EDFL validation failed: {e}", exc_info=True)
            return True, 1.0, f"validation_error: {str(e)}"

    def validate_closed_book(
        self,
        question: str,
        llm_output: str,
        n_samples: int = 3,
        m: int = 4
    ) -> Tuple[bool, float, str]:
        """Validate using closed-book with ALIGNED computation."""
        if not self.enable_validation or self.planner is None:
            return True, 0.0, "validation_disabled"

        try:
            prompt = f"""{question}

Proposed answer:
{llm_output}

INSTRUCTIONS:
1. Check if the answer is internally consistent
2. Verify dates, locations, numbers are logically coherent
3. Answer "yes" if consistent and plausible
4. Answer "no" if contradictions or implausible claims

QUESTION: Is this answer internally consistent and coherent?
Answer: yes or no"""

            # Similar aligned computation as evidence-based
            item = _OpenAIItem(
                prompt=prompt,
                n_samples=n_samples,
                m=m,
                skeleton_policy="closed_book"
            )

            from hallbayes.hallucination_toolkit import make_skeletons_closed_book
            seeds = list(range(m))
            skeletons = make_skeletons_closed_book(prompt, m=m, seeds=seeds)

            P_answer, S_list_answer, q_list, y_label = self._estimate_signals_aligned(
                prompt=prompt,
                skeletons=skeletons,
                n_samples=n_samples,
                temperature=0.2,
                max_tokens=32,
                closed_book=True
            )

            from hallbayes.hallucination_toolkit import q_bar, q_lo as q_lo_func

            q_avg = q_bar(q_list)
            q_cons = max(q_lo_func(q_list), 1.0 / (n_samples + 2))

            dbar = _delta_bar_from_probs(P_answer, S_list_answer, B=12.0, clip_mode="one-sided")
            b2t = _bits_to_trust(q_cons, self.h_star)
            isr_val = _isr(dbar, b2t)
            roh = _roh_upper_bound(dbar, q_avg)

            will_answer = (isr_val >= 1.0) and (dbar >= b2t + 0.2)

            rationale = (
                f"Δ̄={dbar:.4f}, B2T={b2t:.4f}, ISR={isr_val:.3f}, "
                f"P(answer)={P_answer:.3f}, q_lo={q_cons:.3f}, RoH={roh:.3f}"
            )

            logger.info(f"Aligned closed-book validation: {'ANSWER' if will_answer else 'REFUSE'}, RoH={roh:.3f}, ISR={isr_val:.3f}")

            return will_answer, roh, rationale

        except Exception as e:
            logger.error(f"Aligned closed-book validation failed: {e}")
            return True, 1.0, f"validation_error: {str(e)}"

    def validate_extraction_batch(
        self,
        task_description: str,
        evidence: str,
        extracted_items: list,
        item_type: str = "items"
    ) -> Tuple[bool, float, str, int]:
        """Validate batch with aligned computation."""
        if not extracted_items:
            return True, 0.0, "no_items_to_validate", 0

        import json

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
