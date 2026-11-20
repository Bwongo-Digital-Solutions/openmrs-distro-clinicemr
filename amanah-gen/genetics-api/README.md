# AMANAH GEN screening workflow and OpenMRS FHIR adapter

This service currently provides two non-patient-specific foundations:

1. A versioned genetic-screening lifecycle definition and transition validator.
2. A read-only OpenMRS FHIR R4 CapabilityStatement adapter.

It does **not** yet create screening requests, store patient identifiers, accept laboratory results, store genomic data, or release results.

## Screening lifecycle

The current lifecycle is:

`requested → sample_collected → lab_received → processing → result_received → clinical_review → clinically_reviewed → follow_up_required/completed`

A request may be cancelled before a result is received. Completed and cancelled are terminal states. The transition validator rejects skipped steps, including any attempt to move from result receipt directly to completion.

The API exposes:

- `GET /workflow/definition` — returns the workflow states, allowed transitions, consent creation rule and clinical-release rule.
- `POST /workflow/validate-transition` — validates a proposed pair of states without creating or changing a screening record.

Both endpoints require a valid AMANAH GEN OIDC access token with a clinician, counsellor or administrator realm role.

## OpenMRS FHIR R4 capability discovery

The adapter calls only:

`GET {OPENMRS_FHIR_BASE_URL}/metadata`

It normalizes the server's FHIR `CapabilityStatement` into the FHIR version, resource types and supported interactions. It does not access patient data and does not perform FHIR writes.

Protected endpoint:

- `GET /integrations/openmrs/fhir/capabilities`

Configuration (all optional; integration remains disabled by default):

- `OPENMRS_FHIR_ENABLED=false`
- `OPENMRS_FHIR_BASE_URL=http://backend:8080/openmrs/ws/fhir2/R4`
- `OPENMRS_FHIR_USERNAME` — dedicated, least-privilege OpenMRS service account when required.
- `OPENMRS_FHIR_PASSWORD` — corresponding secret; never commit or paste it into chat.
- `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_JWKS_URL` — AMANAH GEN token validation settings.
- `FHIR_ALLOWED_ROLES=AMANAH_GEN_CLINICIAN,AMANAH_GEN_COUNSELLOR,AMANAH_GEN_ADMIN`

Do not enable the FHIR integration until the live endpoint and its authentication requirements have been checked. The capability response, not assumptions, must determine which FHIR resources and interactions can be used.

## Intended resource mapping (subject to live capability verification)

- Patient and Encounter: identity and care-context references only.
- ServiceRequest: screening order, if create/read interactions are supported and the workflow governance is approved.
- Specimen: collection and laboratory hand-off, if supported.
- Observation and DiagnosticReport: laboratory findings and report references, only after result governance and clinician review are implemented.
- Task: workflow coordination, if supported.

No raw genomic files or variant interpretation payloads are sent to OpenMRS by this foundation. Avoid copying demographics into the genetics service; retain only the minimum external reference needed by an approved, consented workflow.

## Clinical and privacy release gates

The screening-record endpoints remain unimplemented until all of the following exist and are tested:

- Server-side, purpose-specific, versioned and revocable consent.
- Independent consent for each individual; no automatic couple record or consent merge.
- OIDC authorization at the record and action level, not merely at the route level.
- Dedicated storage separate from the OpenMRS database, with encryption at rest, managed keys, backups and retention controls.
- Durable audit events with actor, purpose, action, timestamp and record reference; audit history must not be editable through application endpoints.
- Idempotency, concurrency control and validated workflow transitions.
- Clinician review and explicit release controls for laboratory results.
- Qualified clinical governance and applicable legal/privacy review.

Keep `GENETICS_API_ENABLED=false` and do not submit real patient or genetic data to these foundation endpoints. The current workflow definition and FHIR capability discovery are not a clinical service.
