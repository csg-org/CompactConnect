//
//  License.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/8/2024.
//
import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';
import { serverDateFormat, displayDateFormat } from '@/app.config';
import {
    License,
    LicenseType,
    LicenseStatus,
    LicenseSerializer
} from '@models/License/License.model';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { State } from '@models/State/State.model';
import { Address } from '@models/Address/Address.model';
import { LicenseHistoryItem } from '@models/LicenseHistoryItem/LicenseHistoryItem.model';
import i18n from '@/i18n';
import moment from 'moment';

chai.use(chaiMatchPattern);

const { expect } = chai;

describe('License model', () => {
    before(() => {
        const { tm: $tm, t: $t } = i18n.global;

        (window as any).Vue = {
            config: {
                globalProperties: {
                    $tm,
                    $t,
                }
            }
        };
        i18n.global.locale = 'en';
    });
    it('should create a License with expected defaults', () => {
        const license = new License();

        // Test field values
        expect(license).to.be.an.instanceof(License);
        expect(license.id).to.equal(null);
        expect(license.compact).to.equal(null);
        expect(license.isPrivilege).to.equal(false);
        expect(license.licenseeId).to.equal(null);
        expect(license.issueState).to.be.an.instanceof(State);
        expect(license.issueDate).to.equal(null);
        expect(license.renewalDate).to.equal(null);
        expect(license.expireDate).to.equal(null);
        expect(license.npi).to.equal(null);
        expect(license.licenseNumber).to.equal(null);
        expect(license.privilegeId).to.equal(null);
        expect(license.mailingAddress).to.be.an.instanceof(Address);
        expect(license.licenseType).to.equal(null);
        expect(license.history).to.matchPattern([]);
        expect(license.status).to.equal(LicenseStatus.INACTIVE);

        // Test methods
        expect(license.issueDateDisplay()).to.equal('');
        expect(license.renewalDateDisplay()).to.equal('');
        expect(license.expireDateDisplay()).to.equal('');
        expect(license.isExpired()).to.equal(false);
        expect(license.licenseTypeAbbreviation()).to.equal('');
        expect(license.displayName()).to.equal('Unknown');
    });
    it('should create a License with specific values', () => {
        const data = {
            id: 'test-id',
            compact: new Compact(),
            isPrivilege: true,
            licenseeId: 'test-licensee-id',
            issueState: new State(),
            isHomeState: true,
            issueDate: 'test-issueDate',
            renewalDate: 'test-renewalDate',
            expireDate: 'test-expireDate',
            licenseNumber: 'test-license-number',
            privilegeId: 'privilegeId',
            mailingAddress: new Address(),
            npi: 'test-npi',
            licenseType: LicenseType.AUDIOLOGIST,
            status: LicenseStatus.ACTIVE,
            history: [new LicenseHistoryItem()]
        };
        const license = new License(data);

        // Test field values
        expect(license).to.be.an.instanceof(License);
        expect(license.id).to.equal(data.id);
        expect(license.compact).to.be.an.instanceof(Compact);
        expect(license.isPrivilege).to.equal(data.isPrivilege);
        expect(license.licenseeId).to.equal(data.licenseeId);
        expect(license.issueState).to.be.an.instanceof(State);
        expect(license.issueDate).to.equal(data.issueDate);
        expect(license.renewalDate).to.equal(data.renewalDate);
        expect(license.expireDate).to.equal(data.expireDate);
        expect(license.mailingAddress).to.be.an.instanceof(Address);
        expect(license.npi).to.equal(data.npi);
        expect(license.licenseNumber).to.equal(data.licenseNumber);
        expect(license.privilegeId).to.equal(data.privilegeId);
        expect(license.licenseType).to.equal(data.licenseType);
        expect(license.status).to.equal(data.status);
        expect(license.history[0]).to.be.an.instanceof(LicenseHistoryItem);

        // Test methods
        expect(license.issueDateDisplay()).to.equal('Invalid date');
        expect(license.renewalDateDisplay()).to.equal('Invalid date');
        expect(license.expireDateDisplay()).to.equal('Invalid date');
        expect(license.isExpired()).to.equal(false);
        expect(license.licenseTypeAbbreviation()).to.equal('AUD');
        expect(license.displayName()).to.equal('Unknown - AUD');
        expect(license.isDeactivated()).to.equal(false);
    });
    it('should create a License with specific values through serializer', () => {
        const data = {
            compact: CompactType.ASLP,
            type: 'License',
            providerId: 'test-provider-id',
            jurisdiction: 'al',
            dateOfIssuance: moment().format(serverDateFormat),
            dateOfRenewal: moment().format(serverDateFormat),
            dateOfExpiration: moment().subtract(1, 'day').format(serverDateFormat),
            npi: 'npi',
            licenseNumber: 'licenseNumber',
            homeAddressStreet1: 'test-street1',
            homeAddressStreet2: 'test-street2',
            homeAddressCity: 'test-city',
            homeAddressState: 'co',
            homeAddressPostalCode: 'test-zip',
            licenseType: LicenseType.AUDIOLOGIST,
            status: LicenseStatus.ACTIVE,
            history: []
        };
        const license = LicenseSerializer.fromServer(data);

        // Test field values
        expect(license).to.be.an.instanceof(License);
        expect(license.id).to.equal('test-provider-id-al-audiologist');
        expect(license.compact).to.be.an.instanceof(Compact);
        expect(license.isPrivilege).to.equal(false);
        expect(license.licenseeId).to.equal(data.providerId);
        expect(license.issueState).to.be.an.instanceof(State);
        expect(license.mailingAddress).to.be.an.instanceof(Address);
        expect(license.issueState.abbrev).to.equal(data.jurisdiction);
        expect(license.issueDate).to.equal(data.dateOfIssuance);
        expect(license.renewalDate).to.equal(data.dateOfRenewal);
        expect(license.expireDate).to.equal(data.dateOfExpiration);
        expect(license.licenseType).to.equal(data.licenseType);
        expect(license.status).to.equal(data.status);
        expect(license.displayName()).to.equal('Alabama - AUD');
        expect(license.status).to.equal(data.status);

        // Test methods
        expect(license.issueDateDisplay()).to.equal(
            moment(data.dateOfIssuance, serverDateFormat).format(displayDateFormat)
        );
        expect(license.renewalDateDisplay()).to.equal(
            moment(data.dateOfRenewal, serverDateFormat).format(displayDateFormat)
        );
        expect(license.expireDateDisplay()).to.equal(
            moment(data.dateOfExpiration, serverDateFormat).format(displayDateFormat)
        );
        expect(license.isExpired()).to.equal(true);
        expect(license.licenseTypeAbbreviation()).to.equal('AUD');
    });
    it('should create a privilege with specific values through serializer', () => {
        const data = {
            dateOfUpdate: '2025-03-26T16:19:09+00:00',
            type: 'privilege',
            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
            compact: 'octp',
            jurisdiction: 'ne',
            licenseJurisdiction: 'ky',
            licenseType: 'occupational therapy assistant',
            dateOfIssuance: '2022-03-19T21:51:26+00:00',
            dateOfRenewal: '2025-03-26T16:19:09+00:00',
            dateOfExpiration: '2025-02-12',
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
                    dateOfUpdate: '2025-02-13',
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
                    dateOfUpdate: '2025-03-01T16:19:09+00:00',
                    type: 'privilegeUpdate',
                    updateType: 'renewal',
                    providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                    compact: 'octp',
                    jurisdiction: 'ne',
                    licenseType: 'occupational therapy assistant',
                    previous: {
                        dateOfIssuance: '2022-03-19T21:51:26+00:00',
                        dateOfRenewal: '2025-03-01T16:19:09+00:00',
                        dateOfExpiration: '2025-02-12',
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
        };
        const license = LicenseSerializer.fromServer(data);

        // Test field values
        expect(license).to.be.an.instanceof(License);
        expect(license.id).to.equal('aa2e057d-6972-4a68-a55d-aad1c3d05278-ne-occupational therapy assistant');
        expect(license.compact).to.be.an.instanceof(Compact);
        expect(license.isPrivilege).to.equal(true);
        expect(license.licenseeId).to.equal(data.providerId);
        expect(license.issueState).to.be.an.instanceof(State);
        expect(license.mailingAddress).to.be.an.instanceof(Address);
        expect(license.history[0]).to.be.an.instanceof(LicenseHistoryItem);
        expect(license.issueState.abbrev).to.equal(data.jurisdiction);
        expect(license.issueDate).to.equal(data.dateOfIssuance);
        expect(license.renewalDate).to.equal(data.dateOfRenewal);
        expect(license.expireDate).to.equal(data.dateOfExpiration);
        expect(license.licenseType).to.equal(data.licenseType);
        expect(license.status).to.equal(data.status);
        expect(license.privilegeId).to.equal(data.privilegeId);
        expect(license.displayName()).to.equal('Nebraska - OTA');
        expect(license.status).to.equal(data.status);

        // Test methods
        expect(license.issueDateDisplay()).to.equal(
            moment(data.dateOfIssuance, serverDateFormat).format(displayDateFormat)
        );
        expect(license.renewalDateDisplay()).to.equal(
            moment(data.dateOfRenewal, serverDateFormat).format(displayDateFormat)
        );
        expect(license.expireDateDisplay()).to.equal(
            moment(data.dateOfExpiration, serverDateFormat).format(displayDateFormat)
        );
        expect(license.isExpired()).to.equal(true);
        expect(license.licenseTypeAbbreviation()).to.equal('OTA');
        expect(license.historyWithFabricatedEvents().length).to.equal(6);
        expect(license.historyWithFabricatedEvents()[0].updateType).to.equal('purchased');
        expect(license.historyWithFabricatedEvents()[1].updateType).to.equal('deactivation');
        expect(license.historyWithFabricatedEvents()[2].updateType).to.equal('renewal');
        expect(license.historyWithFabricatedEvents()[3].updateType).to.equal('expired');
        expect(license.historyWithFabricatedEvents()[4].updateType).to.equal('renewal');
        expect(license.historyWithFabricatedEvents()[5].updateType).to.equal('expired');
        expect(license.isDeactivated()).to.equal(false);
    });
    it('should create a privilege with specific values through serializer(deactivated)', () => {
        const data = {
            dateOfUpdate: '2025-03-26T16:19:09+00:00',
            type: 'privilege',
            providerId: 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
            compact: 'octp',
            jurisdiction: 'ne',
            licenseJurisdiction: 'ky',
            licenseType: 'occupational therapy assistant',
            dateOfIssuance: '2022-03-19T21:51:26+00:00',
            dateOfRenewal: '2025-03-26T16:19:09+00:00',
            dateOfExpiration: '2025-02-12',
            compactTransactionId: '120060088901',
            attestations: [],
            privilegeId: 'OTA-NE-10',
            persistedStatus: 'active',
            status: 'inactive',
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
                }
            ]
        };
        const license = LicenseSerializer.fromServer(data);

        // Test field values
        expect(license.isDeactivated()).to.equal(true);
    });
});
