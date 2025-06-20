//
//  mock.data.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/6/20.
//
import { serverDateFormat, serverDatetimeFormat } from '@/app.config';
import moment from 'moment';

export const userData = {
    id: 'userId',
    email: 'mock.account@example.com',
    firstName: 'Jane',
    lastName: 'Doe',
};

export const staffAccount = {
    userId: '1',
    attributes: {
        givenName: 'Jane',
        familyName: 'Doe',
        email: 'test@example.com',
    },
    permissions: {
        octp: {
            actions: {
                admin: true,
                readPrivate: true,
                readSsn: true,
            },
            jurisdictions: {
                al: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSsn: true,
                    },
                },
                co: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSsn: true,
                    },
                },
                ky: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSsn: true,
                    },
                },
                ne: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSsn: true,
                    },
                },
                oh: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSsn: true,
                    },
                },
                nv: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSsn: true,
                    },
                },
            },
        },
        aslp: {
            actions: {
                admin: true,
                readPrivate: true,
                readSsn: true,
            },
            jurisdictions: {
                ak: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSsn: true,
                    },
                },
                ar: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSsn: true,
                    },
                },
                co: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSsn: true,
                    },
                },
            },
        },
        coun: {
            actions: {
                admin: true,
                readPrivate: true,
                readSsn: true,
            },
            jurisdictions: {
                al: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSsn: true,
                    },
                },
                co: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSsn: true,
                    },
                },
                ky: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSsn: true,
                    },
                },
            },
        },
    },
};

export const uploadRequestData = {
    upload: {
        url: `https://example.com`,
        fields: {
            field1: 'field1',
            field2: 'field2',
            field3: 'field3',
        },
    },
};

export const privilegePurchaseOptionsResponse = {
    items: [
        {
            compactAbbr: 'octp',
            compactCommissionFee: {
                feeType: 'FLAT_RATE',
                feeAmount: 3.5
            },
            transactionFeeConfiguration: {
                licenseeCharges: {
                    active: true,
                    chargeType: 'FLAT_FEE_PER_PRIVILEGE',
                    chargeAmount: 2
                }
            },
            type: 'compact',
            isSandbox: true,
            paymentProcessorPublicFields: {
                apiLoginId: process.env.VUE_APP_MOCK_API_PAYMENT_LOGIN_ID,
                publicClientKey: process.env.VUE_APP_MOCK_API_PAYMENT_CLIENT_KEY,
            },
        },
        {
            jurisdictionName: 'kentucky',
            postalAbbreviation: 'ky',
            compact: 'octp',
            privilegeFees: [
                {
                    licenseTypeAbbreviation: 'ot',
                    amount: 200
                },
                {
                    licenseTypeAbbreviation: 'ota',
                    amount: 100
                }
            ],
            militaryDiscount: {
                active: true,
                discountType: 'FLAT_RATE',
                discountAmount: 10
            },
            jurisprudenceRequirements: {
                required: true
            },
            type: 'jurisdiction'
        },
        {
            jurisdictionName: 'nebraska',
            postalAbbreviation: 'ne',
            compact: 'octp',
            privilegeFees: [
                {
                    licenseTypeAbbreviation: 'ot',
                    amount: 200
                },
                {
                    licenseTypeAbbreviation: 'ota',
                    amount: 100
                }
            ],
            militaryDiscount: {
                active: true,
                discountType: 'FLAT_RATE',
                discountAmount: 10
            },
            jurisprudenceRequirements: {
                required: true
            },
            type: 'jurisdiction'
        },
        {
            jurisdictionName: 'ohio',
            postalAbbreviation: 'oh',
            compact: 'octp',
            privilegeFees: [
                {
                    licenseTypeAbbreviation: 'ot',
                    amount: 200
                },
                {
                    licenseTypeAbbreviation: 'ota',
                    amount: 100
                }
            ],
            militaryDiscount: {
                active: true,
                discountType: 'FLAT_RATE',
                discountAmount: 10
            },
            jurisprudenceRequirements: {
                required: true
            },
            type: 'jurisdiction'
        },
        {
            jurisdictionName: 'massachusetts',
            postalAbbreviation: 'ma',
            compact: 'octp',
            privilegeFees: [
                {
                    licenseTypeAbbreviation: 'ot',
                    amount: 200
                },
                {
                    licenseTypeAbbreviation: 'ota',
                    amount: 100
                }
            ],
            militaryDiscount: {
                active: false,
                discountType: 'FLAT_RATE',
                discountAmount: 10
            },
            jurisprudenceRequirements: {
                required: true
            },
            type: 'jurisdiction'
        },
        {
            jurisdictionName: 'vermont',
            postalAbbreviation: 'vt',
            compact: 'octp',
            privilegeFees: [
                {
                    licenseTypeAbbreviation: 'ot',
                    amount: 200
                },
                {
                    licenseTypeAbbreviation: 'ota',
                    amount: 100
                }
            ],
            militaryDiscount: {
                active: false,
                discountType: 'FLAT_RATE',
                discountAmount: 10
            },
            jurisprudenceRequirements: {
                required: true
            },
            type: 'jurisdiction'
        },
        {
            jurisdictionName: 'virginia',
            postalAbbreviation: 'va',
            compact: 'octp',
            privilegeFees: [
                {
                    licenseTypeAbbreviation: 'ot',
                    amount: 200
                },
                {
                    licenseTypeAbbreviation: 'ota',
                    amount: 100
                }
            ],
            militaryDiscount: {
                active: false,
                discountType: 'FLAT_RATE',
                discountAmount: 10
            },
            jurisprudenceRequirements: {
                required: false
            },
            type: 'jurisdiction'
        },
        {
            jurisdictionName: 'colorado',
            postalAbbreviation: 'co',
            compact: 'octp',
            privilegeFees: [
                {
                    licenseTypeAbbreviation: 'ot',
                    amount: 200
                },
                {
                    licenseTypeAbbreviation: 'ota',
                    amount: 100
                }
            ],
            militaryDiscount: {
                active: false,
                discountType: 'FLAT_RATE',
                discountAmount: 10
            },
            jurisprudenceRequirements: {
                required: true
            },
            type: 'jurisdiction'
        },
        {
            jurisdictionName: 'maine',
            postalAbbreviation: 'me',
            compact: 'octp',
            privilegeFees: [
                {
                    licenseTypeAbbreviation: 'ot',
                    amount: 250
                },
                {
                    licenseTypeAbbreviation: 'ota',
                    amount: 100
                }
            ],
            militaryDiscount: {
                active: false,
                discountType: 'FLAT_RATE',
                discountAmount: 10
            },
            jurisprudenceRequirements: {
                required: true
            },
            type: 'jurisdiction'
        },
        {
            jurisdictionName: 'connecticut',
            postalAbbreviation: 'ct',
            compact: 'octp',
            privilegeFees: [
                {
                    licenseTypeAbbreviation: 'ot',
                    amount: 200
                },
                {
                    licenseTypeAbbreviation: 'ota',
                    amount: 110
                }
            ],
            militaryDiscount: {
                active: false,
                discountType: 'FLAT_RATE',
                discountAmount: 10
            },
            jurisprudenceRequirements: {
                required: false
            },
            type: 'jurisdiction'
        },
        {
            jurisdictionName: 'rhode island',
            postalAbbreviation: 'ri',
            compact: 'octp',
            privilegeFees: [
                {
                    licenseTypeAbbreviation: 'ot',
                    amount: 200
                },
                {
                    licenseTypeAbbreviation: 'ota',
                    amount: 100
                }
            ],
            militaryDiscount: {
                active: false,
                discountType: 'FLAT_RATE',
                discountAmount: 10
            },
            jurisprudenceRequirements: {
                required: true
            },
            type: 'jurisdiction'
        },
        {
            jurisdictionName: 'nevada',
            postalAbbreviation: 'nv',
            compact: 'octp',
            privilegeFees: [
                {
                    licenseTypeAbbreviation: 'ot',
                    amount: 200
                },
                {
                    licenseTypeAbbreviation: 'ota',
                    amount: 100
                }
            ],
            militaryDiscount: {
                active: false,
                discountType: 'FLAT_RATE',
                discountAmount: 10
            },
            jurisprudenceRequirements: {
                required: true
            },
            type: 'jurisdiction'
        },
        {
            jurisdictionName: 'kansas',
            postalAbbreviation: 'ks',
            compact: 'octp',
            privilegeFees: [
                {
                    licenseTypeAbbreviation: 'ot',
                    amount: 150
                },
                {
                    licenseTypeAbbreviation: 'ota',
                    amount: 100
                }
            ],
            militaryDiscount: {
                active: false,
                discountType: 'FLAT_RATE',
                discountAmount: 10
            },
            jurisprudenceRequirements: {
                required: false
            },
            type: 'jurisdiction'
        },
        {
            jurisdictionName: 'alaska',
            postalAbbreviation: 'ak',
            compact: 'octp',
            privilegeFees: [
                {
                    licenseTypeAbbreviation: 'ot',
                    amount: 100
                },
                {
                    licenseTypeAbbreviation: 'ota',
                    amount: 100
                }
            ],
            militaryDiscount: {
                active: false,
                discountType: 'FLAT_RATE',
                discountAmount: 10
            },
            jurisprudenceRequirements: {
                required: true
            },
            type: 'jurisdiction'
        },
        {
            jurisdictionName: 'arkansas',
            postalAbbreviation: 'ar',
            compact: 'octp',
            privilegeFees: [
                {
                    licenseTypeAbbreviation: 'ot',
                    amount: 200
                },
                {
                    licenseTypeAbbreviation: 'ota',
                    amount: 100
                }
            ],
            militaryDiscount: {
                active: false,
                discountType: 'FLAT_RATE',
                discountAmount: 10
            },
            jurisprudenceRequirements: {
                required: true
            },
            type: 'jurisdiction'
        }
    ],
    pagination: {
        pageSize: 100,
        prevLastKey: null,
        lastKey: null
    }
};

