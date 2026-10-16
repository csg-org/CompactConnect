export const SAMPLE_INGEST_SUCCESS_RECORD = {
    'pk': {
        'S': 'COMPACT#octp#JURISDICTION#oh'
    },
    'sk': {
        'S': 'TYPE#license.ingest#TIME#1731618012#EVENT#08ff0b63-4492-89c6-4372-3e95f03e1234'
    },
    'compact': {
        'S': 'octp'
    },
    'jurisdiction': {
        'S': 'oh'
    },
    'licenseType': {
        'S': 'occupational therapist'
    },
    'status': {
        'S': 'active'
    },
    'dateOfIssuance': {
        'S': '2023-01-01'
    },
    'dateOfRenewal': {
        'S': '2024-01-01'
    },
    'dateOfExpiration': {
        'S': '2025-01-01'
    },
    'eventTime': {
        'S': '2024-11-14T21:00:12.382000+00:00'
    }
};

export const SAMPLE_INGEST_FAILURE_ERROR_RECORD = {
    'pk': {
        'S': 'COMPACT#octp#JURISDICTION#oh'
    },
    'sk': {
        'S': 'TYPE#license.ingest-failure#TIME#1731618012#EVENT#08ff0b63-4492-89c6-4372-3e95f03ee984'
    },
    'compact': {
        'S': 'octp'
    },
    'errors': {
        'L': [
            {
                'S': '\'utf-8\' codec can\'t decode byte 0x83 in position 0: invalid start byte'
            }
        ]
    },
    'eventExpiry': {
        'N': '1739394328'
    },
    'eventTime': {
        'S': '2024-11-14T21:00:12.382000+00:00'
    },
    'eventType': {
        'S': 'license.ingest-failure'
    },
    'jurisdiction': {
        'S': 'oh'
    }
};

export const SAMPLE_UNMARSHALLED_INGEST_FAILURE_ERROR_RECORD = {
    'pk': 'COMPACT#octp#JURISDICTION#oh',
    'sk': 'TYPE#license.ingest-failure#TIME#1731618012#EVENT#08ff0b63-4492-89c6-4372-3e95f03ee984',
    'compact': 'octp',
    'errors': [ '\'utf-8\' codec can\'t decode byte 0x83 in position 0: invalid start byte' ],
    'eventExpiry': '1739394328',
    'eventTime': '2024-11-14T21:00:12.382000+00:00',
    'eventType': 'license.ingest-failure',
    'jurisdiction': 'oh'
};

export const SAMPLE_VALIDATION_ERROR_RECORD = {
    'pk': {
        'S': 'COMPACT#octp#JURISDICTION#oh'
    },
    'sk': {
        'S': 'TYPE#license.validation-error#TIME#1730263675#EVENT#182d8d8b-7fee-6e0c-2e3c-1189a47d5a0c'
    },
    'eventType': {
        'S': 'license.validation-error'
    },
    'eventTime': {
        'S': '2024-10-30T04:47:55.843000+00:00'
    },
    'compact': {
        'S': 'octp'
    },
    'jurisdiction': {
        'S': 'oh'
    },
    'errors': {
        'M': {
            'dateOfRenewal': {
                'L': [
                    {
                        'S': 'Not a valid date.'
                    }
                ]
            }
        }
    },
    'recordNumber': {
        'N': '5'
    },
    'validData': {
        'M': {
            'dateOfExpiration': {
                'S': '2024-06-30'
            },
            'dateOfIssuance': {
                'S': '2024-06-30'
            },
            'familyName': {
                'S': 'Carreño Quiñones'
            },
            'givenName': {
                'S': 'María'
            },
            'licenseType': {
                'S': 'occupational therapist'
            },
            'middleName': {
                'S': 'José'
            },
            'status': {
                'S': 'active'
            }
        }
    }
};

export const SAMPLE_SORTABLE_VALIDATION_ERROR_RECORDS = [
    {
        'pk': 'COMPACT#octp#JURISDICTION#oh',
        'sk': 'TYPE#license.validation-error#TIME#1730263675#EVENT#182d8d8b-7fee-6e0c-2e3c-1189a47d5a0c',
        'eventType': 'license.validation-error',
        'eventTime': '2024-10-30T04:47:55.843000+00:00',
        'compact': 'octp',
        'jurisdiction': 'oh',
        'errors': {
            'dateOfRenewal': [
                'Row 5, 4:47'
            ]
        },
        'recordNumber': 5,
        'validData': {
            'dateOfExpiration': '2024-06-30',
            'dateOfIssuance': '2024-06-30',
            'familyName': 'Carreño Quiñones',
            'givenName': 'María',
            'licenseType': 'occupational therapist',
            'middleName': 'José',
            'status': 'active'
        }
    },
    {
        'pk': 'COMPACT#octp#JURISDICTION#oh',
        'sk': 'TYPE#license.validation-error#TIME#1730263675#EVENT#182d8d8b-7fee-6e0c-2e3c-1189a47d5a0c',
        'eventType': 'license.validation-error',
        'eventTime': '2024-10-30T05:47:55.843000+00:00',
        'compact': 'octp',
        'jurisdiction': 'oh',
        'errors': {
            'dateOfRenewal': [
                'Row 4, 5:47'
            ]
        },
        'recordNumber': 4,
        'validData': {
            'dateOfExpiration': '2024-06-30',
            'dateOfIssuance': '2024-06-30',
            'familyName': 'Carreño Quiñones',
            'givenName': 'María',
            'licenseType': 'occupational therapist',
            'middleName': 'José',
            'status': 'active'
        }
    },
    {
        'pk': 'COMPACT#octp#JURISDICTION#oh',
        'sk': 'TYPE#license.validation-error#TIME#1730263675#EVENT#182d8d8b-7fee-6e0c-2e3c-1189a47d5a0c',
        'eventType': 'license.validation-error',
        'eventTime': '2024-10-30T05:47:55.843000+00:00',
        'compact': 'octp',
        'jurisdiction': 'oh',
        'errors': {
            'dateOfRenewal': [
                'Row 5, 5:47'
            ]
        },
        'recordNumber': 5,
        'validData': {
            'dateOfExpiration': '2024-06-30',
            'dateOfIssuance': '2024-06-30',
            'familyName': 'Carreño Quiñones',
            'givenName': 'María',
            'licenseType': 'occupational therapist',
            'middleName': 'José',
            'status': 'active'
        }
    }
];

