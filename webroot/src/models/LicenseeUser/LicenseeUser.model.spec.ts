//
//  User.model.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/2020.
//
import { AuthTypes } from '@/app.config';
import {
    LicenseeUser,
    LicenseeUserSerializer,
    LicenseeUserPurchaseSerializer
} from '@models/LicenseeUser/LicenseeUser.model';
import { LicenseeSerializer, Licensee } from '@models/Licensee/Licensee.model';
import { AcceptedAttestationToSend } from '@models/AcceptedAttestationToSend/AcceptedAttestationToSend.model';
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
        expect(user.stateProvidedEmail).to.equal(null);
        expect(user.compactConnectEmail).to.equal(null);
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
            stateProvidedEmail: 'hello@example.com',
            compactConnectEmail: 'hello+registered@example.com',
            firstName: 'Faa',
            id: '443df4d8-60e7-4agg-aff4-c5d12ecc1234',
            lastName: 'Foo',
            userType: AuthTypes.LICENSEE,
            licensee: licenseeData
        };

        const user = new LicenseeUser(data);

        expect(user).to.be.an.instanceof(LicenseeUser);
        expect(user.id).to.equal(data.id);
        expect(user.stateProvidedEmail).to.equal(data.stateProvidedEmail);
        expect(user.compactConnectEmail).to.equal(data.compactConnectEmail);
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
            emailAddress: 'hello@example.com',
            compactConnectRegisteredEmailAddress: 'hello+registered@example.com',
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
        expect(user.stateProvidedEmail).to.equal(data.emailAddress);
        expect(user.compactConnectEmail).to.equal(data.compactConnectRegisteredEmailAddress);
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
            emailAddress: 'hello@example.com',
            compactConnectRegisteredEmailAddress: 'hello+registered@example.com',
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
        expect(user.stateProvidedEmail).to.equal(data.emailAddress);
        expect(user.compactConnectEmail).to.equal(data.compactConnectRegisteredEmailAddress);
        expect(user.firstName).to.equal(data.givenName);
        expect(user.lastName).to.equal(data.familyName);
        expect(user.userType).to.equal(AuthTypes.LICENSEE);
        expect(typeof user.licensee).to.equal(typeof licensee);
        expect(user.accountStatus).to.equal('inactive');
        expect(user.getFullName()).to.equal(`${data.givenName} ${data.familyName}`);
        expect(user.getInitials()).to.equal('TD');
        expect(user.accountStatusDisplay()).to.equal('Inactive');
    });
    it('should serialize a privilege purchase request for transmission', () => {
        const formValues = {
            firstName: 'first',
            lastName: 'last',
            expMonth: '12',
            expYear: '25',
            cvv: '900',
            creditCard: '9999 9999 9999 9999',
            streetAddress1: '123 Street st',
            streetAddress2: 'Unit 101',
            noRefunds: true,
            stateSelect: 'ct',
            zip: '90210'
        };

        const statesSelected = ['ne', 'ky'];

        const attestationsSelected = [
            new AcceptedAttestationToSend({
                attestationId: 'id',
                version: '1'
            }),
            new AcceptedAttestationToSend({
                attestationId: 'id-2',
                version: '1'
            })
        ];

        const requestData = LicenseeUserPurchaseSerializer.toServer({
            statesSelected,
            formValues,
            attestationsSelected
        });

        expect(requestData.selectedJurisdictions).to.matchPattern(['ne', 'ky']);
        expect(requestData.attestations).to.matchPattern(attestationsSelected);
        expect(requestData.orderInformation.card.number).to.equal(formValues.creditCard.replace(/\s+/g, ''));
        expect(requestData.orderInformation.card.expiration).to.equal(`20${formValues.expYear}-${formValues.expMonth}`);
        expect(requestData.orderInformation.card.cvv).to.equal(formValues.cvv);
        expect(requestData.orderInformation.billing.firstName).to.equal(formValues.firstName);
        expect(requestData.orderInformation.billing.lastName).to.equal(formValues.lastName);
        expect(requestData.orderInformation.billing.streetAddress).to.equal(formValues.streetAddress1);
        expect(requestData.orderInformation.billing.streetAddress2).to.equal(formValues.streetAddress2);
        expect(requestData.orderInformation.billing.state).to.equal(formValues.stateSelect.toUpperCase());
        expect(requestData.orderInformation.billing.zip).to.equal(formValues.zip);
        expect(requestData.attestations.length).to.equal(2);
    });
});
