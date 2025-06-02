//
//  Licensee.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/8/2024.
//

import chai, { expect } from 'chai';
import chaiMatchPattern from 'chai-match-pattern';
import { serverDateFormat, displayDateFormat } from '@/app.config';
import { CompactType } from '@models/Compact/Compact.model';
import { Licensee, LicenseeStatus, LicenseeSerializer } from '@models/Licensee/Licensee.model';
import { Address } from '@models/Address/Address.model';
import {
    License,
    LicenseType,
    LicenseStatus,
    EligibilityStatus
} from '@models/License/License.model';
import { MilitaryAffiliation } from '@models/MilitaryAffiliation/MilitaryAffiliation.model';
import { State } from '@models/State/State.model';
import i18n from '@/i18n';
import moment from 'moment';

chai.use(chaiMatchPattern);

describe('Licensee model', () => {
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
    });
    it('should create a Licensee with expected defaults', () => {
        const licensee = new Licensee();

        // Test field values
        expect(licensee).to.be.an.instanceof(Licensee);
        expect(licensee.id).to.equal(null);
        expect(licensee.npi).to.equal(null);
        expect(licensee.licenseNumber).to.equal(null);
        expect(licensee.phoneNumber).to.equal(null);
        expect(licensee.homeJurisdiction).to.be.an.instanceof(State);
        expect(licensee.firstName).to.equal(null);
        expect(licensee.middleName).to.equal(null);
        expect(licensee.lastName).to.equal(null);
        expect(licensee.homeJurisdictionLicenseAddress).to.be.an.instanceof(Address);
        expect(licensee.dob).to.equal(null);
        expect(licensee.birthMonthDay).to.equal(null);
        expect(licensee.licenseType).to.equal(null);
        expect(licensee.ssnLastFour).to.equal(null);
        expect(licensee.licenseStates).to.matchPattern([]);
        expect(licensee.licenses).to.matchPattern([]);
        expect(licensee.privilegeStates).to.matchPattern([]);
        expect(licensee.privileges).to.matchPattern([]);
        expect(licensee.militaryAffiliations).to.matchPattern([]);
        expect(licensee.lastUpdated).to.equal(null);
        expect(licensee.status).to.equal(LicenseeStatus.INACTIVE);

        // Test methods
        expect(licensee.nameDisplay()).to.equal('');
        expect(licensee.dobDisplay()).to.equal('');
        expect(licensee.ssnDisplay()).to.equal('');
        expect(licensee.lastUpdatedDisplay()).to.equal('');
        expect(licensee.lastUpdatedDisplayRelative()).to.equal('');
        expect(licensee.getStateListDisplay([])).to.equal('');
        expect(licensee.licenseStatesDisplay()).to.equal('');
        expect(licensee.privilegeStatesAllDisplay()).to.equal('');
        expect(licensee.privilegeStatesDisplay()).to.equal('');
        expect(licensee.licenseTypeName()).to.equal('');
        expect(licensee.statusDisplay()).to.equal('Inactive');
        expect(licensee.phoneNumberDisplay()).to.equal('');
        expect(licensee.isMilitaryStatusActive()).to.equal(false);
        expect(licensee.activeMilitaryAffiliation()).to.equal(null);
        expect(licensee.homeJurisdictionLicenses()).to.matchPattern([]);
        expect(licensee.activeHomeJurisdictionLicenses()).to.matchPattern([]);
        expect(licensee.inactiveHomeJurisdictionLicenses()).to.matchPattern([]);
        expect(licensee.homeJurisdictionDisplay()).to.equal('Unknown');
        expect(licensee.bestHomeJurisdictionLicense()).to.be.an.instanceof(License);
        expect(licensee.bestHomeJurisdictionLicenseMailingAddress()).to.be.an.instanceof(Address);
        expect(licensee.purchaseEligibleLicenses()).to.matchPattern([]);
        expect(licensee.canPurchasePrivileges()).to.equal(false);
    });
    it('should create a Licensee with specific values', () => {
        const data = {
            id: 'test-id',
            npi: 'test-npi',
            licenseNumber: 'test-license-number',
            firstName: 'test-firstName',
            middleName: 'test-middleName',
            lastName: 'test-lastName',
            address: new Address(),
            phoneNumber: '+13234558990',
            homeJurisdiction: new State({ abbrev: 'ma' }),
            dob: '2020-01-01',
            birthMonthDay: '01-16',
            ssnLastFour: '0000',
            militaryAffiliations: [new MilitaryAffiliation()],
            licenseType: LicenseType.AUDIOLOGIST,
            licenseStates: [new State()],
            licenses: [
                new License({
                    issueState: new State({ abbrev: 'co' }),
                    mailingAddress: new Address({
                        street1: 'test-street1',
                        street2: 'test-street2',
                        city: 'test-city',
                        state: 'co',
                        zip: 'test-zip'
                    }),
                    licenseNumber: '1',
                    licenseStatus: 'active'
                }),
                new License({
                    issueState: new State({ abbrev: 'co' }),
                    mailingAddress: new Address({
                        street1: 'test-street1',
                        street2: 'test-street2',
                        city: 'test-city',
                        state: 'co',
                        zip: 'test-zip'
                    }),
                    licenseNumber: '2',
                    licenseStatus: 'inactive'
                }),
                new License(),
            ],
            privilegeStates: [new State()],
            privileges: [
                new License(),
            ],
            lastUpdated: '2020-01-01',
            status: LicenseeStatus.ACTIVE,
        };
        const licensee = new Licensee(data);

        // Test field values
        expect(licensee).to.be.an.instanceof(Licensee);
        expect(licensee.id).to.equal(data.id);
        expect(licensee.npi).to.equal(data.npi);
        expect(licensee.licenseNumber).to.equal(data.licenseNumber);
        expect(licensee.phoneNumber).to.equal(data.phoneNumber);
        expect(licensee.firstName).to.equal(data.firstName);
        expect(licensee.middleName).to.equal(data.middleName);
        expect(licensee.lastName).to.equal(data.lastName);
        expect(licensee.phoneNumber).to.equal(data.phoneNumber);
        expect(licensee.homeJurisdiction).to.be.an.instanceof(State);
        expect(licensee.homeJurisdictionLicenseAddress).to.be.an.instanceof(Address);
        expect(licensee.dob).to.equal(data.dob);
        expect(licensee.birthMonthDay).to.equal(data.birthMonthDay);
        expect(licensee.ssn).to.equal(data.ssn);
        expect(licensee.licenseType).to.equal(data.licenseType);
        expect(licensee.licenseStates).to.be.an('array').with.length(1);
        expect(licensee.licenseStates[0]).to.be.an.instanceof(State);
        expect(licensee.licenses).to.be.an('array').with.length(3);
        expect(licensee.licenses[0]).to.be.an.instanceof(License);
        expect(licensee.privilegeStates).to.be.an('array').with.length(1);
        expect(licensee.privilegeStates[0]).to.be.an.instanceof(State);
        expect(licensee.privileges).to.be.an('array').with.length(1);
        expect(licensee.privileges[0]).to.be.an.instanceof(License);
        expect(licensee.lastUpdated).to.equal(data.lastUpdated);
        expect(licensee.status).to.equal(data.status);

        // Test methods
        expect(licensee.nameDisplay()).to.equal(`${data.firstName} ${data.lastName}`);
        expect(licensee.dobDisplay()).to.equal('1/1/2020');
        expect(licensee.ssnDisplay()).to.equal('*** ** 0000');
        expect(licensee.lastUpdatedDisplay()).to.equal('1/1/2020');
        expect(licensee.lastUpdatedDisplayRelative()).to.be.a('string').that.is.not.empty;
        expect(licensee.getStateListDisplay([])).to.equal('');
        expect(licensee.licenseStatesDisplay()).to.equal('Colorado, Colorado +');
        expect(licensee.privilegeStatesAllDisplay()).to.equal('Unknown');
        expect(licensee.privilegeStatesDisplay()).to.equal('');
        expect(licensee.licenseTypeName()).to.equal('Audiologist');
        expect(licensee.statusDisplay()).to.equal('Active');
        expect(licensee.phoneNumberDisplay()).to.equal('+1 323-455-8990');
        expect(licensee.isMilitaryStatusActive()).to.equal(false);
        expect(licensee.activeMilitaryAffiliation()).to.equal(null);
        expect(licensee.homeJurisdictionLicenses()).to.matchPattern([]);
        expect(licensee.activeHomeJurisdictionLicenses()).to.matchPattern([]);
        expect(licensee.inactiveHomeJurisdictionLicenses()).to.matchPattern([]);
        expect(licensee.homeJurisdictionDisplay()).to.equal('Massachusetts');
        expect(licensee.bestHomeJurisdictionLicense()).to.be.an.instanceof(License);
        expect(licensee.bestHomeJurisdictionLicense().licenseNumber).to.equal(null);
        expect(licensee.bestHomeJurisdictionLicenseMailingAddress()).to.be.an.instanceof(Address);
        expect(licensee.purchaseEligibleLicenses()).to.matchPattern([]);
        expect(licensee.canPurchasePrivileges()).to.equal(false);
    });
    it('should create a Licensee with specific values (null address fallbacks)', () => {
        const data = {
            homeJurisdictionLicenseAddress: null,
        };
        const licensee = new Licensee(data);

        // Test field values
        expect(licensee.homeJurisdictionLicenseAddress).equal(data.homeJurisdictionLicenseAddress);
    });
    it('should create a Licensee with specific values (empty state name fallbacks)', () => {
        const licensee = new Licensee();

        // Test methods
        expect(licensee.getStateListDisplay(['', '', ''])).to.equal('');
    });
    it('should create a Licensee with specific values (empty license & privilege state name fallbacks - getOne)', () => {
        const licensee = new Licensee({
            licenses: [null],
            privileges: [null],
        });

        // Test methods
        expect(licensee.licenseStatesDisplay()).to.equal('');
        expect(licensee.privilegeStatesDisplay()).to.equal('');
        expect(licensee.privilegeStatesAllDisplay()).to.equal('');
    });
    it('should create a Licensee with specific values (empty license & privilege state name fallbacks - getAll)', () => {
        const licensee = new Licensee({
            licenseStates: null,
            privilegeStates: null,
        });

        // Test methods
        expect(licensee.licenseStatesDisplay()).to.equal('');
        expect(licensee.privilegeStatesDisplay()).to.equal('');
        expect(licensee.privilegeStatesAllDisplay()).to.equal('');
    });
    it('should create a Licensee with specific values (best active home license regardless of record order - desc)', () => {
        const licensee = new Licensee({
            licenses: [
                new License({
                    licenseNumber: 'test-id-1',
                    issueDate: '2025-01-02',
                    licenseStatus: 'active',
                }),
                new License({
                    licenseNumber: 'test-id-2',
                    issueDate: '2025-01-01',
                    licenseStatus: 'active',
                }),
            ],
        });

        // Test methods
        expect(licensee.bestHomeJurisdictionLicense()).to.matchPattern({
            licenseNumber: 'test-id-1',
            '...': '',
        });
    });
    it('should create a Licensee with specific values (best active home license regardless of record order - asc)', () => {
        const licensee = new Licensee({
            licenses: [
                new License({
                    licenseNumber: 'test-id-1',
                    dateOfIssuance: '2025-01-01',
                    licenseStatus: 'active',
                }),
                new License({
                    licenseNumber: 'test-id-2',
                    dateOfIssuance: '2025-01-02',
                    licenseStatus: 'active',
                }),
            ],
        });

        // Test methods
        expect(licensee.bestHomeJurisdictionLicense()).to.matchPattern({
            licenseNumber: 'test-id-2',
            '...': '',
        });
    });
    it('should create a Licensee with specific values through serializer', () => {
        const data = {
            providerId: 'test-id',
            npi: 'test-npi',
            givenName: 'test-firstName',
            middleName: 'test-middleName',
            familyName: 'test-lastName',
            homeAddressStreet1: 'test-street1',
            homeAddressStreet2: 'test-street2',
            birthMonthDay: '01-16',
            homeAddressCity: 'test-city',
            homeAddressState: 'co',
            homeAddressPostalCode: 'test-zip',
            dateOfBirth: moment().format(serverDateFormat),
            phoneNumber: '+13234558990',
            homeJurisdictionSelection: {
                compact: 'aslp',
                dateOfSelection: '2025-01-30T18:55:00+00:00',
                dateOfUpdate: '2025-01-30T18:55:00+00:00',
                jurisdiction: 'co',
                providerId: '0a945011-e2a7-4b25-b514-84f4d89b9937',
                type: 'homeJurisdictionSelection'
            },
            ssnLastFour: '0000',
            licenseType: LicenseType.AUDIOLOGIST,
            licenseJurisdiction: 'co',
            militaryAffiliations: [{
                affiliationType: 'affiliationType',
                compact: 'aslp',
                dateOfUpdate: '2025-01-07T23:50:17+00:00',
                dateOfUpload: '2025-01-03T23:50:17+00:00',
                documentKeys: ['key'],
                fileNames: ['file.png'],
                status: 'active'
            },
            {
                affiliationType: 'affiliationType',
                compact: 'aslp',
                dateOfUpdate: '2025-02-07T23:50:17+00:00',
                dateOfUpload: '2025-02-03T23:50:17+00:00',
                documentKeys: ['key'],
                fileNames: ['file.png'],
                status: 'inactive'
            }],
            licenses: [
                {
                    id: 'test-id',
                    licenseNumber: '1',
                    providerId: 'providerId1',
                    compact: CompactType.ASLP,
                    type: 'license-home',
                    jurisdiction: 'co',
                    dateOfIssuance: moment().format(serverDateFormat),
                    homeAddressStreet1: 'test-street1',
                    homeAddressStreet2: 'test-street2',
                    homeAddressCity: 'test-city',
                    homeAddressState: 'co',
                    homeAddressPostalCode: 'test-zip',
                    renewalDate: moment().format(serverDateFormat),
                    expireDate: moment().add(1, 'day').format(serverDateFormat),
                    licenseType: LicenseType.AUDIOLOGIST,
                    licenseStatus: LicenseStatus.ACTIVE,
                    licenseStatusName: 'test-status-name',
                    compactEligibility: EligibilityStatus.ELIGIBLE,
                },
                {
                    id: 'test-id',
                    licenseNumber: '2',
                    providerId: 'providerId2',
                    compact: CompactType.ASLP,
                    type: 'license-home',
                    jurisdiction: 'co',
                    homeAddressStreet1: 'test-street1',
                    homeAddressStreet2: 'test-street2',
                    homeAddressCity: 'test-city',
                    homeAddressState: 'co',
                    homeAddressPostalCode: 'test-zip',
                    dateOfIssuance: moment().format(serverDateFormat),
                    renewalDate: moment().format(serverDateFormat),
                    expireDate: moment().subtract(1, 'day').format(serverDateFormat),
                    licenseType: LicenseType.AUDIOLOGIST,
                    status: LicenseStatus.INACTIVE,
                    licenseStatusName: 'test-status-name',
                    compactEligibility: EligibilityStatus.INELIGIBLE,
                },
                {
                    id: 'test-id',
                    licenseNumber: '3',
                    providerId: 'providerId1',
                    compact: CompactType.ASLP,
                    type: 'license-home',
                    jurisdiction: 'ma',
                    homeAddressStreet1: 'test-street1',
                    homeAddressStreet2: 'test-street2',
                    homeAddressCity: 'test-city',
                    homeAddressState: 'co',
                    homeAddressPostalCode: 'test-zip',
                    dateOfIssuance: moment().format(serverDateFormat),
                    renewalDate: moment().format(serverDateFormat),
                    expireDate: moment().subtract(1, 'day').format(serverDateFormat),
                    licenseType: LicenseType.AUDIOLOGIST,
                    status: LicenseStatus.ACTIVE,
                    licenseStatusName: 'test-status-name',
                    compactEligibility: EligibilityStatus.ELIGIBLE,
                },
            ],
            privilegeJurisdictions: ['co'],
            privileges: [
                {
                    id: 'test-id',
                    compact: CompactType.ASLP,
                    type: 'privilege',
                    jurisdiction: 'co',
                    issueDate: moment().format(serverDateFormat),
                    renewalDate: moment().format(serverDateFormat),
                    expireDate: moment().subtract(1, 'day').format(serverDateFormat),
                    licenseType: LicenseType.AUDIOLOGIST,
                    status: LicenseStatus.ACTIVE,
                }
            ],
            dateOfUpdate: moment().format(serverDateFormat),
            status: LicenseeStatus.ACTIVE,
        };
        const licensee = LicenseeSerializer.fromServer(data);

        // Test field values
        expect(licensee).to.be.an.instanceof(Licensee);
        expect(licensee.id).to.equal(data.providerId);
        expect(licensee.npi).to.equal(data.npi);
        expect(licensee.firstName).to.equal(data.givenName);
        expect(licensee.middleName).to.equal(data.middleName);
        expect(licensee.lastName).to.equal(data.familyName);
        expect(licensee.birthMonthDay).to.equal(data.birthMonthDay);
        expect(licensee.dob).to.equal(data.dateOfBirth);
        expect(licensee.ssnLastFour).to.equal(data.ssnLastFour);
        expect(licensee.licenseType).to.equal(data.licenseType);
        expect(licensee.homeJurisdictionLicenseAddress).to.be.an.instanceof(Address);
        expect(licensee.licenseStates).to.be.an('array').with.length(1);
        expect(licensee.licenseStates[0]).to.be.an.instanceof(State);
        expect(licensee.licenses).to.be.an('array').with.length(3);
        expect(licensee.licenses[0]).to.be.an.instanceof(License);
        expect(licensee.privilegeStates).to.be.an('array').with.length(1);
        expect(licensee.privilegeStates[0]).to.be.an.instanceof(State);
        expect(licensee.privileges).to.be.an('array').with.length(1);
        expect(licensee.privileges[0]).to.be.an.instanceof(License);
        expect(licensee.lastUpdated).to.equal(data.dateOfUpdate);
        expect(licensee.militaryAffiliations).to.be.an('array').with.length(2);
        expect(licensee.militaryAffiliations[0]).to.be.an.instanceof(MilitaryAffiliation);
        expect(licensee.militaryAffiliations[1]).to.be.an.instanceof(MilitaryAffiliation);
        expect(licensee.status).to.equal(data.status);

        // Test methods
        expect(licensee.nameDisplay()).to.equal(`${data.givenName} ${data.familyName}`);
        expect(licensee.dobDisplay()).to.equal(moment(data.dateOfBirth, serverDateFormat).format(displayDateFormat));
        expect(licensee.ssnDisplay()).to.equal('*** ** 0000');
        expect(licensee.lastUpdatedDisplay()).to.equal(
            moment(data.dateOfUpdate, serverDateFormat).format(displayDateFormat)
        );
        expect(licensee.lastUpdatedDisplayRelative()).to.be.a('string').that.is.not.empty;
        expect(licensee.getStateListDisplay([])).to.equal('');
        expect(licensee.licenseStatesDisplay()).to.equal('Colorado, Colorado +');
        expect(licensee.privilegeStatesAllDisplay()).to.equal('Colorado');
        expect(licensee.privilegeStatesDisplay()).to.equal('Colorado');
        expect(licensee.licenseTypeName()).to.equal('Audiologist');
        expect(licensee.statusDisplay()).to.equal('Active');
        expect(licensee.phoneNumberDisplay()).to.equal('+1 323-455-8990');
        expect(licensee.isMilitaryStatusActive()).to.equal(true);
        expect(licensee.activeMilitaryAffiliation()).to.matchPattern({
            affiliationType: 'affiliationType',
            compact: 'aslp',
            dateOfUpdate: '2025-01-07T23:50:17+00:00',
            dateOfUpload: '2025-01-03T23:50:17+00:00',
            documentKeys: ['key'],
            fileNames: ['file.png'],
            status: 'active'
        });
        expect(licensee.homeJurisdictionLicenses()).to.matchPattern([
            {
                id: 'providerId1-co-audiologist',
                '...': '',
            },
            {
                id: 'providerId2-co-audiologist',
                '...': '',
            },
        ]);
        expect(licensee.activeHomeJurisdictionLicenses()).to.matchPattern([
            {
                id: 'providerId1-co-audiologist',
                '...': '',
            },
        ]);
        expect(licensee.inactiveHomeJurisdictionLicenses()).to.matchPattern([
            {
                id: 'providerId2-co-audiologist',
                '...': '',
            },
        ]);
        expect(licensee.homeJurisdictionDisplay()).to.equal('Colorado');
        expect(licensee.bestHomeJurisdictionLicense()).to.be.an.instanceof(License);
        expect(licensee.bestHomeJurisdictionLicense().licenseNumber).to.equal('1');
        expect(licensee.bestHomeJurisdictionLicenseMailingAddress()).to.be.an.instanceof(Address);
        expect(licensee.purchaseEligibleLicenses()).to.matchPattern([
            {
                id: 'providerId1-co-audiologist',
                '...': '',
            },
        ]);
        expect(licensee.canPurchasePrivileges()).to.equal(true);
    });
    it('should create a Licensee with specific values through serializer (with inactive best license)', () => {
        const data = {
            providerId: 'test-id',
            npi: 'test-npi',
            givenName: 'test-firstName',
            middleName: 'test-middleName',
            familyName: 'test-lastName',
            homeAddressStreet1: 'test-street1',
            homeAddressStreet2: 'test-street2',
            phoneNumber: '+13234558990',
            birthMonthDay: '01-16',
            homeAddressCity: 'test-city',
            homeAddressState: 'co',
            homeAddressPostalCode: 'test-zip',
            dateOfBirth: moment().format(serverDateFormat),
            licenseType: LicenseType.AUDIOLOGIST,
            ssnLastFour: '0000',
            licenseJurisdiction: 'co',
            homeJurisdictionSelection: {
                compact: 'aslp',
                dateOfSelection: '2025-01-30T18:55:00+00:00',
                dateOfUpdate: '2025-01-30T18:55:00+00:00',
                jurisdiction: 'co',
                providerId: '0a945011-e2a7-4b25-b514-84f4d89b9937',
                type: 'homeJurisdictionSelection'
            },
            militaryAffiliations: [{
                affiliationType: 'affiliationType',
                compact: 'aslp',
                dateOfUpdate: '2025-01-07T23:50:17+00:00',
                dateOfUpload: '2025-01-03T23:50:17+00:00',
                documentKeys: ['key'],
                fileNames: ['file.png'],
                status: 'inactive'
            },
            {
                affiliationType: 'affiliationType',
                compact: 'aslp',
                dateOfUpdate: '2025-02-07T23:50:17+00:00',
                dateOfUpload: '2025-02-03T23:50:17+00:00',
                documentKeys: ['key'],
                fileNames: ['file.png'],
                status: 'inactive'
            }],
            licenses: [
                {
                    id: 'test-id',
                    licenseNumber: '1',
                    compact: CompactType.ASLP,
                    type: 'license-home',
                    jurisdiction: 'co',
                    dateOfIssuance: moment().subtract(1, 'day').format(serverDateFormat),
                    homeAddressStreet1: 'test-street1',
                    homeAddressStreet2: 'test-street2',
                    homeAddressCity: 'test-city',
                    homeAddressState: 'co',
                    homeAddressPostalCode: 'test-zip',
                    renewalDate: moment().format(serverDateFormat),
                    expireDate: moment().subtract(1, 'day').format(serverDateFormat),
                    licenseType: LicenseType.AUDIOLOGIST,
                    licneseStatus: LicenseStatus.INACTIVE,
                    licenseStatusName: '',
                    compactEligibility: EligibilityStatus.INELIGIBLE,
                },
                {
                    id: 'test-id',
                    licenseNumber: '2',
                    compact: CompactType.ASLP,
                    type: 'license-home',
                    jurisdiction: 'co',
                    homeAddressStreet1: 'test-street1',
                    homeAddressStreet2: 'test-street2',
                    homeAddressCity: 'test-city',
                    homeAddressState: 'co',
                    homeAddressPostalCode: 'test-zip',
                    dateOfIssuance: moment().format(serverDateFormat),
                    renewalDate: moment().format(serverDateFormat),
                    expireDate: moment().subtract(1, 'day').format(serverDateFormat),
                    licenseType: LicenseType.AUDIOLOGIST,
                    licneseStatus: LicenseStatus.INACTIVE,
                    licenseStatusName: '',
                    compactEligibility: EligibilityStatus.INELIGIBLE,
                },
                {
                    id: 'test-id',
                    licenseNumber: '3',
                    compact: CompactType.ASLP,
                    type: 'license-home',
                    jurisdiction: 'co',
                    homeAddressStreet1: 'test-street1',
                    homeAddressStreet2: 'test-street2',
                    homeAddressCity: 'test-city',
                    homeAddressState: 'co',
                    homeAddressPostalCode: 'test-zip',
                    dateOfIssuance: moment().subtract(2, 'day').format(serverDateFormat),
                    renewalDate: moment().format(serverDateFormat),
                    expireDate: moment().subtract(1, 'day').format(serverDateFormat),
                    licenseType: LicenseType.AUDIOLOGIST,
                    licenseStatus: LicenseStatus.INACTIVE,
                    licenseStatusName: '',
                    compactEligibility: EligibilityStatus.INELIGIBLE,
                },
            ],
            privilegeJurisdictions: ['co'],
            privileges: [
                {
                    id: 'test-id',
                    compact: CompactType.ASLP,
                    type: 'privilege',
                    jurisdiction: 'co',
                    issueDate: moment().format(serverDateFormat),
                    renewalDate: moment().format(serverDateFormat),
                    expireDate: moment().subtract(1, 'day').format(serverDateFormat),
                    licenseType: LicenseType.AUDIOLOGIST,
                    status: LicenseStatus.ACTIVE,
                },
            ],
            dateOfUpdate: moment().format(serverDateFormat),
            status: LicenseeStatus.ACTIVE,
        };
        const licensee = LicenseeSerializer.fromServer(data);

        // Test field values
        expect(licensee).to.be.an.instanceof(Licensee);

        // Test methods
        expect(licensee.licenseStatesDisplay()).to.equal('Colorado, Colorado +');
        expect(licensee.privilegeStatesAllDisplay()).to.equal('Colorado');
        expect(licensee.privilegeStatesDisplay()).to.equal('Colorado');
        expect(licensee.licenseTypeName()).to.equal('Audiologist');
        expect(licensee.bestHomeJurisdictionLicense()).to.be.an.instanceof(License);
        expect(licensee.bestHomeJurisdictionLicense().licenseNumber).to.equal('2');
        expect(licensee.bestHomeJurisdictionLicenseMailingAddress()).to.be.an.instanceof(Address);
        expect(licensee.purchaseEligibleLicenses()).to.matchPattern([]);
        expect(licensee.canPurchasePrivileges()).to.equal(false);
    });
    it('should create a Licensee with specific values through serializer (with initiliazing military status)', () => {
        const data = {
            providerId: 'test-id',
            npi: 'test-npi',
            givenName: 'test-firstName',
            middleName: 'test-middleName',
            familyName: 'test-lastName',
            homeAddressStreet1: 'test-street1',
            homeAddressStreet2: 'test-street2',
            birthMonthDay: '01-16',
            homeAddressCity: 'test-city',
            homeAddressState: 'co',
            homeAddressPostalCode: 'test-zip',
            dateOfBirth: moment().format(serverDateFormat),
            phoneNumber: '+13234558990',
            homeJurisdictionSelection: {
                compact: 'aslp',
                dateOfSelection: '2025-01-30T18:55:00+00:00',
                dateOfUpdate: '2025-01-30T18:55:00+00:00',
                jurisdiction: 'co',
                providerId: '0a945011-e2a7-4b25-b514-84f4d89b9937',
                type: 'homeJurisdictionSelection'
            },
            ssnLastFour: '0000',
            licenseType: LicenseType.AUDIOLOGIST,
            licenseJurisdiction: 'co',
            militaryAffiliations: [{
                affiliationType: 'affiliationType',
                compact: 'aslp',
                dateOfUpdate: '2025-01-07T23:50:17+00:00',
                dateOfUpload: '2025-01-03T23:50:17+00:00',
                documentKeys: ['key'],
                fileNames: ['file.png'],
                status: 'inactive'
            },
            {
                affiliationType: 'affiliationType',
                compact: 'aslp',
                dateOfUpdate: '2025-02-07T23:50:17+00:00',
                dateOfUpload: '2025-02-03T23:50:17+00:00',
                documentKeys: ['key'],
                fileNames: ['file.png'],
                status: 'initializing'
            }],
            licenses: [
                {
                    id: 'test-id',
                    licenseNumber: '1',
                    providerId: 'providerId1',
                    compact: CompactType.ASLP,
                    type: 'license-home',
                    jurisdiction: 'co',
                    dateOfIssuance: moment().format(serverDateFormat),
                    homeAddressStreet1: 'test-street1',
                    homeAddressStreet2: 'test-street2',
                    homeAddressCity: 'test-city',
                    homeAddressState: 'co',
                    homeAddressPostalCode: 'test-zip',
                    renewalDate: moment().format(serverDateFormat),
                    expireDate: moment().add(1, 'day').format(serverDateFormat),
                    licenseType: LicenseType.AUDIOLOGIST,
                    licenseStatus: LicenseStatus.ACTIVE,
                    licenseStatusName: 'test-status-name',
                    compactEligibility: EligibilityStatus.ELIGIBLE,
                },
                {
                    id: 'test-id',
                    licenseNumber: '2',
                    providerId: 'providerId2',
                    compact: CompactType.ASLP,
                    type: 'license-home',
                    jurisdiction: 'co',
                    homeAddressStreet1: 'test-street1',
                    homeAddressStreet2: 'test-street2',
                    homeAddressCity: 'test-city',
                    homeAddressState: 'co',
                    homeAddressPostalCode: 'test-zip',
                    dateOfIssuance: moment().format(serverDateFormat),
                    renewalDate: moment().format(serverDateFormat),
                    expireDate: moment().subtract(1, 'day').format(serverDateFormat),
                    licenseType: LicenseType.AUDIOLOGIST,
                    status: LicenseStatus.INACTIVE,
                    licenseStatusName: 'test-status-name',
                    compactEligibility: EligibilityStatus.INELIGIBLE,
                },
                {
                    id: 'test-id',
                    licenseNumber: '3',
                    providerId: 'providerId1',
                    compact: CompactType.ASLP,
                    type: 'license-home',
                    jurisdiction: 'ma',
                    homeAddressStreet1: 'test-street1',
                    homeAddressStreet2: 'test-street2',
                    homeAddressCity: 'test-city',
                    homeAddressState: 'co',
                    homeAddressPostalCode: 'test-zip',
                    dateOfIssuance: moment().format(serverDateFormat),
                    renewalDate: moment().format(serverDateFormat),
                    expireDate: moment().subtract(1, 'day').format(serverDateFormat),
                    licenseType: LicenseType.AUDIOLOGIST,
                    status: LicenseStatus.ACTIVE,
                    licenseStatusName: 'test-status-name',
                    compactEligibility: EligibilityStatus.ELIGIBLE,
                },
            ],
            privilegeJurisdictions: ['co'],
            privileges: [
                {
                    id: 'test-id',
                    compact: CompactType.ASLP,
                    type: 'privilege',
                    jurisdiction: 'co',
                    issueDate: moment().format(serverDateFormat),
                    renewalDate: moment().format(serverDateFormat),
                    expireDate: moment().subtract(1, 'day').format(serverDateFormat),
                    licenseType: LicenseType.AUDIOLOGIST,
                    status: LicenseStatus.ACTIVE,
                }
            ],
            dateOfUpdate: moment().format(serverDateFormat),
            status: LicenseeStatus.ACTIVE,
        };
        const licensee = LicenseeSerializer.fromServer(data);

        // Test field values
        expect(licensee).to.be.an.instanceof(Licensee);

        // Test methods
        expect(licensee.isMilitaryStatusActive()).to.equal(false);
        expect(licensee.isMilitaryStatusInitializing()).to.equal(true);
        expect(licensee.activeMilitaryAffiliation()).to.equal(null);
    });
    it('should serialize a Licensee for transmission to server', () => {
        const licensee = LicenseeSerializer.fromServer({
            providerId: 'test-id',
            npi: 'test-npi',
            givenName: 'test-firstName',
            middleName: 'test-middleName',
            familyName: 'test-lastName',
            homeAddressStreet1: 'test-street1',
            homeAddressStreet2: 'test-street2',
            homeAddressCity: 'test-city',
            homeAddressState: 'co',
            homeAddressPostalCode: 'test-zip',
            dateOfBirth: moment().format(serverDateFormat),
            ssnLastFour: '0000',
            licenseType: LicenseType.AUDIOLOGIST,
            licenseJurisdiction: 'co',
            privilegeJurisdictions: ['co'],
            dateOfUpdate: moment().format(serverDateFormat),
            status: LicenseeStatus.ACTIVE,
        });
        const transmit = LicenseeSerializer.toServer(licensee);

        expect(transmit.id).to.equal(licensee.id);
    });
});