export const licensees = {
    prevLastKey: 'xyz',
    lastKey: 'abc',
    providers: [
        {
            homeJurisdictionSelection: {
                dateOfSelection: '2025-02-19',
                compact: 'octp',
                providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                jurisdiction: 'co',
                type: 'homeJurisdictionSelection',
                dateOfUpdate: '2025-02-19'
            },
            privileges: [
                {
                    dateOfUpdate: '2025-03-19T22:02:28+00:00',
                    type: 'privilege',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    compact: 'octp',
                    jurisdiction: 'ne',
                    licenseJurisdiction: 'ky',
                    licenseType: 'occupational therapist',
                    dateOfIssuance: '2025-03-19T21:21:06+00:00',
                    dateOfRenewal: '2025-03-19T21:21:06+00:00',
                    dateOfExpiration: '2026-02-12',
                    compactTransactionId: '120059524697',
                    attestations: [
                        {
                            attestationId: 'personal-information-address-attestation',
                            version: '3'
                        },
                        {
                            attestationId: 'personal-information-home-state-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'jurisprudence-confirmation',
                            version: '1'
                        },
                        {
                            attestationId: 'scope-of-practice-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'not-under-investigation-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'discipline-no-current-encumbrance-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'discipline-no-prior-encumbrance-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'provision-of-true-information-attestation',
                            version: '1'
                        }
                    ],
                    privilegeId: 'OT-NE-8',
                    persistedStatus: 'inactive',
                    status: 'inactive',
                    history: [
                        {
                            dateOfUpdate: '2025-03-19T22:02:28+00:00',
                            type: 'privilegeUpdate',
                            updateType: 'deactivation',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'ne',
                            licenseType: 'occupational therapist',
                            previous: {
                                dateOfIssuance: '2025-03-19T21:21:06+00:00',
                                dateOfRenewal: '2025-03-19T21:21:06+00:00',
                                dateOfExpiration: '2026-02-12',
                                dateOfUpdate: '2025-03-19T21:21:06+00:00',
                                privilegeId: 'OT-NE-8',
                                compactTransactionId: '120059524697',
                                attestations: [
                                    {
                                        attestationId: 'personal-information-address-attestation',
                                        version: '3'
                                    },
                                    {
                                        attestationId: 'personal-information-home-state-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'jurisprudence-confirmation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'scope-of-practice-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'not-under-investigation-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-current-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-prior-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'provision-of-true-information-attestation',
                                        version: '1'
                                    }
                                ],
                                persistedStatus: 'active',
                                licenseJurisdiction: 'ky'
                            },
                            updatedValues: {
                                persistedStatus: 'inactive'
                            }
                        }
                    ]
                },
                {
                    dateOfUpdate: '2025-03-26T16:19:09+00:00',
                    type: 'privilege',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    compact: 'octp',
                    jurisdiction: 'ne',
                    licenseJurisdiction: 'ky',
                    licenseType: 'occupational therapy assistant',
                    dateOfIssuance: '2022-03-19T21:51:26+00:00',
                    dateOfRenewal: '2025-03-26T16:19:09+00:00',
                    dateOfExpiration: '2025-05-12',
                    compactTransactionId: '120060088901',
                    attestations: [
                        {
                            attestationId: 'personal-information-address-attestation',
                            version: '3'
                        },
                        {
                            attestationId: 'personal-information-home-state-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'jurisprudence-confirmation',
                            version: '1'
                        },
                        {
                            attestationId: 'scope-of-practice-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'not-under-investigation-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'discipline-no-current-encumbrance-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'discipline-no-prior-encumbrance-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'provision-of-true-information-attestation',
                            version: '1'
                        }
                    ],
                    privilegeId: 'OTA-NE-10',
                    persistedStatus: 'active',
                    status: 'active',
                    history: [
                        {
                            dateOfUpdate: '2022-03-19T22:02:17+00:00',
                            type: 'privilegeUpdate',
                            updateType: 'deactivation',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'ne',
                            licenseType: 'occupational therapy assistant',
                            previous: {
                                dateOfIssuance: '2025-03-19T21:51:26+00:00',
                                dateOfRenewal: '2025-03-19T21:51:26+00:00',
                                dateOfExpiration: '2026-02-12',
                                dateOfUpdate: '2022-03-19T21:51:26+00:00',
                                privilegeId: 'OTA-NE-10',
                                compactTransactionId: '120059525522',
                                attestations: [
                                    {
                                        attestationId: 'personal-information-address-attestation',
                                        version: '3'
                                    },
                                    {
                                        attestationId: 'personal-information-home-state-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'jurisprudence-confirmation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'scope-of-practice-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'not-under-investigation-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-current-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-prior-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'provision-of-true-information-attestation',
                                        version: '1'
                                    }
                                ],
                                persistedStatus: 'active',
                                licenseJurisdiction: 'ky'
                            },
                            updatedValues: {
                                persistedStatus: 'inactive'
                            }
                        },
                        {
                            dateOfUpdate: '2022-08-19T19:03:56+00:00',
                            type: 'privilegeUpdate',
                            updateType: 'renewal',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'ne',
                            licenseType: 'occupational therapy assistant',
                            previous: {
                                dateOfIssuance: '2025-03-19T21:51:26+00:00',
                                dateOfRenewal: '2022-08-19T19:03:56+00:00',
                                dateOfExpiration: '2026-02-12',
                                dateOfUpdate: '2022-03-19T22:02:17+00:00',
                                privilegeId: 'OTA-NE-10',
                                compactTransactionId: '120059525522',
                                attestations: [
                                    {
                                        attestationId: 'personal-information-address-attestation',
                                        version: '3'
                                    },
                                    {
                                        attestationId: 'personal-information-home-state-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'jurisprudence-confirmation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'scope-of-practice-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'not-under-investigation-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-current-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-prior-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'provision-of-true-information-attestation',
                                        version: '1'
                                    }
                                ],
                                persistedStatus: 'inactive',
                                licenseJurisdiction: 'ky'
                            },
                            updatedValues: {
                                dateOfRenewal: '2025-03-25T19:03:56+00:00',
                                dateOfExpiration: '2026-02-12',
                                privilegeId: 'OTA-NE-10',
                                compactTransactionId: '120060004893',
                                attestations: [
                                    {
                                        attestationId: 'personal-information-address-attestation',
                                        version: '3'
                                    },
                                    {
                                        attestationId: 'personal-information-home-state-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'jurisprudence-confirmation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'scope-of-practice-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'not-under-investigation-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-current-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-prior-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'provision-of-true-information-attestation',
                                        version: '1'
                                    }
                                ],
                                persistedStatus: 'active'
                            }
                        },
                        {
                            dateOfUpdate: '2024-03-01T16:19:09+00:00',
                            type: 'privilegeUpdate',
                            updateType: 'renewal',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'ne',
                            licenseType: 'occupational therapy assistant',
                            previous: {
                                dateOfIssuance: '2022-03-19T21:51:26+00:00',
                                dateOfRenewal: '2024-03-01T16:19:09+00:00',
                                dateOfExpiration: '2026-02-12',
                                dateOfUpdate: '2024-03-25T19:03:56+00:00',
                                privilegeId: 'OTA-NE-10',
                                compactTransactionId: '120060004893',
                                attestations: [
                                    {
                                        attestationId: 'personal-information-address-attestation',
                                        version: '3'
                                    },
                                    {
                                        attestationId: 'personal-information-home-state-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'jurisprudence-confirmation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'scope-of-practice-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'not-under-investigation-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-current-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-prior-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'provision-of-true-information-attestation',
                                        version: '1'
                                    }
                                ],
                                persistedStatus: 'active',
                                licenseJurisdiction: 'ky'
                            },
                            updatedValues: {
                                dateOfRenewal: '2025-03-26T16:19:09+00:00',
                                dateOfExpiration: '2027-02-12',
                                privilegeId: 'OTA-NE-10',
                                compactTransactionId: '120060088901',
                                attestations: [
                                    {
                                        attestationId: 'personal-information-address-attestation',
                                        version: '3'
                                    },
                                    {
                                        attestationId: 'personal-information-home-state-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'jurisprudence-confirmation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'scope-of-practice-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'not-under-investigation-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-current-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-prior-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'provision-of-true-information-attestation',
                                        version: '1'
                                    }
                                ]
                            }
                        }
                    ]
                },
                {
                    dateOfUpdate: '2025-03-28T18:07:08+00:00',
                    type: 'privilege',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    compact: 'octp',
                    jurisdiction: 'oh',
                    licenseJurisdiction: 'ky',
                    licenseType: 'occupational therapist',
                    dateOfIssuance: '2025-03-28T18:07:08+00:00',
                    dateOfRenewal: '2025-03-28T18:07:08+00:00',
                    dateOfExpiration: '2025-02-12',
                    compactTransactionId: '120060232791',
                    attestations: [
                        {
                            attestationId: 'personal-information-address-attestation',
                            version: '3'
                        },
                        {
                            attestationId: 'personal-information-home-state-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'jurisprudence-confirmation',
                            version: '1'
                        },
                        {
                            attestationId: 'scope-of-practice-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'not-under-investigation-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'discipline-no-current-encumbrance-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'discipline-no-prior-encumbrance-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'provision-of-true-information-attestation',
                            version: '1'
                        }
                    ],
                    privilegeId: 'OT-OH-11',
                    persistedStatus: 'active',
                    status: 'inactive',
                    history: []
                },
                {
                    dateOfUpdate: '2025-03-26T15:56:58+00:00',
                    type: 'privilege',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    compact: 'octp',
                    jurisdiction: 'oh',
                    licenseJurisdiction: 'ky',
                    licenseType: 'occupational therapy assistant',
                    dateOfIssuance: '2024-03-19T21:30:27+00:00',
                    dateOfRenewal: '2025-03-26T15:56:58+00:00',
                    dateOfExpiration: moment().format(serverDateFormat),
                    compactTransactionId: '120060086502',
                    attestations: [
                        {
                            attestationId: 'personal-information-address-attestation',
                            version: '3'
                        },
                        {
                            attestationId: 'personal-information-home-state-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'jurisprudence-confirmation',
                            version: '1'
                        },
                        {
                            attestationId: 'scope-of-practice-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'not-under-investigation-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'discipline-no-current-encumbrance-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'discipline-no-prior-encumbrance-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'provision-of-true-information-attestation',
                            version: '1'
                        }
                    ],
                    privilegeId: 'OTA-OH-9',
                    persistedStatus: 'active',
                    status: 'inactive',
                    history: [
                        {
                            dateOfUpdate: '2025-03-26T15:56:58+00:00',
                            type: 'privilegeUpdate',
                            updateType: 'renewal',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'oh',
                            licenseType: 'occupational therapy assistant',
                            previous: {
                                dateOfIssuance: '2024-03-19T21:30:27+00:00',
                                dateOfRenewal: '2024-03-19T21:30:27+00:00',
                                dateOfExpiration: '2025-02-12',
                                dateOfUpdate: '2024-03-19T21:30:27+00:00',
                                privilegeId: 'OTA-OH-9',
                                compactTransactionId: '120059524934',
                                attestations: [
                                    {
                                        attestationId: 'personal-information-address-attestation',
                                        version: '3'
                                    },
                                    {
                                        attestationId: 'personal-information-home-state-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'jurisprudence-confirmation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'scope-of-practice-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'not-under-investigation-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-current-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-prior-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'provision-of-true-information-attestation',
                                        version: '1'
                                    }
                                ],
                                persistedStatus: 'active',
                                licenseJurisdiction: 'ky'
                            },
                            updatedValues: {
                                dateOfRenewal: '2025-03-26T15:56:58+00:00',
                                dateOfExpiration: '2026-02-12',
                                privilegeId: 'OTA-OH-9',
                                compactTransactionId: '120060086502',
                                attestations: [
                                    {
                                        attestationId: 'personal-information-address-attestation',
                                        version: '3'
                                    },
                                    {
                                        attestationId: 'personal-information-home-state-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'jurisprudence-confirmation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'scope-of-practice-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'not-under-investigation-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-current-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-prior-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'provision-of-true-information-attestation',
                                        version: '1'
                                    }
                                ]
                            }
                        }
                    ],
                    adverseActions: [
                        {
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            type: 'adverseAction',
                            jurisdiction: 'oh',
                            licenseTypeAbbreviation: 'ota',
                            licenseType: 'occupational therapy assistant',
                            actionAgainst: 'privilege',
                            clinicalPrivilegeActionCategory: 'Non-compliance With Requirements',
                            effectiveStartDate: moment().subtract(1, 'month').format(serverDateFormat),
                            submittingUser: '1',
                            creationDate: moment().subtract(1, 'week').format(serverDatetimeFormat),
                            adverseActionId: '12345-ABC',
                            effectiveLiftDate: moment().add(11, 'months').format(serverDateFormat),
                            liftingUser: '1',
                        },
                    ],
                },
                {
                    dateOfUpdate: '2025-03-26T16:19:09+00:00',
                    type: 'privilege',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    compact: 'octp',
                    jurisdiction: 'al',
                    licenseJurisdiction: 'ky',
                    licenseType: 'occupational therapy assistant',
                    dateOfIssuance: '2022-03-19T21:51:26+00:00',
                    dateOfRenewal: '2025-03-26T16:19:09+00:00',
                    dateOfExpiration: '2025-05-12',
                    compactTransactionId: '120060088901',
                    attestations: [
                        {
                            attestationId: 'personal-information-address-attestation',
                            version: '3'
                        },
                        {
                            attestationId: 'personal-information-home-state-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'jurisprudence-confirmation',
                            version: '1'
                        },
                        {
                            attestationId: 'scope-of-practice-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'not-under-investigation-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'discipline-no-current-encumbrance-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'discipline-no-prior-encumbrance-attestation',
                            version: '1'
                        },
                        {
                            attestationId: 'provision-of-true-information-attestation',
                            version: '1'
                        }
                    ],
                    privilegeId: 'OTA-AL-10',
                    persistedStatus: 'active',
                    status: 'active',
                    history: [
                        {
                            dateOfUpdate: '2022-03-19T22:02:17+00:00',
                            type: 'privilegeUpdate',
                            updateType: 'deactivation',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'al',
                            licenseType: 'occupational therapy assistant',
                            previous: {
                                dateOfIssuance: '2025-03-19T21:51:26+00:00',
                                dateOfRenewal: '2025-03-19T21:51:26+00:00',
                                dateOfExpiration: '2026-02-12',
                                dateOfUpdate: '2022-03-19T21:51:26+00:00',
                                privilegeId: 'OTA-NE-10',
                                compactTransactionId: '120059525522',
                                attestations: [
                                    {
                                        attestationId: 'personal-information-address-attestation',
                                        version: '3'
                                    },
                                    {
                                        attestationId: 'personal-information-home-state-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'jurisprudence-confirmation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'scope-of-practice-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'not-under-investigation-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-current-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-prior-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'provision-of-true-information-attestation',
                                        version: '1'
                                    }
                                ],
                                persistedStatus: 'active',
                                licenseJurisdiction: 'ky'
                            },
                            updatedValues: {
                                persistedStatus: 'inactive'
                            }
                        },
                        {
                            dateOfUpdate: '2022-08-19T19:03:56+00:00',
                            type: 'privilegeUpdate',
                            updateType: 'renewal',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'al',
                            licenseType: 'occupational therapy assistant',
                            previous: {
                                dateOfIssuance: '2025-03-19T21:51:26+00:00',
                                dateOfRenewal: '2022-08-19T19:03:56+00:00',
                                dateOfExpiration: '2026-02-12',
                                dateOfUpdate: '2022-03-19T22:02:17+00:00',
                                privilegeId: 'OTA-AL-10',
                                compactTransactionId: '120059525522',
                                attestations: [
                                    {
                                        attestationId: 'personal-information-address-attestation',
                                        version: '3'
                                    },
                                    {
                                        attestationId: 'personal-information-home-state-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'jurisprudence-confirmation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'scope-of-practice-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'not-under-investigation-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-current-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-prior-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'provision-of-true-information-attestation',
                                        version: '1'
                                    }
                                ],
                                persistedStatus: 'inactive',
                                licenseJurisdiction: 'ky'
                            },
                            updatedValues: {
                                dateOfRenewal: '2025-03-25T19:03:56+00:00',
                                dateOfExpiration: '2026-02-12',
                                privilegeId: 'OTA-AL-10',
                                compactTransactionId: '120060004893',
                                attestations: [
                                    {
                                        attestationId: 'personal-information-address-attestation',
                                        version: '3'
                                    },
                                    {
                                        attestationId: 'personal-information-home-state-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'jurisprudence-confirmation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'scope-of-practice-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'not-under-investigation-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-current-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-prior-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'provision-of-true-information-attestation',
                                        version: '1'
                                    }
                                ],
                                persistedStatus: 'active'
                            }
                        },
                        {
                            dateOfUpdate: '2024-03-01T16:19:09+00:00',
                            type: 'privilegeUpdate',
                            updateType: 'renewal',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'al',
                            licenseType: 'occupational therapy assistant',
                            previous: {
                                dateOfIssuance: '2022-03-19T21:51:26+00:00',
                                dateOfRenewal: '2024-03-01T16:19:09+00:00',
                                dateOfExpiration: '2026-02-12',
                                dateOfUpdate: '2024-03-25T19:03:56+00:00',
                                privilegeId: 'OTA-AL-10',
                                compactTransactionId: '120060004893',
                                attestations: [
                                    {
                                        attestationId: 'personal-information-address-attestation',
                                        version: '3'
                                    },
                                    {
                                        attestationId: 'personal-information-home-state-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'jurisprudence-confirmation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'scope-of-practice-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'not-under-investigation-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-current-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-prior-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'provision-of-true-information-attestation',
                                        version: '1'
                                    }
                                ],
                                persistedStatus: 'active',
                                licenseJurisdiction: 'ky'
                            },
                            updatedValues: {
                                dateOfRenewal: '2025-03-26T16:19:09+00:00',
                                dateOfExpiration: '2027-02-12',
                                privilegeId: 'OTA-AL-10',
                                compactTransactionId: '120060088901',
                                attestations: [
                                    {
                                        attestationId: 'personal-information-address-attestation',
                                        version: '3'
                                    },
                                    {
                                        attestationId: 'personal-information-home-state-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'jurisprudence-confirmation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'scope-of-practice-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'not-under-investigation-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-current-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'discipline-no-prior-encumbrance-attestation',
                                        version: '1'
                                    },
                                    {
                                        attestationId: 'provision-of-true-information-attestation',
                                        version: '1'
                                    }
                                ]
                            }
                        }
                    ],
                    adverseActions: [
                        {
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            type: 'adverseAction',
                            jurisdiction: 'al',
                            licenseTypeAbbreviation: 'ota',
                            licenseType: 'occupational therapy assistant',
                            actionAgainst: 'privilege',
                            clinicalPrivilegeActionCategory: 'Non-compliance With Requirements',
                            effectiveStartDate: moment().subtract(1, 'month').format(serverDateFormat),
                            submittingUser: '1',
                            creationDate: moment().subtract(1, 'week').format(serverDatetimeFormat),
                            adverseActionId: '12345-DEF',
                            effectiveLiftDate: moment().add(11, 'months').format(serverDateFormat),
                            liftingUser: '1',
                        },
                        {
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            type: 'adverseAction',
                            jurisdiction: 'al',
                            licenseTypeAbbreviation: 'ota',
                            licenseType: 'occupational therapy assistant',
                            actionAgainst: 'privilege',
                            clinicalPrivilegeActionCategory: 'Unsafe Practice or Substandard Care',
                            effectiveStartDate: moment().subtract(3, 'months').format(serverDateFormat),
                            submittingUser: '1',
                            creationDate: moment().subtract(1, 'week').format(serverDatetimeFormat),
                            adverseActionId: '12345-GHI',
                            effectiveLiftDate: null,
                            liftingUser: null,
                        },
                    ],
                },
            ],
            licenseJurisdiction: 'co',
            compact: 'octp',
            homeAddressStreet2: '',
            militaryAffiliations: [{
                affiliationType: 'militaryMember',
                compact: 'octp',
                dateOfUpdate: '2024-08-29',
                dateOfUpload: '2024-08-29',
                documentKeys: 'key',
                fileNames: ['military-document.pdf'],
                status: 'active'
            }],
            npi: '6944447281',
            licenseNumber: 'A-944447281',
            homeAddressPostalCode: '',
            givenName: 'Janet',
            homeAddressStreet1: '1640 Riverside Drive',
            emailAddress: 'test@test.com',
            dateOfBirth: '1990-08-29',
            privilegeJurisdictions: [
                'al'
            ],
            type: 'provider',
            ssnLastFour: '1111',
            licenseType: 'occupational therapy assistant',
            licenses: [
                {
                    compact: 'octp',
                    homeAddressStreet2: '',
                    npi: '6944447281',
                    licenseNumber: 'A-944447281',
                    homeAddressPostalCode: '',
                    jurisdiction: 'co',
                    givenName: 'Jane',
                    homeAddressStreet1: '1640 Riverside Drive',
                    dateOfBirth: '1990-08-29',
                    type: 'license-home',
                    dateOfIssuance: '2023-08-29',
                    ssnLastFour: '1111',
                    licenseType: 'occupational therapy assistant',
                    dateOfExpiration: '2025-08-29',
                    homeAddressState: 'co',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    dateOfRenewal: '2024-08-29',
                    familyName: 'Doe',
                    homeAddressCity: 'Riverside',
                    middleName: '',
                    dateOfUpdate: '2024-08-29',
                    licenseStatus: 'active',
                    licenseStatusName: 'Active in renewal',
                    compactEligibility: 'eligible',
                },
                {
                    compact: 'octp',
                    homeAddressStreet2: '',
                    npi: '6944447281',
                    licenseNumber: 'A-944447281',
                    homeAddressPostalCode: '',
                    jurisdiction: 'co',
                    givenName: 'Jane',
                    homeAddressStreet1: '1640 Riverside Drive',
                    dateOfBirth: '1990-08-29',
                    type: 'license-home',
                    dateOfIssuance: '2023-08-29',
                    ssnLastFour: '1111',
                    licenseType: 'occupational therapist',
                    dateOfExpiration: '2026-08-29',
                    homeAddressState: 'co',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    dateOfRenewal: '2023-08-29',
                    familyName: 'Doe',
                    homeAddressCity: 'Riverside',
                    middleName: '',
                    dateOfUpdate: '2023-08-29',
                    licenseStatus: 'active',
                    licenseStatusName: null,
                    compactEligibility: 'eligible',
                },
                {
                    compact: 'octp',
                    homeAddressStreet2: '',
                    npi: '6944447281',
                    licenseNumber: 'A-944447281',
                    homeAddressPostalCode: '',
                    jurisdiction: 'co',
                    givenName: 'Jane',
                    homeAddressStreet1: '1640 Riverside Drive',
                    dateOfBirth: '1990-08-29',
                    type: 'license-home',
                    dateOfIssuance: '2023-08-29',
                    ssnLastFour: '1111',
                    licenseType: 'occupational therapist',
                    dateOfExpiration: '2026-08-29',
                    homeAddressState: 'co',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    dateOfRenewal: '2023-08-29',
                    familyName: 'Doe',
                    homeAddressCity: 'Riverside',
                    middleName: '',
                    dateOfUpdate: '2023-08-29',
                    licenseStatus: 'active',
                    licenseStatusName: 'Custom text with longer content provided by the state that may not fit completely in the default area of the UI and could overflow',
                    compactEligibility: 'ineligible',
                },
                {
                    compact: 'octp',
                    homeAddressStreet2: '',
                    licenseNumber: 'A-944447281',
                    npi: '6944447281',
                    homeAddressPostalCode: '',
                    jurisdiction: 'ca',
                    givenName: 'Jane',
                    homeAddressStreet1: '1640 Riverside Drive',
                    dateOfBirth: '1990-08-29',
                    type: 'license-home',
                    dateOfIssuance: '2024-08-29',
                    ssnLastFour: '1111',
                    licenseType: 'occupational therapy assistant',
                    dateOfExpiration: '2024-08-29',
                    homeAddressState: 'co',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    dateOfRenewal: '2024-08-29',
                    familyName: 'Doe',
                    homeAddressCity: 'Riverside',
                    middleName: '',
                    dateOfUpdate: '2024-08-29',
                    licenseStatus: 'inactive',
                    licenseStatusName: 'Under review',
                    compactEligibility: 'ineligible',
                },
                {
                    compact: 'octp',
                    homeAddressStreet2: '',
                    licenseNumber: 'A-944447281',
                    npi: '6944447281',
                    homeAddressPostalCode: '',
                    jurisdiction: 'nv',
                    givenName: 'Jane',
                    homeAddressStreet1: '1640 Riverside Drive',
                    dateOfBirth: '1990-08-29',
                    type: 'license-home',
                    dateOfIssuance: '2023-08-29',
                    ssnLastFour: '1111',
                    licenseType: 'occupational therapy assistant',
                    dateOfExpiration: '2024-08-29',
                    homeAddressState: 'co',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    dateOfRenewal: '2024-08-29',
                    familyName: 'Doe',
                    homeAddressCity: 'Riverside',
                    middleName: '',
                    dateOfUpdate: '2024-08-29',
                    licenseStatus: 'inactive',
                    licenseStatusName: '',
                    compactEligibility: 'ineligible',
                    adverseActions: [
                        {
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            type: 'adverseAction',
                            jurisdiction: 'nv',
                            licenseTypeAbbreviation: 'ota',
                            licenseType: 'occupational therapy assistant',
                            actionAgainst: 'privilege',
                            clinicalPrivilegeActionCategory: 'Non-compliance With Requirements',
                            effectiveStartDate: moment().subtract(1, 'month').format(serverDateFormat),
                            submittingUser: '1',
                            creationDate: moment().subtract(1, 'week').format(serverDatetimeFormat),
                            adverseActionId: '12345-JKL',
                            effectiveLiftDate: null,
                            liftingUser: null,
                        },
                    ],
                },
                {
                    compact: 'octp',
                    homeAddressStreet2: '',
                    licenseNumber: 'A-944447281',
                    npi: '6944447281',
                    homeAddressPostalCode: '',
                    jurisdiction: 'nv',
                    givenName: 'Jane',
                    homeAddressStreet1: '1640 Riverside Drive',
                    dateOfBirth: '1990-08-29',
                    type: 'license-home',
                    dateOfIssuance: '2024-08-29',
                    ssnLastFour: '1111',
                    licenseType: 'occupational therapy assistant',
                    dateOfExpiration: '2023-08-29',
                    homeAddressState: 'co',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    dateOfRenewal: '2023-08-29',
                    familyName: 'Doe',
                    homeAddressCity: 'Riverside',
                    middleName: '',
                    dateOfUpdate: '2023-08-29',
                    licenseStatus: 'inactive',
                    licenseStatusName: '',
                    compactEligibility: 'ineligible',
                    adverseActions: [
                        {
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            type: 'adverseAction',
                            jurisdiction: 'al',
                            licenseTypeAbbreviation: 'ota',
                            licenseType: 'occupational therapy assistant',
                            actionAgainst: 'privilege',
                            clinicalPrivilegeActionCategory: 'Non-compliance With Requirements',
                            effectiveStartDate: moment().subtract(1, 'month').format(serverDateFormat),
                            submittingUser: '1',
                            creationDate: moment().subtract(1, 'week').format(serverDatetimeFormat),
                            adverseActionId: '12345-MNO',
                            effectiveLiftDate: moment().add(11, 'months').format(serverDateFormat),
                            liftingUser: '1',
                        },
                        {
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            type: 'adverseAction',
                            jurisdiction: 'al',
                            licenseTypeAbbreviation: 'ota',
                            licenseType: 'occupational therapy assistant',
                            actionAgainst: 'privilege',
                            clinicalPrivilegeActionCategory: 'Unsafe Practice or Substandard Care',
                            effectiveStartDate: moment().subtract(3, 'months').format(serverDateFormat),
                            submittingUser: '1',
                            creationDate: moment().subtract(1, 'week').format(serverDatetimeFormat),
                            adverseActionId: '12345-PQR',
                            effectiveLiftDate: null,
                            liftingUser: null,
                        },
                    ],
                }
            ],
            dateOfExpiration: '2024-08-29',
            homeAddressState: 'co',
            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
            familyName: 'Doe',
            homeAddressCity: 'Riverside',
            middleName: '',
            birthMonthDay: '1990-08-29',
            dateOfUpdate: '2024-08-29',
            status: 'active'
        },
        {
            homeJurisdictionSelection: {
                dateOfSelection: '2025-02-19',
                compact: 'octp',
                providerId: '2',
                jurisdiction: 'co',
                type: 'homeJurisdictionSelection',
                dateOfUpdate: '2025-02-19'
            },
            privileges: [
                {
                    licenseJurisdiction: 'al',
                    dateOfExpiration: '2024-08-29',
                    compact: 'octp',
                    providerId: '2',
                    type: 'privilege',
                    dateOfIssuance: '2024-08-29',
                    dateOfUpdate: '2024-08-29',
                    status: 'active'
                }
            ],
            licenseJurisdiction: 'co',
            compact: 'octp',
            homeAddressStreet2: '',
            npi: '2522457223',
            homeAddressPostalCode: '80302',
            givenName: 'Tyler',
            homeAddressStreet1: '1045 Pearl St',
            emailAddress: 'test@test.com',
            dateOfBirth: '1975-01-01',
            privilegeJurisdictions: [
                'al'
            ],
            type: 'provider',
            ssnLastFour: '2222',
            licenseType: 'occupational therapy assistant',
            licenses: [
                {
                    compact: 'octp',
                    homeAddressStreet2: '',
                    npi: '2522457223',
                    homeAddressPostalCode: '80302',
                    jurisdiction: 'co',
                    givenName: 'Tyler',
                    homeAddressStreet1: '1045 Pearl St',
                    dateOfBirth: '1975-01-01',
                    type: 'license-home',
                    dateOfIssuance: '2024-08-29',
                    ssnLastFour: '2222',
                    licenseType: 'occupational therapy assistant',
                    dateOfExpiration: '2024-08-29',
                    homeAddressState: 'co',
                    providerId: '2',
                    dateOfRenewal: '2024-08-29',
                    familyName: 'Durden',
                    homeAddressCity: 'Boulder',
                    middleName: '',
                    dateOfUpdate: '2024-08-29',
                    licenseStatus: 'inactive',
                    licenseStatusName: 'Custom text with longer content provided by the state that may not fit completely in the default area of the UI and could overflow',
                    compactEligibility: 'eligible',
                }
            ],
            dateOfExpiration: '2024-08-29',
            homeAddressState: 'co',
            providerId: '2',
            familyName: 'Durden',
            homeAddressCity: 'Boulder',
            middleName: '',
            birthMonthDay: '1975-01-01',
            dateOfUpdate: '2024-08-29',
            status: 'inactive'
        },
        {
            homeJurisdictionSelection: {
                dateOfSelection: '2025-02-19',
                compact: 'octp',
                providerId: '3',
                jurisdiction: 'co',
                type: 'homeJurisdictionSelection',
                dateOfUpdate: '2025-02-19'
            },
            privileges: [
                {
                    licenseJurisdiction: 'al',
                    dateOfExpiration: '2024-08-29',
                    compact: 'octp',
                    providerId: '3',
                    type: 'privilege',
                    dateOfIssuance: '2024-08-29',
                    dateOfUpdate: '2024-08-29',
                    status: 'active'
                }
            ],
            licenseJurisdiction: 'co',
            compact: 'octp',
            homeAddressStreet2: '',
            npi: '6944447283',
            homeAddressPostalCode: '80301',
            givenName: 'Marla',
            homeAddressStreet1: '1495 Canyon Blvd',
            emailAddress: 'test@test.com',
            dateOfBirth: '1965-01-01',
            privilegeJurisdictions: [
                'al',
                'ak',
                'ar'
            ],
            type: 'provider',
            ssnLastFour: '3333',
            licenseType: 'occupational therapy assistant',
            licenses: [
                {
                    compact: 'octp',
                    homeAddressStreet2: '',
                    npi: '6944447283',
                    homeAddressPostalCode: '80301',
                    jurisdiction: 'co',
                    givenName: 'Marla',
                    homeAddressStreet1: '1495 Canyon Blvd',
                    dateOfBirth: '1965-01-01',
                    type: 'license-home',
                    dateOfIssuance: '2024-08-29',
                    ssnLastFour: '3333',
                    licenseType: 'occupational therapy assistant',
                    dateOfExpiration: '2024-08-29',
                    homeAddressState: 'co',
                    providerId: '3',
                    dateOfRenewal: '2024-08-29',
                    familyName: 'Singer',
                    homeAddressCity: 'Boulder',
                    middleName: '',
                    dateOfUpdate: '2024-08-29',
                    licenseStatus: 'active',
                    licenseStatusName: 'text from state',
                    compactEligibility: 'eligible',
                }
            ],
            dateOfExpiration: '2024-08-29',
            homeAddressState: 'co',
            providerId: '3',
            familyName: 'Singer',
            homeAddressCity: 'Boulder',
            middleName: '',
            birthMonthDay: '1965-01-01',
            dateOfUpdate: '2024-08-29',
            status: 'active'
        },
        {
            homeJurisdictionSelection: {
                dateOfSelection: '2025-02-19',
                compact: 'octp',
                providerId: '4',
                jurisdiction: 'co',
                type: 'homeJurisdictionSelection',
                dateOfUpdate: '2025-02-19'
            },
            privileges: [
                {
                    licenseJurisdiction: 'al',
                    dateOfExpiration: '2024-08-29',
                    compact: 'octp',
                    providerId: '123',
                    type: 'privilege',
                    dateOfIssuance: '2023-08-29',
                    dateOfUpdate: '2024-08-29',
                    status: 'active'
                },
                {
                    licenseJurisdiction: 'ak',
                    dateOfExpiration: '2024-08-29',
                    compact: 'octp',
                    providerId: '222',
                    type: 'privilege',
                    dateOfIssuance: '2023-08-29',
                    dateOfUpdate: '2024-08-29',
                    status: 'active'
                },
                {
                    licenseJurisdiction: 'ar',
                    dateOfExpiration: '2023-08-29',
                    compact: 'octp',
                    providerId: '22222',
                    type: 'privilege',
                    dateOfIssuance: '2023-08-29',
                    dateOfUpdate: '2024-08-29',
                    status: 'active'
                }
            ],
            licenseJurisdiction: 'co',
            compact: 'octp',
            homeAddressStreet2: '',
            npi: '6944447281',
            homeAddressPostalCode: '',
            givenName: 'Jane',
            homeAddressStreet1: '1640 Riverside Drive',
            emailAddress: 'test@test.com',
            dateOfBirth: '1990-08-29',
            privilegeJurisdictions: [
                'al'
            ],
            type: 'provider',
            ssnLastFour: '4444',
            licenseType: 'occupational therapy assistant',
            licenses: [
                {
                    compact: 'octp',
                    homeAddressStreet2: '',
                    npi: '6944447281',
                    homeAddressPostalCode: '',
                    jurisdiction: 'co',
                    givenName: 'Jane',
                    homeAddressStreet1: '1640 Riverside Drive',
                    dateOfBirth: '1990-08-29',
                    type: 'license-home',
                    dateOfIssuance: '2024-08-29',
                    ssnLastFour: '4444',
                    licenseType: 'occupational therapy assistant',
                    dateOfExpiration: '2024-08-29',
                    homeAddressState: 'co',
                    providerId: '4',
                    dateOfRenewal: '2024-08-29',
                    familyName: 'Doe',
                    homeAddressCity: 'Riverside',
                    middleName: '',
                    dateOfUpdate: '2024-08-29',
                    licenseStatus: 'active',
                    licenseStatusName: '',
                    compactEligibility: 'ineligible',
                }
            ],
            dateOfExpiration: '2024-08-29',
            homeAddressState: 'co',
            providerId: '4',
            familyName: 'Doe',
            homeAddressCity: 'Riverside',
            middleName: '',
            birthMonthDay: '1990-08-29',
            dateOfUpdate: '2024-08-29',
            status: 'active'
        },
    ],
};

