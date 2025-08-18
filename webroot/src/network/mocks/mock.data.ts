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

export const createStatePrivilegePurchaseOption = (config: any = {}) => {
    const purchaseOption: any = {
        type: 'jurisdiction',
        postalAbbreviation: config?.stateAbbrev,
        jurisdictionName: config?.stateName,
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
            active: Boolean(config?.hasMilitaryDiscount),
            discountType: 'FLAT_RATE',
            discountAmount: 10,
        },
        jurisprudenceRequirements: {
            required: Boolean(config?.hasJurisprudence),
        },
    };

    if (config.hasJurisprudenceLink) {
        purchaseOption.jurisprudenceRequirements.linkToDocumentation = 'https://example.com';
    }

    return purchaseOption;
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
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'ak',
            stateName: 'alaska',
            hasMilitaryDiscount: false,
            hasJurisprudence: true,
            hasJurisprudenceLink: true,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'al',
            stateName: 'alabama',
            hasMilitaryDiscount: false,
            hasJurisprudence: true,
            hasJurisprudenceLink: false,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'ar',
            stateName: 'arkansas',
            hasMilitaryDiscount: false,
            hasJurisprudence: true,
            hasJurisprudenceLink: false,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'co',
            stateName: 'colorado',
            hasMilitaryDiscount: false,
            hasJurisprudence: true,
            hasJurisprudenceLink: true,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'ct',
            stateName: 'connecticut',
            hasMilitaryDiscount: false,
            hasJurisprudence: false,
            hasJurisprudenceLink: false,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'ks',
            stateName: 'kansas',
            hasMilitaryDiscount: false,
            hasJurisprudence: false,
            hasJurisprudenceLink: false,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'ky',
            stateName: 'kentucky',
            hasMilitaryDiscount: true,
            hasJurisprudence: true,
            hasJurisprudenceLink: true,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'ma',
            stateName: 'massachusetts',
            hasMilitaryDiscount: false,
            hasJurisprudence: true,
            hasJurisprudenceLink: false,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'md',
            stateName: 'maryland',
            hasMilitaryDiscount: false,
            hasJurisprudence: false,
            hasJurisprudenceLink: false,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'me',
            stateName: 'maine',
            hasMilitaryDiscount: false,
            hasJurisprudence: true,
            hasJurisprudenceLink: false,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'mt',
            stateName: 'montana',
            hasMilitaryDiscount: false,
            hasJurisprudence: false,
            hasJurisprudenceLink: false,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'ne',
            stateName: 'nebraska',
            hasMilitaryDiscount: true,
            hasJurisprudence: true,
            hasJurisprudenceLink: false,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'nh',
            stateName: 'new hampshire',
            hasMilitaryDiscount: false,
            hasJurisprudence: false,
            hasJurisprudenceLink: false,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'nm',
            stateName: 'new mexico',
            hasMilitaryDiscount: false,
            hasJurisprudence: false,
            hasJurisprudenceLink: false,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'nv',
            stateName: 'nevada',
            hasMilitaryDiscount: false,
            hasJurisprudence: true,
            hasJurisprudenceLink: false,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'oh',
            stateName: 'ohio',
            hasMilitaryDiscount: true,
            hasJurisprudence: true,
            hasJurisprudenceLink: false,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'ok',
            stateName: 'oklahoma',
            hasMilitaryDiscount: false,
            hasJurisprudence: false,
            hasJurisprudenceLink: false,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'or',
            stateName: 'oregon',
            hasMilitaryDiscount: false,
            hasJurisprudence: false,
            hasJurisprudenceLink: false,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'ri',
            stateName: 'rhode island',
            hasMilitaryDiscount: false,
            hasJurisprudence: true,
            hasJurisprudenceLink: false,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'ut',
            stateName: 'utah',
            hasMilitaryDiscount: false,
            hasJurisprudence: false,
            hasJurisprudenceLink: false,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'va',
            stateName: 'virginia',
            hasMilitaryDiscount: false,
            hasJurisprudence: false,
            hasJurisprudenceLink: false,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'vt',
            stateName: 'vermont',
            hasMilitaryDiscount: false,
            hasJurisprudence: true,
            hasJurisprudenceLink: false,
        }),
        createStatePrivilegePurchaseOption({
            stateAbbrev: 'wa',
            stateName: 'washington',
            hasMilitaryDiscount: false,
            hasJurisprudence: false,
            hasJurisprudenceLink: false,
        }),
    ],
    pagination: {
        pageSize: 100,
        prevLastKey: null,
        lastKey: null
    }
};

export const attestationResponses = [
    {
        attestationId: 'personal-information-address-attestation',
        version: '3',
    },
    {
        attestationId: 'personal-information-home-state-attestation',
        version: '1',
    },
    {
        attestationId: 'jurisprudence-confirmation',
        version: '1',
    },
    {
        attestationId: 'scope-of-practice-attestation',
        version: '1',
    },
    {
        attestationId: 'not-under-investigation-attestation',
        version: '1',
    },
    {
        attestationId: 'discipline-no-current-encumbrance-attestation',
        version: '1',
    },
    {
        attestationId: 'discipline-no-prior-encumbrance-attestation',
        version: '1',
    },
    {
        attestationId: 'provision-of-true-information-attestation',
        version: '1',
    },
];

