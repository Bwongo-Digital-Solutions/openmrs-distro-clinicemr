# AMANAH GEN — How the Solution Works

## 1. Overview

**AMANAH GEN** is a proposed privacy-first Genetic Health Intelligence and Counselling Platform. It is designed to help individuals, families and health systems understand and appropriately respond to inherited disease risks that may be relevant to consanguinity.

Its purpose is not to judge relationships or make decisions for people. It aims to close the gap between **having a screening test** and **understanding the result, accessing qualified guidance, and receiving appropriate follow-up**.

**Tagline:** Understand your genetic health. Make informed choices. Protect what matters.

## 2. The problem it addresses

Premarital and population genetic screening can identify some inherited-disease risks. However, a screening result by itself may not be enough. People may still need help to:

- Understand what a carrier result means.
- Understand when two individual results may have a clinically relevant connection.
- Access qualified genetic counselling.
- Know what follow-up or referral is appropriate.
- Share sensitive information safely and only with permission.

AMANAH GEN connects these steps in one coordinated journey.

## 3. The six solution modules

1. **Genetic Screening Management** — coordinates screening requests, laboratory result receipt and clinical review.
2. **Genetic Risk Intelligence** — organises clinically validated findings and supports approved risk assessment. It must not generate a generic risk score based only on consanguinity.
3. **AI Health Explainer** — explains clinician-approved information in clear, accessible language, with Arabic and English support as a product goal. It can help users check their understanding and prepare questions.
4. **Genetic Counselling Hub** — helps people access qualified genetic counsellors for professional interpretation and guidance.
5. **Privacy & Consent Engine** — keeps individual records separate and manages purpose-specific permission for sharing sensitive information.
6. **Care Navigation** — coordinates referrals, follow-up appointments and appropriate next steps.

## 4. How a typical journey works

The following is the intended end-to-end workflow:

1. **Separate registration:** Each individual creates and controls their own account and health record.
2. **Screening request:** An authorised clinician requests the appropriate screening.
3. **Laboratory processing:** The laboratory performs the tests and returns results through an authorised integration.
4. **Clinical review:** A qualified healthcare professional reviews the results before they are used to guide the individual.
5. **Validated risk information:** The genetics service organises relevant, clinically validated findings using approved rules and evidence.
6. **Clear explanation:** The AI explainer can present clinician-approved information in plain language and help the individual understand terminology and prepare questions.
7. **Optional partner sharing:** Information is shared between individuals only when each person has independently provided the required consent. Records are not automatically merged.
8. **Professional counselling:** A qualified genetic counsellor discusses relevant findings, uncertainty and available options.
9. **Care navigation:** The platform helps coordinate any recommended referral or follow-up.

The platform supports informed decisions; it does not make relationship, marriage or reproductive decisions for anyone.

## 5. How the platform addresses the problem

| Challenge | AMANAH GEN response |
| --- | --- |
| Screening results are difficult to understand | Plain-language explanations based on clinician-approved information |
| People are unsure what a result means for them | Clinical review and access to qualified genetic counselling |
| Relevant findings may need to be considered together | A controlled genetics service using validated clinical rules |
| Follow-up can be fragmented | Referrals and follow-up coordinated through care navigation |
| Genetic information is highly sensitive | Separate individual records, granular consent, access controls and audit trails |
| People may feel pressured to disclose results | Sharing is voluntary, purpose-specific and independently authorised |

## 6. Privacy, consent and trust

Genetic information is particularly sensitive. Privacy is therefore a core part of the product rather than an optional feature.

The intended safeguards include:

- Separate records for each individual; no automatic couple-record merge.
- Explicit, purpose-specific consent before information is shared.
- Granular controls over who can access information, what they can see and for how long.
- Independent consent from each person before couple-level sharing.
- Server-side consent records and auditable access logs.
- Revocation that stops future access where applicable.
- Encryption, access control and data minimisation.
- No sale of genetic data and no advertising based on genetic traits.

Declining to share information must not reveal another person's result or even disclose that the other person participated in screening. Withdrawal of consent does not necessarily erase clinical records that must be retained under applicable law. The final product must be reviewed by qualified UAE legal, privacy and clinical-governance specialists against applicable requirements.

## 7. Responsible use of AI and clinical rules

AI is an explanation and navigation aid, not a genetic specialist or a diagnostic authority.

The AI component may:
- Explain approved clinical information in accessible language.
- Clarify common terms used in a reviewed result.
- Help users prepare questions for a clinician or genetic counsellor.
- Support teach-back so users can check their understanding.

It must not:
- Diagnose a genetic condition.
- Independently classify genetic variants.
- Infer that someone is a carrier.
- Calculate or present unvalidated inherited-disease risks.
- Make marriage or reproductive recommendations.
- Replace a clinician or qualified genetic counsellor.

Any risk calculations must use clinically validated, approved rules and the necessary verified information. For example, the familiar 25% affected, 50% carrier and 25% unaffected probabilities apply only in the appropriate autosomal-recessive scenario when both biological parents carry relevant pathogenic variants for the same condition. They are not a general estimate for consanguinity.

The AI should retrieve information only from approved clinical sources and receive only the minimum clinician-approved context needed for an explanation. Raw genomic or identifiable patient data must not be sent to an external model provider. Running a model locally can reduce external data exposure, but local hosting alone does not guarantee privacy or security.

## 8. Technical architecture

AMANAH GEN is designed as a set of connected layers:

