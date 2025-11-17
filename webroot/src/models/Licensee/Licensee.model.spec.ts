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
import { Investigation } from '@models/Investigation/Investigation.model';
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
        expect(licensee.bestLicense()).to.be.an.instanceof(License);
        expect(licensee.bestHomeJurisdictionLicenseMailingAddress()).to.be.an.instanceof(Address);
        expect(licensee.purchaseEligibleLicenses()).to.matchPattern([]);
        expect(licensee.canPurchasePrivileges()).to.equal(false);
        expect(licensee.hasEncumberedLicenses()).to.equal(false);
        expect(licensee.hasEncumberedPrivileges()).to.equal(false);
        expect(licensee.isEncumbered()).to.equal(false);
        expect(licensee.hasEncumbranceLiftedWithinWaitPeriod()).to.equal(false);
        expect(licensee.hasUnderInvestigationLicenses()).to.equal(false);
        expect(licensee.hasUnderInvestigationPrivileges()).to.equal(false);
        expect(licensee.isUnderInvestigation()).to.equal(false);
        expect(licensee.underInvestigationStates()).to.matchPattern([]);
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
                    status: 'active'
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
                    status: 'inactive'
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
        expect(licensee.dob).to.equal(data.dob);
        expect(licensee.birthMonthDay).to.equal(data.birthMonthDay);
        expect(licensee.ssnLastFour).to.equal(data.ssnLastFour);
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
        expect(licensee.bestHomeJurisdictionLicenseMailingAddress()).to.be.an.instanceof(Address);
        expect(licensee.bestLicense()).to.be.an.instanceof(License);
        expect(licensee.purchaseEligibleLicenses()).to.matchPattern([]);
        expect(licensee.canPurchasePrivileges()).to.equal(false);
        expect(licensee.hasEncumberedLicenses()).to.equal(false);
        expect(licensee.hasEncumberedPrivileges()).to.equal(false);
        expect(licensee.isEncumbered()).to.equal(false);
        expect(licensee.hasEncumbranceLiftedWithinWaitPeriod()).to.equal(false);
        expect(licensee.hasUnderInvestigationLicenses()).to.equal(false);
        expect(licensee.hasUnderInvestigationPrivileges()).to.equal(false);
        expect(licensee.isUnderInvestigation()).to.equal(false);
        expect(licensee.underInvestigationStates()).to.matchPattern([]);
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
                    status: 'active',
                    licenseeId: 'test-provider-id',
                }),
                new License({
                    licenseNumber: 'test-id-2',
                    issueDate: '2025-01-01',
                    status: 'active',
                    licenseeId: 'test-provider-id',
                }),
            ],
        });

        // Test methods
        expect(licensee.bestHomeJurisdictionLicense()).to.matchPattern({
            licenseNumber: 'test-id-1',
            '...': '',
        });
        expect(licensee.bestLicense()).to.matchPattern({
            licenseNumber: 'test-id-1',
            '...': '',
        });
    });
    it('should create a Licensee with specific values (best active home license regardless of record order - asc)', () => {
        const licensee = new Licensee({
            licenses: [
                new License({
                    licenseNumber: 'test-id-1',
                    issueDate: '2025-01-01',
                    status: 'active',
                    licenseeId: 'test-provider-id',
                }),
                new License({
                    licenseNumber: 'test-id-2',
                    issueDate: '2025-01-02',
                    status: 'active',
                    licenseeId: 'test-provider-id',
                }),
            ],
        });

        // Test methods
        expect(licensee.bestHomeJurisdictionLicense()).to.matchPattern({
            licenseNumber: 'test-id-2',
            '...': '',
        });
        expect(licensee.bestLicense()).to.matchPattern({
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
            birthMonthDay: '01-16',
            dateOfBirth: moment().format(serverDateFormat),
            phoneNumber: '+13234558990',
            currentHomeJurisdiction: 'co',
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
                downloadLinks: [{
                    fileName: 'file.png',
                    url: 'https://example.com',
                }],
                status: 'active'
            },
            {
                affiliationType: 'affiliationType',
                compact: 'aslp',
                dateOfUpdate: '2025-02-07T23:50:17+00:00',
                dateOfUpload: '2025-02-03T23:50:17+00:00',
                documentKeys: ['key'],
                fileNames: ['file.png'],
                downloadLinks: [{
                    fileName: 'file.png',
                    url: 'https://example.com',
                }],
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
            licenseStatus: LicenseeStatus.ACTIVE,
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
        expect(licensee.status).to.equal(data.licenseStatus);

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
            downloadLinks: [{
                filename: 'file.png',
                url: 'https://example.com',
            }],
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
        expect(licensee.bestLicense()).to.be.an.instanceof(License);
        expect(licensee.bestLicense().licenseNumber).to.equal('1');
        expect(licensee.bestHomeJurisdictionLicenseMailingAddress()).to.be.an.instanceof(Address);
        expect(licensee.purchaseEligibleLicenses()).to.matchPattern([
            {
                id: 'providerId1-co-audiologist',
                '...': '',
            },
        ]);
        expect(licensee.canPurchasePrivileges()).to.equal(true);
        expect(licensee.hasEncumberedLicenses()).to.equal(false);
        expect(licensee.hasEncumberedPrivileges()).to.equal(false);
        expect(licensee.isEncumbered()).to.equal(false);
        expect(licensee.hasEncumbranceLiftedWithinWaitPeriod()).to.equal(false);
        expect(licensee.hasUnderInvestigationLicenses()).to.equal(false);
        expect(licensee.hasUnderInvestigationPrivileges()).to.equal(false);
        expect(licensee.isUnderInvestigation()).to.equal(false);
        expect(licensee.underInvestigationStates()).to.matchPattern([]);
    });
    it('should create a Licensee with specific values through serializer (with inactive best license)', () => {
        const data = {
            providerId: 'test-id',
            npi: 'test-npi',
            givenName: 'test-firstName',
            middleName: 'test-middleName',
            familyName: 'test-lastName',
            phoneNumber: '+13234558990',
            birthMonthDay: '01-16',
            dateOfBirth: moment().format(serverDateFormat),
            licenseType: LicenseType.AUDIOLOGIST,
            ssnLastFour: '0000',
            licenseJurisdiction: 'co',
            currentHomeJurisdiction: 'co',
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
                    providerId: 'test-id',
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
                    licenseStatus: LicenseStatus.INACTIVE,
                    licenseStatusName: '',
                    compactEligibility: EligibilityStatus.INELIGIBLE,
                },
                {
                    id: 'test-id',
                    providerId: 'test-id',
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
                    licenseStatus: LicenseStatus.INACTIVE,
                    licenseStatusName: '',
                    compactEligibility: EligibilityStatus.INELIGIBLE,
                },
                {
                    id: 'test-id',
                    providerId: 'test-id',
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
                    providerId: 'test-id',
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
            licenseStatus: LicenseeStatus.ACTIVE,
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
        expect(licensee.bestLicense()).to.be.an.instanceof(License);
        expect(licensee.bestLicense().licenseNumber).to.equal('2');
        expect(licensee.bestHomeJurisdictionLicenseMailingAddress()).to.be.an.instanceof(Address);
        expect(licensee.purchaseEligibleLicenses()).to.matchPattern([]);
        expect(licensee.canPurchasePrivileges()).to.equal(false);
        expect(licensee.hasEncumberedLicenses()).to.equal(false);
        expect(licensee.hasEncumberedPrivileges()).to.equal(false);
        expect(licensee.isEncumbered()).to.equal(false);
        expect(licensee.hasEncumbranceLiftedWithinWaitPeriod()).to.equal(false);
        expect(licensee.hasUnderInvestigationLicenses()).to.equal(false);
        expect(licensee.hasUnderInvestigationPrivileges()).to.equal(false);
        expect(licensee.isUnderInvestigation()).to.equal(false);
        expect(licensee.underInvestigationStates()).to.matchPattern([]);
    });
    it('should create a Licensee with specific values through serializer (with initiliazing military status)', () => {
        const data = {
            militaryAffiliations: [{
                affiliationType: 'affiliationType',
                compact: 'aslp',
                dateOfUpdate: '2025-01-07T23:50:17+00:00',
                dateOfUpload: '2025-01-03T23:50:17+00:00',
                documentKeys: ['key'],
                fileNames: ['file.png'],
                downloadLinks: [{
                    fileName: 'file.png',
                    url: 'https://example.com',
                }],
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
            }]
        };
        const licensee = LicenseeSerializer.fromServer(data);

        // Test field values
        expect(licensee).to.be.an.instanceof(Licensee);

        // Test methods
        expect(licensee.isMilitaryStatusActive()).to.equal(false);
        expect(licensee.isMilitaryStatusInitializing()).to.equal(true);
        expect(licensee.activeMilitaryAffiliation()).to.equal(null);
    });
    it('should return best license', () => {
        const licensee = new Licensee({
            homeJurisdiction: new State({ abbrev: 'co' }),
            licenses: [
                // Home jurisdiction license (Priority 1)
                new License({
                    licenseNumber: 'home-license',
                    issueState: new State({ abbrev: 'co' }),
                    issueDate: '2025-01-01',
                    status: LicenseStatus.ACTIVE,
                    licenseeId: 'test-provider-id',
                }),
                // Active non-home license (Priority 3)
                new License({
                    licenseNumber: 'ny-active',
                    issueState: new State({ abbrev: 'ny' }),
                    issueDate: '2025-01-02',
                    status: LicenseStatus.ACTIVE,
                    licenseeId: 'test-provider-id',
                }),
                // Inactive non-home license (Priority 4)
                new License({
                    licenseNumber: 'ma-inactive',
                    issueState: new State({ abbrev: 'ma' }),
                    issueDate: '2025-01-03',
                    status: LicenseStatus.INACTIVE,
                    licenseeId: 'test-provider-id',
                }),
                // Inactive home license (Priority 2)
                new License({
                    licenseNumber: 'home-inactive',
                    issueState: new State({ abbrev: 'co' }),
                    issueDate: '2024-12-31',
                    status: LicenseStatus.INACTIVE,
                    licenseeId: 'test-provider-id',
                }),
            ]
        });

        // Should return home license (Priority 1)
        let bestLicense = licensee.bestLicense();

        expect(bestLicense.licenseNumber).to.equal('home-license');

        // Remove active home license, should return inactive home (Priority 2)
        licensee.licenses = licensee.licenses.filter((license) => license.licenseNumber !== 'home-license');
        bestLicense = licensee.bestLicense();
        expect(bestLicense.licenseNumber).to.equal('home-inactive');

        // Remove home license, should return active non-home (Priority 3)
        licensee.licenses = licensee.licenses.filter((license) => license.issueState?.abbrev !== 'co');
        bestLicense = licensee.bestLicense();
        expect(bestLicense.licenseNumber).to.equal('ny-active');

        // Remove active non-home, should return inactive non-home (Priority 4)
        licensee.licenses = licensee.licenses.filter((license) => license.status !== LicenseStatus.ACTIVE);
        bestLicense = licensee.bestLicense();
        expect(bestLicense.licenseNumber).to.equal('ma-inactive');

        // Remove all licenses, should return empty license
        licensee.licenses = [];
        bestLicense = licensee.bestLicense();
        expect(bestLicense.licenseNumber).to.equal(null);
    });
    it('should return best license with edge cases and data handling', () => {
        const licensee = new Licensee({
            homeJurisdiction: new State({ abbrev: 'co' }),
            licenses: [
                // Test missing issueDate handling
                new License({
                    licenseNumber: 'ny-no-date',
                    issueState: new State({ abbrev: 'ny' }),
                    status: LicenseStatus.ACTIVE,
                    licenseeId: 'test-provider-id',
                }),
                new License({
                    licenseNumber: 'ny-valid-date',
                    issueState: new State({ abbrev: 'ny' }),
                    issueDate: '2025-01-01',
                    status: LicenseStatus.ACTIVE,
                    licenseeId: 'test-provider-id',
                })
            ]
        });

        // Should return license with valid date
        let bestLicense = licensee.bestLicense();

        expect(bestLicense.licenseNumber).to.equal('ny-valid-date');

        // Undefined/null/empty licenses
        licensee.licenses = undefined;
        bestLicense = licensee.bestLicense();
        expect(bestLicense.licenseNumber).to.equal(null);

        licensee.licenses = null;
        bestLicense = licensee.bestLicense();
        expect(bestLicense.licenseNumber).to.equal(null);

        licensee.licenses = [];
        bestLicense = licensee.bestLicense();
        expect(bestLicense.licenseNumber).to.equal(null);

        // Test missing issueState (treated as non-home)
        licensee.licenses = [
            new License({
                licenseNumber: 'no-issue-state',
                status: LicenseStatus.ACTIVE,
                licenseeId: 'test-provider-id',
            })
        ];
        bestLicense = licensee.bestLicense();
        expect(bestLicense.licenseNumber).to.equal('no-issue-state');

        // Null issueDate
        licensee.licenses = [
            new License({
                licenseNumber: 'valid-date',
                issueState: new State({ abbrev: 'co' }),
                issueDate: '2025-01-01',
                status: LicenseStatus.ACTIVE,
                licenseeId: 'test-provider-id',
            }),
            new License({
                licenseNumber: 'null-date',
                issueState: new State({ abbrev: 'co' }),
                issueDate: null,
                status: LicenseStatus.ACTIVE,
                licenseeId: 'test-provider-id',
            })
        ];
        bestLicense = licensee.bestLicense();
        expect(bestLicense.licenseNumber).to.equal('valid-date');
    });
    it('should return best license with most recent date', () => {
        const licenseeWithDateComparison = new Licensee({
            homeJurisdiction: new State({ abbrev: 'co' }),
            licenses: [
                new License({
                    licenseNumber: 'ny-older',
                    issueState: new State({ abbrev: 'ny' }),
                    issueDate: '2025-01-01',
                    status: LicenseStatus.ACTIVE,
                    licenseeId: 'test-provider-id',
                }),
                new License({
                    licenseNumber: 'ny-newer',
                    issueState: new State({ abbrev: 'ny' }),
                    issueDate: '2025-01-02',
                    status: LicenseStatus.ACTIVE,
                    licenseeId: 'test-provider-id',
                })
            ]
        });
        const bestLicense = licenseeWithDateComparison.bestLicense();

        expect(bestLicense.licenseNumber).to.equal('ny-newer');
    });
    it('should return best license with missing current license issueDate', () => {
        const licensee = new Licensee({
            homeJurisdiction: new State({ abbrev: 'co' }),
            licenses: [
                // Active non-home licenses where current.issueDate is missing
                new License({
                    licenseNumber: 'ny-with-date',
                    issueState: new State({ abbrev: 'ny' }),
                    issueDate: '2025-01-01',
                    status: LicenseStatus.ACTIVE,
                    licenseeId: 'test-provider-id',
                }),
                new License({
                    licenseNumber: 'ny-no-date',
                    issueState: new State({ abbrev: 'ny' }),
                    // No issueDate (undefined)
                    status: LicenseStatus.ACTIVE,
                    licenseeId: 'test-provider-id',
                })
            ]
        });
        let bestLicense = licensee.bestLicense();

        expect(bestLicense.licenseNumber).to.equal('ny-with-date');

        // Inactive non-home licenses where current.issueDate is missing
        licensee.licenses = [
            new License({
                licenseNumber: 'ma-with-date',
                issueState: new State({ abbrev: 'ma' }),
                issueDate: '2025-01-01',
                status: LicenseStatus.INACTIVE,
                licenseeId: 'test-provider-id',
            }),
            new License({
                licenseNumber: 'ma-no-date',
                issueState: new State({ abbrev: 'ma' }),
                status: LicenseStatus.INACTIVE,
                licenseeId: 'test-provider-id',
            })
        ];

        bestLicense = licensee.bestLicense();

        expect(bestLicense.licenseNumber).to.equal('ma-with-date');
    });
    it('should return best home jurisdiction license', () => {
        // Scenario 1: Home jurisdiction license with missing issueDate
        const licenseeWithMissingIssueDate = new Licensee({
            homeJurisdiction: new State({ abbrev: 'co' }),
            licenses: [
                new License({
                    licenseNumber: 'co-no-date',
                    issueState: new State({ abbrev: 'co' }),
                    status: LicenseStatus.ACTIVE,
                }),
                new License({
                    licenseNumber: 'co-with-date',
                    issueState: new State({ abbrev: 'co' }),
                    issueDate: '2025-01-01',
                    status: LicenseStatus.ACTIVE,
                })
            ]
        });
        let bestHomeLicense = licenseeWithMissingIssueDate.bestHomeJurisdictionLicense();

        expect(bestHomeLicense.licenseNumber).to.equal('co-with-date');

        // Scenario 2: Home jurisdiction license with null issueDate
        const licenseeWithNullIssueDate = new Licensee({
            homeJurisdiction: new State({ abbrev: 'co' }),
            licenses: [
                new License({
                    licenseNumber: 'co-null-date',
                    issueState: new State({ abbrev: 'co' }),
                    issueDate: null,
                    status: LicenseStatus.ACTIVE,
                }),
                new License({
                    licenseNumber: 'co-valid-date',
                    issueState: new State({ abbrev: 'co' }),
                    issueDate: '2025-01-01',
                    status: LicenseStatus.ACTIVE,
                })
            ]
        });

        bestHomeLicense = licenseeWithNullIssueDate.bestHomeJurisdictionLicense();

        expect(bestHomeLicense.licenseNumber).to.equal('co-valid-date');

        // Scenario 3: Multiple home jurisdiction licenses with same issueDate
        const licenseeWithSameDateHome = new Licensee({
            homeJurisdiction: new State({ abbrev: 'co' }),
            licenses: [
                new License({
                    licenseNumber: 'co-same-date-1',
                    issueState: new State({ abbrev: 'co' }),
                    issueDate: '2025-01-01',
                    status: LicenseStatus.ACTIVE,
                }),
                new License({
                    licenseNumber: 'co-same-date-2',
                    issueState: new State({ abbrev: 'co' }),
                    issueDate: '2025-01-01', // Same date
                    status: LicenseStatus.ACTIVE,
                })
            ]
        });

        bestHomeLicense = licenseeWithSameDateHome.bestHomeJurisdictionLicense();

        expect(bestHomeLicense.licenseNumber).to.equal('co-same-date-2');

        // Scenario 3b: Same issue date, but active vs inactive (active should win)
        const licenseeWithSameDateActiveInactive = new Licensee({
            homeJurisdiction: new State({ abbrev: 'co' }),
            licenses: [
                new License({
                    licenseNumber: 'co-inactive-same-date',
                    issueState: new State({ abbrev: 'co' }),
                    issueDate: '2025-01-02',
                    status: LicenseStatus.INACTIVE,
                }),
                new License({
                    licenseNumber: 'co-active-same-date',
                    issueState: new State({ abbrev: 'co' }),
                    issueDate: '2025-01-02', // Same date as inactive
                    status: LicenseStatus.ACTIVE,
                })
            ]
        });

        bestHomeLicense = licenseeWithSameDateActiveInactive.bestHomeJurisdictionLicense();

        expect(bestHomeLicense.licenseNumber).to.equal('co-active-same-date');

        // Scenario 3c: Same issue date, active vs inactive in reverse order (active should still win)
        const licenseeWithSameDateActiveInactiveReverse = new Licensee({
            homeJurisdiction: new State({ abbrev: 'co' }),
            licenses: [
                new License({
                    licenseNumber: 'co-active-first',
                    issueState: new State({ abbrev: 'co' }),
                    issueDate: '2025-01-01',
                    status: LicenseStatus.ACTIVE,
                }),
                new License({
                    licenseNumber: 'co-inactive-second',
                    issueState: new State({ abbrev: 'co' }),
                    issueDate: '2025-01-01', // Same date as active
                    status: LicenseStatus.INACTIVE,
                })
            ]
        });

        bestHomeLicense = licenseeWithSameDateActiveInactiveReverse.bestHomeJurisdictionLicense();

        expect(bestHomeLicense.licenseNumber).to.equal('co-active-first');

        // Scenario 4: Home jurisdiction is undefined
        const licenseeWithUndefinedHome = new Licensee({
            homeJurisdiction: undefined,
            licenses: [
                new License({
                    licenseNumber: 'ny-license',
                    issueState: new State({ abbrev: 'ny' }),
                    issueDate: '2025-01-01',
                    status: LicenseStatus.ACTIVE,
                })
            ]
        });

        bestHomeLicense = licenseeWithUndefinedHome.bestHomeJurisdictionLicense();

        expect(bestHomeLicense.licenseNumber).to.equal(null);
    });
    it('should return home jurisdiction', () => {
        const licenseeWithFilteringTest = new Licensee({
            homeJurisdiction: new State({ abbrev: 'co' }),
            licenses: [
                new License({
                    licenseNumber: 'co-exact-match',
                    issueState: new State({ abbrev: 'co' }),
                    status: LicenseStatus.ACTIVE,
                }),
                new License({
                    licenseNumber: 'co-undefined-issue-state',
                    status: LicenseStatus.ACTIVE,
                }),
                new License({
                    licenseNumber: 'co-null-abbrev',
                    issueState: new State({ abbrev: null }),
                    status: LicenseStatus.ACTIVE,
                }),
                new License({
                    licenseNumber: 'co-empty-abbrev',
                    issueState: new State({ abbrev: '' }),
                    status: LicenseStatus.ACTIVE,
                }),
                new License({
                    licenseNumber: 'ny-different-state',
                    issueState: new State({ abbrev: 'ny' }),
                    status: LicenseStatus.ACTIVE,
                })
            ]
        });
        const homeLicenses = licenseeWithFilteringTest.homeJurisdictionLicenses();

        expect(homeLicenses).to.have.length(1);
        expect(homeLicenses[0].licenseNumber).to.equal('co-exact-match');
    });
    it('should test best license mailing address', () => {
        // License that has mailing address
        const licenseeWithAddress = new Licensee({
            homeJurisdiction: new State({ abbrev: 'co' }),
            licenses: [
                new License({
                    licenseNumber: 'test-1',
                    issueState: new State({ abbrev: 'co' }),
                    mailingAddress: new Address({
                        street1: 'test-street1',
                        street2: 'test-street2',
                        city: 'test-city',
                        state: new State({ abbrev: 'co' }),
                        zip: 'test-zip'
                    }),
                    status: LicenseStatus.ACTIVE,
                    licenseeId: 'test-provider-id'
                })
            ]
        });
        const bestAddress = licenseeWithAddress.bestLicenseMailingAddress();

        expect(bestAddress).to.be.an.instanceof(Address);
        expect(bestAddress.street1).to.equal('test-street1');
        expect(bestAddress.street2).to.equal('test-street2');
        expect(bestAddress.city).to.equal('test-city');
        expect(bestAddress.state?.abbrev).to.equal('co');
        expect(bestAddress.zip).to.equal('test-zip');

        // License that has no mailing address
        const licenseeWithoutAddress = new Licensee({
            homeJurisdiction: new State({ abbrev: 'ny' }),
            licenses: [
                new License({
                    licenseNumber: 'test-2',
                    issueState: new State({ abbrev: 'ny' }),
                    status: LicenseStatus.ACTIVE,
                    licenseeId: 'test-provider-id'
                })
            ]
        });
        const emptyAddress = licenseeWithoutAddress.bestLicenseMailingAddress();

        expect(emptyAddress).to.be.an.instanceof(Address);
        expect(emptyAddress.street1).to.equal(null);
    });
    it('should create a Licensee with encumbered licenses and privileges', () => {
        // Create mock licenses with encumbered status
        const encumberedLicense = new License({
            licenseNumber: 'encumbered-license',
            status: LicenseStatus.INACTIVE,
        });

        // Mock the isEncumbered method
        encumberedLicense.isEncumbered = () => true;

        const encumberedPrivilege = new License({
            licenseNumber: 'encumbered-privilege',
            status: LicenseStatus.INACTIVE,
        });

        // Mock the isEncumbered method
        encumberedPrivilege.isEncumbered = () => true;

        const licensee = new Licensee({
            licenses: [encumberedLicense],
            privileges: [encumberedPrivilege],
        });

        // Test encumbered methods
        expect(licensee.hasEncumberedLicenses()).to.equal(true);
        expect(licensee.hasEncumberedPrivileges()).to.equal(true);
        expect(licensee.isEncumbered()).to.equal(true);
    });
    it('should create a Licensee with under-investigation licenses and privileges', () => {
        const homeState = new State({ abbrev: 'co' });
        const underInvestigationLicense = new License({
            issueState: homeState,
            licenseNumber: 'investigation-license',
            status: LicenseStatus.ACTIVE,
            eligibility: EligibilityStatus.ELIGIBLE,
            investigations: [new Investigation({
                state: new State({ abbrev: 'al' }),
                startDate: moment().subtract(1, 'day').format(serverDateFormat),
                updateDate: moment().add(1, 'day').format(serverDateFormat),
            })],
        });
        const underInvestigationPrivilege = new License({
            licenseNumber: 'investigation-privilege',
            investigations: [
                new Investigation({
                    state: new State({ abbrev: 'al' }),
                    startDate: moment().subtract(1, 'day').format(serverDateFormat),
                    updateDate: moment().add(1, 'day').format(serverDateFormat),
                }),
                new Investigation({
                    state: new State({ abbrev: 'co' }),
                    startDate: moment().subtract(1, 'day').format(serverDateFormat),
                    updateDate: moment().add(1, 'day').format(serverDateFormat),
                }),
            ],
        });
        const licensee = new Licensee({
            homeJurisdiction: homeState,
            licenses: [underInvestigationLicense],
            privileges: [underInvestigationPrivilege],
        });

        // Test encumbered methods
        expect(licensee.hasUnderInvestigationLicenses()).to.equal(true);
        expect(licensee.hasUnderInvestigationPrivileges()).to.equal(true);
        expect(licensee.isUnderInvestigation()).to.equal(true);
        expect(licensee.underInvestigationStates()).to.matchPattern([
            new State({ abbrev: 'al' }),
            new State({ abbrev: 'co' }),
        ]);
        expect(licensee.canPurchasePrivileges()).to.equal(true);
    });
    it(`should handle 'unknown' currentHomeJurisdiction by falling back to licenseJurisdiction`, () => {
        const data = {
            providerId: 'test-id',
            currentHomeJurisdiction: 'unknown',
            licenseJurisdiction: 'ma',
            licenseType: LicenseType.AUDIOLOGIST,
            licenseStatus: LicenseeStatus.ACTIVE,
        };
        const licensee = LicenseeSerializer.fromServer(data);

        expect(licensee.homeJurisdiction).to.be.an.instanceof(State);
        expect(licensee.homeJurisdiction?.abbrev).to.equal('ma');
        expect(licensee.homeJurisdictionDisplay()).to.equal('Massachusetts');
    });
    it(`should test serializer fallback when currentHomeJurisdiction is 'unknown'`, () => {
        const data = {
            providerId: 'test-id',
            currentHomeJurisdiction: 'unknown',
            licenseJurisdiction: 'ny',
            licenseType: LicenseType.AUDIOLOGIST,
            licenseStatus: LicenseeStatus.ACTIVE,
        };
        const licensee = LicenseeSerializer.fromServer(data);

        expect(licensee.homeJurisdiction).to.be.an.instanceof(State);
        expect(licensee.homeJurisdiction?.abbrev).to.equal('ny');
        expect(licensee.homeJurisdictionDisplay()).to.equal('New York');
        expect(licensee.bestLicenseMailingAddress()).to.be.an.instanceof(Address);
    });
    it('should create a Licensee with privileges that have encumbrances lifted within wait period', () => {
        // Create mock privileges with encumbrances lifted within wait period
        const privilegeWithRecentLift = new License({
            licenseNumber: 'privilege-with-recent-lift',
            status: LicenseStatus.ACTIVE,
        });

        // Mock the isLatestLiftedEncumbranceWithinWaitPeriod method
        privilegeWithRecentLift.isLatestLiftedEncumbranceWithinWaitPeriod = () => true;

        const privilegeWithoutRecentLift = new License({
            licenseNumber: 'privilege-without-recent-lift',
            status: LicenseStatus.ACTIVE,
        });

        // Mock the isLatestLiftedEncumbranceWithinWaitPeriod method
        privilegeWithoutRecentLift.isLatestLiftedEncumbranceWithinWaitPeriod = () => false;

        const licensee = new Licensee({
            privileges: [privilegeWithRecentLift, privilegeWithoutRecentLift],
        });

        // Test hasEncumbranceLiftedWithinWaitPeriod method
        expect(licensee.hasEncumbranceLiftedWithinWaitPeriod()).to.equal(true);
    });
    it('should serialize a Licensee for transmission to server', () => {
        const licensee = LicenseeSerializer.fromServer({
            providerId: 'test-id',
            npi: 'test-npi',
            givenName: 'test-firstName',
            middleName: 'test-middleName',
            familyName: 'test-lastName',
            dateOfBirth: moment().format(serverDateFormat),
            ssnLastFour: '0000',
            licenseType: LicenseType.AUDIOLOGIST,
            licenseJurisdiction: 'co',
            privilegeJurisdictions: ['co'],
            dateOfUpdate: moment().format(serverDateFormat),
            licenseStatus: LicenseeStatus.ACTIVE,
        });
        const transmit = LicenseeSerializer.toServer(licensee);

        expect(transmit.id).to.equal(licensee.id);
    });
});