export const licensees = {
    prevLastKey: 'xyz',
    lastKey: 'abc',
    providers: [
        {
            providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
            givenName: 'Layne',
            middleName: '',
            familyName: 'Cornell',
            compact: 'octp',
            type: 'provider',
            emailAddress: 'test@example.com',
            compactConnectRegisteredEmailAddress: 'test@example.com',
            dateOfBirth: '1967-08-22',
            birthMonthDay: '1967-08-22',
            ssnLastFour: '7777',
            homeAddressStreet1: '16639 Northup Way',
            homeAddressStreet2: '',
            homeAddressCity: 'Bellevue',
            homeAddressState: 'wa',
            homeAddressPostalCode: '98008',
            militaryAffiliations: [
                {
                    affiliationType: 'militaryMember',
                    compact: 'octp',
                    dateOfUpdate: '2024-08-29',
                    dateOfUpload: '2024-08-29',
                    documentKeys: 'key',
                    fileNames: ['military-document.pdf'],
                    status: 'active'
                }
            ],
            licenseStatus: 'active',
            licenseJurisdiction: 'co',
            currentHomeJurisdiction: 'co',
            npi: '1234567890',
            licenseNumber: 'A-555666777',
            dateOfUpdate: moment().subtract(10, 'months').format(serverDateFormat),
            dateOfExpiration: moment().add(2, 'months').format(serverDateFormat),
            licenseType: 'occupational therapy assistant',
            licenses: [
                {
                    providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                    givenName: 'Jeff',
                    middleName: '',
                    familyName: 'Cornell',
                    compact: 'octp',
                    dateOfBirth: '1967-08-22',
                    ssnLastFour: '7777',
                    homeAddressStreet1: '79 N Washington Street',
                    homeAddressStreet2: '',
                    homeAddressCity: 'Denver',
                    homeAddressState: 'co',
                    homeAddressPostalCode: '80203',
                    npi: '1234567890',
                    licenseNumber: 'A-987654321',
                    type: 'license-home',
                    licenseType: 'occupational therapy assistant',
                    jurisdiction: 'co',
                    dateOfIssuance: moment().subtract(10, 'months').format(serverDateFormat),
                    dateOfUpdate: moment().subtract(10, 'months').format(serverDateFormat),
                    dateOfExpiration: moment().add(2, 'months').format(serverDateFormat),
                    dateOfRenewal: '2024-08-29',
                    licenseStatus: 'active',
                    licenseStatusName: 'Active in renewal',
                    compactEligibility: 'eligible',
                },
                {
                    providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                    givenName: 'Layne',
                    middleName: '',
                    familyName: 'Cornell',
                    compact: 'octp',
                    dateOfBirth: '1967-08-22',
                    ssnLastFour: '7777',
                    homeAddressStreet1: '8021 Floral Ave',
                    homeAddressStreet2: '',
                    homeAddressCity: 'Los Angeles',
                    homeAddressState: 'ca',
                    homeAddressPostalCode: '90046',
                    npi: '1234567890',
                    licenseNumber: 'A-555666777',
                    type: 'license-home',
                    licenseType: 'occupational therapist',
                    jurisdiction: 'ca',
                    dateOfIssuance: moment().subtract(2, 'years').subtract(7, 'days').subtract(10, 'months')
                        .format(serverDateFormat),
                    dateOfUpdate: moment().subtract(7, 'days').subtract(10, 'months').format(serverDateFormat),
                    dateOfExpiration: moment().subtract(7, 'days').add(2, 'months').format(serverDateFormat),
                    dateOfRenewal: moment().subtract(7, 'days').subtract(10, 'months').format(serverDateFormat),
                    licenseStatus: 'active',
                    licenseStatusName: null,
                    compactEligibility: 'eligible',
                },
            ],
            privilegeJurisdictions: [
                'ne',
                'oh'
            ],
            privileges: [
                {
                    privilegeId: 'OTA-NE-11',
                    providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                    compact: 'octp',
                    compactTransactionId: '120060088902',
                    type: 'privilege',
                    jurisdiction: 'ne',
                    licenseJurisdiction: 'co',
                    licenseType: 'occupational therapy assistant',
                    persistedStatus: 'active',
                    status: 'active',
                    dateOfIssuance: moment().subtract(2, 'years').subtract(7, 'months').format(serverDateFormat),
                    dateOfUpdate: moment().subtract(7, 'months').format(serverDateFormat),
                    dateOfRenewal: moment().subtract(2, 'months').format(serverDateFormat),
                    dateOfExpiration: moment().add(10, 'months').format(serverDateFormat),
                    attestations: attestationResponses.map((response) => ({ ...response })),
                    history: [
                        {
                            providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                            compact: 'octp',
                            jurisdiction: 'ne',
                            type: 'privilegeUpdate',
                            updateType: 'deactivation',
                            licenseType: 'occupational therapy assistant',
                            dateOfUpdate: moment().subtract(1, 'years').subtract(7, 'months').format(serverDateFormat),
                            previous: {
                                privilegeId: 'OTA-NE-11',
                                compactTransactionId: '120059525523',
                                licenseJurisdiction: 'co',
                                persistedStatus: 'active',
                                dateOfIssuance: '2025-03-19T21:51:26+00:00',
                                dateOfUpdate: '2022-03-19T21:51:26+00:00',
                                dateOfRenewal: '2025-03-19T21:51:26+00:00',
                                dateOfExpiration: '2026-02-12',
                                attestations: attestationResponses.map((response) => ({ ...response })),
                            },
                            updatedValues: {
                                persistedStatus: 'inactive',
                            }
                        },
                        {
                            providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                            compact: 'octp',
                            jurisdiction: 'ne',
                            type: 'privilegeUpdate',
                            updateType: 'renewal',
                            licenseType: 'occupational therapy assistant',
                            dateOfUpdate: moment().subtract(1, 'years').subtract(2, 'months').format(serverDateFormat),
                            previous: {
                                privilegeId: 'OTA-NE-11',
                                compactTransactionId: '120059525523',
                                licenseJurisdiction: 'ca',
                                persistedStatus: 'inactive',
                                dateOfIssuance: '2025-03-19T21:51:26+00:00',
                                dateOfUpdate: '2022-03-19T22:02:17+00:00',
                                dateOfRenewal: '2022-08-19T19:03:56+00:00',
                                dateOfExpiration: '2026-02-12',
                                attestations: attestationResponses.map((response) => ({ ...response })),
                            },
                            updatedValues: {
                                privilegeId: 'OTA-NE-11',
                                compactTransactionId: '120060004894',
                                persistedStatus: 'active',
                                dateOfRenewal: '2025-03-25T19:03:56+00:00',
                                dateOfExpiration: '2026-02-12',
                                attestations: attestationResponses.map((response) => ({ ...response })),
                            }
                        },
                        {
                            providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                            compact: 'octp',
                            jurisdiction: 'ne',
                            type: 'privilegeUpdate',
                            updateType: 'renewal',
                            licenseType: 'occupational therapy assistant',
                            dateOfUpdate: moment().subtract(2, 'months').format(serverDateFormat),
                            previous: {
                                privilegeId: 'OTA-NE-11',
                                compactTransactionId: '120060004894',
                                licenseJurisdiction: 'ky',
                                persistedStatus: 'active',
                                dateOfIssuance: '2022-03-19T21:51:26+00:00',
                                dateOfUpdate: '2024-03-25T19:03:56+00:00',
                                dateOfRenewal: '2024-03-01T16:19:09+00:00',
                                dateOfExpiration: '2026-02-12',
                                attestations: attestationResponses.map((response) => ({ ...response })),
                            },
                            updatedValues: {
                                privilegeId: 'OTA-NE-11',
                                compactTransactionId: '120060088902',
                                dateOfRenewal: '2025-03-26T16:19:09+00:00',
                                dateOfExpiration: '2027-02-12',
                                attestations: attestationResponses.map((response) => ({ ...response })),
                            },
                        },
                    ],
                },
                {
                    privilegeId: 'OTA-OH-12',
                    providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                    compact: 'octp',
                    compactTransactionId: '120060088903',
                    type: 'privilege',
                    jurisdiction: 'oh',
                    licenseJurisdiction: 'ca',
                    licenseType: 'occupational therapist',
                    persistedStatus: 'active',
                    status: 'active',
                    dateOfIssuance: moment().subtract(9, 'months').format(serverDateFormat),
                    dateOfUpdate: moment().subtract(9, 'months').format(serverDateFormat),
                    dateOfRenewal: moment().subtract(9, 'months').format(serverDateFormat),
                    dateOfExpiration: moment().add(1, 'month').format(serverDateFormat),
                    attestations: attestationResponses.map((response) => ({ ...response })),
                    history: [
                        {
                            providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                            compact: 'octp',
                            jurisdiction: 'oh',
                            type: 'privilegeUpdate',
                            updateType: 'deactivation',
                            licenseType: 'occupational therapist',
                            dateOfUpdate: moment().subtract(7, 'months').format(serverDateFormat),
                            previous: {
                                privilegeId: 'OTA-OH-12',
                                compactTransactionId: '120059525524',
                                licenseJurisdiction: 'ca',
                                persistedStatus: 'active',
                                dateOfIssuance: '2025-03-19T21:51:26+00:00',
                                dateOfUpdate: '2022-03-19T21:51:26+00:00',
                                dateOfRenewal: '2025-03-19T21:51:26+00:00',
                                dateOfExpiration: '2026-02-12',
                                attestations: attestationResponses.map((response) => ({ ...response })),
                            },
                            updatedValues: {
                                persistedStatus: 'inactive',
                            },
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
                                privilegeId: 'OTA-OH-12',
                                compactTransactionId: '120060004895',
                                licenseJurisdiction: 'ca',
                                persistedStatus: 'active',
                                dateOfIssuance: '2022-03-19T21:51:26+00:00',
                                dateOfUpdate: '2024-03-25T19:03:56+00:00',
                                dateOfRenewal: '2024-03-01T16:19:09+00:00',
                                dateOfExpiration: '2026-02-12',
                                attestations: attestationResponses.map((response) => ({ ...response })),
                            },
                            updatedValues: {
                                privilegeId: 'OTA-OH-12',
                                compactTransactionId: '120060088903',
                                dateOfRenewal: '2025-03-26T16:19:09+00:00',
                                dateOfExpiration: '2027-02-12',
                                attestations: attestationResponses.map((response) => ({ ...response })),
                            },
                        },
                    ],
                    adverseActions: [
                        {
                            adverseActionId: '12345-DEF-JW',
                            providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                            compact: 'octp',
                            type: 'adverseAction',
                            encumbranceType: 'fine',
                            clinicalPrivilegeActionCategory: 'Non-compliance With Requirements',
                            actionAgainst: 'privilege',
                            jurisdiction: 'oh',
                            licenseTypeAbbreviation: 'ota',
                            licenseType: 'occupational therapy assistant',
                            creationDate: moment().subtract(8, 'months').format(serverDatetimeFormat),
                            effectiveStartDate: moment().subtract(7, 'months').format(serverDateFormat),
                            effectiveLiftDate: moment().subtract(5, 'months').format(serverDateFormat),
                            submittingUser: '1',
                            liftingUser: '1',
                        },
                        {
                            adverseActionId: '12345-GHI-JW',
                            providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                            compact: 'octp',
                            type: 'adverseAction',
                            encumbranceType: 'fine',
                            clinicalPrivilegeActionCategory: 'Unsafe Practice or Substandard Care',
                            actionAgainst: 'privilege',
                            jurisdiction: 'oh',
                            licenseTypeAbbreviation: 'ota',
                            licenseType: 'occupational therapy assistant',
                            creationDate: moment().subtract(1, 'week').format(serverDatetimeFormat),
                            effectiveStartDate: moment().subtract(3, 'months').format(serverDateFormat),
                            effectiveLiftDate: moment().subtract(1, 'months').format(serverDateFormat),
                            submittingUser: '1',
                            liftingUser: null,
                        },
                    ],
                },
            ],
        },
        {
            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
            givenName: 'Janet',
            middleName: '',
            familyName: 'Doe',
            compact: 'octp',
            type: 'provider',
            emailAddress: 'test@example.com',
            compactConnectRegisteredEmailAddress: 'test@example.com',
            dateOfBirth: '1990-08-29',
            birthMonthDay: '1990-08-29',
            ssnLastFour: '1111',
            homeAddressStreet1: '1640 Riverside Drive',
            homeAddressStreet2: '',
            homeAddressCity: 'Riverside',
            homeAddressState: 'co',
            homeAddressPostalCode: '',
            militaryAffiliations: [
                {
                    affiliationType: 'militaryMember',
                    compact: 'octp',
                    dateOfUpdate: '2024-08-29',
                    dateOfUpload: '2024-08-29',
                    documentKeys: 'key',
                    fileNames: ['military-document.pdf'],
                    status: 'initializing'
                }
            ],
            licenseStatus: 'active',
            licenseJurisdiction: 'co',
            currentHomeJurisdiction: 'co',
            npi: '6441445289',
            licenseNumber: 'A-944447281',
            dateOfUpdate: '2024-08-29',
            dateOfExpiration: '2024-08-29',
            licenseType: 'occupational therapy assistant',
            licenses: [
                {
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    givenName: 'Jane',
                    middleName: '',
                    familyName: 'Doe',
                    compact: 'octp',
                    dateOfBirth: '1990-08-29',
                    ssnLastFour: '1111',
                    homeAddressStreet1: '1640 Riverside Drive',
                    homeAddressStreet2: '',
                    homeAddressCity: 'Riverside',
                    homeAddressState: 'co',
                    homeAddressPostalCode: '',
                    npi: '6441445289',
                    licenseNumber: 'A-441445289',
                    type: 'license-home',
                    licenseType: 'occupational therapy assistant',
                    jurisdiction: 'co',
                    dateOfIssuance: moment().subtract(10, 'months').format(serverDateFormat),
                    dateOfUpdate: moment().subtract(10, 'months').format(serverDateFormat),
                    dateOfRenewal: '2024-08-29',
                    dateOfExpiration: moment().add(2, 'months').format(serverDateFormat),
                    licenseStatus: 'active',
                    licenseStatusName: 'Active in renewal',
                    compactEligibility: 'eligible',
                },
                {
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    givenName: 'Jane',
                    middleName: '',
                    familyName: 'Doe',
                    compact: 'octp',
                    dateOfBirth: '1990-08-29',
                    ssnLastFour: '1111',
                    homeAddressStreet1: '1640 Riverside Drive',
                    homeAddressStreet2: '',
                    homeAddressCity: 'Riverside',
                    homeAddressState: 'co',
                    homeAddressPostalCode: '',
                    npi: '6441445289',
                    licenseNumber: 'A-921445289',
                    type: 'license-home',
                    licenseType: 'occupational therapist',
                    jurisdiction: 'co',
                    dateOfIssuance: moment().subtract(1, 'years').subtract(11, 'months').format(serverDateFormat),
                    dateOfUpdate: moment().subtract(1, 'months').format(serverDateFormat),
                    dateOfExpiration: moment().add(1, 'months').format(serverDateFormat),
                    dateOfRenewal: moment().subtract(11, 'months').format(serverDateFormat),
                    licenseStatus: 'active',
                    licenseStatusName: null,
                    compactEligibility: 'eligible',
                },
                {
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    givenName: 'Jane',
                    middleName: '',
                    familyName: 'Doe',
                    compact: 'octp',
                    dateOfBirth: '1990-08-29',
                    ssnLastFour: '1111',
                    homeAddressStreet1: '1640 Riverside Drive',
                    homeAddressStreet2: '',
                    homeAddressCity: 'Riverside',
                    homeAddressState: 'co',
                    homeAddressPostalCode: '',
                    npi: '6441445289',
                    licenseNumber: 'A-944945289',
                    type: 'license-home',
                    licenseType: 'occupational therapist',
                    jurisdiction: 'ma',
                    dateOfIssuance: moment().subtract(2, 'years').subtract(7, 'days').subtract(10, 'months')
                        .format(serverDateFormat),
                    dateOfUpdate: moment().subtract(7, 'days').subtract(10, 'months').format(serverDateFormat),
                    dateOfExpiration: moment().subtract(7, 'days').add(2, 'months').format(serverDateFormat),
                    dateOfRenewal: moment().subtract(7, 'days').subtract(10, 'months').format(serverDateFormat),
                    licenseStatus: 'active',
                    licenseStatusName: 'Custom text with longer content provided by the state that may not fit completely in the default area of the UI and could overflow',
                    compactEligibility: 'ineligible',
                },
                {
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    givenName: 'Jane',
                    middleName: '',
                    familyName: 'Doe',
                    compact: 'octp',
                    dateOfBirth: '1990-08-29',
                    ssnLastFour: '1111',
                    homeAddressStreet1: '1640 Riverside Drive',
                    homeAddressStreet2: '',
                    homeAddressCity: 'Riverside',
                    homeAddressState: 'co',
                    homeAddressPostalCode: '',
                    licenseNumber: 'A-421445219',
                    npi: '6441445289',
                    type: 'license-home',
                    licenseType: 'occupational therapy assistant',
                    jurisdiction: 'ca',
                    dateOfIssuance: '2024-08-29',
                    dateOfUpdate: '2024-08-29',
                    dateOfExpiration: '2024-08-29',
                    dateOfRenewal: '2024-08-29',
                    licenseStatus: 'inactive',
                    licenseStatusName: 'Under review',
                    compactEligibility: 'ineligible',
                },
                {
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    givenName: 'Jane',
                    middleName: '',
                    familyName: 'Doe',
                    compact: 'octp',
                    dateOfBirth: '1990-08-29',
                    ssnLastFour: '1111',
                    homeAddressStreet1: '1640 Riverside Drive',
                    homeAddressStreet2: '',
                    homeAddressCity: 'Riverside',
                    homeAddressState: 'co',
                    homeAddressPostalCode: '',
                    licenseNumber: 'A-531445219',
                    npi: '6441445289',
                    type: 'license-home',
                    licenseType: 'occupational therapy assistant',
                    jurisdiction: 'nv',
                    dateOfIssuance: '2023-08-29',
                    dateOfUpdate: '2024-08-29',
                    dateOfExpiration: '2024-08-29',
                    dateOfRenewal: '2024-08-29',
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
                            encumbranceType: 'fine',
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
            privilegeJurisdictions: [
                'al',
                'ne',
                'oh',
            ],
            privileges: [
                {
                    privilegeId: 'OT-NE-8',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    compact: 'octp',
                    compactTransactionId: '120059524697',
                    type: 'privilege',
                    jurisdiction: 'ne',
                    licenseJurisdiction: 'ky',
                    licenseType: 'occupational therapist',
                    persistedStatus: 'inactive',
                    status: 'inactive',
                    dateOfIssuance: '2025-03-19T21:21:06+00:00',
                    dateOfUpdate: '2025-03-19T22:02:28+00:00',
                    dateOfRenewal: '2025-03-19T21:21:06+00:00',
                    dateOfExpiration: '2026-02-12',
                    attestations: attestationResponses.map((response) => ({ ...response })),
                    history: [
                        {
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'ne',
                            type: 'privilegeUpdate',
                            updateType: 'deactivation',
                            licenseType: 'occupational therapist',
                            dateOfUpdate: '2025-03-19T22:02:28+00:00',
                            previous: {
                                privilegeId: 'OT-NE-8',
                                compactTransactionId: '120059524697',
                                licenseJurisdiction: 'ky',
                                persistedStatus: 'active',
                                dateOfIssuance: '2025-03-19T21:21:06+00:00',
                                dateOfUpdate: '2025-03-19T21:21:06+00:00',
                                dateOfRenewal: '2025-03-19T21:21:06+00:00',
                                dateOfExpiration: '2026-02-12',
                                attestations: attestationResponses.map((response) => ({ ...response })),
                            },
                            updatedValues: {
                                persistedStatus: 'inactive',
                            },
                        },
                    ],
                },
                {
                    privilegeId: 'OTA-NE-10',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    compact: 'octp',
                    compactTransactionId: '120060088901',
                    type: 'privilege',
                    jurisdiction: 'ne',
                    licenseJurisdiction: 'ky',
                    licenseType: 'occupational therapy assistant',
                    persistedStatus: 'active',
                    status: 'active',
                    dateOfIssuance: moment().subtract(2, 'years').subtract(7, 'months').format(serverDateFormat),
                    dateOfUpdate: moment().subtract(7, 'months').format(serverDateFormat),
                    dateOfRenewal: moment().subtract(2, 'months').format(serverDateFormat),
                    dateOfExpiration: moment().add(10, 'months').format(serverDateFormat),
                    attestations: attestationResponses.map((response) => ({ ...response })),
                    history: [
                        {
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'ne',
                            type: 'privilegeUpdate',
                            updateType: 'deactivation',
                            licenseType: 'occupational therapy assistant',
                            dateOfUpdate: moment().subtract(1, 'years').subtract(7, 'months').format(serverDateFormat),
                            previous: {
                                privilegeId: 'OTA-NE-10',
                                compactTransactionId: '120059525522',
                                licenseJurisdiction: 'ky',
                                persistedStatus: 'active',
                                dateOfIssuance: '2025-03-19T21:51:26+00:00',
                                dateOfUpdate: '2022-03-19T21:51:26+00:00',
                                dateOfRenewal: '2025-03-19T21:51:26+00:00',
                                dateOfExpiration: '2026-02-12',
                                attestations: attestationResponses.map((response) => ({ ...response })),
                            },
                            updatedValues: {
                                persistedStatus: 'inactive',
                            },
                        },
                        {
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'ne',
                            type: 'privilegeUpdate',
                            updateType: 'renewal',
                            licenseType: 'occupational therapy assistant',
                            dateOfUpdate: moment().subtract(1, 'years').subtract(2, 'months').format(serverDateFormat),
                            previous: {
                                privilegeId: 'OTA-NE-10',
                                compactTransactionId: '120059525522',
                                licenseJurisdiction: 'ky',
                                persistedStatus: 'inactive',
                                dateOfIssuance: '2025-03-19T21:51:26+00:00',
                                dateOfUpdate: '2022-03-19T22:02:17+00:00',
                                dateOfRenewal: '2022-08-19T19:03:56+00:00',
                                dateOfExpiration: '2026-02-12',
                                attestations: attestationResponses.map((response) => ({ ...response })),
                            },
                            updatedValues: {
                                privilegeId: 'OTA-NE-10',
                                compactTransactionId: '120060004893',
                                persistedStatus: 'active',
                                dateOfRenewal: '2025-03-25T19:03:56+00:00',
                                dateOfExpiration: '2026-02-12',
                                attestations: attestationResponses.map((response) => ({ ...response })),
                            },
                        },
                        {
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'ne',
                            type: 'privilegeUpdate',
                            updateType: 'renewal',
                            licenseType: 'occupational therapy assistant',
                            dateOfUpdate: moment().subtract(2, 'months').format(serverDateFormat),
                            previous: {
                                privilegeId: 'OTA-NE-10',
                                compactTransactionId: '120060004893',
                                licenseJurisdiction: 'ky',
                                persistedStatus: 'active',
                                dateOfIssuance: '2022-03-19T21:51:26+00:00',
                                dateOfUpdate: '2024-03-25T19:03:56+00:00',
                                dateOfRenewal: '2024-03-01T16:19:09+00:00',
                                dateOfExpiration: '2026-02-12',
                                attestations: attestationResponses.map((response) => ({ ...response })),
                            },
                            updatedValues: {
                                privilegeId: 'OTA-NE-10',
                                compactTransactionId: '120060088901',
                                dateOfRenewal: '2025-03-26T16:19:09+00:00',
                                dateOfExpiration: '2027-02-12',
                                attestations: attestationResponses.map((response) => ({ ...response })),
                            },
                        },
                    ],
                },
                {
                    privilegeId: 'OT-OH-11',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    compact: 'octp',
                    compactTransactionId: '120060232791',
                    type: 'privilege',
                    jurisdiction: 'oh',
                    licenseJurisdiction: 'ky',
                    licenseType: 'occupational therapist',
                    persistedStatus: 'active',
                    status: 'inactive',
                    dateOfIssuance: '2024-03-28T18:07:08+00:00',
                    dateOfUpdate: '2025-03-28T18:07:08+00:00',
                    dateOfRenewal: '2025-03-28T18:07:08+00:00',
                    dateOfExpiration: '2025-03-28',
                    attestations: attestationResponses.map((response) => ({ ...response })),
                    history: []
                },
                {
                    privilegeId: 'OTA-OH-9',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    compact: 'octp',
                    compactTransactionId: '120060086502',
                    type: 'privilege',
                    jurisdiction: 'oh',
                    licenseJurisdiction: 'ky',
                    licenseType: 'occupational therapy assistant',
                    persistedStatus: 'active',
                    status: 'inactive',
                    dateOfIssuance: '2024-03-19T21:30:27+00:00',
                    dateOfUpdate: '2025-03-26T15:56:58+00:00',
                    dateOfRenewal: '2025-03-26T15:56:58+00:00',
                    dateOfExpiration: moment().format(serverDateFormat),
                    attestations: attestationResponses.map((response) => ({ ...response })),
                    history: [
                        {
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'oh',
                            type: 'privilegeUpdate',
                            updateType: 'renewal',
                            licenseType: 'occupational therapy assistant',
                            dateOfUpdate: '2025-03-26T15:56:58+00:00',
                            previous: {
                                privilegeId: 'OTA-OH-9',
                                compactTransactionId: '120059524934',
                                licenseJurisdiction: 'ky',
                                persistedStatus: 'active',
                                dateOfIssuance: '2024-03-19T21:30:27+00:00',
                                dateOfUpdate: '2024-03-19T21:30:27+00:00',
                                dateOfRenewal: '2024-03-19T21:30:27+00:00',
                                dateOfExpiration: '2025-02-12',
                                attestations: attestationResponses.map((response) => ({ ...response })),
                            },
                            updatedValues: {
                                privilegeId: 'OTA-OH-9',
                                compactTransactionId: '120060086502',
                                dateOfRenewal: '2025-03-26T15:56:58+00:00',
                                dateOfExpiration: '2026-02-12',
                                attestations: attestationResponses.map((response) => ({ ...response })),
                            },
                        },
                    ],
                    adverseActions: [
                        {
                            adverseActionId: '12345-ABC',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            type: 'adverseAction',
                            encumbranceType: 'fine',
                            clinicalPrivilegeActionCategory: 'Non-compliance With Requirements',
                            actionAgainst: 'privilege',
                            jurisdiction: 'oh',
                            licenseTypeAbbreviation: 'ota',
                            licenseType: 'occupational therapy assistant',
                            creationDate: moment().subtract(1, 'week').format(serverDatetimeFormat),
                            effectiveStartDate: moment().subtract(1, 'month').format(serverDateFormat),
                            effectiveLiftDate: moment().add(11, 'months').format(serverDateFormat),
                            submittingUser: '1',
                            liftingUser: '1',
                        },
                    ],
                },
                {
                    privilegeId: 'OTA-AL-10',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    compact: 'octp',
                    compactTransactionId: '120060088901',
                    type: 'privilege',
                    jurisdiction: 'al',
                    licenseJurisdiction: 'ky',
                    licenseType: 'occupational therapy assistant',
                    persistedStatus: 'active',
                    status: 'active',
                    dateOfIssuance: moment().subtract(9, 'months').format(serverDateFormat),
                    dateOfUpdate: moment().subtract(9, 'months').format(serverDateFormat),
                    dateOfRenewal: moment().subtract(9, 'months').format(serverDateFormat),
                    dateOfExpiration: moment().add(1, 'month').format(serverDateFormat),
                    attestations: attestationResponses.map((response) => ({ ...response })),
                    history: [
                        {
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'al',
                            type: 'privilegeUpdate',
                            updateType: 'deactivation',
                            licenseType: 'occupational therapy assistant',
                            dateOfUpdate: moment().subtract(7, 'months').format(serverDateFormat),
                            previous: {
                                privilegeId: 'OTA-AL-10',
                                compactTransactionId: '120059525522',
                                licenseJurisdiction: 'ky',
                                persistedStatus: 'active',
                                dateOfIssuance: '2025-03-19T21:51:26+00:00',
                                dateOfUpdate: '2022-03-19T21:51:26+00:00',
                                dateOfRenewal: '2025-03-19T21:51:26+00:00',
                                dateOfExpiration: '2026-02-12',
                                attestations: attestationResponses.map((response) => ({ ...response })),
                            },
                            updatedValues: {
                                persistedStatus: 'inactive',
                            },
                        },
                        {
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'al',
                            type: 'privilegeUpdate',
                            updateType: 'renewal',
                            licenseType: 'occupational therapy assistant',
                            dateOfUpdate: moment().subtract(6, 'months').format(serverDateFormat),
                            previous: {
                                privilegeId: 'OTA-AL-10',
                                compactTransactionId: '120060004893',
                                licenseJurisdiction: 'ky',
                                persistedStatus: 'active',
                                dateOfIssuance: '2022-03-19T21:51:26+00:00',
                                dateOfUpdate: '2024-03-25T19:03:56+00:00',
                                dateOfRenewal: '2024-03-01T16:19:09+00:00',
                                dateOfExpiration: '2026-02-12',
                                attestations: attestationResponses.map((response) => ({ ...response })),
                            },
                            updatedValues: {
                                privilegeId: 'OTA-AL-10',
                                compactTransactionId: '120060088901',
                                dateOfRenewal: '2025-03-26T16:19:09+00:00',
                                dateOfExpiration: '2027-02-12',
                                attestations: attestationResponses.map((response) => ({ ...response })),
                            },
                        },
                    ],
                    adverseActions: [
                        {
                            adverseActionId: '12345-DEF',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            type: 'adverseAction',
                            encumbranceType: 'fine',
                            clinicalPrivilegeActionCategory: 'Non-compliance With Requirements',
                            actionAgainst: 'privilege',
                            jurisdiction: 'al',
                            licenseTypeAbbreviation: 'ota',
                            licenseType: 'occupational therapy assistant',
                            creationDate: moment().subtract(8, 'months').format(serverDatetimeFormat),
                            effectiveStartDate: moment().subtract(7, 'months').format(serverDateFormat),
                            effectiveLiftDate: moment().subtract(5, 'months').format(serverDateFormat),
                            submittingUser: '1',
                            liftingUser: '1',
                        },
                        {
                            adverseActionId: '12345-GHI',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            type: 'adverseAction',
                            encumbranceType: 'fine',
                            clinicalPrivilegeActionCategory: 'Unsafe Practice or Substandard Care',
                            actionAgainst: 'privilege',
                            jurisdiction: 'al',
                            licenseTypeAbbreviation: 'ota',
                            licenseType: 'occupational therapy assistant',
                            creationDate: moment().subtract(1, 'week').format(serverDatetimeFormat),
                            effectiveStartDate: moment().subtract(3, 'months').format(serverDateFormat),
                            effectiveLiftDate: moment().subtract(1, 'months').format(serverDateFormat),
                            submittingUser: '1',
                            liftingUser: null,
                        },
                    ],
                },
            ],
        },
        {
            providerId: '2',
            givenName: 'Tyler',
            middleName: '',
            familyName: 'Durden',
            compact: 'octp',
            type: 'provider',
            emailAddress: 'test@example.com',
            compactConnectRegisteredEmailAddress: 'test@example.com',
            dateOfBirth: '1975-01-01',
            birthMonthDay: '1975-01-01',
            ssnLastFour: '2222',
            homeAddressStreet1: '1045 Pearl St',
            homeAddressStreet2: '',
            homeAddressCity: 'Boulder',
            homeAddressState: 'co',
            homeAddressPostalCode: '80302',
            militaryAffiliations: [],
            licenseStatus: 'inactive',
            licenseJurisdiction: 'co',
            currentHomeJurisdiction: 'co',
            npi: '2522457223',
            dateOfUpdate: '2024-08-29',
            dateOfExpiration: '2024-08-29',
            licenseType: 'occupational therapy assistant',
            licenses: [
                {
                    providerId: '2',
                    givenName: 'Tyler',
                    middleName: '',
                    familyName: 'Durden',
                    compact: 'octp',
                    dateOfBirth: '1975-01-01',
                    ssnLastFour: '2222',
                    homeAddressStreet1: '1045 Pearl St',
                    homeAddressStreet2: '',
                    homeAddressCity: 'Boulder',
                    homeAddressState: 'co',
                    homeAddressPostalCode: '80302',
                    npi: '2522457223',
                    licenseNumber: 'A-312445289',
                    type: 'license-home',
                    licenseType: 'occupational therapy assistant',
                    jurisdiction: 'co',
                    dateOfIssuance: '2023-08-29',
                    dateOfUpdate: '2023-08-29',
                    dateOfExpiration: '2024-08-29',
                    dateOfRenewal: '2023-08-29',
                    licenseStatus: 'inactive',
                    licenseStatusName: 'Custom text with longer content provided by the state that may not fit completely in the default area of the UI and could overflow',
                    compactEligibility: 'ineligible',
                }
            ],
            privilegeJurisdictions: [
                'al'
            ],
            privileges: [
                {
                    privilegeId: 'OCTP-AL-19',
                    providerId: '2',
                    compact: 'octp',
                    compactTransactionId: null,
                    type: 'privilege',
                    jurisdiction: 'al',
                    licenseJurisdiction: 'co',
                    persistedStatus: 'inactive',
                    status: 'inactive',
                    dateOfIssuance: '2023-08-29',
                    dateOfUpdate: '2024-08-29',
                    dateOfRenewal: '2024-08-29',
                    dateOfExpiration: '2024-08-29',
                    attestations: [],
                },
            ],
        },
        {
            providerId: '3',
            givenName: 'Marla',
            middleName: '',
            familyName: 'Singer',
            compact: 'octp',
            type: 'provider',
            emailAddress: 'test@example.com',
            compactConnectRegisteredEmailAddress: 'test@example.com',
            dateOfBirth: '1965-01-01',
            birthMonthDay: '1965-01-01',
            ssnLastFour: '3333',
            homeAddressStreet1: '1495 Canyon Blvd',
            homeAddressStreet2: '',
            homeAddressCity: 'Boulder',
            homeAddressState: 'co',
            homeAddressPostalCode: '80301',
            militaryAffiliations: [],
            licenseStatus: 'active',
            licenseJurisdiction: 'co',
            currentHomeJurisdiction: 'co',
            npi: '6944447283',
            dateOfUpdate: '2024-08-29',
            dateOfExpiration: '2024-08-29',
            licenseType: 'occupational therapy assistant',
            licenses: [
                {
                    providerId: '3',
                    givenName: 'Marla',
                    middleName: '',
                    familyName: 'Singer',
                    compact: 'octp',
                    dateOfBirth: '1965-01-01',
                    ssnLastFour: '3333',
                    homeAddressStreet1: '1495 Canyon Blvd',
                    homeAddressStreet2: '',
                    homeAddressCity: 'Boulder',
                    homeAddressState: 'co',
                    homeAddressPostalCode: '80301',
                    npi: '6944447283',
                    licenseNumber: 'A-1234567890',
                    type: 'license-home',
                    licenseType: 'occupational therapy assistant',
                    jurisdiction: 'co',
                    dateOfIssuance: moment().add(1, 'day').subtract(11, 'months').subtract(2, 'years')
                        .format(serverDateFormat),
                    dateOfUpdate: moment().add(1, 'day').subtract(1, 'year').format(serverDateFormat),
                    dateOfExpiration: moment().add(1, 'day').add(1, 'month').format(serverDateFormat),
                    dateOfRenewal: moment().add(1, 'day').subtract(1, 'year').format(serverDateFormat),
                    licenseStatus: 'active',
                    licenseStatusName: 'text from state',
                    compactEligibility: 'eligible',
                },
            ],
            privilegeJurisdictions: [
                'al',
            ],
            privileges: [
                {
                    privilegeId: 'OCTP-AL-22',
                    providerId: '3',
                    compact: 'octp',
                    compactTransactionId: null,
                    type: 'privilege',
                    jurisdiction: 'al',
                    licenseJurisdiction: 'co',
                    persistedStatus: 'active',
                    status: 'active',
                    dateOfIssuance: moment().subtract(10, 'months').subtract(1, 'year').format(serverDateFormat),
                    dateOfUpdate: moment().subtract(10, 'months').subtract(1, 'year').format(serverDateFormat),
                    dateOfRenewal: null,
                    dateOfExpiration: moment().add(2, 'months').format(serverDateFormat),
                    attestations: [],
                }
            ],
        },
        {
            providerId: '4',
            givenName: 'Jane',
            middleName: '',
            familyName: 'Doe',
            compact: 'octp',
            type: 'provider',
            emailAddress: 'test@example.com',
            compactConnectRegisteredEmailAddress: 'test@example.com',
            dateOfBirth: '1990-08-29',
            birthMonthDay: '1990-08-29',
            ssnLastFour: '4444',
            homeAddressStreet1: '1640 Riverside Drive',
            homeAddressStreet2: '',
            homeAddressCity: 'Riverside',
            homeAddressState: 'co',
            homeAddressPostalCode: '',
            militaryAffiliations: [],
            npi: '6441445289',
            licenseStatus: 'active',
            licenseJurisdiction: 'co',
            currentHomeJurisdiction: 'co    ',
            dateOfUpdate: '2024-08-29',
            dateOfExpiration: '2024-08-29',
            licenseType: 'occupational therapy assistant',
            licenses: [
                {
                    providerId: '4',
                    givenName: 'Jane',
                    middleName: '',
                    familyName: 'Doe',
                    compact: 'octp',
                    dateOfBirth: '1990-08-29',
                    ssnLastFour: '4444',
                    homeAddressStreet1: '1640 Riverside Drive',
                    homeAddressStreet2: '',
                    homeAddressCity: 'Riverside',
                    homeAddressState: 'co',
                    homeAddressPostalCode: '',
                    npi: '6441445289',
                    licenseNumber: null,
                    type: 'license-home',
                    licenseType: 'occupational therapy assistant',
                    jurisdiction: 'co',
                    dateOfIssuance: '2024-08-29',
                    dateOfUpdate: '2024-08-29',
                    dateOfExpiration: '2024-08-29',
                    dateOfRenewal: '2024-08-29',
                    licenseStatus: 'active',
                    licenseStatusName: '',
                    compactEligibility: 'ineligible',
                }
            ],
            privilegeJurisdictions: [
                'al',
                'ak',
                'ar',
            ],
            privileges: [
                {
                    privilegeId: null,
                    providerId: '4',
                    compact: 'octp',
                    compactTransactionId: null,
                    type: 'privilege',
                    jurisdiction: 'al',
                    licenseJurisdiction: 'co',
                    dateOfIssuance: '2023-08-29',
                    dateOfUpdate: '2024-08-29',
                    dateOfRenewal: null,
                    dateOfExpiration: '2024-08-29',
                    persistedStatus: 'active',
                    status: 'active',
                    attestations: [],
                },
                {
                    providerId: '4',
                    compact: 'octp',
                    compactTransactionId: null,
                    type: 'privilege',
                    jurisdiction: 'ak',
                    licenseJurisdiction: 'co',
                    dateOfIssuance: '2023-08-29',
                    dateOfUpdate: '2024-08-29',
                    dateOfRenewal: null,
                    dateOfExpiration: '2024-08-29',
                    persistedStatus: 'active',
                    status: 'active',
                    attestations: [],
                },
                {
                    providerId: '4',
                    compact: 'octp',
                    compactTransactionId: null,
                    type: 'privilege',
                    jurisdiction: 'ar',
                    licenseJurisdiction: 'co',
                    dateOfIssuance: '2023-08-29',
                    dateOfUpdate: '2024-08-29',
                    dateOfRenewal: null,
                    dateOfExpiration: '2023-08-29',
                    persistedStatus: 'active',
                    status: 'active',
                    attestations: [],
                }
            ],
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