export const SAMPLE_UNMARSHALLED_VALIDATION_ERROR_RECORD = {
    'pk': 'COMPACT#octp#JURISDICTION#oh',
    'sk': 'TYPE#license.validation-error#TIME#1730263675#EVENT#182d8d8b-7fee-6e0c-2e3c-1189a47d5a0c',
    'eventType': 'license.validation-error',
    'eventTime': '2024-10-30T04:47:55.843000+00:00',
    'compact': 'octp',
    'jurisdiction': 'oh',
    'errors': {
        'dateOfRenewal': [
            'Not a valid date.'
        ]
    },
    'recordNumber': 5,
    'validData': {
        'dateOfExpiration': '2024-06-30',
        'dateOfIssuance': '2024-06-30',
        'familyName': 'Carreño Quiñones',
        'givenName': 'María',
        'licenseType': 'occupational therapist',
        'middleName': 'José',
        'status': 'active'
    }
};

export const SAMPLE_JURISDICTION_CONFIGURATION = {
    'pk': {
        'S': 'aslp#CONFIGURATION'
    },
    'sk': {
        'S': 'aslp#JURISDICTION#oh'
    },
    'compact': {
        'S': 'aslp'
    },
    'dateOfUpdate': {
        'S': '2024-11-14'
    },
    'jurisdictionAdverseActionsNotificationEmails': {
        'L': []
    },
    'privilegeFees': {
        'L': [
            {
                'M': {
                    'licenseTypeAbbreviation': {
                        'S': 'aud'
                    },
                    'amount': {
                        'N': '100'
                    }
                }
            },
            {
                'M': {
                    'licenseTypeAbbreviation': {
                        'S': 'slp'
                    },
                    'amount': {
                        'N': '100'
                    }
                }
            }
        ]
    },
    'jurisdictionName': {
        'S': 'Ohio'
    },
    'jurisdictionOperationsTeamEmails': {
        'L': [
            {
                'S': 'justin@inspiringapps.com'
            }
        ]
    },
    'jurisdictionSummaryReportNotificationEmails': {
        'L': []
    },
    'jurisprudenceRequirements': {
        'M': {
            'required': {
                'BOOL': true
            }
        }
    },
    'postalAbbreviation': {
        'S': 'oh'
    },
    'type': {
        'S': 'jurisdiction'
    }
};

export const SAMPLE_UNMARSHALLED_JURISDICTION_CONFIGURATION = {
    'pk': 'aslp#CONFIGURATION',
    'sk': 'aslp#JURISDICTION#oh',
    'compact': 'aslp',
    'dateOfUpdate': '2024-11-14',
    'jurisdictionAdverseActionsNotificationEmails': [],
    'privilegeFees': [
        {
            'licenseTypeAbbreviation': 'aud',
            'amount': '100'
        },
        {
            'licenseTypeAbbreviation': 'slp',
            'amount': '100'
        }
    ],
    'jurisdictionName': 'Ohio',
    'jurisdictionOperationsTeamEmails': [ 'justin@inspiringapps.com' ],
    'jurisdictionSummaryReportNotificationEmails': [],
    'jurisprudenceRequirements': {
        'required': true
    },
    'postalAbbreviation': 'oh',
    'type': 'jurisdiction',
};

export const SAMPLE_COMPACT_CONFIGURATION = {
    'pk': { 'S': 'aslp#CONFIGURATION' },
    'sk': { 'S': 'aslp#CONFIGURATION' },
    'compactAdverseActionsNotificationEmails': { 'L': [{ 'S': 'adverse@example.com' }]},
    'compactCommissionFee': {
        'M': {
            'feeAmount': { 'N': '3.5' },
            'feeType': { 'S': 'FLAT_RATE' }
        }
    },
    'compactAbbr': { 'S': 'aslp' },
    'compactName': { 'S': 'Audiology and Speech Language Pathology' },
    'compactOperationsTeamEmails': { 'L': [{ 'S': 'compact-ops@example.com' }]},
    'compactSummaryReportNotificationEmails': { 'L': [{ 'S': 'summary@example.com' }]},
    'dateOfUpdate': { 'S': '2024-12-10T19:27:28+00:00' },
    'type': { 'S': 'compact' }
};

export const SAMPLE_UNMARSHALLED_COMPACT_CONFIGURATION = {
    'pk': 'aslp#CONFIGURATION',
    'sk': 'aslp#CONFIGURATION',
    'compactAdverseActionsNotificationEmails': ['adverse@example.com'],
    'compactCommissionFee': {
        'feeAmount': 3.5,
        'feeType': 'FLAT_RATE'
    },
    'compactAbbr': 'aslp',
    'compactName': 'Audiology and Speech Language Pathology',
    'compactOperationsTeamEmails': ['compact-ops@example.com'],
    'compactSummaryReportNotificationEmails': ['summary@example.com'],
    'dateOfUpdate': '2024-12-10T19:27:28+00:00',
    'type': 'compact'
};
