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

export const stateUploadRequestData = {
    upload: {
        url: `https://example.com`,
        fields: {
            field1: 'field1',
            field2: 'field2',
            field3: 'field3',
        },
    },
};

export const licensees = {
    prevLastKey: 'xyz',
    lastKey: 'abc',
    items: [
        {
            providerId: '1',
            compact: 'aslp',
            type: 'license-home',
            licenseType: 'audiologist',
            jurisdiction: 'al',
            dateOfIssuance: '2020-01-01',
            dateOfUpdate: '2024-01-01',
            dateOfExpiration: '2025-01-01',
            dateOfRenewal: '2025-01-01',
            npi: '5512037670',
            givenName: 'Jane',
            middleName: '',
            familyName: 'Doe',
            homeStateStreet1: '1640 Riverside Drive',
            homeStateStreet2: '',
            homeStateCity: 'Hill Valley',
            homeStatePostalCode: '',
            dateOfBirth: '1985-01-01',
            ssn: '748-19-5031',
            status: 'active',
        },
        {
            providerId: '2',
            compact: 'aslp',
            type: 'license-home',
            licenseType: 'audiologist',
            jurisdiction: 'co',
            dateOfIssuance: '2021-01-01',
            dateOfUpdate: '2022-03-01',
            dateOfExpiration: '2025-01-01',
            dateOfRenewal: '2025-01-01',
            npi: '5512037671',
            givenName: 'Tyler',
            middleName: '',
            familyName: 'Durden',
            homeStateStreet1: '1045 Pearl St',
            homeStateStreet2: '',
            homeStateCity: 'Boulder',
            homeStatePostalCode: '80302',
            dateOfBirth: '1975-01-01',
            ssn: '748-19-5032',
            status: 'inactive',
        },
        {
            providerId: '3',
            compact: 'aslp',
            type: 'license-home',
            licenseType: 'audiologist',
            jurisdiction: 'co',
            dateOfIssuance: '2018-01-01',
            dateOfUpdate: '2024-06-01',
            dateOfExpiration: '2025-01-01',
            dateOfRenewal: '2025-01-01',
            npi: '5512037672',
            givenName: 'Marla',
            middleName: '',
            familyName: 'Singer',
            homeStateStreet1: '1495 Canyon Blvd',
            homeStateStreet2: '',
            homeStateCity: 'Boulder',
            homeStatePostalCode: '80301',
            dateOfBirth: '1965-01-01',
            ssn: '748-19-5033',
            status: 'active',
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
