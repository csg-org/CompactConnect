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
                wy: {
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
                amount: 200,
                militaryRate: (config?.hasMilitaryDiscount) ? 90 : undefined,
            },
            {
                licenseTypeAbbreviation: 'ota',
                amount: 100,
                militaryRate: (config?.hasMilitaryDiscount) ? 50 : undefined,
            }
        ],
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
            // ================================================================
            //                         LAYNE CORNELL
            // ================================================================
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
                    activeSince: moment().subtract(2, 'months').format(serverDateFormat),
                    attestations: attestationResponses.map((response) => ({ ...response })),
                },
                {
                    privilegeId: 'OTA-OH-12',
                    providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                    compact: 'octp',
                    compactTransactionId: '120060088903',
                    type: 'privilege',
                    jurisdiction: 'oh',
                    licenseJurisdiction: 'ca',
                    licenseType: 'occupational therapy assistant',
                    persistedStatus: 'active',
                    status: 'active',
                    dateOfIssuance: moment().subtract(9, 'months').format(serverDateFormat),
                    dateOfUpdate: moment().subtract(9, 'months').format(serverDateFormat),
                    dateOfRenewal: moment().subtract(9, 'months').format(serverDateFormat),
                    dateOfExpiration: moment().add(3, 'months').format(serverDateFormat),
                    activeSince: moment().subtract(9, 'months').format(serverDateFormat),
                    attestations: attestationResponses.map((response) => ({ ...response })),
                    adverseActions: [],
                },
            ],
        },
        {
            // ================================================================
            //                         JANET DOE
            // ================================================================
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
                    homeAddressStreet1: '79 N Washington Street',
                    homeAddressStreet2: '',
                    homeAddressCity: 'Denver',
                    homeAddressState: 'co',
                    homeAddressPostalCode: '80203',
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
                            adverseActionId: '12345-MNO',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            type: 'adverseAction',
                            encumbranceType: 'fine',
                            clinicalPrivilegeActionCategory: 'Non-compliance With Requirements',
                            actionAgainst: 'privilege',
                            jurisdiction: 'nv',
                            licenseTypeAbbreviation: 'ota',
                            licenseType: 'occupational therapy assistant',
                            creationDate: moment().subtract(1, 'year').format(serverDatetimeFormat),
                            effectiveStartDate: moment().subtract(1, 'year').format(serverDateFormat),
                            effectiveLiftDate: moment().subtract(1, 'month').format(serverDateFormat),
                            submittingUser: '1',
                            liftingUser: '1',
                        },
                        {
                            adverseActionId: '12345-JKL',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            type: 'adverseAction',
                            encumbranceType: 'fine',
                            clinicalPrivilegeActionCategory: 'Non-compliance With Requirements',
                            actionAgainst: 'privilege',
                            jurisdiction: 'nv',
                            licenseTypeAbbreviation: 'ota',
                            licenseType: 'occupational therapy assistant',
                            creationDate: moment().subtract(1, 'week').format(serverDatetimeFormat),
                            effectiveStartDate: moment().subtract(1, 'month').format(serverDateFormat),
                            effectiveLiftDate: null,
                            submittingUser: '1',
                            liftingUser: null,
                        },
                    ],
                    investigations: [
                        {
                            investigationId: '12345-ABC',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'wy',
                            licenseType: 'occupational therapy assistant',
                            type: 'investigation',
                            creationDate: moment().subtract(1, 'week').format(serverDatetimeFormat),
                            dateOfUpdate: moment().subtract(1, 'week').format(serverDatetimeFormat),
                            endDate: null,
                        },
                        {
                            investigationId: '12345-DEF',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'wy',
                            licenseType: 'occupational therapy assistant',
                            type: 'investigation',
                            creationDate: moment().subtract(1, 'month').format(serverDatetimeFormat),
                            dateOfUpdate: moment().subtract(1, 'month').format(serverDatetimeFormat),
                            endDate: moment().subtract(2, 'weeks').format(serverDatetimeFormat),
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
                    activeSince: moment().subtract(1, 'years').subtract(2, 'months').format(serverDateFormat),
                    attestations: attestationResponses.map((response) => ({ ...response })),
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
                    dateOfIssuance: moment().subtract(1, 'year').subtract(9, 'months').format(serverDateFormat),
                    dateOfUpdate: moment().subtract(2, 'months').format(serverDateFormat),
                    dateOfRenewal: moment().subtract(5, 'months').format(serverDateFormat),
                    dateOfExpiration: moment().add(3, 'month').format(serverDateFormat),
                    activeSince: moment().subtract(5, 'months').format(serverDateFormat),
                    attestations: attestationResponses.map((response) => ({ ...response })),
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
                {
                    privilegeId: 'OTA-WY-1',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    compact: 'octp',
                    compactTransactionId: '120060086502',
                    type: 'privilege',
                    jurisdiction: 'wy',
                    licenseJurisdiction: 'co',
                    licenseType: 'occupational therapy assistant',
                    persistedStatus: 'active',
                    status: 'active',
                    dateOfIssuance: '2024-03-19T21:30:27+00:00',
                    dateOfUpdate: '2025-03-26T15:56:58+00:00',
                    dateOfRenewal: moment().subtract(11, 'months').format(serverDateFormat),
                    dateOfExpiration: moment().add(1, 'month').format(serverDateFormat),
                    attestations: attestationResponses.map((response) => ({ ...response })),
                    investigations: [
                        {
                            investigationId: '12345-ABC',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'wy',
                            licenseType: 'occupational therapy assistant',
                            type: 'investigation',
                            creationDate: moment().subtract(1, 'week').format(serverDatetimeFormat),
                            dateOfUpdate: null,
                            endDate: null,
                        },
                        {
                            investigationId: '12345-DEF',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'wy',
                            licenseType: 'occupational therapy assistant',
                            type: 'investigation',
                            creationDate: moment().subtract(1, 'month').format(serverDatetimeFormat),
                            dateOfUpdate: moment().subtract(1, 'month').format(serverDatetimeFormat),
                            endDate: moment().subtract(3, 'weeks').format(serverDatetimeFormat),
                        },
                        {
                            investigationId: '12345-GHI',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            jurisdiction: 'wy',
                            licenseType: 'occupational therapy assistant',
                            type: 'investigation',
                            creationDate: moment().subtract(1, 'year').format(serverDatetimeFormat),
                            dateOfUpdate: null,
                            endDate: null,
                        },
                    ],
                },
            ],
        },
        {
            // ================================================================
            //                         TYLER DURDEN
            // ================================================================
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
                    licenseType: 'occupational therapy assistant',
                    persistedStatus: 'inactive',
                    status: 'inactive',
                    dateOfIssuance: moment().subtract(10, 'months').subtract(1, 'year').format(serverDateFormat),
                    dateOfUpdate: moment().subtract(10, 'months').subtract(1, 'year').format(serverDateFormat),
                    dateOfRenewal: '2024-08-29',
                    dateOfExpiration: moment().add(2, 'months').format(serverDateFormat),
                    activeSince: moment().subtract(10, 'months').subtract(1, 'year').format(serverDateFormat),
                    attestations: [],
                },
            ],
        },
        {
            // ================================================================
            //                         MARLA SINGER
            // ================================================================
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
                    licenseType: 'occupational therapy assistant',
                    persistedStatus: 'active',
                    status: 'active',
                    dateOfIssuance: moment().subtract(10, 'months').subtract(1, 'year').format(serverDateFormat),
                    dateOfUpdate: moment().subtract(10, 'months').format(serverDateFormat),
                    dateOfRenewal: moment().subtract(10, 'months').format(serverDateFormat),
                    dateOfExpiration: moment().add(2, 'months').format(serverDateFormat),
                    attestations: [],
                }
            ],
        },
        {
            // ================================================================
            //                         JANE DOE
            // ================================================================
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
            militaryAffiliations: [],
            npi: '6441445289',
            licenseStatus: 'active',
            licenseJurisdiction: 'ny',
            currentHomeJurisdiction: 'unknown',
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
                    privilegeId: 'OTA-AL-11',
                    providerId: '4',
                    compact: 'octp',
                    compactTransactionId: null,
                    type: 'privilege',
                    jurisdiction: 'al',
                    licenseJurisdiction: 'co',
                    licenseType: 'occupational therapy assistant',
                    persistedStatus: 'active',
                    status: 'active',
                    dateOfIssuance: '2023-08-29',
                    dateOfUpdate: '2024-08-29',
                    dateOfRenewal: null,
                    dateOfExpiration: '2024-08-29',
                    attestations: [],
                },
                {
                    privilegeId: 'OTA-AK-12',
                    providerId: '4',
                    compact: 'octp',
                    compactTransactionId: null,
                    type: 'privilege',
                    jurisdiction: 'ak',
                    licenseJurisdiction: 'co',
                    licenseType: 'occupational therapy assistant',
                    persistedStatus: 'active',
                    status: 'active',
                    dateOfIssuance: '2023-08-29',
                    dateOfUpdate: '2024-08-29',
                    dateOfRenewal: null,
                    dateOfExpiration: '2024-08-29',
                    attestations: [],
                },
                {
                    privilegeId: 'OTA-AR-13',
                    providerId: '4',
                    compact: 'octp',
                    compactTransactionId: null,
                    type: 'privilege',
                    jurisdiction: 'ar',
                    licenseJurisdiction: 'co',
                    licenseType: 'occupational therapy assistant',
                    persistedStatus: 'active',
                    status: 'active',
                    dateOfIssuance: '2023-08-29',
                    dateOfUpdate: '2024-08-29',
                    dateOfRenewal: null,
                    dateOfExpiration: '2023-08-29',
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
    case 'military-personal-information-state-license-attestation':
        attestationObj.text = `As active duty military or the spouse of such, I hereby attest and affirm that this is my personal and licensure information and I hold an eligible license in the state listed on this page.*`;
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

export const compactStatesForRegistration = {
    aslp: [ 'al', 'co', 'fl', 'ga', 'il', 'ia', 'ky', 'ne' ],
    coun: [ 'al', 'ak', 'co', 'il', 'ia', 'ky', 'ne', 'nm' ],
    octp: [ 'al', 'ar', 'co', 'ct', 'il', 'ky' ],
};

export const compactConfig = {
    compactAbbr: 'octp',
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
    compact: 'octp',
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

export const mockPrivilegeHistoryResponses = [
    {
        // ================================================================
        //                         LAYNE CORNELL (NE OTA)
        // ================================================================
        providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
        compact: 'octp',
        jurisdiction: 'ne',
        licenseType: 'occupational therapy assistant',
        privilegeId: 'OTA-NE-11',
        events: [
            {
                type: 'privilegeUpdate',
                updateType: 'issuance',
                dateOfUpdate: moment().subtract(2, 'years').subtract(7, 'months').format(serverDateFormat),
                effectiveDate: moment().subtract(2, 'years').subtract(7, 'months').format(serverDateFormat),
                createDate: moment().subtract(2, 'years').subtract(7, 'months').format(serverDateFormat)
            },
            {
                type: 'privilegeUpdate',
                updateType: 'renewal',
                dateOfUpdate: moment().subtract(1, 'years').subtract(7, 'months').format(serverDateFormat),
                effectiveDate: moment().subtract(1, 'years').subtract(7, 'months').format(serverDateFormat),
                createDate: moment().subtract(1, 'years').subtract(7, 'months').format(serverDateFormat)
            },
            {
                type: 'privilegeUpdate',
                updateType: 'renewal',
                dateOfUpdate: moment().subtract(2, 'months').format(serverDateFormat),
                effectiveDate: moment().subtract(2, 'months').format(serverDateFormat),
                createDate: moment().subtract(2, 'months').format(serverDateFormat)
            },
        ]
    },
    {
        // ================================================================
        //                         LAYNE CORNELL (OH OTA)
        // ================================================================
        providerId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
        compact: 'octp',
        jurisdiction: 'oh',
        licenseType: 'occupational therapy assistant',
        privilegeId: 'OTA-OH-12',
        events: [
            {
                type: 'privilegeUpdate',
                updateType: 'issuance',
                dateOfUpdate: moment().subtract(9, 'months').format(serverDateFormat),
                effectiveDate: moment().subtract(9, 'months').format(serverDateFormat),
                createDate: moment().subtract(9, 'months').format(serverDateFormat)
            }
        ]
    },
    {
        // ================================================================
        //                         JANET DOE (NE OTA)
        // ================================================================
        providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
        compact: 'octp',
        jurisdiction: 'ne',
        licenseType: 'occupational therapy assistant',
        privilegeId: 'OTA-NE-10',
        events: [
            {
                type: 'privilegeUpdate',
                updateType: 'issuance',
                dateOfUpdate: moment().subtract(2, 'years').subtract(7, 'months').format(serverDateFormat),
                effectiveDate: moment().subtract(2, 'years').subtract(7, 'months').format(serverDateFormat),
                createDate: moment().subtract(2, 'years').subtract(7, 'months').format(serverDateFormat)
            },
            {
                type: 'privilegeUpdate',
                updateType: 'renewal',
                dateOfUpdate: moment().subtract(1, 'years').subtract(2, 'months').format(serverDateFormat),
                effectiveDate: moment().subtract(1, 'years').subtract(2, 'months').format(serverDateFormat),
                createDate: moment().subtract(1, 'years').subtract(2, 'months').format(serverDateFormat)
            },
            {
                type: 'privilegeUpdate',
                updateType: 'renewal',
                dateOfUpdate: moment().subtract(2, 'months').format(serverDateFormat),
                effectiveDate: moment().subtract(2, 'months').format(serverDateFormat),
                createDate: moment().subtract(2, 'months').format(serverDateFormat)
            },
        ]
    },
    {
        // ================================================================
        //                         JANET DOE (NE OTA)
        // ================================================================
        providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
        compact: 'octp',
        jurisdiction: 'ne',
        licenseType: 'occupational therapy assistant',
        privilegeId: 'OT-NE-26',
        events: [
            {
                type: 'privilegeUpdate',
                updateType: 'issuance',
                dateOfUpdate: '2024-06-23T07:46:19+00:00',
                effectiveDate: '2024-06-23T17:04:38+00:00',
                createDate: '2024-06-23T07:46:19+00:00'
            },
            {
                type: 'privilegeUpdate',
                updateType: 'encumbrance',
                dateOfUpdate: '2025-07-17T17:04:38+00:00',
                effectiveDate: '2025-07-01T17:04:38+00:00',
                createDate: '2025-07-17T17:04:38+00:00',
                note: 'Misconduct or Abuse'
            },
            {
                type: 'privilegeUpdate',
                updateType: 'lifting_encumbrance',
                dateOfUpdate: '2025-07-29T23:10:15+00:00',
                effectiveDate: '2025-07-18T17:04:38+00:00',
                createDate: '2025-07-29T23:10:15+00:00'
            },
            {
                type: 'privilegeUpdate',
                updateType: 'deactivation',
                dateOfUpdate: '2025-07-29T23:10:15+00:00',
                effectiveDate: '2025-07-29T17:04:38+00:00',
                createDate: '2025-07-29T23:10:15+00:00',
                note: 'Bought wrong state'
            },
            {
                type: 'privilegeUpdate',
                updateType: 'renewal',
                dateOfUpdate: '2025-08-04T22:28:59+00:00',
                effectiveDate: '2025-08-04T17:04:38+00:00',
                createDate: '2025-08-04T22:28:59+00:00'
            },
            {
                type: 'privilegeUpdate',
                updateType: 'expiration',
                dateOfUpdate: '2025-08-05T22:28:59+00:00',
                effectiveDate: '2025-08-05T17:04:38+00:00',
                createDate: '2025-08-05T22:28:59+00:00'
            },
            {
                type: 'privilegeUpdate',
                updateType: 'renewal',
                dateOfUpdate: '2025-08-06T22:28:59+00:00',
                effectiveDate: '2025-08-06T17:04:38+00:00',
                createDate: '2025-08-06T22:28:59+00:00'
            },
            {
                type: 'privilegeUpdate',
                updateType: 'homeJurisdictionChange',
                dateOfUpdate: '2025-08-07T20:36:31+00:00',
                effectiveDate: '2025-08-07T17:04:38+00:00',
                createDate: '2025-08-07T20:36:31+00:00'
            },
            {
                type: 'privilegeUpdate',
                updateType: 'renewal',
                dateOfUpdate: '2025-08-08T20:42:14+00:00',
                effectiveDate: '2025-08-08T17:04:38+00:00',
                createDate: '2025-08-08T20:42:14+00:00'
            },
            {
                type: 'privilegeUpdate',
                updateType: 'licenseDeactivation',
                dateOfUpdate: '2025-08-09T21:56:37+00:00',
                effectiveDate: '2025-08-09T17:04:38+00:00',
                createDate: '2025-08-09T21:56:37+00:00'
            },
            {
                type: 'privilegeUpdate',
                updateType: 'renewal',
                dateOfUpdate: '2025-08-10T22:28:59+00:00',
                effectiveDate: '2025-08-10',
                createDate: '2025-08-10T22:28:59+00:00'
            },
        ]
    },
    {
        // ================================================================
        //                         JANET DOE (AL OTA)
        // ================================================================
        providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
        compact: 'octp',
        jurisdiction: 'al',
        licenseType: 'occupational therapy assistant',
        privilegeId: 'OTA-AL-10',
        events: [
            {
                type: 'privilegeUpdate',
                updateType: 'issuance',
                dateOfUpdate: moment().subtract(1, 'year').subtract(9, 'months').format(serverDateFormat),
                effectiveDate: moment().subtract(1, 'year').subtract(9, 'months').format(serverDateFormat),
                createDate: moment().subtract(1, 'year').subtract(9, 'months').format(serverDateFormat)
            },
            {
                type: 'privilegeUpdate',
                updateType: 'expiration',
                dateOfUpdate: moment().subtract(9, 'months').format(serverDateFormat),
                effectiveDate: moment().subtract(9, 'months').format(serverDateFormat),
                createDate: moment().subtract(9, 'months').format(serverDateFormat)
            },
            {
                type: 'privilegeUpdate',
                updateType: 'renewal',
                dateOfUpdate: moment().subtract(5, 'months').format(serverDateFormat),
                effectiveDate: moment().subtract(5, 'months').format(serverDateFormat),
                createDate: moment().subtract(5, 'months').format(serverDateFormat)
            },
            {
                type: 'privilegeUpdate',
                updateType: 'encumbrance',
                dateOfUpdate: moment().subtract(4, 'months').format(serverDateFormat),
                effectiveDate: moment().subtract(4, 'months').format(serverDateFormat),
                createDate: moment().subtract(4, 'months').format(serverDateFormat),
                note: 'Misconduct or Abuse'
            },
            {
                type: 'privilegeUpdate',
                updateType: 'lifting_encumbrance',
                dateOfUpdate: moment().subtract(2, 'months').format(serverDateFormat),
                effectiveDate: moment().subtract(2, 'months').format(serverDateFormat),
                createDate: moment().subtract(2, 'months').format(serverDateFormat)
            },
        ]
    },
    {
        // ================================================================
        //                         JANET DOE (NE OT)
        // ================================================================
        providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
        compact: 'octp',
        jurisdiction: 'ne',
        licenseType: 'occupational therapist',
        privilegeId: 'OT-NE-8',
        events: [
            {
                type: 'privilegeUpdate',
                updateType: 'issuance',
                dateOfUpdate: '2025-03-19T21:21:06+00:00',
                effectiveDate: '2025-03-19T21:21:06+00:00',
                createDate: '2025-03-19T21:21:06+00:00'
            },
            {
                type: 'privilegeUpdate',
                updateType: 'deactivation',
                dateOfUpdate: '2025-04-19T22:02:28+00:00',
                effectiveDate: '2025-04-19T22:02:28+00:00',
                createDate: '2025-04-19T22:02:28+00:00',
                note: 'Privilege deactivated'
            }
        ]
    },
    {
        // ================================================================
        //                         JANET DOE (OH OT)
        // ================================================================
        providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
        compact: 'octp',
        jurisdiction: 'oh',
        licenseType: 'occupational therapist',
        privilegeId: 'OT-OH-11',
        events: [
            {
                type: 'privilegeUpdate',
                updateType: 'issuance',
                dateOfUpdate: '2024-03-28T18:07:08+00:00',
                effectiveDate: '2024-03-28T18:07:08+00:00',
                createDate: '2024-03-28T18:07:08+00:00'
            },
            {
                type: 'privilegeUpdate',
                updateType: 'deactivation',
                dateOfUpdate: '2025-03-28T18:07:08+00:00',
                effectiveDate: '2025-03-28T18:07:08+00:00',
                createDate: '2025-03-28T18:07:08+00:00',
                note: 'Privilege deactivated'
            }
        ]
    },
    {
        // ================================================================
        //                         JANET DOE (OH OTA)
        // ================================================================
        providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
        compact: 'octp',
        jurisdiction: 'oh',
        licenseType: 'occupational therapy assistant',
        privilegeId: 'OTA-OH-9',
        events: [
            {
                type: 'privilegeUpdate',
                updateType: 'issuance',
                dateOfUpdate: '2024-03-19T21:30:27+00:00',
                effectiveDate: '2024-03-19T21:30:27+00:00',
                createDate: '2024-03-19T21:30:27+00:00'
            },
            {
                type: 'privilegeUpdate',
                updateType: 'deactivation',
                dateOfUpdate: '2025-03-26T15:56:58+00:00',
                effectiveDate: '2025-03-26T15:56:58+00:00',
                createDate: '2025-03-26T15:56:58+00:00',
                note: 'Privilege deactivated'
            }
        ]
    },
    {
        // ================================================================
        //                         JANET DOE (WY OTA)
        // ================================================================
        providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
        compact: 'octp',
        jurisdiction: 'wy',
        licenseType: 'occupational therapy assistant',
        privilegeId: 'OTA-WY-1',
        events: [
            {
                type: 'privilegeUpdate',
                updateType: 'issuance',
                dateOfUpdate: '2024-03-19T21:30:27+00:00',
                effectiveDate: '2024-03-19T21:30:27+00:00',
                createDate: '2024-03-19T21:30:27+00:00'
            },
            {
                type: 'privilegeUpdate',
                updateType: 'investigation',
                dateOfUpdate: moment().subtract(1, 'week').format(serverDatetimeFormat),
                effectiveDate: moment().subtract(1, 'week').format(serverDatetimeFormat),
                createDate: moment().subtract(1, 'week').format(serverDatetimeFormat),
                note: '',
            }
        ]
    },
    {
        // ================================================================
        //                         TYLER DURDEN (AL OTA)
        // ================================================================
        providerId: '2',
        compact: 'octp',
        jurisdiction: 'al',
        licenseType: 'occupational therapy assistant',
        privilegeId: 'OCTP-AL-19',
        events: [
            {
                type: 'privilegeUpdate',
                updateType: 'issuance',
                dateOfUpdate: moment().subtract(10, 'months').subtract(1, 'year').format(serverDateFormat),
                effectiveDate: moment().subtract(10, 'months').subtract(1, 'year').format(serverDateFormat),
                createDate: moment().subtract(10, 'months').subtract(1, 'year').format(serverDateFormat)
            },
            {
                type: 'privilegeUpdate',
                updateType: 'deactivation',
                dateOfUpdate: '2024-08-29',
                effectiveDate: '2024-08-29',
                createDate: '2024-08-29',
                note: 'License deactivated'
            }
        ]
    },
    {
        // ================================================================
        //                         MARLA SINGER (AL OTA)
        // ================================================================
        providerId: '3',
        compact: 'octp',
        jurisdiction: 'al',
        licenseType: 'occupational therapy assistant',
        privilegeId: 'OCTP-AL-22',
        events: [
            {
                type: 'privilegeUpdate',
                updateType: 'issuance',
                dateOfUpdate: moment().subtract(10, 'months').subtract(1, 'year').format(serverDateFormat),
                effectiveDate: moment().subtract(10, 'months').subtract(1, 'year').format(serverDateFormat),
                createDate: moment().subtract(10, 'months').subtract(1, 'year').format(serverDateFormat)
            },
            {
                type: 'privilegeUpdate',
                updateType: 'renewal',
                dateOfUpdate: moment().subtract(10, 'months').format(serverDateFormat),
                effectiveDate: moment().subtract(10, 'months').format(serverDateFormat),
                createDate: moment().subtract(10, 'months').format(serverDateFormat)
            }
        ]
    },
    {
        // ================================================================
        //                         JANE DOE (AL OTA)
        // ================================================================
        providerId: '4',
        compact: 'octp',
        jurisdiction: 'al',
        licenseType: 'occupational therapy assistant',
        privilegeId: 'OTA-AL-11',
        events: [
            {
                type: 'privilegeUpdate',
                updateType: 'issuance',
                dateOfUpdate: '2023-08-29',
                effectiveDate: '2023-08-29',
                createDate: '2023-08-29'
            }
        ]
    },
    {
        // ================================================================
        //                         JANE DOE (AK OTA)
        // ================================================================
        providerId: '4',
        compact: 'octp',
        jurisdiction: 'ak',
        licenseType: 'occupational therapy assistant',
        privilegeId: 'OTA-AK-12',
        events: [
            {
                type: 'privilegeUpdate',
                updateType: 'issuance',
                dateOfUpdate: '2023-08-29',
                effectiveDate: '2023-08-29',
                createDate: '2023-08-29'
            }
        ]
    },
    {
        // ================================================================
        //                         JANE DOE (AR OTA)
        // ================================================================
        providerId: '4',
        compact: 'octp',
        jurisdiction: 'ar',
        licenseType: 'occupational therapy assistant',
        privilegeId: 'OTA-AR-13',
        events: [
            {
                type: 'privilegeUpdate',
                updateType: 'issuance',
                dateOfUpdate: '2023-08-29',
                effectiveDate: '2023-08-29',
                createDate: '2023-08-29'
            }
        ]
    }
];

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
