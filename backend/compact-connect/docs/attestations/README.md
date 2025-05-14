# Compact Connect Attestation Versioning Design

The Compact Connect system defines a set of attestations that providers must accept when purchasing privileges. Attestations are legally binding statements that providers must agree to, and they are versioned to ensure providers always see and accept the most current version.

## Required Attestations

The following attestations must be defined for each compact:

1. **Jurisprudence Confirmation** (`jurisprudence-confirmation`)
   - Confirms understanding that attestations are legally binding and false information may result in license/privilege loss

2. **Scope of Practice** (`scope-of-practice-attestation`)
   - Confirms understanding and agreement to abide by the state's scope of practice and applicable laws
   - Acknowledges that violations may result in privilege revocation and two-year prohibition

3. **Personal Information - Home State** (`personal-information-home-state-attestation`)
   - Confirms residency in the declared home state
   - Verifies personal and licensure information accuracy

4. **Personal Information - Address** (`personal-information-address-attestation`)
   - Confirms current address accuracy and consent to service of process
   - Acknowledges requirement to notify Commission of address changes
   - Confirms understanding of home state eligibility requirements

5. **Discipline - No Current Encumbrance** (`discipline-no-current-encumbrance-attestation`)
   - Confirms no current disciplinary restrictions on any state license
   - Includes probation, supervision, program completion, and CE requirements

6. **Discipline - No Prior Encumbrance** (`discipline-no-prior-encumbrance-attestation`)
   - Confirms no disciplinary restrictions on any state license within the past two years

7. **Provision of True Information** (`provision-of-true-information-attestation`)
   - General attestation that all provided information is true and accurate

8. **Not Under Investigation** (`not-under-investigation-attestation`) - Mutually exclusive with #9
   - Confirms no current investigations by any board or regulatory body

9. **Under Investigation** (`under-investigation-attestation`) - Mutually exclusive with #8
   - Declares current investigation status
   - Acknowledges that disciplinary action may result in privilege revocation

10. **Military Affiliation** (`military-affiliation-confirmation-attestation`)
    - Required only for providers with active military affiliation
    - Confirms accuracy of uploaded military status documentation

Each attestation includes:
- `attestationId`: Unique identifier for the attestation
- `displayName`: Human-readable name
- `description`: Brief description of the attestation's purpose
- `text`: The full text of the attestation
- `required`: Whether the attestation is required
- `locale`: Language code (currently only "en" supported)

## Attestation Versioning

The system automatically handles versioning of attestations. When any of the following fields change, the system creates a new version:
- Display name
- Description
- Text content
- Required status

Each attestation in the database is stored with:
- A version number (incremented with each change)
- A timestamp of when the version was created
- All other fields needed to display the attestation

When a provider views attestations, they always see the most recent version. When submitting attestations during a privilege purchase, the system includes the version number they agreed to. The system validates that the version is the latest, ensuring providers always see and accept the most up-to-date terms.

## Attestation Validation During Privilege Purchase

When a provider purchases a privilege, they must agree to all required attestations. The system performs the following validation:

1. All required attestations must be included (the 7 core attestations, plus either "Not Under Investigation" OR "Under Investigation")
2. The Military Affiliation attestation is required if and only if the provider has an active military affiliation
3. All attestations must include the current version number
4. Exactly one of the investigation attestations must be provided (either "Not Under Investigation" OR "Under Investigation")
5. No invalid or unrecognized attestation IDs are permitted

If any of these validation rules fail, the purchase is rejected with an appropriate error message.

## Implementation Details

Attestations are stored in the Compact Configuration table with the following structure:
- `pk`: `COMPACT#{compact}#ATTESTATIONS`
- `sk`: `COMPACT#{compact}#LOCALE#{locale}#ATTESTATION#{attestationId}#VERSION#{version}`

The system retrieves the latest attestation version for a given attestation ID by querying with the appropriate prefix and sorting in descending order, then taking the first result.

Attestations are retrieved during the privilege purchase process via the `get_attestations_by_locale` method, which returns a dictionary of attestation records keyed by attestation ID.