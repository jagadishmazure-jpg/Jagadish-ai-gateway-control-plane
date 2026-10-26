# ADR 0001: Route on measured evals, not model size
Status: accepted. Context: routing by heuristics saves cost but can silently cut quality. Decision: the router picks the cheapest allowed model within a tolerance of the best *measured* accuracy for the task type. Consequences: an eval set per task must be maintained; routing decisions are explainable from `routing_eval_table`.
