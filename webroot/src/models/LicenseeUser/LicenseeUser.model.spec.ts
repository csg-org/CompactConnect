//
//  User.model.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/2020.
//
import { AuthTypes } from '@/app.config';
import { LicenseeUser, LicenseeUserSerializer } from '@models/LicenseeUser/LicenseeUser.model';
import { LicenseeSerializer, Licensee } from '@models/Licensee/Licensee.model';
import i18n from '@/i18n';

import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';

chai.use(chaiMatchPattern);

const { expect } = chai;

describe('User model', () => {
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
    it('should create a Licensee User with expected defaults', () => {
        const user = new LicenseeUser();

        expect(user).to.be.an.instanceof(LicenseeUser);
        expect(user.id).to.equal(null);
        expect(user.email).to.equal(null);
        expect(user.firstName).to.equal(null);
        expect(user.lastName).to.equal(null);
        expect(user.userType).to.equal(null);
        expect(user.licensee).to.matchPattern(null);
        expect(user.accountStatus).to.equal('');
    });
    it('should create a Licensee User with specific values', () => {
        const licenseeData = new Licensee({});
        const data = {
            accountStatus: 'active',
            email: 'hello@hello.com',
            firstName: 'Faa',
            id: '443df4d8-60e7-4agg-aff4-c5d12ecc1234',
            lastName: 'Foo',
            userType: AuthTypes.LICENSEE,
            licensee: licenseeData
        };

        const user = new LicenseeUser(data);

        expect(user).to.be.an.instanceof(LicenseeUser);
        expect(user.id).to.equal(data.id);
        expect(user.email).to.equal(data.email);
        expect(user.firstName).to.equal(data.firstName);
        expect(user.lastName).to.equal(data.lastName);
        expect(user.userType).to.equal(data.userType);
        expect(typeof user.licensee).to.equal(typeof licenseeData);
    });
    it('should create a Licensee User with specific values through licensee serializer', () => {
        const data = {
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
            emailAddress: 'asfadfd@slsgfss.com',
            dateOfExpiration: '2024-08-29',
            homeAddressState: 'co',
            providerId: '2',
            familyName: 'Durden',
            homeAddressCity: 'Boulder',
            middleName: '',
            birthMonthDay: '1975-01-01',
            dateOfUpdate: '2024-08-29',
            status: 'active'
        };
        const user = LicenseeUserSerializer.fromServer(data);
        const licensee = LicenseeSerializer.fromServer(data);

        expect(user).to.be.an.instanceof(LicenseeUser);
        expect(user.id).to.equal(data.providerId);
        expect(user.email).to.equal(data.emailAddress);
        expect(user.firstName).to.equal(data.givenName);
        expect(user.lastName).to.equal(data.familyName);
        expect(user.userType).to.equal(AuthTypes.LICENSEE);
        expect(typeof user.licensee).to.equal(typeof licensee);
        expect(user.accountStatus).to.equal(data.status);
        expect(user.getFullName()).to.equal(`${data.givenName} ${data.familyName}`);
        expect(user.getInitials()).to.equal('TD');
        expect(user.accountStatusDisplay()).to.equal('Active');
    });
    it('should create a Licensee User with values through licensee serializer with status defaulting to inactive if not provided', () => {
        const data = {
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
            emailAddress: 'asfadfd@slsgfss.com',
            dateOfExpiration: '2024-08-29',
            homeAddressState: 'co',
            providerId: '2',
            familyName: 'Durden',
            homeAddressCity: 'Boulder',
            middleName: '',
            birthMonthDay: '1975-01-01',
            dateOfUpdate: '2024-08-29',
        };
        const user = LicenseeUserSerializer.fromServer(data);
        const licensee = LicenseeSerializer.fromServer(data);

        expect(user).to.be.an.instanceof(LicenseeUser);
        expect(user.id).to.equal(data.providerId);
        expect(user.email).to.equal(data.emailAddress);
        expect(user.firstName).to.equal(data.givenName);
        expect(user.lastName).to.equal(data.familyName);
        expect(user.userType).to.equal(AuthTypes.LICENSEE);
        expect(typeof user.licensee).to.equal(typeof licensee);
        expect(user.accountStatus).to.equal('inactive');
        expect(user.getFullName()).to.equal(`${data.givenName} ${data.familyName}`);
        expect(user.getInitials()).to.equal('TD');
        expect(user.accountStatusDisplay()).to.equal('Inactive');
    });
});
