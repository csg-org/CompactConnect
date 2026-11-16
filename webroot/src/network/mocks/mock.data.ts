//
//  mock.data.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/6/20.
//
import { serverDateFormat, serverDatetimeFormat } from '@/app.config';
import { CompactType } from '@models/Compact/Compact.model';
import { LicenseType } from '@models/License/License.model';
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
                readSSN: true,
            },
            jurisdictions: {
                al: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                co: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                ky: {
                    actions: {
                        admin: false,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                ne: {
                    actions: {
                        admin: false,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                oh: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                nv: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                ma: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                wy: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
            },
        },
        aslp: {
            actions: {
                admin: true,
                readPrivate: true,
                readSSN: true,
            },
            jurisdictions: {
                ak: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                ar: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                co: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
            },
        },
        coun: {
            actions: {
                admin: true,
                readPrivate: true,
                readSSN: true,
            },
            jurisdictions: {
                al: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                co: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                ky: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
            },
        },
        cosm: {
            actions: {
                admin: true,
                readPrivate: true,
                readSSN: true,
            },
            jurisdictions: {
                al: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                co: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                ky: {
                    actions: {
                        admin: false,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                ne: {
                    actions: {
                        admin: false,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                oh: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                nv: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                ma: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                wy: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
            },
        },
        socw: {
            actions: {
                admin: true,
                readPrivate: true,
                readSSN: true,
            },
            jurisdictions: {
                al: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                co: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                ky: {
                    actions: {
                        admin: false,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                ne: {
                    actions: {
                        admin: false,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                oh: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                nv: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                ma: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                wy: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
            },
        },
        psypact: {
            actions: {
                admin: true,
                readPrivate: true,
                readSSN: true,
            },
            jurisdictions: {
                al: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                co: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                ky: {
                    actions: {
                        admin: false,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                ne: {
                    actions: {
                        admin: false,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                oh: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                nv: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                ma: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                wy: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
            },
        },
        diet: {
            actions: {
                admin: true,
                readPrivate: true,
                readSSN: true,
            },
            jurisdictions: {
                ak: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                ar: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                },
                co: {
                    actions: {
                        admin: true,
                        write: true,
                        readPrivate: true,
                        readSSN: true,
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

// Privilege fees for compacts in AppGroupModes.PRIVILEGE_PURCHASE.
const mockPrivilegeFeesByCompact: Partial<Record<CompactType, Array<{
    licenseTypeAbbreviation: string,
    amount: number,
    militaryAmount: number,
}>>> = {
    [CompactType.ASLP]: [
        { licenseTypeAbbreviation: 'aud', amount: 200, militaryAmount: 90 },
        { licenseTypeAbbreviation: 'slp', amount: 100, militaryAmount: 50 },
    ],
    [CompactType.OT]: [
        { licenseTypeAbbreviation: 'ot', amount: 200, militaryAmount: 90 },
        { licenseTypeAbbreviation: 'ota', amount: 100, militaryAmount: 50 },
    ],
    [CompactType.COUNSELING]: [
        { licenseTypeAbbreviation: 'lpc', amount: 100, militaryAmount: 50 },
    ],
    [CompactType.DIETITIANS]: [
        { licenseTypeAbbreviation: 'diet', amount: 100, militaryAmount: 50 },
    ],
};

export const createStatePrivilegePurchaseOption = (config: any = {}) => {
    const compact = (config?.compact) ? config.compact as CompactType : CompactType.OT;
    const compactFees = mockPrivilegeFeesByCompact[compact];
    const otFees = mockPrivilegeFeesByCompact[CompactType.OT] || [];
    const feeTemplates = compactFees || otFees;
    const purchaseOption: any = {
        type: 'jurisdiction',
        postalAbbreviation: config?.stateAbbrev,
        jurisdictionName: config?.stateName,
        compact,
        privilegeFees: feeTemplates.map((fee) => {
            const privilegeFee = {
                licenseTypeAbbreviation: fee.licenseTypeAbbreviation,
                amount: fee.amount,
                militaryRate: (config?.hasMilitaryDiscount) ? fee.militaryAmount : undefined,
            };

            return privilegeFee;
        }),
        jurisprudenceRequirements: {
            required: Boolean(config?.hasJurisprudence),
        },
    };

    if (config.hasJurisprudenceLink) {
        purchaseOption.jurisprudenceRequirements.linkToDocumentation = 'https://example.com';
    }

    return purchaseOption;
};

const privilegePurchaseStateConfigs = [
    {
        stateAbbrev: 'ak',
        stateName: 'alaska',
        hasMilitaryDiscount: false,
        hasJurisprudence: true,
        hasJurisprudenceLink: true,
    },
    {
        stateAbbrev: 'al',
        stateName: 'alabama',
        hasMilitaryDiscount: false,
        hasJurisprudence: true,
        hasJurisprudenceLink: false,
    },
    {
        stateAbbrev: 'ar',
        stateName: 'arkansas',
        hasMilitaryDiscount: false,
        hasJurisprudence: true,
        hasJurisprudenceLink: false,
    },
    {
        stateAbbrev: 'co',
        stateName: 'colorado',
        hasMilitaryDiscount: false,
        hasJurisprudence: true,
        hasJurisprudenceLink: true,
    },
    {
        stateAbbrev: 'ct',
        stateName: 'connecticut',
        hasMilitaryDiscount: false,
        hasJurisprudence: false,
        hasJurisprudenceLink: false,
    },
    {
        stateAbbrev: 'ks',
        stateName: 'kansas',
        hasMilitaryDiscount: false,
        hasJurisprudence: false,
        hasJurisprudenceLink: false,
    },
    {
        stateAbbrev: 'ky',
        stateName: 'kentucky',
        hasMilitaryDiscount: true,
        hasJurisprudence: true,
        hasJurisprudenceLink: true,
    },
    {
        stateAbbrev: 'ma',
        stateName: 'massachusetts',
        hasMilitaryDiscount: false,
        hasJurisprudence: true,
        hasJurisprudenceLink: false,
    },
    {
        stateAbbrev: 'md',
        stateName: 'maryland',
        hasMilitaryDiscount: false,
        hasJurisprudence: false,
        hasJurisprudenceLink: false,
    },
    {
        stateAbbrev: 'me',
        stateName: 'maine',
        hasMilitaryDiscount: false,
        hasJurisprudence: true,
        hasJurisprudenceLink: false,
    },
    {
        stateAbbrev: 'mt',
        stateName: 'montana',
        hasMilitaryDiscount: false,
        hasJurisprudence: false,
        hasJurisprudenceLink: false,
    },
    {
        stateAbbrev: 'ne',
        stateName: 'nebraska',
        hasMilitaryDiscount: true,
        hasJurisprudence: true,
        hasJurisprudenceLink: false,
    },
    {
        stateAbbrev: 'nh',
        stateName: 'new hampshire',
        hasMilitaryDiscount: false,
        hasJurisprudence: false,
        hasJurisprudenceLink: false,
    },
    {
        stateAbbrev: 'nm',
        stateName: 'new mexico',
        hasMilitaryDiscount: false,
        hasJurisprudence: false,
        hasJurisprudenceLink: false,
    },
    {
        stateAbbrev: 'nv',
        stateName: 'nevada',
        hasMilitaryDiscount: false,
        hasJurisprudence: true,
        hasJurisprudenceLink: false,
    },
    {
        stateAbbrev: 'oh',
        stateName: 'ohio',
        hasMilitaryDiscount: true,
        hasJurisprudence: true,
        hasJurisprudenceLink: false,
    },
    {
        stateAbbrev: 'ok',
        stateName: 'oklahoma',
        hasMilitaryDiscount: false,
        hasJurisprudence: false,
        hasJurisprudenceLink: false,
    },
    {
        stateAbbrev: 'or',
        stateName: 'oregon',
        hasMilitaryDiscount: false,
        hasJurisprudence: false,
        hasJurisprudenceLink: false,
    },
    {
        stateAbbrev: 'ri',
        stateName: 'rhode island',
        hasMilitaryDiscount: false,
        hasJurisprudence: true,
        hasJurisprudenceLink: false,
    },
    {
        stateAbbrev: 'ut',
        stateName: 'utah',
        hasMilitaryDiscount: false,
        hasJurisprudence: false,
        hasJurisprudenceLink: false,
    },
    {
        stateAbbrev: 'va',
        stateName: 'virginia',
        hasMilitaryDiscount: false,
        hasJurisprudence: false,
        hasJurisprudenceLink: false,
    },
    {
        stateAbbrev: 'vt',
        stateName: 'vermont',
        hasMilitaryDiscount: false,
        hasJurisprudence: true,
        hasJurisprudenceLink: false,
    },
    {
        stateAbbrev: 'wa',
        stateName: 'washington',
        hasMilitaryDiscount: false,
        hasJurisprudence: false,
        hasJurisprudenceLink: false,
    },
];

export const getPrivilegePurchaseOptionsResponse = (compactType?: string | null) => {
    const requestedCompact = compactType as CompactType;
    const hasPrivilegeFees = Boolean(mockPrivilegeFeesByCompact[requestedCompact]);
    const compact = (hasPrivilegeFees) ? requestedCompact : CompactType.OT;
    const stateOptions = privilegePurchaseStateConfigs.map((stateConfig) => createStatePrivilegePurchaseOption({
        ...stateConfig,
        compact,
    }));

    return {
        items: [
            {
                compactAbbr: compact,
                compactCommissionFee: {
                    feeType: 'FLAT_RATE',
                    feeAmount: 3.5,
                },
                transactionFeeConfiguration: {
                    licenseeCharges: {
                        active: true,
                        chargeType: 'FLAT_FEE_PER_PRIVILEGE',
                        chargeAmount: 2,
                    },
                },
                type: 'compact',
                isSandbox: true,
                paymentProcessorPublicFields: {
                    apiLoginId: process.env.VUE_APP_MOCK_API_PAYMENT_LOGIN_ID,
                    publicClientKey: process.env.VUE_APP_MOCK_API_PAYMENT_CLIENT_KEY,
                },
            },
            ...stateOptions,
        ],
        pagination: {
            pageSize: 100,
            prevLastKey: null,
            lastKey: null,
        },
    };
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
            compactConnectRegisteredEmailAddress: 'registration@example.com',
            dateOfBirth: '1967-08-22',
            birthMonthDay: '1967-08-22',
            ssnLastFour: '7777',
            cuid: 'SWC-5122-9193666441870158440122579252169899203244419470545948771',
            militaryAffiliations: [
                {
                    affiliationType: 'militaryMember',
                    compact: 'octp',
                    dateOfUpdate: '2024-08-29',
                    dateOfUpload: '2024-08-29',
                    documentKeys: 'key',
                    fileNames: ['military-document.pdf'],
                    downloadLinks: [{
                        fileName: 'military-document.pdf',
                        url: '/examples/military-document.pdf',
                    }],
                    status: 'active',
                }
            ],
            militaryStatus: 'approved',
            militaryStatusNote: 'All the docs look good!',
            licenseStatus: 'active',
            licenseEligibility: 'eligible', // COSM list fetch
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
                    emailAddress: 'state.license@example.com',
                    compact: 'octp',
                    dateOfBirth: '1967-08-22',
                    ssnLastFour: '7777',
                    homeAddressStreet1: '79 N Washington Street',
                    homeAddressStreet2: '',
                    homeAddressCity: 'Denver',
                    homeAddressState: 'co',
                    homeAddressPostalCode: '80203',
                    phoneNumber: '+17179511820',
                    npi: '1234567890',
                    licenseNumber: 'A-987654321',
                    type: 'license-home',
                    licenseType: 'occupational therapy assistant',
                    licenseScope: 'single-state',
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
                    emailAddress: 'state.license@example.com',
                    compact: 'octp',
                    dateOfBirth: '1967-08-22',
                    ssnLastFour: '7777',
                    homeAddressStreet1: '8021 Floral Ave',
                    homeAddressStreet2: '',
                    homeAddressCity: 'Los Angeles',
                    homeAddressState: 'ca',
                    homeAddressPostalCode: '90046',
                    phoneNumber: '+17179511821',
                    npi: '1234567890',
                    licenseNumber: 'A-555666777',
                    type: 'license-home',
                    licenseType: 'occupational therapist',
                    licenseScope: 'multi-state',
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
            cuid: 'SWC-5122-9193666441870158440122579252169899203244419470545948772',
            militaryAffiliations: [
                {
                    affiliationType: 'militaryMember',
                    compact: 'octp',
                    dateOfUpdate: '2024-08-29',
                    dateOfUpload: '2024-08-29',
                    documentKeys: 'key',
                    fileNames: ['military-document.pdf'],
                    downloadLinks: [{
                        fileName: 'military-document.pdf',
                        url: '/examples/military-document.pdf',
                    }],
                    status: 'initializing',
                }
            ],
            militaryStatus: 'declined',
            militaryStatusNote: 'Could not view the required docs. Please upload new copies.',
            licenseStatus: 'active',
            licenseEligibility: 'ineligible', // COSM list fetch
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
                    phoneNumber: '+17179511822',
                    npi: '6441445289',
                    licenseNumber: 'A-441445289',
                    type: 'license-home',
                    licenseType: 'occupational therapy assistant',
                    licenseScope: 'single-state',
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
                    phoneNumber: '+17179511823',
                    npi: '6441445289',
                    licenseNumber: 'A-921445289',
                    type: 'license-home',
                    licenseType: 'occupational therapist',
                    licenseScope: 'multi-state',
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
                    phoneNumber: '+17179511824',
                    npi: '6441445289',
                    licenseNumber: 'A-944945289',
                    type: 'license-home',
                    licenseType: 'occupational therapist',
                    licenseScope: 'single-state',
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
                    phoneNumber: '',
                    licenseNumber: 'A-421445219',
                    npi: '6441445289',
                    type: 'license-home',
                    licenseType: 'occupational therapy assistant',
                    licenseScope: 'multi-state',
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
                    phoneNumber: '',
                    licenseNumber: 'A-531445219',
                    npi: '6441445289',
                    type: 'license-home',
                    licenseType: 'occupational therapy assistant',
                    licenseScope: 'single-state',
                    jurisdiction: 'nv',
                    dateOfIssuance: '2023-08-29',
                    dateOfUpdate: '2024-08-29',
                    dateOfExpiration: '2024-08-29',
                    dateOfRenewal: '2024-08-29',
                    licenseStatus: 'inactive',
                    licenseStatusName: '',
                    compactEligibility: 'ineligible',
                    history: [
                        {
                            updateType: 'issuance',
                            effectiveDate: '2023-08-29',
                            createDate: moment().subtract(2, 'years').format(serverDatetimeFormat),
                        },
                        {
                            updateType: 'encumbrance',
                            effectiveDate: moment().subtract(1, 'year').format(serverDateFormat),
                            createDate: moment().subtract(1, 'year').format(serverDatetimeFormat),
                            encumbranceType: 'fine',
                            npdbCategories: ['Non-compliance With Requirements'],
                        },
                        {
                            updateType: 'liftingEncumbrance',
                            effectiveDate: moment().subtract(1, 'month').format(serverDateFormat),
                            createDate: moment().subtract(1, 'month').format(serverDatetimeFormat),
                        },
                        {
                            updateType: 'encumbrance',
                            effectiveDate: moment().subtract(1, 'month').format(serverDateFormat),
                            createDate: moment().subtract(1, 'week').format(serverDatetimeFormat),
                            encumbranceType: 'fine',
                            npdbCategories: ['Non-compliance With Requirements'],
                        },
                    ],
                    adverseActions: [
                        {
                            adverseActionId: '12345-MNO',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            type: 'adverseAction',
                            encumbranceType: 'fine',
                            clinicalPrivilegeActionCategories: ['Non-compliance With Requirements'],
                            actionAgainst: 'license',
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
                            clinicalPrivilegeActionCategories: ['Non-compliance With Requirements'],
                            actionAgainst: 'license',
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
                    history: [
                        {
                            updateType: 'issuance',
                            effectiveDate: '2024-03-19T21:30:27+00:00',
                            createDate: '2024-03-19T21:30:27+00:00',
                        },
                        {
                            updateType: 'encumbrance',
                            effectiveDate: moment().subtract(1, 'month').format(serverDateFormat),
                            createDate: moment().subtract(1, 'week').format(serverDatetimeFormat),
                            encumbranceType: 'fine',
                            npdbCategories: ['Non-compliance With Requirements'],
                        },
                    ],
                    adverseActions: [
                        {
                            adverseActionId: '12345-ABC',
                            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                            compact: 'octp',
                            type: 'adverseAction',
                            encumbranceType: 'fine',
                            clinicalPrivilegeActionCategories: ['Non-compliance With Requirements'],
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
                            clinicalPrivilegeActionCategories: ['Non-compliance With Requirements'],
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
                            clinicalPrivilegeActionCategories: ['Unsafe Practice or Substandard Care'],
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
            adverseActions: [
                {
                    adverseActionId: '12345-ABC',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    compact: 'octp',
                    type: 'adverseAction',
                    encumbranceType: 'fine',
                    clinicalPrivilegeActionCategories: [
                        'Non-compliance With Requirements',
                        'Confidentiality, Consent or Disclosure Violations',
                        'Improper Supervision or Allowing Unlicensed Practice',
                        'Consumer Harm',
                    ],
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
                {
                    adverseActionId: '12345-DEF',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    compact: 'octp',
                    type: 'adverseAction',
                    encumbranceType: 'fine',
                    clinicalPrivilegeActionCategories: ['Non-compliance With Requirements'],
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
                    clinicalPrivilegeActionCategories: ['Unsafe Practice or Substandard Care'],
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
                {
                    adverseActionId: '12345-MNO',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    compact: 'octp',
                    type: 'adverseAction',
                    encumbranceType: 'fine',
                    clinicalPrivilegeActionCategories: ['Non-compliance With Requirements'],
                    actionAgainst: 'license',
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
                    clinicalPrivilegeActionCategories: ['Non-compliance With Requirements'],
                    actionAgainst: 'license',
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
            cuid: 'SWC-5122-9193666441870158440122579252169899203244419470545948773',
            militaryAffiliations: [],
            militaryStatus: 'notApplicable',
            militaryStatusNote: '',
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
                    phoneNumber: '+17179511825',
                    npi: '2522457223',
                    licenseNumber: 'A-312445289',
                    type: 'license-home',
                    licenseType: 'occupational therapy assistant',
                    licenseScope: 'multi-state',
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
            cuid: 'SWC-5122-9193666441870158440122579252169899203244419470545948774',
            militaryAffiliations: [],
            militaryStatus: 'notApplicable',
            militaryStatusNote: '',
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
                    phoneNumber: null,
                    npi: '6944447283',
                    licenseNumber: 'A-1234567890',
                    type: 'license-home',
                    licenseType: 'occupational therapy assistant',
                    licenseScope: 'single-state',
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
            cuid: 'SWC-5122-9193666441870158440122579252169899203244419470545948775',
            militaryAffiliations: [],
            militaryStatus: 'notApplicable',
            militaryStatusNote: '',
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
                    phoneNumber: null,
                    npi: '6441445289',
                    licenseNumber: null,
                    type: 'license-home',
                    licenseType: 'occupational therapy assistant',
                    licenseScope: 'single-state',
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
            userId: staffAccount.userId,
            status: 'active',
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
                        readSSN: true,
                    },
                    jurisdictions: {
                        al: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                        co: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                        ky: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                    },
                },
                aslp: {
                    actions: {
                        admin: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                    jurisdictions: {
                        ak: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                        ar: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                        co: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                    },
                },
                coun: {
                    actions: {
                        admin: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                    jurisdictions: {
                        al: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                        co: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                        ky: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                    },
                },
                cosm: {
                    actions: {
                        admin: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                    jurisdictions: {
                        al: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                        co: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                        ky: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                    },
                },
                socw: {
                    actions: {
                        admin: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                    jurisdictions: {
                        al: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                        co: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                        ky: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                    },
                },
                psypact: {
                    actions: {
                        admin: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                    jurisdictions: {
                        al: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                        co: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                        ky: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                    },
                },
                diet: {
                    actions: {
                        admin: true,
                        readPrivate: true,
                        readSSN: true,
                    },
                    jurisdictions: {
                        al: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                        co: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                        ky: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                    },
                },
            },
        },
        {
            userId: '11',
            status: 'pending',
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
                        readSSN: false,
                    },
                    jurisdictions: {
                        al: {
                            actions: {
                                admin: false,
                                write: false,
                                readPrivate: false,
                                readSSN: false,
                            },
                        },
                        co: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                        ky: {
                            actions: {
                                admin: false,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
                            },
                        },
                    },
                },
            },
        },
        {
            userId: '12',
            status: '',
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
                        readSSN: false,
                    },
                    jurisdictions: {
                        ky: {
                            actions: {
                                admin: true,
                                write: true,
                                readPrivate: true,
                                readSSN: true,
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
    //
    // PRIVILEGE PURCHASE
    //
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
    //
    // APPLICATION FOR AUTHORIZATION
    //
    case 'education-institutional-verification':
        attestationObj.text = `I certify this information is complete and accurate. When you submit your full application, we'll email your institutional contact to verify it.`;
        break;
    case 'rejected-or-denied-licensure-application':
        attestationObj.text = `Has any jurisdiction (e.g., state, province, the District of Columbia, or US possession or territory) rejected or denied your application for licensure/certification/registration as a psychologist or any other profession?`;
        break;
    case 'disciplined-by-licensing-board':
        attestationObj.text = `Have you ever been disciplined (i.e., revocation, suspension, reprimand, censure, or any other publicly reported disciplinary action) by a psychology licensing board?`;
        break;
    case 'jurisdiction-limited-practice':
        attestationObj.text = `Has any jurisdiction limited your practice in any way or by any other action?`;
        break;
    case 'publicly-reported-non-disciplinary-action':
        attestationObj.text = `Have you ever been issued a publicly reported non-disciplinary action on any professional license by any licensing board through an order, settlement, and/or agreement?`;
        break;
    case 'disciplined-while-holding-professional-license':
        attestationObj.text = `Have you ever been disciplined while holding any other professional license/registration/certificate?`;
        break;
    case 'voluntarily-surrendered-or-restricted-professional-license':
        attestationObj.text = `Have you ever voluntarily surrendered or restricted your professional license/registration/certificate in any jurisdiction?`;
        break;
    case 'disciplinary-action-as-professional':
        attestationObj.text = `Have you ever been censured, reprimanded, dismissed, suspended, terminated, or asked to resign, or has any disciplinary action been taken against you during your education, training, or employment as a mental health professional?`;
        break;
    case 'refused-renewal-of-any-professional-license':
        attestationObj.text = `Have you ever been refused renewal of any professional license/registration/certificate for any reason in any jurisdiction?`;
        break;
    case 'registered-sex-offender':
        attestationObj.text = `Are you registered as a sex offender?`;
        break;
    case 'subject-of-current-proceeding-or-investigation':
        attestationObj.text = `Are you the subject of a current proceeding or outstanding/unresolved complaint or investigation in relation to the profession of psychology or any other profession?`;
        break;
    case 'aided-or-abetted-another-individual-practicing-psychology':
        attestationObj.text = `Have you ever aided or abetted another individual in practicing psychology without a license or an exemption in any jurisdiction?`;
        break;
    case 'practiced-psychology-without-license-or-exemption':
        attestationObj.text = `Have you ever practiced psychology without a license or an exemption in any jurisdiction?`;
        break;
    case 'physically-or-mentally-incapable':
        attestationObj.text = `Are you physically or mentally incapable to render psychological services with reasonable skill, safety, and competency at present?`;
        break;
    case 'drugs-or-alcohol-affecting-competency':
        attestationObj.text = `Do you use drugs and/or alcohol to an extent that affects your professional competency?`;
        break;
    case 'malpractice-action-or-settlement':
        attestationObj.text = `Have you ever been party to a malpractice action or had a malpractice action brought against you or entered into a malpractice settlement?`;
        break;
    case 'action-by-ethics-committee':
        attestationObj.text = `Have you ever been the subject of an action by an ethics committee of any professional organization in any jurisdiction?`;
        break;
    case 'denied-revoked-suspended-restricted-staff-membership':
        attestationObj.text = `Have you ever been denied staff membership or privileges in any hospital or health care facility or had such membership or privileges revoked, suspended, or subjected to restriction or have been requested to withdraw or resign?`;
        break;
    case 'status-as-provider-revoked-suspended-restricted-by-payor':
        attestationObj.text = `Has any third party payor (including Medicare and Medicaid), terminated, suspended, restricted, or revoked your status as a provider for reasons related to your professional practice?`;
        break;
    case 'professional-liability-insurance-canceled':
        attestationObj.text = `Have you ever had professional liability insurance canceled?`;
        break;
    case 'governmental-agency-substantiated-allegations':
        attestationObj.text = `Has any governmental agency ever substantiated allegations made against you for physical, mental, emotional abuse or neglect, sexual abuse, or exploitation of (1) child, (2) resident of an adult care home, medical care facility, psychiatric hospital or state institution for intellectual disabilities, or (3) an adult?`;
        break;
    case 'information-true-and-complete':
        attestationObj.text = `I attest that all information in this section is true and complete to the best of my knowledge.`;
        break;
    case 'comply-with-state-requirements':
        attestationObj.text = `I acknowledge I must comply with this state's requirements and will update my home state within 30 days of any change.`;
        break;
    case 'home-state-is-psypact-state-with-active-license':
        attestationObj.text = `I acknowledge and agree that my declared Home State is a PSYPACT participating jurisdiction in which I hold a current active license.`;
        break;
    case 'telepsychology-only-while-present-in-home-state':
        attestationObj.text = `I acknowledge and agree that when practicing under the authority of PSYPACT, I will only provide telepsychology services while physically present and located in my declared PSYPACT Home State of license. This does not pertain to providing telepsychology services to clients located within my home state or any other state where I may hold a current active license to practice as a psychologist.`;
        break;
    case 'update-home-state-within-30-days':
        attestationObj.text = `I acknowledge and agree to update my Home State within 30 days if my Home State changes. PSYPACT Policy 2.4`;
        break;
    case 'not-make-false-or-misleading-representations':
        attestationObj.text = `I acknowledge and agree to only represent my participation in PSYPACT as defined by PSYPACT Policy 2.6 so as to not make any false or misleading representations about myself or PSYPACT. PSYPACT Policy 2.6`;
        break;
    case 'protect-health-and-safety-of-citizens':
        attestationObj.text = `I acknowledge and agree to be aware of and abide by the Receiving PSYPACT State's laws to protect the health and safety of its citizens as defined in PSYPACT Rule 4.10. PSYPACT Rule 4.10`;
        break;
    case 'failure-to-abide-by-acknowledgements-will-result-in-revocation':
        attestationObj.text = `I acknowledge and agree that failure to abide by the above acknowledgements will result in revocation of my PSYPACT authorization. `;
        break;
    case 'agree-to-report-complaint-or-discipline':
        attestationObj.text = `I acknowledge and agree to report to the PSYPACT Commission any complaint and/or discipline taken against any psychology license I hold within thirty (30) days.`;
        break;
    case 'sign-and-submit':
        attestationObj.text = `I understand failing to abide by the above acknowledgements may be grounds for revocation of any authorization granted to me based on this information. I understand that additional information may be requested.

        I acknowledge and agree that submission of this application does not create any right to a legal review of any application decision, nor does such submission create any cause of action against the PSYPACT Commission or its Committee members, or any claim for damages if I am denied authorization status.

        I acknowledge that I have not been promised or guaranteed that my qualifications will result in the granting of any authorization by the PSYPACT Commission.

        By completing the electronic signature information below, you are signing this form electronically. You agree your electronic signature is the legal equivalent of your manual signature on this form.`;
        break;
    case 'information-presented-is-factual':
        attestationObj.text = `I hereby attest that all information presented is factual to the best of my knowledge.`;
        break;
    case 'submission-does-not-guarantee-approval':
        attestationObj.text = `I acknowledge this submission does not guarantee approval and that my application fee is non-refundable.`;
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
    {
        compact: 'octp',
        postalAbbreviation: 'tn',
    },
    {
        compact: 'octp',
        postalAbbreviation: 'wa',
    },
];

export const compactStatesForRegistration = {
    aslp: [ 'al', 'co', 'fl', 'ga', 'il', 'ia', 'ky', 'ne' ],
    coun: [ 'al', 'ak', 'co', 'il', 'ia', 'ky', 'ne', 'nm' ],
    octp: [ 'al', 'ar', 'co', 'ct', 'il', 'ky' ],
    psypact: [ 'al', 'co', 'fl', 'ga', 'il', 'ia', 'ky', 'ne' ],
    diet: [ 'al', 'co', 'fl', 'ga', 'il', 'ia', 'ky', 'ne' ],
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
            jurisdictionAdverseActionsNotificationEmails: [`adverse@example.com`],
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

// =========================================================================================
// =                                   APPLICATIONS                                        =
// =========================================================================================
export const attestationResponsesEducation = [
    {
        attestationId: 'education-institutional-verification',
        version: '1',
    },
];

export const attestationResponsesConduct = [
    {
        attestationId: 'rejected-or-denied-licensure-application',
        version: '1',
    },
    {
        attestationId: 'disciplined-by-licensing-board',
        version: '1',
    },
    {
        attestationId: 'jurisdiction-limited-practice',
        version: '1',
    },
    {
        attestationId: 'publicly-reported-non-disciplinary-action',
        version: '1',
    },
    {
        attestationId: 'disciplined-while-holding-professional-license',
        version: '1',
    },
    {
        attestationId: 'voluntarily-surrendered-or-restricted-professional-license',
        version: '1',
    },
    {
        attestationId: 'disciplinary-action-as-professional',
        version: '1',
    },
    {
        attestationId: 'refused-renewal-of-any-professional-license',
        version: '1',
    },
    {
        attestationId: 'registered-sex-offender',
        version: '1',
    },
    {
        attestationId: 'subject-of-current-proceeding-or-investigation',
        version: '1',
    },
    {
        attestationId: 'aided-or-abetted-another-individual-practicing-psychology',
        version: '1',
    },
    {
        attestationId: 'practiced-psychology-without-license-or-exemption',
        version: '1',
    },
    {
        attestationId: 'physically-or-mentally-incapable',
        version: '1',
    },
    {
        attestationId: 'drugs-or-alcohol-affecting-competency',
        version: '1',
    },
    {
        attestationId: 'malpractice-action-or-settlement',
        version: '1',
    },
    {
        attestationId: 'action-by-ethics-committee',
        version: '1',
    },
    {
        attestationId: 'denied-revoked-suspended-restricted-staff-membership',
        version: '1',
    },
    {
        attestationId: 'status-as-provider-revoked-suspended-restricted-by-payor',
        version: '1',
    },
    {
        attestationId: 'professional-liability-insurance-canceled',
        version: '1',
    },
    {
        attestationId: 'governmental-agency-substantiated-allegations',
        version: '1',
    },
    {
        attestationId: 'information-true-and-complete',
        version: '1',
    },
];

export const attestationResponsesHomeState = [
    {
        attestationId: 'comply-with-state-requirements',
        version: '1',
    },
];

export const attestationResponsesAcknowledgements = [
    {
        attestationId: 'home-state-is-psypact-state-with-active-license',
        version: '1',
    },
    {
        attestationId: 'telepsychology-only-while-present-in-home-state',
        version: '1',
    },
    {
        attestationId: 'update-home-state-within-30-days',
        version: '1',
    },
    {
        attestationId: 'not-make-false-or-misleading-representations',
        version: '1',
    },
    {
        attestationId: 'protect-health-and-safety-of-citizens',
        version: '1',
    },
    {
        attestationId: 'failure-to-abide-by-acknowledgements-will-result-in-revocation',
        version: '1',
    },
    {
        attestationId: 'agree-to-report-complaint-or-discipline',
        version: '1',
    },
    {
        attestationId: 'sign-and-submit',
        version: '1',
    },
    {
        attestationId: 'information-presented-is-factual',
        version: '1',
    },
];

export const attestationResponsesSubmit = [
    {
        attestationId: 'submission-does-not-guarantee-approval',
        version: '1',
    },
];

export const applicantApplications = [
    // ========================================================
    // =              STARTED BUT BLANK (APIT)                =
    // ========================================================
    {
        id: '1',
        created: moment().subtract(2, 'weeks').format(serverDatetimeFormat),
        submitted: null,
        completed: null,
        types: ['apit'],
        isRenewal: false,
        status: 'started',
        reviews: [],
        attestations: [],
        paymentCompensated: [],
        personalInformation: {
            applicantStatus: 'incomplete',
            reviewStatus: 'awaiting-applicant',
            reviews: [],
            firstName: null,
            middleName: null,
            lastName: null,
            suffix: null,
            phone: null,
            altPhone: null,
            dob: null,
            ssnLastFour: null,
            npi: null,
            gender: null,
            professionalName: null,
            citizenship: null,
            placeOfBirth: null,
            languages: [],
            mailingAddress1: null,
            mailingAddress2: null,
            mailingCity: null,
            mailingState: null,
            mailingZip: null,
        },
        licenseHistory: {
            applicantStatus: 'incomplete',
            reviewStatus: 'awaiting-applicant',
            reviews: [],
            ePassport: {
                mobilityNumber: null,
                issueDate: null,
            },
            ipc: {
                mobilityNumber: null,
                issueDate: null,
            },
            licenses: [],
        },
        education: {
            applicantStatus: 'incomplete',
            reviewStatus: 'awaiting-applicant',
            reviews: [],
            nameAtTime: null,
            institution: null,
            city: null,
            state: null,
            degreeType: null,
            program: null,
            department: null,
            conferredDate: null,
            isCompleted: false,
            accreditingBody: null,
            accreditingYear: null,
            isAccreditedByAuthority: false,
            isProgramEquivalent: false,
            accreditingContact: null,
            hasResidence: false,
            transcripts: [],
        },
        conductHistory: {
            applicantStatus: 'incomplete',
            reviewStatus: 'awaiting-applicant',
            reviews: [],
            attestations: [],
            convictions: [],
            notes: null,
            documents: [],
        },
        homeState: {
            applicantStatus: 'incomplete',
            reviewStatus: 'awaiting-applicant',
            reviews: [],
            applicationTypes: [],
        },
        acknowledgements: {
            applicantStatus: 'incomplete',
            reviewStatus: 'awaiting-applicant',
            reviews: [],
            attestations: [],
            signatureName: null,
        },
    },
    // ========================================================
    // =         COMPLETED READY TO SUBMIT (APIT + TAP)       =
    // ========================================================
    {
        id: '2',
        created: moment().subtract(2, 'weeks').format(serverDatetimeFormat),
        submitted: null,
        completed: null,
        types: ['apit', 'tap'],
        isRenewal: false,
        status: 'started',
        reviews: [],
        attestations: [],
        paymentCompensated: [],
        personalInformation: {
            applicantStatus: 'complete',
            reviewStatus: 'awaiting-applicant',
            reviews: [],
            firstName: 'Test',
            middleName: null,
            lastName: 'Applicant',
            suffix: null,
            phone: '+12223334444',
            altPhone: null,
            dob: moment().subtract(50, 'years').format(serverDateFormat),
            ssnLastFour: '1111',
            npi: '1111111111',
            gender: 'male',
            professionalName: 'Test Applicant, PhD.',
            citizenship: 'us',
            placeOfBirth: 'Springfield',
            languages: ['en', 'es'],
            mailingAddress1: '123 Fake St',
            mailingAddress2: 'Apt 1',
            mailingCity: 'Springfield',
            mailingState: 'co',
            mailingZip: '11111',
        },
        licenseHistory: {
            applicantStatus: 'complete',
            reviewStatus: 'awaiting-applicant',
            reviews: [],
            ePassport: {
                mobilityNumber: '1111111',
                issueDate: moment().subtract(6, 'months').format(serverDateFormat),
            },
            ipc: {
                mobilityNumber: '2222222',
                issueDate: moment().subtract(6, 'months').format(serverDateFormat),
            },
            licenses: [
                {
                    state: 'co',
                    issueDate: moment().subtract(6, 'months').format(serverDateFormat),
                    licenseNumber: '1111111111',
                    status: 'active',
                },
                {
                    state: 'ky',
                    issueDate: moment().subtract(6, 'months').format(serverDateFormat),
                    licenseNumber: '2222222222',
                    status: 'active',
                },
            ],
        },
        education: {
            applicantStatus: 'complete',
            reviewStatus: 'awaiting-applicant',
            reviews: [],
            nameAtTime: 'Test Applicant',
            institution: 'University of Psychology',
            city: 'Springfield',
            state: 'co',
            degreeType: 'phd',
            program: 'Family, friends, & family friends',
            department: 'Psychology',
            conferredDate: moment().subtract(7, 'months').format(serverDateFormat),
            isCompleted: true,
            accreditingBody: 'University of Psychology',
            accreditingYear: moment().subtract(7, 'months').format('YYYY'),
            isAccreditedByAuthority: true,
            isProgramEquivalent: true,
            accreditingContact: null,
            hasResidence: true,
            transcripts: [],
        },
        conductHistory: {
            applicantStatus: 'complete',
            reviewStatus: 'awaiting-applicant',
            reviews: [],
            attestations: attestationResponsesConduct.map((response) => ({ ...response })),
            convictions: [],
            notes: 'Adding some files just in case.',
            documents: [
                {
                    filename: 'document_1.pdf',
                    sizeBytes: 2500000,
                    downloadUri: '/examples/military-document.pdf',
                },
            ],
        },
        homeState: {
            applicantStatus: 'complete',
            reviewStatus: 'awaiting-applicant',
            reviews: [],
            applicationTypes: [
                {
                    applicationType: 'apit',
                    state: 'co',
                    startDate: moment().subtract(6, 'months').format(serverDateFormat),
                    isActiveMilitary: false,
                    militaryDocuments: [],
                    attestations: attestationResponsesHomeState.map((response) => ({ ...response })),
                },
                {
                    applicationType: 'tap',
                    state: 'ky',
                    startDate: moment().subtract(6, 'months').format(serverDateFormat),
                    isActiveMilitary: false,
                    militaryDocuments: [],
                    attestations: attestationResponsesHomeState.map((response) => ({ ...response })),
                },
            ],
        },
        acknowledgements: {
            applicantStatus: 'complete',
            reviewStatus: 'awaiting-applicant',
            reviews: [],
            attestations: attestationResponsesAcknowledgements.map((response) => ({ ...response })),
            signatureName: 'Test Applicant',
        },
    },
    // ========================================================
    // =         SUBMITTED IN REVIEW (APIT + TAP)             =
    // ========================================================
    {
        id: '3',
        created: moment().subtract(2, 'weeks').format(serverDatetimeFormat),
        submitted: moment().subtract(1, 'day').format(serverDatetimeFormat),
        completed: null,
        types: ['apit', 'tap'],
        isRenewal: false,
        status: 'staff-review',
        reviews: [],
        attestations: attestationResponsesSubmit.map((response) => ({ ...response })),
        paymentCompensated: [],
        personalInformation: {
            applicantStatus: 'complete',
            reviewStatus: 'pending',
            reviews: [],
            firstName: 'Test',
            middleName: null,
            lastName: 'Applicant',
            suffix: null,
            phone: '+12223334444',
            altPhone: null,
            dob: moment().subtract(50, 'years').format(serverDateFormat),
            ssnLastFour: '1111',
            npi: '1111111111',
            gender: 'male',
            professionalName: 'Test Applicant, PhD.',
            citizenship: 'us',
            placeOfBirth: 'Springfield',
            languages: ['en', 'es'],
            mailingAddress1: '123 Fake St',
            mailingAddress2: 'Apt 1',
            mailingCity: 'Springfield',
            mailingState: 'co',
            mailingZip: '11111',
        },
        licenseHistory: {
            applicantStatus: 'complete',
            reviewStatus: 'pending',
            reviews: [],
            ePassport: {
                mobilityNumber: '1111111',
                issueDate: moment().subtract(6, 'months').format(serverDateFormat),
            },
            ipc: {
                mobilityNumber: '2222222',
                issueDate: moment().subtract(6, 'months').format(serverDateFormat),
            },
            licenses: [
                {
                    state: 'co',
                    issueDate: moment().subtract(6, 'months').format(serverDateFormat),
                    licenseNumber: '1111111111',
                    status: 'active',
                },
                {
                    state: 'ky',
                    issueDate: moment().subtract(6, 'months').format(serverDateFormat),
                    licenseNumber: '2222222222',
                    status: 'active',
                },
            ],
        },
        education: {
            applicantStatus: 'complete',
            reviewStatus: 'pending',
            reviews: [],
            nameAtTime: 'Test Applicant',
            institution: 'University of Psychology',
            city: 'Springfield',
            state: 'co',
            degreeType: 'phd',
            program: 'Family, friends, & family friends',
            department: 'Psychology',
            conferredDate: moment().subtract(7, 'months').format(serverDateFormat),
            isCompleted: true,
            accreditingBody: 'University of Psychology',
            accreditingYear: moment().subtract(7, 'months').format('YYYY'),
            isAccreditedByAuthority: true,
            isProgramEquivalent: true,
            accreditingContact: {
                name: 'Joe Accreditor',
                email: 'joe@example.com',
                city: 'Springfield',
                state: 'co',
                zip: '11111',
                phone: '+12223334444',
                attestations: attestationResponsesEducation.map((response) => ({ ...response })),
            },
            hasResidence: true,
            transcripts: [],
        },
        conductHistory: {
            applicantStatus: 'complete',
            reviewStatus: 'pending',
            reviews: [],
            attestations: attestationResponsesConduct.map((response) => ({ ...response })),
            convictions: [
                {
                    charge: 'Looting',
                    location: 'Los Angeles',
                    date: moment().subtract(35, 'years').format(serverDateFormat),
                    type: 'Misdemenor',
                },
            ],
            notes: 'Added a doc explaining the conviction',
            documents: [
                {
                    filename: 'document_1.pdf',
                    sizeBytes: 2500000,
                    downloadUri: '/examples/military-document.pdf',
                },
            ],
        },
        homeState: {
            applicantStatus: 'complete',
            reviewStatus: 'pending',
            reviews: [],
            applicationTypes: [
                {
                    applicationType: 'apit',
                    state: 'co',
                    startDate: moment().subtract(6, 'months').format(serverDateFormat),
                    isActiveMilitary: true,
                    militaryDocuments: [
                        {
                            filename: 'military_1.pdf',
                            sizeBytes: 1400000,
                            downloadUri: '/examples/military-document.pdf',
                        },
                    ],
                    attestations: attestationResponsesHomeState.map((response) => ({ ...response })),
                },
                {
                    applicationType: 'tap',
                    state: 'ky',
                    startDate: moment().subtract(6, 'months').format(serverDateFormat),
                    isActiveMilitary: false,
                    militaryDocuments: [],
                    attestations: attestationResponsesHomeState.map((response) => ({ ...response })),
                },
            ],
        },
        acknowledgements: {
            applicantStatus: 'complete',
            reviewStatus: 'pending',
            reviews: [],
            attestations: attestationResponsesAcknowledgements.map((response) => ({ ...response })),
            signatureName: 'Test Applicant',
        },
    },
    // ========================================================
    // =       SUBMITTED NEEDS ATTENTION (APIT + TAP)         =
    // ========================================================
    {
        id: '4',
        created: moment().subtract(2, 'weeks').format(serverDatetimeFormat),
        submitted: moment().subtract(2, 'days').format(serverDatetimeFormat),
        completed: null,
        types: ['apit', 'tap'],
        isRenewal: false,
        status: 'awaiting-applicant',
        reviews: [],
        attestations: attestationResponsesSubmit.map((response) => ({ ...response })),
        paymentCompensated: [],
        personalInformation: {
            applicantStatus: 'complete',
            reviewStatus: 'approved',
            reviews: [
                {
                    reviewerStatus: 'approved',
                    reviewDate: moment().subtract(1, 'day').format(serverDatetimeFormat),
                    notesForApplicant: null,
                },
            ],
            firstName: 'Test',
            middleName: null,
            lastName: 'Applicant',
            suffix: null,
            phone: '+12223334444',
            altPhone: null,
            dob: moment().subtract(50, 'years').format(serverDateFormat),
            ssnLastFour: '1111',
            npi: '1111111111',
            gender: 'male',
            professionalName: 'Test Applicant, PhD.',
            citizenship: 'us',
            placeOfBirth: 'Springfield',
            languages: ['en', 'es'],
            mailingAddress1: '123 Fake St',
            mailingAddress2: 'Apt 1',
            mailingCity: 'Springfield',
            mailingState: 'co',
            mailingZip: '11111',
        },
        licenseHistory: {
            applicantStatus: 'complete',
            reviewStatus: 'approved',
            reviews: [
                {
                    reviewerStatus: 'approved',
                    reviewDate: moment().subtract(1, 'day').format(serverDatetimeFormat),
                    notesForApplicant: null,
                },
            ],
            ePassport: {
                mobilityNumber: '1111111',
                issueDate: moment().subtract(6, 'months').format(serverDateFormat),
            },
            ipc: {
                mobilityNumber: '2222222',
                issueDate: moment().subtract(6, 'months').format(serverDateFormat),
            },
            licenses: [
                {
                    state: 'co',
                    issueDate: moment().subtract(6, 'months').format(serverDateFormat),
                    licenseNumber: '1111111111',
                    status: 'active',
                },
                {
                    state: 'ky',
                    issueDate: moment().subtract(6, 'months').format(serverDateFormat),
                    licenseNumber: '2222222222',
                    status: 'active',
                },
            ],
        },
        education: {
            applicantStatus: 'needs-attention',
            reviewStatus: 'awaiting-applicant',
            reviews: [
                {
                    reviewerStatus: 'awaiting-applicant',
                    reviewDate: moment().subtract(1, 'day').format(serverDatetimeFormat),
                    notesForApplicant: 'Could not confirm your accredidation. Please provide an accrediting contact.',
                },
            ],
            nameAtTime: 'Test Applicant',
            institution: 'University of Psychology',
            city: 'Springfield',
            state: 'co',
            degreeType: 'phd',
            program: 'Family, friends, & family friends',
            department: 'Psychology',
            conferredDate: moment().subtract(7, 'months').format(serverDateFormat),
            isCompleted: true,
            accreditingBody: 'University of Psychology',
            accreditingYear: moment().subtract(7, 'months').format('YYYY'),
            isAccreditedByAuthority: true,
            isProgramEquivalent: true,
            accreditingContact: null,
            hasResidence: true,
            transcripts: [],
        },
        conductHistory: {
            applicantStatus: 'complete',
            reviewStatus: 'approved',
            reviews: [
                {
                    reviewerStatus: 'approved',
                    reviewDate: moment().subtract(1, 'day').format(serverDatetimeFormat),
                    notesForApplicant: null,
                },
            ],
            attestations: attestationResponsesConduct.map((response) => ({ ...response })),
            convictions: [],
            notes: null,
            documents: [],
        },
        homeState: {
            applicantStatus: 'complete',
            reviewStatus: 'approved',
            reviews: [
                {
                    reviewerStatus: 'approved',
                    reviewDate: moment().subtract(1, 'day').format(serverDatetimeFormat),
                    notesForApplicant: null,
                },
            ],
            applicationTypes: [
                {
                    applicationType: 'apit',
                    state: 'co',
                    startDate: moment().subtract(6, 'months').format(serverDateFormat),
                    isActiveMilitary: false,
                    militaryDocuments: [],
                    attestations: attestationResponsesHomeState.map((response) => ({ ...response })),
                },
                {
                    applicationType: 'tap',
                    state: 'ky',
                    startDate: moment().subtract(6, 'months').format(serverDateFormat),
                    isActiveMilitary: false,
                    militaryDocuments: [],
                    attestations: attestationResponsesHomeState.map((response) => ({ ...response })),
                },
            ],
        },
        acknowledgements: {
            applicantStatus: 'complete',
            reviewStatus: 'pending',
            reviews: [],
            attestations: attestationResponsesAcknowledgements.map((response) => ({ ...response })),
            signatureName: 'Test Applicant',
        },
    },
    // ========================================================
    // =           SUBMITTED AND APPROVED (APIT)              =
    // ========================================================
    {
        id: '5',
        created: moment().subtract(2, 'weeks').format(serverDatetimeFormat),
        submitted: moment().subtract(2, 'days').format(serverDatetimeFormat),
        completed: moment().subtract(1, 'day').format(serverDatetimeFormat),
        types: ['apit'],
        isRenewal: false,
        status: 'approved',
        reviews: [
            {
                reviewerStatus: 'approved',
                reviewDate: moment().subtract(1, 'day').format(serverDatetimeFormat),
                notesForApplicant: null,
            },
        ],
        attestations: attestationResponsesSubmit.map((response) => ({ ...response })),
        paymentCompensated: [],
        personalInformation: {
            applicantStatus: 'complete',
            reviewStatus: 'approved',
            reviews: [
                {
                    reviewerStatus: 'approved',
                    reviewDate: moment().subtract(1, 'day').format(serverDatetimeFormat),
                    notesForApplicant: null,
                },
            ],
            firstName: 'Test',
            middleName: null,
            lastName: 'Applicant',
            suffix: null,
            phone: '+12223334444',
            altPhone: null,
            dob: moment().subtract(50, 'years').format(serverDateFormat),
            ssnLastFour: '1111',
            npi: '1111111111',
            gender: 'male',
            professionalName: 'Test Applicant, PhD.',
            citizenship: 'us',
            placeOfBirth: 'Springfield',
            languages: ['en', 'es'],
            mailingAddress1: '123 Fake St',
            mailingAddress2: 'Apt 1',
            mailingCity: 'Springfield',
            mailingState: 'co',
            mailingZip: '11111',
        },
        licenseHistory: {
            applicantStatus: 'complete',
            reviewStatus: 'approved',
            reviews: [
                {
                    reviewerStatus: 'approved',
                    reviewDate: moment().subtract(1, 'day').format(serverDatetimeFormat),
                    notesForApplicant: null,
                },
            ],
            ePassport: {
                mobilityNumber: '1111111',
                issueDate: moment().subtract(6, 'months').format(serverDateFormat),
            },
            ipc: {
                mobilityNumber: null,
                issueDate: null,
            },
            licenses: [
                {
                    state: 'co',
                    issueDate: moment().subtract(6, 'months').format(serverDateFormat),
                    licenseNumber: '1111111111',
                    status: 'active',
                },
            ],
        },
        education: {
            applicantStatus: 'complete',
            reviewStatus: 'approved',
            reviews: [
                {
                    reviewerStatus: 'approved',
                    reviewDate: moment().subtract(1, 'day').format(serverDatetimeFormat),
                    notesForApplicant: null,
                },
            ],
            nameAtTime: 'Test Applicant',
            institution: 'University of Psychology',
            city: 'Springfield',
            state: 'co',
            degreeType: 'phd',
            program: 'Family, friends, & family friends',
            department: 'Psychology',
            conferredDate: moment().subtract(7, 'months').format(serverDateFormat),
            isCompleted: true,
            accreditingBody: 'University of Psychology',
            accreditingYear: moment().subtract(7, 'months').format('YYYY'),
            isAccreditedByAuthority: true,
            isProgramEquivalent: true,
            accreditingContact: null,
            hasResidence: true,
            transcripts: [
                {
                    filename: 'transcript_1.pdf',
                    sizeBytes: 2500000,
                    downloadUri: '/examples/military-document.pdf',
                },
                {
                    filename: 'transcript_2.pdf',
                    sizeBytes: 1700000,
                    downloadUri: '/examples/military-document.pdf',
                },
            ],
        },
        conductHistory: {
            applicantStatus: 'complete',
            reviewStatus: 'approved',
            reviews: [
                {
                    reviewerStatus: 'approved',
                    reviewDate: moment().subtract(1, 'day').format(serverDatetimeFormat),
                    notesForApplicant: null,
                },
            ],
            attestations: attestationResponsesConduct.map((response) => ({ ...response })),
            convictions: [],
            notes: null,
            documents: [],
        },
        homeState: {
            applicantStatus: 'complete',
            reviewStatus: 'approved',
            reviews: [
                {
                    reviewerStatus: 'approved',
                    reviewDate: moment().subtract(1, 'day').format(serverDatetimeFormat),
                    notesForApplicant: null,
                },
            ],
            applicationTypes: [
                {
                    applicationType: 'apit',
                    state: 'co',
                    startDate: moment().subtract(6, 'months').format(serverDateFormat),
                    isActiveMilitary: false,
                    militaryDocuments: [],
                    attestations: attestationResponsesHomeState.map((response) => ({ ...response })),
                },
            ],
        },
        acknowledgements: {
            applicantStatus: 'complete',
            reviewStatus: 'approved',
            reviews: [
                {
                    reviewerStatus: 'approved',
                    reviewDate: moment().subtract(1, 'day').format(serverDatetimeFormat),
                    notesForApplicant: null,
                },
            ],
            attestations: attestationResponsesAcknowledgements.map((response) => ({ ...response })),
            signatureName: 'Test Applicant',
        },
    },
    // ========================================================
    // =           SUBMITTED AND REJECTED (TAP)               =
    // ========================================================
    {
        id: '6',
        created: moment().subtract(2, 'weeks').format(serverDatetimeFormat),
        submitted: moment().subtract(2, 'days').format(serverDatetimeFormat),
        completed: moment().subtract(1, 'day').format(serverDatetimeFormat),
        types: ['tap'],
        isRenewal: false,
        status: 'rejected',
        reviews: [
            {
                reviewerStatus: 'rejected',
                reviewDate: moment().subtract(1, 'day').format(serverDatetimeFormat),
                notesForApplicant: 'Unable to verify education and license information.',
            },
        ],
        attestations: attestationResponsesSubmit.map((response) => ({ ...response })),
        paymentCompensated: [],
        personalInformation: {
            applicantStatus: 'complete',
            reviewStatus: 'approved',
            reviews: [
                {
                    reviewerStatus: 'approved',
                    reviewDate: moment().subtract(1, 'day').format(serverDatetimeFormat),
                    notesForApplicant: null,
                },
            ],
            firstName: 'Test',
            middleName: null,
            lastName: 'Applicant',
            suffix: null,
            phone: '+12223334444',
            altPhone: null,
            dob: moment().subtract(50, 'years').format(serverDateFormat),
            ssnLastFour: '1111',
            npi: '1111111111',
            gender: 'male',
            professionalName: 'Test Applicant, PhD.',
            citizenship: 'us',
            placeOfBirth: 'Springfield',
            languages: ['en', 'es'],
            mailingAddress1: '123 Fake St',
            mailingAddress2: 'Apt 1',
            mailingCity: 'Springfield',
            mailingState: 'co',
            mailingZip: '11111',
        },
        licenseHistory: {
            applicantStatus: 'complete',
            reviewStatus: 'rejected',
            reviews: [
                {
                    reviewerStatus: 'rejected',
                    reviewDate: moment().subtract(1, 'day').format(serverDatetimeFormat),
                    notesForApplicant: 'Unable to verify license history.',
                },
            ],
            ePassport: {
                mobilityNumber: null,
                issueDate: null,
            },
            ipc: {
                mobilityNumber: '2222222',
                issueDate: moment().subtract(6, 'months').format(serverDateFormat),
            },
            licenses: [
                {
                    state: 'co',
                    issueDate: moment().subtract(6, 'months').format(serverDateFormat),
                    licenseNumber: '1111111111',
                    status: 'active',
                },
            ],
        },
        education: {
            applicantStatus: 'complete',
            reviewStatus: 'rejected',
            reviews: [
                {
                    reviewerStatus: 'rejected',
                    reviewDate: moment().subtract(1, 'day').format(serverDatetimeFormat),
                    notesForApplicant: 'Unable to verify transcripts.',
                },
            ],
            nameAtTime: 'Test Applicant',
            institution: 'University of Psychology',
            city: 'Springfield',
            state: 'co',
            degreeType: 'phd',
            program: 'Family, friends, & family friends',
            department: 'Psychology',
            conferredDate: moment().subtract(7, 'months').format(serverDateFormat),
            isCompleted: true,
            accreditingBody: 'University of Psychology',
            accreditingYear: moment().subtract(7, 'months').format('YYYY'),
            isAccreditedByAuthority: true,
            isProgramEquivalent: true,
            accreditingContact: null,
            hasResidence: true,
            transcripts: [],
        },
        conductHistory: {
            applicantStatus: 'complete',
            reviewStatus: 'approved',
            reviews: [
                {
                    reviewerStatus: 'approved',
                    reviewDate: moment().subtract(1, 'day').format(serverDatetimeFormat),
                    notesForApplicant: null,
                },
            ],
            attestations: attestationResponsesConduct.map((response) => ({ ...response })),
            convictions: [],
            notes: null,
            documents: [],
        },
        homeState: {
            applicantStatus: 'complete',
            reviewStatus: 'approved',
            reviews: [
                {
                    reviewerStatus: 'approved',
                    reviewDate: moment().subtract(1, 'day').format(serverDatetimeFormat),
                    notesForApplicant: null,
                },
            ],
            applicationTypes: [
                {
                    applicationType: 'tap',
                    state: 'co',
                    startDate: moment().subtract(6, 'months').format(serverDateFormat),
                    isActiveMilitary: false,
                    militaryDocuments: [],
                    attestations: attestationResponsesHomeState.map((response) => ({ ...response })),
                },
            ],
        },
        acknowledgements: {
            applicantStatus: 'complete',
            reviewStatus: 'pending',
            reviews: [],
            attestations: attestationResponsesAcknowledgements.map((response) => ({ ...response })),
            signatureName: 'Test Applicant',
        },
    },
];

export const applicantAuthorizations = [
    // This authorization is to allow the renewal workflow.
    {
        id: '1',
        type: 'apit',
        status: 'active',
        issueDate: moment().subtract(11, 'months').format(serverDatetimeFormat),
        renewalDate: null,
        expireDate: moment().add(1, 'month').format(serverDatetimeFormat),
    },
    // If other authorizaion states are needed to test other workflows or to align with specific approved applications, add them below & comment out others as needed.
];

// =========================================================================================
// =                            MOCK PROVIDER OVERLAY HELPERS                              =
// =========================================================================================
const MOCK_PROVIDER_NESTED_COLLECTIONS = ['licenses', 'privileges', 'militaryAffiliations'];

// Compact-specific fields and collections applied to the shared mock practitioner at read time.
// Add values here as a compact's mock data needs to diverge (privilege IDs, etc).
export interface MockProviderCompactOverlay {
    compact?: string;
    licenseType?: string;
    applications?: Array<any>;
    authorizations?: Array<any>;
}

export const mockProviderCompactOverlays: Record<CompactType, MockProviderCompactOverlay> = {
    [CompactType.ASLP]: {
        compact: CompactType.ASLP,
        licenseType: LicenseType.AUDIOLOGIST,
    },
    [CompactType.OT]: {
        compact: CompactType.OT,
        licenseType: LicenseType.OCCUPATIONAL_THERAPY_ASSISTANT,
    },
    [CompactType.COUNSELING]: {
        compact: CompactType.COUNSELING,
        licenseType: LicenseType.PROFESSIONAL_COUNSELOR,
    },
    [CompactType.COSMETOLOGY]: {
        compact: CompactType.COSMETOLOGY,
        licenseType: LicenseType.COSMETOLOGIST,
    },
    [CompactType.SOCIAL_WORK]: {
        compact: CompactType.SOCIAL_WORK,
        licenseType: LicenseType.LICENSED_CLINICAL_SOCIAL_WORKER,
    },
    [CompactType.PSYPACT]: {
        compact: CompactType.PSYPACT,
        licenseType: LicenseType.PSYCHOLOGIST,
        applications: applicantApplications,
        authorizations: applicantAuthorizations,
    },
    [CompactType.DIETITIANS]: {
        compact: CompactType.DIETITIANS,
        licenseType: LicenseType.DIETITIAN,
    },
};

export const applyProviderCompactOverlay = (provider: any, overlay?: MockProviderCompactOverlay | null): any => {
    if (!provider || !overlay) {
        return provider;
    }

    const { applications, authorizations, ...fieldOverlay } = overlay;
    const nextProvider = JSON.parse(JSON.stringify(provider));

    Object.assign(nextProvider, fieldOverlay);

    // Copied so that mutations of a returned provider can't leak into the shared module-level mock arrays
    if (applications) {
        nextProvider.applications = JSON.parse(JSON.stringify(applications));
    }

    if (authorizations) {
        nextProvider.authorizations = JSON.parse(JSON.stringify(authorizations));
    }

    MOCK_PROVIDER_NESTED_COLLECTIONS.forEach((collectionKey) => {
        const collection = nextProvider[collectionKey];

        if (Array.isArray(collection)) {
            nextProvider[collectionKey] = collection.map((item) => {
                const nextItem = { ...item };

                Object.keys(fieldOverlay).forEach((field) => {
                    if (Object.prototype.hasOwnProperty.call(item, field)) {
                        nextItem[field] = fieldOverlay[field];
                    }
                });

                return nextItem;
            });
        }
    });

    return nextProvider;
};

export const getMockProviderForCompact = (provider: any, compactType?: string | null): any =>
    applyProviderCompactOverlay(provider, mockProviderCompactOverlays[compactType as CompactType]);

// =========================================================================================
// =                         EXAMPLE API MOCKS (KEEP THIS LAST)                            =
// =========================================================================================
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
