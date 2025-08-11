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
                        admin: false,
                        write: true,
                        readPrivate: true,
                        readSsn: true,
                    },
                },
                ne: {
                    actions: {
                        admin: false,
                        write: true,
                        readPrivate: true,
                        readSsn: true,
                    },
                },
                oh: {
                    actions: {
                        admin: false,
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
                ma: {
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
                required: true,
                linkToDocumentation: 'https://example.com',
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
                required: true,
                linkToDocumentation: 'https://example.com',
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
                required: true,
                linkToDocumentation: 'https://example.com',
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
        },
        {
            jurisdictionName: 'alabama',
            postalAbbreviation: 'al',
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
            jurisdictionName: 'montana',
            postalAbbreviation: 'mt',
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
            jurisdictionName: 'maryland',
            postalAbbreviation: 'md',
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
            jurisdictionName: 'utah',
            postalAbbreviation: 'ut',
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
            jurisdictionName: 'new mexico',
            postalAbbreviation: 'nm',
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
            jurisdictionName: 'oklahoma',
            postalAbbreviation: 'ok',
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
            jurisdictionName: 'washington',
            postalAbbreviation: 'wa',
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
            jurisdictionName: 'oregon',
            postalAbbreviation: 'or',
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
            jurisdictionName: 'new hampshire',
            postalAbbreviation: 'nh',
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
            currentHomeJurisdiction: 'co',
            privileges: [
                {
                    dateOfUpdate: moment().subtract(7, 'months').format(serverDateFormat),
                    type: 'privilege',
                    providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                    compact: 'octp',
                    jurisdiction: 'ne',
                    licenseJurisdiction: 'co',
                    licenseType: 'occupational therapy assistant',
                    dateOfIssuance: moment().subtract(2, 'years').subtract(7, 'months').format(serverDateFormat),
                    dateOfRenewal: moment().subtract(2, 'months').format(serverDateFormat),
                    dateOfExpiration: moment().add(10, 'months').format(serverDateFormat),
                    compactTransactionId: '120060088902',
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
                    privilegeId: 'OTA-NE-11',
                    persistedStatus: 'active',
                    status: 'active',
                    history: [
                        {
                            dateOfUpdate: moment().subtract(1, 'years').subtract(7, 'months').format(serverDateFormat),
                            type: 'privilegeUpdate',
                            updateType: 'deactivation',
                            providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                            compact: 'octp',
                            jurisdiction: 'ne',
                            licenseType: 'occupational therapy assistant',
                            previous: {
                                dateOfIssuance: '2025-03-19T21:51:26+00:00',
                                dateOfRenewal: '2025-03-19T21:51:26+00:00',
                                dateOfExpiration: '2026-02-12',
                                dateOfUpdate: '2022-03-19T21:51:26+00:00',
                                privilegeId: 'OTA-NE-11',
                                compactTransactionId: '120059525523',
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
                                licenseJurisdiction: 'co'
                            },
                            updatedValues: {
                                persistedStatus: 'inactive'
                            }
                        },
                        {
                            dateOfUpdate: moment().subtract(1, 'years').subtract(2, 'months').format(serverDateFormat),
                            type: 'privilegeUpdate',
                            updateType: 'renewal',
                            providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                            compact: 'octp',
                            jurisdiction: 'ne',
                            licenseType: 'occupational therapy assistant',
                            previous: {
                                dateOfIssuance: '2025-03-19T21:51:26+00:00',
                                dateOfRenewal: '2022-08-19T19:03:56+00:00',
                                dateOfExpiration: '2026-02-12',
                                dateOfUpdate: '2022-03-19T22:02:17+00:00',
                                privilegeId: 'OTA-NE-11',
                                compactTransactionId: '120059525523',
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
                                licenseJurisdiction: 'ca'
                            },
                            updatedValues: {
                                dateOfRenewal: '2025-03-25T19:03:56+00:00',
                                dateOfExpiration: '2026-02-12',
                                privilegeId: 'OTA-NE-11',
                                compactTransactionId: '120060004894',
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
                            dateOfUpdate: moment().subtract(2, 'months').format(serverDateFormat),
                            type: 'privilegeUpdate',
                            updateType: 'renewal',
                            providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                            compact: 'octp',
                            jurisdiction: 'ne',
                            licenseType: 'occupational therapy assistant',
                            previous: {
                                dateOfIssuance: '2022-03-19T21:51:26+00:00',
                                dateOfRenewal: '2024-03-01T16:19:09+00:00',
                                dateOfExpiration: '2026-02-12',
                                dateOfUpdate: '2024-03-25T19:03:56+00:00',
                                privilegeId: 'OTA-NE-11',
                                compactTransactionId: '120060004894',
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
                                privilegeId: 'OTA-NE-11',
                                compactTransactionId: '120060088902',
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
                    dateOfUpdate: moment().subtract(9, 'months').format(serverDateFormat),
                    type: 'privilege',
                    providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                    compact: 'octp',
                    jurisdiction: 'oh',
                    licenseJurisdiction: 'ca',
                    licenseType: 'occupational therapist',
                    dateOfIssuance: moment().subtract(9, 'months').format(serverDateFormat),
                    dateOfRenewal: moment().subtract(9, 'months').format(serverDateFormat),
                    dateOfExpiration: moment().add(1, 'month').format(serverDateFormat),
                    compactTransactionId: '120060088903',
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
                    privilegeId: 'OTA-OH-12',
                    persistedStatus: 'active',
                    status: 'active',
                    history: [
                        {
                            dateOfUpdate: moment().subtract(7, 'months').format(serverDateFormat),
                            type: 'privilegeUpdate',
                            updateType: 'deactivation',
                            providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                            compact: 'octp',
                            jurisdiction: 'oh',
                            licenseType: 'occupational therapist',
                            previous: {
                                dateOfIssuance: '2025-03-19T21:51:26+00:00',
                                dateOfRenewal: '2025-03-19T21:51:26+00:00',
                                dateOfExpiration: '2026-02-12',
                                dateOfUpdate: '2022-03-19T21:51:26+00:00',
                                privilegeId: 'OTA-OH-12',
                                compactTransactionId: '120059525524',
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
                                licenseJurisdiction: 'ca'
                            },
                            updatedValues: {
                                persistedStatus: 'inactive'
                            }
                        },
                        {
                            dateOfUpdate: moment().subtract(6, 'months').format(serverDateFormat),
                            type: 'privilegeUpdate',
                            updateType: 'renewal',
                            providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                            compact: 'octp',
                            jurisdiction: 'oh',
                            licenseType: 'occupational therapist',
                            previous: {
                                dateOfIssuance: '2022-03-19T21:51:26+00:00',
                                dateOfRenewal: '2024-03-01T16:19:09+00:00',
                                dateOfExpiration: '2026-02-12',
                                dateOfUpdate: '2024-03-25T19:03:56+00:00',
                                privilegeId: 'OTA-OH-12',
                                compactTransactionId: '120060004895',
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
                                licenseJurisdiction: 'ca'
                            },
                            updatedValues: {
                                dateOfRenewal: '2025-03-26T16:19:09+00:00',
                                dateOfExpiration: '2027-02-12',
                                privilegeId: 'OTA-OH-12',
                                compactTransactionId: '120060088903',
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
                            providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                            compact: 'octp',
                            type: 'adverseAction',
                            jurisdiction: 'oh',
                            licenseTypeAbbreviation: 'ota',
                            licenseType: 'occupational therapy assistant',
                            actionAgainst: 'privilege',
                            clinicalPrivilegeActionCategory: 'Non-compliance With Requirements',
                            effectiveStartDate: moment().subtract(7, 'months').format(serverDateFormat),
                            submittingUser: '1',
                            creationDate: moment().subtract(8, 'months').format(serverDatetimeFormat),
                            adverseActionId: '12345-DEF-JW',
                            effectiveLiftDate: moment().subtract(5, 'months').format(serverDateFormat),
                            liftingUser: '1',
                        },
                        {
                            providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                            compact: 'octp',
                            type: 'adverseAction',
                            jurisdiction: 'oh',
                            licenseTypeAbbreviation: 'ota',
                            licenseType: 'occupational therapy assistant',
                            actionAgainst: 'privilege',
                            clinicalPrivilegeActionCategory: 'Unsafe Practice or Substandard Care',
                            effectiveStartDate: moment().subtract(3, 'months').format(serverDateFormat),
                            submittingUser: '1',
                            creationDate: moment().subtract(1, 'week').format(serverDatetimeFormat),
                            adverseActionId: '12345-GHI-JW',
                            effectiveLiftDate: moment().subtract(1, 'months').format(serverDateFormat),
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
            npi: '1234567890',
            licenseNumber: 'A-555666777',
            homeAddressPostalCode: '98008',
            givenName: 'Layne',
            homeAddressStreet1: '16639 Northup Way',
            emailAddress: 'test@example.com',
            compactConnectRegisteredEmailAddress: 'test@example.com',
            dateOfBirth: '1967-08-22',
            privilegeJurisdictions: [
                'ne',
                'oh'
            ],
            type: 'provider',
            ssnLastFour: '7777',
            licenseType: 'occupational therapy assistant',
            licenses: [
                {
                    compact: 'octp',
                    homeAddressStreet2: '',
                    npi: '1234567890',
                    licenseNumber: 'A-987654321',
                    homeAddressPostalCode: '80203',
                    jurisdiction: 'co',
                    givenName: 'Jeff',
                    homeAddressStreet1: '79 N Washington Street',
                    dateOfBirth: '1967-08-22',
                    type: 'license-home',
                    dateOfIssuance: moment().subtract(10, 'months').format(serverDateFormat),
                    ssnLastFour: '7777',
                    licenseType: 'occupational therapy assistant',
                    dateOfExpiration: moment().add(2, 'months').format(serverDateFormat),
                    homeAddressState: 'co',
                    providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                    dateOfRenewal: '2024-08-29',
                    familyName: 'Cornell',
                    homeAddressCity: 'Denver',
                    middleName: '',
                    dateOfUpdate: moment().subtract(10, 'months').format(serverDateFormat),
                    licenseStatus: 'active',
                    licenseStatusName: 'Active in renewal',
                    compactEligibility: 'eligible',
                },
                {
                    compact: 'octp',
                    homeAddressStreet2: '',
                    npi: '1234567890',
                    licenseNumber: 'A-555666777',
                    homeAddressPostalCode: '90046',
                    jurisdiction: 'ca',
                    givenName: 'Layne',
                    homeAddressStreet1: '8021 Floral Ave',
                    dateOfBirth: '1967-08-22',
                    type: 'license-home',
                    dateOfIssuance: moment().subtract(2, 'years').subtract(7, 'days').subtract(10, 'months')
                        .format(serverDateFormat),
                    ssnLastFour: '7777',
                    licenseType: 'occupational therapist',
                    dateOfExpiration: moment().subtract(7, 'days').add(2, 'months').format(serverDateFormat),
                    homeAddressState: 'ca',
                    providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                    dateOfRenewal: moment().subtract(7, 'days').subtract(10, 'months').format(serverDateFormat),
                    familyName: 'Cornell',
                    homeAddressCity: 'Los Angeles',
                    middleName: '',
                    dateOfUpdate: moment().subtract(7, 'days').subtract(10, 'months').format(serverDateFormat),
                    licenseStatus: 'active',
                    licenseStatusName: null,
                    compactEligibility: 'eligible',
                },
            ],
            dateOfExpiration: moment().add(2, 'months').format(serverDateFormat),
            homeAddressState: 'wa',
            providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
            familyName: 'Cornell',
            homeAddressCity: 'Bellevue',
            middleName: '',
            birthMonthDay: '1967-08-22',
            dateOfUpdate: moment().subtract(10, 'months').format(serverDateFormat),
            licenseStatus: 'active'
        },
        {
            currentHomeJurisdiction: 'co',
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
                    dateOfUpdate: moment().subtract(7, 'months').format(serverDateFormat),
                    type: 'privilege',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    compact: 'octp',
                    jurisdiction: 'ne',
                    licenseJurisdiction: 'ky',
                    licenseType: 'occupational therapy assistant',
                    dateOfIssuance: moment().subtract(2, 'years').subtract(7, 'months').format(serverDateFormat),
                    dateOfRenewal: moment().subtract(2, 'months').format(serverDateFormat),
                    dateOfExpiration: moment().add(10, 'months').format(serverDateFormat),
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
                            dateOfUpdate: moment().subtract(1, 'years').subtract(7, 'months').format(serverDateFormat),
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
                            dateOfUpdate: moment().subtract(1, 'years').subtract(2, 'months').format(serverDateFormat),
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
                            dateOfUpdate: moment().subtract(2, 'months').format(serverDateFormat),
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
                    dateOfIssuance: '2024-03-28T18:07:08+00:00',
                    dateOfRenewal: '2025-03-28T18:07:08+00:00',
                    dateOfExpiration: '2025-03-28',
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
                    dateOfUpdate: moment().subtract(9, 'months').format(serverDateFormat),
                    type: 'privilege',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    compact: 'octp',
                    jurisdiction: 'al',
                    licenseJurisdiction: 'ky',
                    licenseType: 'occupational therapy assistant',
                    dateOfIssuance: moment().subtract(9, 'months').format(serverDateFormat),
                    dateOfRenewal: moment().subtract(9, 'months').format(serverDateFormat),
                    dateOfExpiration: moment().add(1, 'month').format(serverDateFormat),
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
                            dateOfUpdate: moment().subtract(7, 'months').format(serverDateFormat),
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
                                persistedStatus: 'active',
                                licenseJurisdiction: 'ky'
                            },
                            updatedValues: {
                                persistedStatus: 'inactive'
                            }
                        },
                        {
                            dateOfUpdate: moment().subtract(6, 'months').format(serverDateFormat),
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
                            effectiveStartDate: moment().subtract(7, 'months').format(serverDateFormat),
                            submittingUser: '1',
                            creationDate: moment().subtract(8, 'months').format(serverDatetimeFormat),
                            adverseActionId: '12345-DEF',
                            effectiveLiftDate: moment().subtract(5, 'months').format(serverDateFormat),
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
                            effectiveLiftDate: moment().subtract(1, 'months').format(serverDateFormat),
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
                status: 'initializing'
            }],
            npi: '6441445289',
            licenseNumber: 'A-944447281',
            homeAddressPostalCode: '',
            givenName: 'Janet',
            homeAddressStreet1: '1640 Riverside Drive',
            emailAddress: 'test@example.com',
            compactConnectRegisteredEmailAddress: 'test@example.com',
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
                    npi: '6441445289',
                    licenseNumber: 'A-441445289',
                    homeAddressPostalCode: '',
                    jurisdiction: 'co',
                    givenName: 'Jane',
                    homeAddressStreet1: '1640 Riverside Drive',
                    dateOfBirth: '1990-08-29',
                    type: 'license-home',
                    dateOfIssuance: moment().subtract(10, 'months').format(serverDateFormat),
                    ssnLastFour: '1111',
                    licenseType: 'occupational therapy assistant',
                    dateOfExpiration: moment().add(2, 'months').format(serverDateFormat),
                    homeAddressState: 'co',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    dateOfRenewal: '2024-08-29',
                    familyName: 'Doe',
                    homeAddressCity: 'Riverside',
                    middleName: '',
                    dateOfUpdate: moment().subtract(10, 'months').format(serverDateFormat),
                    licenseStatus: 'active',
                    licenseStatusName: 'Active in renewal',
                    compactEligibility: 'eligible',
                },
                {
                    compact: 'octp',
                    homeAddressStreet2: '',
                    npi: '6441445289',
                    licenseNumber: 'A-921445289',
                    homeAddressPostalCode: '',
                    jurisdiction: 'co',
                    givenName: 'Jane',
                    homeAddressStreet1: '1640 Riverside Drive',
                    dateOfBirth: '1990-08-29',
                    type: 'license-home',
                    dateOfIssuance: moment().subtract(1, 'years').subtract(11, 'months').format(serverDateFormat),
                    ssnLastFour: '1111',
                    licenseType: 'occupational therapist',
                    dateOfExpiration: moment().add(1, 'months').format(serverDateFormat),
                    homeAddressState: 'co',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    dateOfRenewal: moment().subtract(11, 'months').format(serverDateFormat),
                    familyName: 'Doe',
                    homeAddressCity: 'Riverside',
                    middleName: '',
                    dateOfUpdate: moment().subtract(1, 'months').format(serverDateFormat),
                    licenseStatus: 'active',
                    licenseStatusName: null,
                    compactEligibility: 'eligible',
                },
                {
                    compact: 'octp',
                    homeAddressStreet2: '',
                    npi: '6441445289',
                    licenseNumber: 'A-944945289',
                    homeAddressPostalCode: '',
                    jurisdiction: 'ma',
                    givenName: 'Jane',
                    homeAddressStreet1: '1640 Riverside Drive',
                    dateOfBirth: '1990-08-29',
                    type: 'license-home',
                    dateOfIssuance: moment().subtract(2, 'years').subtract(7, 'days').subtract(10, 'months')
                        .format(serverDateFormat),
                    ssnLastFour: '1111',
                    licenseType: 'occupational therapist',
                    dateOfExpiration: moment().subtract(7, 'days').add(2, 'months').format(serverDateFormat),
                    homeAddressState: 'co',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    dateOfRenewal: moment().subtract(7, 'days').subtract(10, 'months').format(serverDateFormat),
                    familyName: 'Doe',
                    homeAddressCity: 'Riverside',
                    middleName: '',
                    dateOfUpdate: moment().subtract(7, 'days').subtract(10, 'months').format(serverDateFormat),
                    licenseStatus: 'active',
                    licenseStatusName: 'Custom text with longer content provided by the state that may not fit completely in the default area of the UI and could overflow',
                    compactEligibility: 'ineligible',
                },
                {
                    compact: 'octp',
                    homeAddressStreet2: '',
                    licenseNumber: 'A-421445219',
                    npi: '6441445289',
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
                    licenseNumber: 'A-531445219',
                    npi: '6441445289',
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
            ],
            dateOfExpiration: '2024-08-29',
            homeAddressState: 'co',
            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
            familyName: 'Doe',
            homeAddressCity: 'Riverside',
            middleName: '',
            birthMonthDay: '1990-08-29',
            dateOfUpdate: '2024-08-29',
            licenseStatus: 'active'
        },
        {
            currentHomeJurisdiction: 'co',
            privileges: [
                {
                    licenseJurisdiction: 'al',
                    dateOfExpiration: '2024-08-29',
                    compact: 'octp',
                    providerId: '2',
                    type: 'privilege',
                    dateOfIssuance: '2023-08-29',
                    dateOfUpdate: '2024-08-29',
                    status: 'inactive',
                    privilegeId: 'OCTP-AL-19'
                }
            ],
            licenseJurisdiction: 'co',
            compact: 'octp',
            homeAddressStreet2: '',
            npi: '2522457223',
            homeAddressPostalCode: '80302',
            givenName: 'Tyler',
            homeAddressStreet1: '1045 Pearl St',
            emailAddress: 'test@example.com',
            compactConnectRegisteredEmailAddress: 'test@example.com',
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
                    licenseNumber: 'A-312445289',
                    homeAddressStreet2: '',
                    npi: '2522457223',
                    homeAddressPostalCode: '80302',
                    jurisdiction: 'co',
                    givenName: 'Tyler',
                    homeAddressStreet1: '1045 Pearl St',
                    dateOfBirth: '1975-01-01',
                    type: 'license-home',
                    dateOfIssuance: '2023-08-29',
                    ssnLastFour: '2222',
                    licenseType: 'occupational therapy assistant',
                    dateOfExpiration: '2024-08-29',
                    homeAddressState: 'co',
                    providerId: '2',
                    dateOfRenewal: '2023-08-29',
                    familyName: 'Durden',
                    homeAddressCity: 'Boulder',
                    middleName: '',
                    dateOfUpdate: '2023-08-29',
                    licenseStatus: 'inactive',
                    licenseStatusName: 'Custom text with longer content provided by the state that may not fit completely in the default area of the UI and could overflow',
                    compactEligibility: 'ineligible',
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
            licenseStatus: 'inactive'
        },
        {
            currentHomeJurisdiction: 'co',
            privileges: [
                {
                    licenseJurisdiction: 'al',
                    dateOfExpiration: moment().add(2, 'months').format(serverDateFormat),
                    compact: 'octp',
                    providerId: '3',
                    type: 'privilege',
                    dateOfIssuance: moment().subtract(10, 'months').subtract(1, 'year').format(serverDateFormat),
                    dateOfUpdate: moment().subtract(10, 'months').subtract(1, 'year').format(serverDateFormat),
                    status: 'active',
                    privilegeId: 'OCTP-AL-22'
                }
            ],
            licenseJurisdiction: 'co',
            compact: 'octp',
            homeAddressStreet2: '',
            npi: '6944447283',
            homeAddressPostalCode: '80301',
            givenName: 'Marla',
            homeAddressStreet1: '1495 Canyon Blvd',
            emailAddress: 'test@example.com',
            compactConnectRegisteredEmailAddress: 'test@example.com',
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
                    dateOfIssuance: moment().add(1, 'day').subtract(11, 'months').subtract(2, 'years')
                        .format(serverDateFormat),
                    ssnLastFour: '3333',
                    licenseType: 'occupational therapy assistant',
                    dateOfExpiration: moment().add(1, 'day').add(1, 'month').format(serverDateFormat),
                    homeAddressState: 'co',
                    providerId: '3',
                    dateOfRenewal: moment().add(1, 'day').subtract(1, 'year').format(serverDateFormat),
                    familyName: 'Singer',
                    homeAddressCity: 'Boulder',
                    middleName: '',
                    dateOfUpdate: moment().add(1, 'day').subtract(1, 'year').format(serverDateFormat),
                    licenseStatus: 'active',
                    licenseStatusName: 'text from state',
                    compactEligibility: 'eligible',
                    licenseNumber: 'A-1234567890'
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
            licenseStatus: 'active'
        },
        {
            currentHomeJurisdiction: 'co    ',
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
            npi: '6441445289',
            homeAddressPostalCode: '',
            givenName: 'Jane',
            homeAddressStreet1: '1640 Riverside Drive',
            emailAddress: 'test@example.com',
            compactConnectRegisteredEmailAddress: 'test@example.com',
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
                    npi: '6441445289',
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
            licenseStatus: 'active'
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

export const getAttestation = (attestationId) => {
    const attestationObj = { ...attestation };

    switch (attestationId) {
    case 'personal-information-address-attestation':
        attestationObj.text = 'I hereby attest and affirm that the address information I have provided herein and is my current address. I further consent to accept service of process at this address. I will notify the Commission of a change in my Home State address or email address via updating personal information records in this system. I understand that I am only eligible for a Compact Privilege if I am a licensee in my Home State as defined by the Compact. If I mislead the Compact Commission about my Home State, the appropriate board may take action against my Compact Privilege, which may result in the revocation of other Compact Privileges I may hold. I will also be prohibited from obtaining any other Compact Privileges for a period of at least two (2) years.*';
        break;
    case 'personal-information-home-state-attestation':
        attestationObj.text = 'I hereby attest and affirm that this is my personal and licensure information and that I am a resident of the state listed on this page.*';
        break;
    case 'not-under-investigation-attestation':
        attestationObj.text = 'I hereby attest and affirm that I am not currently under investigation by any board, agency, department, association, certifying body, or other body.';
        break;
    case 'under-investigation-attestation':
        attestationObj.text = 'I hereby attest and affirm that I am currently under investigation by any board, agency, department, association, certifying body, or other body. I understand that if any investigation results in a disciplinary action, my Compact Privileges may be revoked.';
        break;
    case 'discipline-no-current-encumbrance-attestation':
        attestationObj.text = 'I hereby attest and affirm that I have no encumbrance (any discipline that restricts my full practice or any unmet condition before returning to a full and unrestricted license, including, but not limited, to probation, supervision, completion of a program, and/or completion of CEs) on ANY state license.';
        break;
    case 'discipline-no-prior-encumbrance-attestation':
        attestationObj.text = 'I hereby attest and affirm that I have not had any encumbrance on ANY state license within the previous two years from date of this application for a Compact Privilege.';
        break;
    case 'provision-of-true-information-attestation':
        attestationObj.text = 'I hereby attest and affirm that all information contained in this privilege application is true to the best of my knowledge.';
        break;
    case 'military-affiliation-confirmation-attestation':
        attestationObj.text = 'I hereby attest and affirm that my current military status documentation as uploaded to CompactConnect is accurate.';
        break;
    case 'jurisprudence-confirmation':
        attestationObj.text = 'I understand that an attestation is a legally binding statement. I understand that providing false information on this application could result in a loss of my licenses and/or privileges. I acknowledge that the Commission may audit jurisprudence attestations at their discretion.';
        break;
    case 'scope-of-practice-attestation':
        attestationObj.text = `I hereby attest and affirm that I have reviewed, understand, and will abide by this state's scope of practice and all applicable laws and rules when practicing in the state. I understand that the issuance of a Compact Privilege authorizes me to legally practice in the member jurisdiction in accordance with the laws and rules governing practice of my profession in that jurisdiction.

        If I violate the practice act, the appropriate board may take action against my Compact Privilege, which may result in the revocation of other Compact Privileges or licenses I may hold. I will also be prohibited from obtaining any other Compact Privileges for a period of at least two (2) years.`;
        break;
    default:
        break;
    }

    return attestationObj;
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
    configuredStates: [
        {
            postalAbbreviation: 'al',
            isLive: false,
        },
        {
            postalAbbreviation: 'co',
            isLive: true,
        },
        {
            postalAbbreviation: 'ky',
            isLive: false,
        },
        {
            postalAbbreviation: 'ne',
            isLive: false,
        },
        {
            postalAbbreviation: 'oh',
            isLive: true,
        },
    ],
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
