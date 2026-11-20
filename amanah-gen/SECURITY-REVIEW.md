# Security and clinical release checklist

- [ ] Confirm UAE legal basis, data residency, cross-border transfer, genetic-data, and health-data obligations with qualified counsel.
- [ ] Complete a privacy impact assessment and threat model.
- [ ] Configure OIDC issuer, audience, signing keys, short token lifetime, and least-privilege role mapping.
- [ ] Add rate limiting, request-size limits, security headers, structured audit events, and monitoring at the gateway.
- [ ] Confirm no public Ollama port, no external model egress, and no raw genomic data in model prompts or logs.
- [ ] Implement consent as server-side, purpose-specific, versioned, revocable records with independent consent for each individual.
- [ ] Implement encryption at rest and in transit, managed keys, backups, retention, and incident response.
- [ ] Validate approved clinical content and Arabic/English explanations with genetics professionals.
- [ ] Validate model outputs, bias, hallucinations, accessibility, and escalation pathways.
- [ ] Complete penetration testing and clinical safety approval before enabling real workflows.

The scaffold defaults AI off and Genetics API clinical workflows off. Do not enable either for patient-facing clinical use until all applicable reviews and controls are complete.
