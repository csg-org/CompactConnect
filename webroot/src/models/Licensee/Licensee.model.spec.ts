//
//  Licensee.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/8/2024.
//

import { expect } from 'chai';
import { serverDateFormat, displayDateFormat } from '@/app.config';
import { Licensee, LicenseeStatus, LicenseeSerializer } from '@models/Licensee/Licensee.model';
import { Address } from '@models/Address/Address.model';
import { License, LicenseType } from '@models/License/License.model';
import i18n from '@/i18n';
import moment from 'moment';

describe('Licensee model', () => {
    before(() => {
        const { tm: $tm } = i18n.global;

        (window as any).Vue = {
            config: {
                globalProperties: {
                    $tm,
                }
            }
        };
    });
    it('should create a Licensee with expected defaults', () => {
        const licensee = new Licensee();

        // Test field values
        expect(licensee).to.be.an.instanceof(Licensee);
        expect(licensee.id).to.equal(null);
        expect(licensee.firstName).to.equal(null);
        expect(licensee.middleName).to.equal(null);
        expect(licensee.lastName).to.equal(null);
        expect(licensee.address).to.be.an.instanceof(Address);
        expect(licensee.licenses).to.be.an('array').that.is.empty;
        expect(licensee.dob).to.equal(null);
        expect(licensee.ssn).to.equal(null);
        expect(licensee.lastUpdated).to.equal(null);
        expect(licensee.status).to.equal(null);

        // Test methods
        expect(licensee.nameDisplay()).to.equal('');
        expect(licensee.residenceLocation()).to.equal('');
        expect(licensee.dobDisplay()).to.equal('');
        expect(licensee.lastUpdatedDisplay()).to.equal('');
        expect(licensee.lastUpdatedDisplayRelative()).to.equal('');
        expect(licensee.licenseStatesDisplay()).to.equal('');
        expect(licensee.practicingLocationsAll()).to.equal('');
        expect(licensee.practicingLocationsDisplay()).to.equal('');
        expect(licensee.ssnMaskedFull()).to.equal('');
        expect(licensee.ssnMaskedPartial()).to.equal('');
    });
    it('should create a Licensee with specific values', () => {
        const data = {
            id: 'test-id',
            firstName: 'test-firstName',
            middleName: 'test-middleName',
            lastName: 'test-lastName',
            address: new Address(),
            licenses: [
                new License(),
                new License(),
                new License(),
            ],
            dob: 'test-dob',
            ssn: 'test-ssn',
            lastUpdated: 'test-lastUpdated',
            status: LicenseeStatus.ACTIVE,
        };
        const licensee = new Licensee(data);

        // Test field values
        expect(licensee).to.be.an.instanceof(Licensee);
        expect(licensee.id).to.equal(data.id);
        expect(licensee.firstName).to.equal(data.firstName);
        expect(licensee.middleName).to.equal(data.middleName);
        expect(licensee.lastName).to.equal(data.lastName);
        expect(licensee.address).to.be.an.instanceof(Address);
        expect(licensee.licenses).to.be.an('array').with.length(3);
        expect(licensee.licenses[0]).to.be.an.instanceof(License);
        expect(licensee.dob).to.equal(data.dob);
        expect(licensee.ssn).to.equal(data.ssn);
        expect(licensee.lastUpdated).to.equal(data.lastUpdated);
        expect(licensee.status).to.equal(data.status);

        // Test methods
        expect(licensee.nameDisplay()).to.equal(`${data.firstName} ${data.lastName}`);
        expect(licensee.residenceLocation()).to.equal('');
        expect(licensee.dobDisplay()).to.equal('Invalid date');
        expect(licensee.lastUpdatedDisplay()).to.equal('Invalid date');
        expect(licensee.lastUpdatedDisplayRelative()).to.equal('Invalid date');
        expect(licensee.licenseStatesDisplay()).to.equal('');
        expect(licensee.practicingLocationsAll()).to.equal('');
        expect(licensee.practicingLocationsDisplay()).to.equal('');
        expect(licensee.ssnMaskedFull()).to.equal(data.ssn);
        expect(licensee.ssnMaskedPartial()).to.equal('test-ss-ssn');
    });
    it('should create a Licensee with specific values through serializer', () => {
        const data = {
            providerId: 'test-id',
            givenName: 'test-firstName',
            middleName: 'test-middleName',
            familyName: 'test-lastName',
            dateOfBirth: moment().format(serverDateFormat),
            ssn: '000-00-0000',
            jurisdiction: 'co',
            homeStateStreet1: 'test-street1',
            homeStateStreet2: 'test-street2',
            homeStateCity: 'test-city',
            homeStatePostalCode: 'test-zip',
            dateOfIssuance: 'test-issueDate',
            dateOfRenewal: 'test-renewalDate',
            dateOfExpiration: 'test-expireDate',
            licenseType: LicenseType.AUDIOLOGIST,
            dateOfUpdate: moment().format(serverDateFormat),
            status: LicenseeStatus.ACTIVE,
        };
        const licensee = LicenseeSerializer.fromServer(data);

        // Test field values
        expect(licensee).to.be.an.instanceof(Licensee);
        expect(licensee.id).to.equal(data.providerId);
        expect(licensee.firstName).to.equal(data.givenName);
        expect(licensee.middleName).to.equal(data.middleName);
        expect(licensee.lastName).to.equal(data.familyName);
        expect(licensee.address).to.be.an.instanceof(Address);
        expect(licensee.licenses).to.be.an('array').with.length(1);
        expect(licensee.licenses[0]).to.be.an.instanceof(License);
        expect(licensee.dob).to.equal(data.dateOfBirth);
        expect(licensee.ssn).to.equal(data.ssn);
        expect(licensee.lastUpdated).to.equal(data.dateOfUpdate);
        expect(licensee.status).to.equal(data.status);

        // Test methods
        expect(licensee.nameDisplay()).to.equal(`${data.givenName} ${data.familyName}`);
        expect(licensee.residenceLocation()).to.equal('Colorado');
        expect(licensee.dobDisplay()).to.equal(
            moment(data.dateOfBirth, serverDateFormat).format(displayDateFormat)
        );
        expect(licensee.lastUpdatedDisplay()).to.equal(
            moment(data.dateOfUpdate, serverDateFormat).format(displayDateFormat)
        );
        expect(licensee.lastUpdatedDisplayRelative()).to.be.a('string').that.is.not.empty;
        expect(licensee.licenseStatesDisplay()).to.equal('Colorado');
        expect(licensee.practicingLocationsAll()).to.equal('Colorado');
        expect(licensee.practicingLocationsDisplay()).to.equal('Colorado');
        expect(licensee.ssnMaskedFull()).to.equal(`###-##-####`);
        expect(licensee.ssnMaskedPartial()).to.equal(`###-##-0000`);
    });
    it('should serialize a Licensee for transmission to server', () => {
        const licensee = LicenseeSerializer.fromServer({
            providerId: 'test-id',
            givenName: 'test-firstName',
            middleName: 'test-middleName',
            familyName: 'test-lastName',
            dateOfBirth: moment().format(serverDateFormat),
            ssn: '000-00-0000',
            jurisdiction: 'co',
            homeStateStreet1: 'test-street1',
            homeStateStreet2: 'test-street2',
            homeStateCity: 'test-city',
            homeStatePostalCode: 'test-zip',
            dateOfIssuance: 'test-issueDate',
            dateOfRenewal: 'test-renewalDate',
            dateOfExpiration: 'test-expireDate',
            licenseType: LicenseType.AUDIOLOGIST,
            dateOfUpdate: moment().format(serverDateFormat),
            status: LicenseeStatus.ACTIVE,
        });
        const transmit = LicenseeSerializer.toServer(licensee);

        expect(transmit.id).to.equal(licensee.id);
    });
});
