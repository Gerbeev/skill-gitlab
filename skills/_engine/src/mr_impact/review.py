"""Versioned semantic-review attestations; evidence binding is not semantic proof."""

from .safety import EngineError

REVIEW_CONTRACT_VERSION = 1


def validate_mr_review(plan, context, changes, require_review):
    if not isinstance(plan, dict):
        raise EngineError("MR interpretation must be an object")
    reviewed = plan.get("reviewed", False)
    if type(reviewed) is not bool:
        raise EngineError("MR reviewed must be a boolean")
    if "review_context" in plan and plan["review_context"] != context:
        raise EngineError("MR interpretation context changed; inspect the current analysis again")
    decisions = plan.get("reviewed_changes", {})
    if not isinstance(decisions, dict):
        raise EngineError("MR reviewed changes must be an object")
    expected = {str(i) for i in range(len(changes))}
    if set(decisions) - expected:
        raise EngineError("MR review references unknown changes")
    for decision in decisions.values():
        if (not isinstance(decision, dict) or decision.get("status") not in {"analyzed", "unresolved", "not_applicable"}
                or not isinstance(decision.get("reason"), str) or not decision["reason"].strip()):
            raise EngineError("MR change review requires a decision and reason")
    if reviewed and (plan.get("review_context") != context or set(decisions) != expected):
        raise EngineError("Completed MR review requires current context and a decision for every change")
    if require_review and not reviewed:
        raise EngineError("A completed, context-bound MR semantic review is required")
    status = "reviewed_with_gaps" if any(d["status"] == "unresolved" for d in decisions.values()) else "reviewed"
    return (status if reviewed else "pending"), decisions
