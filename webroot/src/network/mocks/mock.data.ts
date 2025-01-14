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
                read: true,
                admin: true,
            },
            jurisdictions: {
                al: {
                    actions: {
                        admin: true,
                        write: true,
                    },
                },
                co: {
                    actions: {
                        admin: true,
                        write: true,
                    },
                },
                ky: {
                    actions: {
                        admin: true,
                        write: true,
                    },
                },
            },
        },
        octp: {
            actions: {
                read: true,
                admin: true,
            },
            jurisdictions: {
                ak: {
                    actions: {
                        admin: true,
                        write: true,
                    },
                },
                ar: {
                    actions: {
                        admin: true,
                        write: true,
                    },
                },
                co: {
                    actions: {
                        admin: true,
                        write: true,
                    },
                },
            },
        },
        coun: {
            actions: {
                read: true,
                admin: true,
            },
            jurisdictions: {
                al: {
                    actions: {
                        admin: true,
                        write: true,
                    },
                },
                co: {
                    actions: {
                        admin: true,
                        write: true,
                    },
                },
                ky: {
                    actions: {
                        admin: true,
                        write: true,
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
            compactName: 'aslp',
            compactCommissionFee: {
                feeType: 'FLAT_RATE',
                feeAmount: 3.5
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
    items: [
        {
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
                    licenseJurisdiction: 'al',
                    dateOfExpiration: '2024-08-29',
                    compact: 'aslp',
                    providerId: '1',
                    type: 'privilege',
                    dateOfIssuance: '2022-08-29',
                    dateOfRenewal: '2023-08-29',
                    dateOfUpdate: '2023-08-29',
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
                    status: 'active'
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
                    licenseJurisdiction: 'ma',
                    dateOfExpiration: '2024-08-29',
                    compact: 'aslp',
                    providerId: '1',
                    type: 'privilege',
                    dateOfIssuance: '2023-08-29',
                    dateOfRenewal: '2023-08-29',
                    dateOfUpdate: '2023-08-29',
                    status: 'inactive'
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
            npi: '6944447281',
            homeAddressPostalCode: '',
            givenName: 'Janet',
            homeAddressStreet1: '1640 Riverside Drive',
            militaryWaiver: true,
            emailAddress: 'test@test.com',
            dateOfBirth: '1990-08-29',
            privilegeJurisdictions: [
                'al'
            ],
            type: 'provider',
            ssn: '085-32-1496',
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
                    militaryWaiver: true,
                    dateOfBirth: '1990-08-29',
                    type: 'license-home',
                    dateOfIssuance: '2023-08-29',
                    ssn: '085-32-1496',
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
                    homeAddressPostalCode: '',
                    jurisdiction: 'co',
                    givenName: 'Jane',
                    homeAddressStreet1: '1640 Riverside Drive',
                    militaryWaiver: true,
                    dateOfBirth: '1990-08-29',
                    type: 'license-home',
                    dateOfIssuance: '2023-08-29',
                    ssn: '085-32-1496',
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
                    npi: '6944447281',
                    homeAddressPostalCode: '',
                    jurisdiction: 'ca',
                    givenName: 'Jane',
                    homeAddressStreet1: '1640 Riverside Drive',
                    militaryWaiver: true,
                    dateOfBirth: '1990-08-29',
                    type: 'license-home',
                    dateOfIssuance: '2024-08-29',
                    ssn: '085-32-1496',
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
                    npi: '6944447281',
                    homeAddressPostalCode: '',
                    jurisdiction: 'nv',
                    givenName: 'Jane',
                    homeAddressStreet1: '1640 Riverside Drive',
                    militaryWaiver: true,
                    dateOfBirth: '1990-08-29',
                    type: 'license-home',
                    dateOfIssuance: '2023-08-29',
                    ssn: '085-32-1496',
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
                    npi: '6944447281',
                    homeAddressPostalCode: '',
                    jurisdiction: 'nv',
                    givenName: 'Jane',
                    homeAddressStreet1: '1640 Riverside Drive',
                    militaryWaiver: true,
                    dateOfBirth: '1990-08-29',
                    type: 'license-home',
                    dateOfIssuance: '2024-08-29',
                    ssn: '085-32-1496',
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
            privileges: [
                {
                    licenseJurisdiction: 'al',
                    dateOfExpiration: '2024-08-29',
                    compact: 'aslp',
                    providerId: '1',
                    type: 'privilege',
                    dateOfIssuance: '2023-08-29',
                    dateOfUpdate: '2024-08-29',
                    status: 'active'
                },
                {
                    licenseJurisdiction: 'ak',
                    dateOfExpiration: '2024-08-29',
                    compact: 'aslp',
                    providerId: '1',
                    type: 'privilege',
                    dateOfIssuance: '2023-08-29',
                    dateOfUpdate: '2024-08-29',
                    status: 'active'
                },
                {
                    licenseJurisdiction: 'ar',
                    dateOfExpiration: '2023-08-29',
                    compact: 'aslp',
                    providerId: '1',
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
            militaryWaiver: true,
            dateOfBirth: '1990-08-29',
            privilegeJurisdictions: [
                'al'
            ],
            type: 'provider',
            ssn: '085-32-1496',
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
                    militaryWaiver: true,
                    dateOfBirth: '1990-08-29',
                    type: 'license-home',
                    dateOfIssuance: '2024-08-29',
                    ssn: '085-32-1496',
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
            militaryWaiver: true,
            dateOfBirth: '1975-01-01',
            privilegeJurisdictions: [
                'al'
            ],
            type: 'provider',
            ssn: '748-19-5032',
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
                    militaryWaiver: true,
                    dateOfBirth: '1975-01-01',
                    type: 'license-home',
                    dateOfIssuance: '2024-08-29',
                    ssn: '748-19-5032',
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
            militaryWaiver: true,
            dateOfBirth: '1965-01-01',
            privilegeJurisdictions: [
                'al'
            ],
            type: 'provider',
            ssn: '748-19-5033',
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
                    militaryWaiver: true,
                    dateOfBirth: '1965-01-01',
                    type: 'license-home',
                    dateOfIssuance: '2024-08-29',
                    ssn: '748-19-5033',
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
                        read: true,
                        admin: true,
                    },
                    jurisdictions: {
                        al: {
                            actions: {
                                admin: true,
                                write: true,
                            },
                        },
                        co: {
                            actions: {
                                admin: true,
                                write: true,
                            },
                        },
                        ky: {
                            actions: {
                                admin: true,
                                write: true,
                            },
                        },
                    },
                },
                octp: {
                    actions: {
                        read: true,
                        admin: true,
                    },
                    jurisdictions: {
                        ak: {
                            actions: {
                                admin: true,
                                write: true,
                            },
                        },
                        ar: {
                            actions: {
                                admin: true,
                                write: true,
                            },
                        },
                        co: {
                            actions: {
                                admin: true,
                                write: true,
                            },
                        },
                    },
                },
                coun: {
                    actions: {
                        read: true,
                        admin: true,
                    },
                    jurisdictions: {
                        al: {
                            actions: {
                                admin: true,
                                write: true,
                            },
                        },
                        co: {
                            actions: {
                                admin: true,
                                write: true,
                            },
                        },
                        ky: {
                            actions: {
                                admin: true,
                                write: true,
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
                        read: false,
                        admin: false,
                    },
                    jurisdictions: {
                        al: {
                            actions: {
                                admin: false,
                                write: false,
                            },
                        },
                        co: {
                            actions: {
                                admin: true,
                                write: true,
                            },
                        },
                        ky: {
                            actions: {
                                admin: false,
                                write: true,
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
                        read: false,
                        admin: false,
                    },
                    jurisdictions: {
                        ky: {
                            actions: {
                                admin: true,
                                write: true,
                            },
                        },
                    },
                },
            },
        },
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