export const users = {
    prevLastKey: 'xyz',
    lastKey: 'abc',
    items: [
        {
            userId: '10',
            attributes: {
                givenName: 'Miles',
                familyName: 'Bennet-Dyson',
                email: 'test@example.com',
            },
            permissions: {
                octp: {
                    actions: {
                        admin: true,
                        readPrivate: true,
                        readSsn: true,
                    },
                    jurisdictions: {
                        al: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSsn: true,
                            },
                        },
                        co: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSsn: true,
                            },
                        },
                        ky: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSsn: true,
                            },
                        },
                    },
                },
                aslp: {
                    actions: {
                        admin: true,
                        readPrivate: true,
                        readSsn: true,
                    },
                    jurisdictions: {
                        ak: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSsn: true,
                            },
                        },
                        ar: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSsn: true,
                            },
                        },
                        co: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSsn: true,
                            },
                        },
                    },
                },
                coun: {
                    actions: {
                        admin: true,
                        readPrivate: true,
                        readSsn: true,
                    },
                    jurisdictions: {
                        al: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSsn: true,
                            },
                        },
                        co: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSsn: true,
                            },
                        },
                        ky: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSsn: true,
                            },
                        },
                    },
                },
            },
        },
        {
            userId: '11',
            attributes: {
                givenName: 'John',
                familyName: 'Conner',
                email: 'test1@example.com',
            },
            permissions: {
                octp: {
                    actions: {
                        admin: false,
                        readPrivate: false,
                        readSsn: false,
                    },
                    jurisdictions: {
                        al: {
                            actions: {
                                admin: false,
                                write: false,
                                readPrivate: false,
                                readSsn: false,
                            },
                        },
                        co: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSsn: true,
                            },
                        },
                        ky: {
                            actions: {
                                admin: false,
                                write: true,
                                readPrivate: true,
                                readSsn: true,
                            },
                        },
                    },
                },
            },
        },
        {
            userId: '12',
            attributes: {
                givenName: 'Sarah',
                familyName: 'Conner',
                email: 'test2@example.com',
            },
            permissions: {
                octp: {
                    actions: {
                        admin: false,
                        readPrivate: false,
                        readSsn: false,
                    },
                    jurisdictions: {
                        ky: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSsn: true,
                            },
                        },
                    },
                },
            },
        },
    ],
};