### User-facing layer
- Individual/patient experience.
- Clinician experience.
- Genetic counsellor experience.
- Administrative and health-system oversight.

### AMANAH GEN application services
- AI Gateway.
- Genetics API and validated risk-rules service.
- Consent and permissions service.
- Counselling and referral service.
- Care-navigation and notification services.

### Clinical and data infrastructure
- OpenMRS for core clinical workflows and patient-linked clinical records.
- FHIR and other authorised interfaces for interoperability.
- Relational databases for application and clinical metadata.
- Encrypted document/object storage for authorised documents.
- Identity provider, API gateway, audit and monitoring infrastructure.
- A private AI model service where approved.

**OpenMRS is the clinical backbone, not the genetic interpretation engine.** It can support patient identity, encounters, observations, orders, referrals and clinical workflows. Dedicated services should handle genetics-specific logic, consent, AI orchestration and counselling workflows. FHIR Genomics Reporting resources or implementation guides should be adopted only after confirming actual interoperability and implementation support.

## 9. Technology direction

The current technical direction includes:

- OpenMRS 3 / OpenMRS 3 frontend for the clinical platform.
- Java/Spring Boot for clinical and workflow services where appropriate.
- Python/FastAPI for AI and genetics-service orchestration.
- HL7 FHIR R4 for interoperability, with genomics profiles where supported.
- MariaDB for the OpenMRS database and PostgreSQL for genetics-service metadata.
- Encrypted S3-compatible object storage.
- Keycloak or another approved OIDC identity provider.
- NGINX or Kong as an API gateway.
- RabbitMQ for asynchronous integration events.
- Docker Compose for an isolated development/MVP deployment; Kubernetes can be evaluated for later scale.
- Prometheus and Grafana for monitoring.

The exact versions, integrations and hosting model must be pinned, tested and security-reviewed before a production deployment.

## 10. What is currently in the repository

The current integration work is on the **`amanah-gen-integration`** branch of:

`Bwongo-Digital-Solutions/openmrs-distro-clinicemr`

The implementation is an **integration foundation and early scaffold**, not a complete clinical product.

### Implemented in the repository

- Docker Compose overlay for the AMANAH GEN services.
- Private Ollama service configuration without a publicly published model port.
- FastAPI AI Gateway scaffold.
- OIDC/JWT authentication checks for protected AI endpoints.
- An empty tools endpoint; no patient lookup, unrestricted SQL or database tools are exposed.
- AI safety instructions that restrict the assistant to explaining clinician-approved information.
- Genetics API scaffold with a health endpoint; clinical routes remain disabled/not implemented.
- NGINX routes for the AI and genetics API services.
- Deployment and project documentation.

### Not yet implemented

- Individual, clinician and counsellor user interfaces.
- Complete screening request and laboratory-result workflows.
- Production genetics data model and validated clinical risk rules.
- Consent management and consent-based partner sharing.
- Durable clinical audit and full production access-governance controls.
- AI user interface and approved clinical knowledge retrieval.
- Counselling appointments, referrals and care-navigation workflows.
- End-to-end automated tests, clinical validation and production security certification.

The current scaffolding must not be used to make clinical decisions or connected to real patient/genomic data before the missing controls and clinical workflows are implemented and approved.

## 11. Recommended MVP

Build one complete, testable journey before attempting to deliver all six modules:

**Individual registration → screening request → laboratory result → clinician review → AI explanation → independently consented partner sharing → genetic counselling referral.**

This journey demonstrates the central value of AMANAH GEN: turning screening into understandable, supported and privacy-respecting care.

A sensible delivery sequence is:

1. **Discovery and governance:** confirm user needs, clinical scope, consent model, UAE legal requirements and clinical oversight.
2. **Platform foundation:** identity, roles, OpenMRS integration, API gateway, audit design and secure deployment.
3. **Core workflow:** individual registration, screening requests, laboratory integration and clinician review.
4. **Understanding and counselling:** approved AI explanations, counsellor workflow and referrals.
5. **Consent-based sharing:** independently authorised sharing with clear scope and revocation controls.
6. **Pilot and evaluation:** test usability, understanding, safety, privacy and operational fit with appropriate clinical partners.

## 12. Measuring whether it works

Evaluate the platform using measures such as:

- Whether users understand their screening results.
- Whether people can access qualified genetic counselling.
- Whether appropriate follow-up is completed.
- User confidence and experience.
- Consent compliance and privacy incidents.
- Timeliness and coordination of clinical workflows.
- Clinician and counsellor experience.

Do not define success by whether people make a particular marriage or reproductive choice. Success means people receive accurate information, understand their options and can make informed decisions voluntarily.

## 13. Business and sustainability model

Potential revenue sources include:

- Institutional licensing for health systems and authorised screening programmes.
- Implementation, integration and support services.
- Managed hosting and operations under appropriate governance.
- Approved interoperability and workflow integrations.
- Research and public-health partnerships with suitable ethics, consent and data-governance approvals.

Genetic data must never be sold or used for targeted advertising.

## 14. Important release principle

AMANAH GEN should be released in stages. A working interface or successful Docker deployment does not establish clinical validity, privacy compliance or production readiness. Before any real-world clinical pilot, the system needs qualified clinical ownership, validated rules and content, informed-consent workflows, security testing, auditability, operational procedures and applicable regulatory/legal review.

**In summary:** AMANAH GEN connects genetic screening to understandable explanations, qualified counselling and appropriate follow-up—while keeping each person's genetic information under their control.
