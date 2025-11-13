//
//  License.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/8/2024.
//
import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';
import { serverDateFormat, displayDateFormat, serverDatetimeFormat } from '@/app.config';
import {
    License,
    LicenseType,
    LicenseStatus,
    EligibilityStatus,
    LicenseSerializer
} from '@models/License/License.model';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { State } from '@models/State/State.model';
import { Address } from '@models/Address/Address.model';
import { LicenseHistoryItem } from '@models/LicenseHistoryItem/LicenseHistoryItem.model';
import { AdverseAction } from '@models/AdverseAction/AdverseAction.model';
import { Investigation } from '@models/Investigation/Investigation.model';
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
        expect(license.activeFromDate).to.equal(null);
        expect(license.renewalDate).to.equal(null);
        expect(license.expireDate).to.equal(null);
        expect(license.npi).to.equal(null);
        expect(license.licenseNumber).to.equal(null);
        expect(license.privilegeId).to.equal(null);
        expect(license.mailingAddress).to.be.an.instanceof(Address);
        expect(license.licenseType).to.equal(null);
        expect(license.history).to.matchPattern([]);
        expect(license.status).to.equal(LicenseStatus.INACTIVE);
        expect(license.statusDescription).to.equal(null);
        expect(license.eligibility).to.equal(EligibilityStatus.INELIGIBLE);
        expect(license.adverseActions).to.matchPattern([]);
        expect(license.investigations).to.matchPattern([]);

        // Test methods
        expect(license.issueDateDisplay()).to.equal('');
        expect(license.renewalDateDisplay()).to.equal('');
        expect(license.expireDateDisplay()).to.equal('');
        expect(license.activeFromDateDisplay()).to.equal('');
        expect(license.isExpired()).to.equal(false);
        expect(license.isAdminDeactivated()).to.equal(false);
        expect(license.isCompactEligible()).to.equal(false);
        expect(license.licenseTypeAbbreviation()).to.equal('');
        expect(license.displayName()).to.equal('Unknown');
        expect(license.isEncumbered()).to.equal(false);
        expect(license.isLatestLiftedEncumbranceWithinWaitPeriod()).to.equal(false);
        expect(license.isUnderInvestigation()).to.equal(false);
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
            history: [new LicenseHistoryItem()],
            status: LicenseStatus.ACTIVE,
            statusDescription: 'test-status-desc',
            eligibility: EligibilityStatus.ELIGIBLE,
            adverseActions: [new AdverseAction()],
            investigations: [new Investigation()],
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
        expect(license.activeFromDate).to.be.null;
        expect(license.renewalDate).to.equal(data.renewalDate);
        expect(license.expireDate).to.equal(data.expireDate);
        expect(license.mailingAddress).to.be.an.instanceof(Address);
        expect(license.npi).to.equal(data.npi);
        expect(license.licenseNumber).to.equal(data.licenseNumber);
        expect(license.privilegeId).to.equal(data.privilegeId);
        expect(license.licenseType).to.equal(data.licenseType);
        expect(license.history[0]).to.be.an.instanceof(LicenseHistoryItem);
        expect(license.status).to.equal(data.status);
        expect(license.statusDescription).to.equal(data.statusDescription);
        expect(license.eligibility).to.equal(data.eligibility);
        expect(license.adverseActions[0]).to.be.an.instanceof(AdverseAction);
        expect(license.investigations[0]).to.be.an.instanceof(Investigation);

        // Test methods
        expect(license.issueDateDisplay()).to.equal('Invalid date');
        expect(license.renewalDateDisplay()).to.equal('Invalid date');
        expect(license.expireDateDisplay()).to.equal('Invalid date');
        expect(license.activeFromDateDisplay()).to.equal('');
        expect(license.isExpired()).to.equal(false);
        expect(license.isAdminDeactivated()).to.equal(false);
        expect(license.isCompactEligible()).to.equal(true);
        expect(license.licenseTypeAbbreviation()).to.equal('AUD');
        expect(license.displayName()).to.equal('Unknown - audiologist');
        expect(license.displayName(', ', true)).to.equal('Unknown, AUD');
        expect(license.isEncumbered()).to.equal(false);
        expect(license.isLatestLiftedEncumbranceWithinWaitPeriod()).to.equal(false);
        expect(license.isUnderInvestigation()).to.equal(false);
    });
    it('should create a License with specific values (custom displayName delimiter)', () => {
        const data = {
            issueState: new State({ abbrev: 'co' }),
            licenseType: LicenseType.AUDIOLOGIST,
        };
        const license = new License(data);

        // Test field values
        expect(license).to.be.an.instanceof(License);

        // Test methods
        expect(license.displayName(' ... ')).to.equal('Colorado ... audiologist');
        expect(license.displayName(' ... ', true)).to.equal('Colorado ... AUD');
    });
    it('should create a License with specific values through serializer', () => {
        const data = {
            compact: CompactType.ASLP,
            type: 'license',
            providerId: 'test-provider-id',
            jurisdiction: 'al',
            dateOfIssuance: moment().format(serverDateFormat),
            dateOfRenewal: moment().format(serverDateFormat),
            dateOfExpiration: moment().subtract(1, 'day').format(serverDateFormat),
            activeSince: null,
            npi: 'npi',
            licenseNumber: 'licenseNumber',
            homeAddressStreet1: 'test-street1',
            homeAddressStreet2: 'test-street2',
            homeAddressCity: 'test-city',
            homeAddressState: 'co',
            homeAddressPostalCode: 'test-zip',
            licenseType: LicenseType.AUDIOLOGIST,
            history: [],
            licenseStatus: LicenseStatus.ACTIVE,
            licenseStatusName: 'test-status-desc',
            compactEligibility: EligibilityStatus.ELIGIBLE,
            adverseActions: [
                {
                    adverseActionId: 'test-id',
                    effectiveStartDate: moment().subtract(1, 'day').format(serverDateFormat),
                    effectiveLiftDate: moment().add(1, 'day').format(serverDateFormat),
                },
            ],
            investigations: [
                {
                    investigationId: 'test-id',
                    compact: CompactType.ASLP,
                    providerId: 'test-provider-id',
                    jurisdiction: 'al',
                    type: 'investigation',
                    creationDate: moment().subtract(1, 'day').format(serverDateFormat),
                    dateOfUpdate: moment().add(1, 'day').format(serverDateFormat),
                },
            ],
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
        expect(license.activeFromDate).to.equal(data.activeSince);
        expect(license.licenseType).to.equal(data.licenseType);
        expect(license.status).to.equal(data.licenseStatus);
        expect(license.statusDescription).to.equal(data.licenseStatusName);
        expect(license.eligibility).to.equal(data.compactEligibility);
        expect(license.adverseActions).to.be.an('array').with.length(1);
        expect(license.adverseActions[0]).to.be.an.instanceof(AdverseAction);
        expect(license.investigations).to.be.an('array').with.length(1);
        expect(license.investigations[0]).to.be.an.instanceof(Investigation);

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
        expect(license.isAdminDeactivated()).to.equal(false);
        expect(license.isCompactEligible()).to.equal(true);
        expect(license.displayName()).to.equal('Alabama - audiologist');
        expect(license.displayName(', ', true)).to.equal('Alabama, AUD');
        expect(license.licenseTypeAbbreviation()).to.equal('AUD');
        expect(license.isEncumbered()).to.equal(true);
        expect(license.isLatestLiftedEncumbranceWithinWaitPeriod()).to.equal(false);
        expect(license.isUnderInvestigation()).to.equal(true);
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
            activeSince: '2025-05-26T16:19:09+00:00',
            compactTransactionId: '120060088901',
            adverseActions: [
                {
                    adverseActionId: 'test-id',
                    creationDate: moment().subtract(6, 'months').format(serverDatetimeFormat),
                    effectiveLiftDate: moment().subtract(3, 'months').format(serverDateFormat),
                },
            ],
            investigations: [
                {
                    investigationId: 'test-id',
                    compact: CompactType.ASLP,
                    providerId: 'test-provider-id',
                    jurisdiction: 'al',
                    type: 'investigation',
                    creationDate: moment().subtract(1, 'day').format(serverDateFormat),
                    dateOfUpdate: moment().add(1, 'day').format(serverDateFormat),
                },
            ],
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
        expect(license.issueState.abbrev).to.equal(data.jurisdiction);
        expect(license.issueDate).to.equal(data.dateOfIssuance);
        expect(license.renewalDate).to.equal(data.dateOfRenewal);
        expect(license.expireDate).to.equal(data.dateOfExpiration);
        expect(license.activeFromDate).to.equal(data.activeSince);
        expect(license.licenseType).to.equal(data.licenseType);
        expect(license.privilegeId).to.equal(data.privilegeId);
        expect(license.status).to.equal(data.status);
        expect(license.statusDescription).to.equal(null);
        expect(license.eligibility).to.equal(EligibilityStatus.NA);
        expect(license.adverseActions).to.be.an('array').with.length(1);
        expect(license.adverseActions[0]).to.be.an.instanceof(AdverseAction);
        expect(license.adverseActions[0].endDate).to.equal(data.adverseActions[0].effectiveLiftDate);
        expect(license.investigations).to.be.an('array').with.length(1);
        expect(license.investigations[0]).to.be.an.instanceof(Investigation);

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
        expect(license.activeFromDateDisplay()).to.equal(
            moment(data.activeSince, serverDateFormat).format(displayDateFormat)
        );
        expect(license.isExpired()).to.equal(true);
        expect(license.isAdminDeactivated()).to.equal(false);
        expect(license.isCompactEligible()).to.equal(false);
        expect(license.displayName()).to.equal('Nebraska - occupational therapy assistant');
        expect(license.displayName(', ', true)).to.equal('Nebraska, OTA');
        expect(license.licenseTypeAbbreviation()).to.equal('OTA');
        expect(license.history.length).to.equal(0);
        expect(license.isEncumbered()).to.equal(false);
        expect(license.isLatestLiftedEncumbranceWithinWaitPeriod()).to.equal(true);
        expect(license.isUnderInvestigation()).to.equal(true);
    });
    it('should populate isDeactivated correctly given license history (deactivation)', () => {
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
            activeSince: '2025-05-26T16:19:09+00:00',
            compactTransactionId: '120060088901',
            attestations: [],
            privilegeId: 'OTA-NE-10',
            persistedStatus: 'active',
            status: 'inactive',
        };
        const license = LicenseSerializer.fromServer(data);

        license.history = [ new LicenseHistoryItem({
            type: 'privilegeUpdate',
            updateType: 'deactivation',
            dateOfUpdate: '2025-05-01T15:27:35+00:00',
            effectiveDate: '2025-05-01',
            createDate: '2025-05-01T15:27:35+00:00',
            serverNote: 'Note'
        })];

        // Test field values
        expect(license.isAdminDeactivated()).to.equal(true);
    });
    it('should populate isDeactivated correctly given license history (homeJurisdictionChange)', () => {
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
        };

        const license = LicenseSerializer.fromServer(data);

        license.history = [ new LicenseHistoryItem({
            type: 'privilegeUpdate',
            updateType: 'homeJurisdictionChange',
            dateOfUpdate: '2025-05-01T15:27:35+00:00',
            effectiveDate: '2025-05-01',
            createDate: '2025-05-01T15:27:35+00:00',
            serverNote: 'Note'
        })];

        // Test field values
        expect(license.isAdminDeactivated()).to.equal(true);
        expect(license.isLatestLiftedEncumbranceWithinWaitPeriod()).to.equal(false);
    });
    it('should return false when isLatestLiftedEncumbranceWithinWaitPeriod called with no adverse actions', () => {
        const license = new License();

        expect(license.isLatestLiftedEncumbranceWithinWaitPeriod()).to.equal(false);
    });
    it('should return false when isLatestLiftedEncumbranceWithinWaitPeriod called with all active encumbrances (no endDate)', () => {
        const license = new License({
            adverseActions: [
                new AdverseAction({
                    creationDate: '2024-01-01T00:00:00Z',
                    startDate: '2024-01-01',
                    endDate: null
                }),
                new AdverseAction({
                    creationDate: '2024-02-01T00:00:00Z',
                    startDate: '2024-01-01',
                    endDate: null
                })
            ]
        });

        expect(license.isLatestLiftedEncumbranceWithinWaitPeriod()).to.equal(false);
    });
    it('should return true when isLatestLiftedEncumbranceWithinWaitPeriod called with latest non-active encumbrance endDate within 2 years', () => {
        const oneYearAgo = moment().subtract(1, 'year').format(serverDateFormat);
        const license = new License({
            adverseActions: [
                new AdverseAction({
                    creationDate: '2020-01-01T00:00:00Z',
                    startDate: '2020-01-01',
                    endDate: '2020-06-01'
                }),
                new AdverseAction({
                    creationDate: '2021-01-01T00:00:00Z',
                    startDate: '2021-01-01',
                    endDate: oneYearAgo
                })
            ]
        });

        expect(license.isLatestLiftedEncumbranceWithinWaitPeriod()).to.equal(true);
    });
    it('should return false when isLatestLiftedEncumbranceWithinWaitPeriod called with latest non-active encumbrance endDate more than 2 years ago', () => {
        const threeYearsAgo = moment().subtract(3, 'years').format(serverDateFormat);
        const license = new License({
            adverseActions: [
                new AdverseAction({
                    creationDate: '2020-01-01T00:00:00Z',
                    startDate: '2020-01-01',
                    endDate: '2020-06-01'
                }),
                new AdverseAction({
                    creationDate: '2021-01-01T00:00:00Z',
                    startDate: '2021-01-01',
                    endDate: threeYearsAgo
                })
            ]
        });

        expect(license.isLatestLiftedEncumbranceWithinWaitPeriod()).to.equal(false);
    });
    it('should handle mixed active and non-active encumbrances correctly in isLatestLiftedEncumbranceWithinWaitPeriod', () => {
        const recentEndDate = moment().subtract(6, 'months').format(serverDateFormat);
        const license = new License({
            adverseActions: [
                new AdverseAction({
                    creationDate: '2024-01-01T00:00:00Z',
                    startDate: '2024-01-01',
                    endDate: null // Active encumbrance
                }),
                new AdverseAction({
                    creationDate: '2021-01-01T00:00:00Z',
                    startDate: '2021-01-01',
                    endDate: recentEndDate // Non-active encumbrance within 2 years
                }),
                new AdverseAction({
                    creationDate: '2020-01-01T00:00:00Z',
                    startDate: '2020-01-01',
                    endDate: '2020-06-01' // Non-active encumbrance more than 2 years ago
                })
            ]
        });

        // Should return true because the encumbrance with recentEndDate (6 months ago) is within 2 years
        expect(license.isLatestLiftedEncumbranceWithinWaitPeriod()).to.equal(true);
    });
    it('should handle edge case of exactly 2 years ago in isLatestLiftedEncumbranceWithinWaitPeriod', () => {
        const exactlyTwoYearsAgo = moment().subtract(2, 'years').format(serverDateFormat);
        const license = new License({
            adverseActions: [
                new AdverseAction({
                    creationDate: '2020-01-01T00:00:00Z',
                    startDate: '2020-01-01',
                    endDate: exactlyTwoYearsAgo
                })
            ]
        });

        // Should return false because exactly 2 years ago is not "within" the last 2 years
        expect(license.isLatestLiftedEncumbranceWithinWaitPeriod()).to.equal(false);
    });
    it('should handle edge case of just under 2 years ago in isLatestLiftedEncumbranceWithinWaitPeriod', () => {
        const justUnderTwoYears = moment().subtract(2, 'years').add(1, 'day').format(serverDateFormat);
        const license = new License({
            adverseActions: [
                new AdverseAction({
                    creationDate: '2020-01-01T00:00:00Z',
                    startDate: '2020-01-01',
                    endDate: justUnderTwoYears
                })
            ]
        });

        // Should return true because just under 2 years ago is within the last 2 years
        expect(license.isLatestLiftedEncumbranceWithinWaitPeriod()).to.equal(true);
    });
});
