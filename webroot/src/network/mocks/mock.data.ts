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
    // count: 1500,
    lastKey: 'abc',
    items: [
        {
            id: '1',
            compact: 'aslp',
            type: 'license-home',
            license_type: 'audiologist',
            jurisdiction: 'al',
            date_of_issuance: '2020-01-01',
            date_of_update: '2024-01-01',
            date_of_expiration: '2025-01-01',
            date_of_renewal: '2025-01-01',
            npi: '5512037670',
            given_name: 'Jane',
            middle_name: '',
            family_name: 'Doe',
            home_state_street_1: '1640 Riverside Drive',
            home_state_street_2: '',
            home_state_city: 'Hill Valley',
            home_state_postal_code: '',
            date_of_birth: '1985-01-01',
            ssn: '748-19-5031',
            status: 'active',
        },
        {
            id: '2',
            compact: 'aslp',
            type: 'license-home',
            license_type: 'audiologist',
            jurisdiction: 'co',
            date_of_issuance: '2021-01-01',
            date_of_update: '2022-03-01',
            date_of_expiration: '2025-01-01',
            date_of_renewal: '2025-01-01',
            npi: '5512037671',
            given_name: 'Tyler',
            middle_name: '',
            family_name: 'Durden',
            home_state_street_1: '1045 Pearl St',
            home_state_street_2: '',
            home_state_city: 'Boulder',
            home_state_postal_code: '80302',
            date_of_birth: '1975-01-01',
            ssn: '748-19-5032',
            status: 'inactive',
        },
        {
            id: '3',
            compact: 'aslp',
            type: 'license-home',
            license_type: 'audiologist',
            jurisdiction: 'co',
            date_of_issuance: '2018-01-01',
            date_of_update: '2024-06-01',
            date_of_expiration: '2025-01-01',
            date_of_renewal: '2025-01-01',
            npi: '5512037672',
            given_name: 'Marla',
            middle_name: '',
            family_name: 'Singer',
            home_state_street_1: '1495 Canyon Blvd',
            home_state_street_2: '',
            home_state_city: 'Boulder',
            home_state_postal_code: '80301',
            date_of_birth: '1965-01-01',
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