export const attestation = {
    attestationId: 'test-id',
    dateCreated: '2020-01-01',
    dateOfUpdate: '2021-12-31',
    compact: 'octp',
    type: 'test-type',
    displayName: 'Test Attestation',
    text: 'Test Text',
    version: '1',
    locale: 'en',
    required: true,
};

export const compactStates = [
    {
        compact: 'octp',
        postalAbbreviation: 'al',
    },
    {
        compact: 'octp',
        postalAbbreviation: 'co',
    },
    {
        compact: 'octp',
        postalAbbreviation: 'ky',
    },
    {
        compact: 'octp',
        postalAbbreviation: 'ne',
    },
    {
        compact: 'octp',
        postalAbbreviation: 'oh',
    },
];

export const compactConfig = {
    compactAbbr: 'otcp',
    compactName: 'Occupational Therapy',
    compactCommissionFee: {
        feeType: 'FLAT_RATE',
        feeAmount: 10,
    },
    licenseeRegistrationEnabled: false,
    compactOperationsTeamEmails: [
        'ops@example.com',
    ],
    compactAdverseActionsNotificationEmails: [
        'adverse@example.com',
    ],
    compactSummaryReportNotificationEmails: [
        'summary@example.com',
    ],
    transactionFeeConfiguration: {
        licenseeCharges: {
            active: true,
            chargeType: 'FLAT_FEE_PER_PRIVILEGE',
            chargeAmount: 5,
        },
    },
};

