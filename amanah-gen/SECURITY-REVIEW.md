# Security and clinical release checklist

- [ ] Confirm UAE and other applicable legal basis, data residency, cross-border transfer, genetic-data, and health-data obligations with qualified counsel.
- [ ] Complete a privacy impact assessment and threat model.
- [ ] Configure OIDC issuer, audience, signing keys, short token lifetime, and least-privilege role mapping.
- [ ] Add rate limiting, request-size limits, security headers, structured audit events, and monitoring at the gateway.
- [ ] Confirm no public Ollama or Knowledge API port, no external model egress, and no raw genomic data in model prompts or logs.
- [ ] Keep the Knowledge API on the private Compose network and protect retrieval with a separate high-entropy service credential.
- [ ] Review source authority, licensing, version, review date, language, and translation before approving any knowledge document.
- [ ] Verify pending and withdrawn documents are never returned by retrieval; test approval and withdrawal behavior.
- [ ] Replace the local registry event trail with central append-only audit storage and enforce separation of duties before production.
- [ ] Validate retrieval relevance, source attribution, source faithfulness, prompt-injection resilience, and refusal when approved sources are insufficient.
- [ ] Implement consent as server-side, purpose-specific, versioned, revocable records with independent consent for each individual.
- [ ] Implement encryption at rest and in transit, managed keys, backups, retention, and incident response.
- [ ] Validate approved clinical content and Arabic/English explanations with genetics professionals.
- [ ] Validate model outputs, bias, hallucinations, accessibility, and escalation pathways.
- [ ] Complete penetration testing and clinical safety approval before enabling real workflows.

The scaffold defaults AI off and Genetics API clinical workflows off. The Knowledge API is an educational retrieval foundation only; it is not approved for patient-specific interpretation. Do not enable patient-facing AI until all applicable reviews and controls are complete.
