//
//  mock.data.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/6/20.
//

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
        aslp: {
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
        octp: {
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
            compactAbbr: 'aslp',
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
            type: 'compact'
        },
        {
            jurisdictionName: 'kentucky',
            postalAbbreviation: 'ky',
            compact: 'aslp',
            jurisdictionFee: 100,
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
            compact: 'aslp',
            jurisdictionFee: 100,
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
            compact: 'aslp',
            jurisdictionFee: 100,
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
            compact: 'aslp',
            jurisdictionFee: 100,
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
            compact: 'aslp',
            jurisdictionFee: 100,
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
            compact: 'aslp',
            jurisdictionFee: 100,
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
            compact: 'aslp',
            jurisdictionFee: 100,
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
            compact: 'aslp',
            jurisdictionFee: 100,
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
            compact: 'aslp',
            jurisdictionFee: 100,
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
            compact: 'aslp',
            jurisdictionFee: 100,
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
            compact: 'aslp',
            jurisdictionFee: 100,
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
            compact: 'aslp',
            jurisdictionFee: 100,
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
            compact: 'aslp',
            jurisdictionFee: 100,
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
            compact: 'aslp',
            jurisdictionFee: 100,
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
                compact: 'aslp',
                providerId: '1',
                jurisdiction: 'co',
                type: 'homeJurisdictionSelection',
                dateOfUpdate: '2025-02-19'
            },
            privileges: [
                {
                    licenseJurisdiction: 'al',
                    dateOfExpiration: '2025-08-29',
                    compact: 'aslp',
                    providerId: '1',
                    type: 'privilege',
                    dateOfIssuance: '2022-08-29',
                    dateOfRenewal: '2024-08-29',
                    dateOfUpdate: '2024-08-29',
                    status: 'inactive'
                },
                {
                    licenseJurisdiction: 'ak',
                    dateOfExpiration: '2025-08-29',
                    compact: 'aslp',
                    providerId: '1',
                    type: 'privilege',
                    dateOfIssuance: '2023-08-29',
                    dateOfRenewal: '2024-08-29',
                    dateOfUpdate: '2024-08-29',
                    status: 'active',
                    history: [{
                        type: 'privilegeUpdate',
                        updateType: 'renewal',
                        previous: {
                            compactTransactionId: '123',
                            dateOfIssuance: '2022-08-29',
                            dateOfRenewal: '2023-08-29',
                            dateOfUpdate: '2023-08-29',
                        },
                        updatedValues: {
                            compactTransactionId: '124',
                            dateOfIssuance: '2022-08-29',
                            dateOfRenewal: '2024-08-29',
                        }
                    }]
                },
                {
                    licenseJurisdiction: 'ar',
                    dateOfExpiration: '2026-08-29',
                    compact: 'aslp',
                    providerId: '1',
                    type: 'privilege',
                    dateOfIssuance: '2023-08-29',
                    dateOfRenewal: '2024-08-29',
                    dateOfUpdate: '2024-08-29',
                    status: 'active'
                },
                {
                    licenseJurisdiction: 'ma',
                    dateOfExpiration: '2026-08-29',
                    compact: 'aslp',
                    providerId: '1',
                    type: 'privilege',
                    dateOfIssuance: '2023-08-29',
                    dateOfRenewal: '2024-08-29',
                    dateOfUpdate: '2024-08-29',
                    status: 'active'
                },
                {
                    licenseJurisdiction: 'me',
                    dateOfExpiration: '2020-08-29',
                    compact: 'aslp',
                    providerId: '1',
                    type: 'privilege',
                    dateOfIssuance: '2019-08-29',
                    dateOfRenewal: '2024-08-29',
                    dateOfUpdate: '2024-08-29',
                    status: 'inactive'
                }
            ],
            licenseJurisdiction: 'co',
            compact: 'aslp',
            homeAddressStreet2: '',
            militaryAffiliations: [{
                affiliationType: 'militaryMember',
                compact: 'aslp',
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
            licenseType: 'audiologist',
            licenses: [
                {
                    compact: 'aslp',
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
                    licenseType: 'audiologist',
                    dateOfExpiration: '2025-08-29',
                    homeAddressState: 'co',
                    providerId: '1',
                    dateOfRenewal: '2024-08-29',
                    familyName: 'Doe',
                    homeAddressCity: 'Riverside',
                    middleName: '',
                    dateOfUpdate: '2024-08-29',
                    status: 'active'
                },
                {
                    compact: 'aslp',
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
                    licenseType: 'audiologist',
                    dateOfExpiration: '2024-08-29',
                    homeAddressState: 'co',
                    providerId: '1',
                    dateOfRenewal: '2023-08-29',
                    familyName: 'Doe',
                    homeAddressCity: 'Riverside',
                    middleName: '',
                    dateOfUpdate: '2023-08-29',
                    status: 'inactive'
                },
                {
                    compact: 'aslp',
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
                    licenseType: 'audiologist',
                    dateOfExpiration: '2024-08-29',
                    homeAddressState: 'co',
                    providerId: '1',
                    dateOfRenewal: '2024-08-29',
                    familyName: 'Doe',
                    homeAddressCity: 'Riverside',
                    middleName: '',
                    dateOfUpdate: '2024-08-29',
                    status: 'active'
                },
                {
                    compact: 'aslp',
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
                    licenseType: 'audiologist',
                    dateOfExpiration: '2024-08-29',
                    homeAddressState: 'co',
                    providerId: '1',
                    dateOfRenewal: '2024-08-29',
                    familyName: 'Doe',
                    homeAddressCity: 'Riverside',
                    middleName: '',
                    dateOfUpdate: '2024-08-29',
                    status: 'inactive'
                },
                {
                    compact: 'aslp',
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
                    licenseType: 'audiologist',
                    dateOfExpiration: '2023-08-29',
                    homeAddressState: 'co',
                    providerId: '1',
                    dateOfRenewal: '2023-08-29',
                    familyName: 'Doe',
                    homeAddressCity: 'Riverside',
                    middleName: '',
                    dateOfUpdate: '2023-08-29',
                    status: 'inactive'
                }
            ],
            dateOfExpiration: '2024-08-29',
            homeAddressState: 'co',
            providerId: '1',
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
                compact: 'aslp',
                providerId: '2',
                jurisdiction: 'co',
                type: 'homeJurisdictionSelection',
                dateOfUpdate: '2025-02-19'
            },
            privileges: [
                {
                    licenseJurisdiction: 'al',
                    dateOfExpiration: '2024-08-29',
                    compact: 'aslp',
                    providerId: '2',
                    type: 'privilege',
                    dateOfIssuance: '2024-08-29',
                    dateOfUpdate: '2024-08-29',
                    status: 'active'
                }
            ],
            licenseJurisdiction: 'co',
            compact: 'aslp',
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
            licenseType: 'audiologist',
            licenses: [
                {
                    compact: 'aslp',
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
                    licenseType: 'audiologist',
                    dateOfExpiration: '2024-08-29',
                    homeAddressState: 'co',
                    providerId: '2',
                    dateOfRenewal: '2024-08-29',
                    familyName: 'Durden',
                    homeAddressCity: 'Boulder',
                    middleName: '',
                    dateOfUpdate: '2024-08-29',
                    status: 'inactive'
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
                compact: 'aslp',
                providerId: '3',
                jurisdiction: 'co',
                type: 'homeJurisdictionSelection',
                dateOfUpdate: '2025-02-19'
            },
            privileges: [
                {
                    licenseJurisdiction: 'al',
                    dateOfExpiration: '2024-08-29',
                    compact: 'aslp',
                    providerId: '3',
                    type: 'privilege',
                    dateOfIssuance: '2024-08-29',
                    dateOfUpdate: '2024-08-29',
                    status: 'active'
                }
            ],
            licenseJurisdiction: 'co',
            compact: 'aslp',
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
            licenseType: 'audiologist',
            licenses: [
                {
                    compact: 'aslp',
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
                    licenseType: 'audiologist',
                    dateOfExpiration: '2024-08-29',
                    homeAddressState: 'co',
                    providerId: '3',
                    dateOfRenewal: '2024-08-29',
                    familyName: 'Singer',
                    homeAddressCity: 'Boulder',
                    middleName: '',
                    dateOfUpdate: '2024-08-29',
                    status: 'active'
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
                compact: 'aslp',
                providerId: '4',
                jurisdiction: 'co',
                type: 'homeJurisdictionSelection',
                dateOfUpdate: '2025-02-19'
            },
            privileges: [
                {
                    licenseJurisdiction: 'al',
                    dateOfExpiration: '2024-08-29',
                    compact: 'aslp',
                    providerId: '4',
                    type: 'privilege',
                    dateOfIssuance: '2023-08-29',
                    dateOfUpdate: '2024-08-29',
                    status: 'active'
                },
                {
                    licenseJurisdiction: 'ak',
                    dateOfExpiration: '2024-08-29',
                    compact: 'aslp',
                    providerId: '4',
                    type: 'privilege',
                    dateOfIssuance: '2023-08-29',
                    dateOfUpdate: '2024-08-29',
                    status: 'active'
                },
                {
                    licenseJurisdiction: 'ar',
                    dateOfExpiration: '2023-08-29',
                    compact: 'aslp',
                    providerId: '4',
                    type: 'privilege',
                    dateOfIssuance: '2023-08-29',
                    dateOfUpdate: '2024-08-29',
                    status: 'active'
                }
            ],
            licenseJurisdiction: 'co',
            compact: 'aslp',
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
            licenseType: 'audiologist',
            licenses: [
                {
                    compact: 'aslp',
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
                    licenseType: 'audiologist',
                    dateOfExpiration: '2024-08-29',
                    homeAddressState: 'co',
                    providerId: '4',
                    dateOfRenewal: '2024-08-29',
                    familyName: 'Doe',
                    homeAddressCity: 'Riverside',
                    middleName: '',
                    dateOfUpdate: '2024-08-29',
                    status: 'active'
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
                aslp: {
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
                octp: {
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
                aslp: {
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
                aslp: {
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
    compact: 'aslp',
    type: 'test-type',
    displayName: 'Test Attestation',
    text: 'Test Text',
    version: '1',
    locale: 'en',
    required: true,
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