export const stateConfig = {
    compact: 'otcp',
    jurisdictionName: 'Kentucky',
    postalAbbreviation: 'ky',
    licenseeRegistrationEnabled: false,
    privilegeFees: [
        {
            licenseTypeAbbreviation: 'ot',
            amount: 30,
            militaryRate: null,
        },
        {
            licenseTypeAbbreviation: 'ota',
            amount: 30,
            militaryRate: 25,
        },
    ],
    jurisprudenceRequirements: {
        required: true,
        linkToDocumentation: 'https://example.com',
    },
    jurisdictionOperationsTeamEmails: [
        'ops@example.com',
    ],
    jurisdictionAdverseActionsNotificationEmails: [
        'adverse@example.com',
    ],
    jurisdictionSummaryReportNotificationEmails: [
        'summary@example.com',
    ],
};

export const pets = [
    {
        id: 1,
        type: 'Dog',
        name: 'Cujo',
        size: 'Large',
        isEvil: true,
    },
    {
        id: 2,
        type: 'Dog',
        name: 'Beethoven',
        size: 'Large',
        isEvil: false,
    },
    {
        id: 3,
        type: 'Dog',
        name: 'Cerberus',
        size: 'Very Large',
        isEvil: true,
    },
    {
        id: 4,
        type: 'Dog',
        name: 'Otis',
        size: 'Small',
        isEvil: false,
    },
];
