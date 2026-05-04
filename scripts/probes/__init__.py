"""One-shot diagnostic probes against the live Graphiti / FalkorDB stack.

Each probe is a single-purpose script that writes throwaway state under
``*-probetest`` group_ids, captures a structured JSON outcome, and self-cleans
its partitions on both success and failure. Probes are not part of the
production runtime and are not imported by ``study_tutor.*`` modules.
"""
