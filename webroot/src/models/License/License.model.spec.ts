//
//  License.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/8/2024.
//

import { expect } from 'chai';
import { serverDateFormat, displayDateFormat } from '@/app.config';
import { License, LicenseType, LicenseSerializer } from '@models/License/License.model';
import { State } from '@models/State/State.model';
import moment from 'moment';

describe('License model', () => {
    it('should create a License with expected defaults', () => {
        const license = new License();

        // Test field values
        expect(license).to.be.an.instanceof(License);
        expect(license.id).to.equal(null);
        expect(license.issueState).to.be.an.instanceof(State);
        expect(license.issueDate).to.equal(null);
        expect(license.renewalDate).to.equal(null);
        expect(license.expireDate).to.equal(null);
        expect(license.type).to.equal(null);

        // Test methods
        expect(license.issueDateDisplay()).to.equal('');
        expect(license.renewalDateDisplay()).to.equal('');
        expect(license.expireDateDisplay()).to.equal('');
        expect(license.isExpired()).to.equal(false);
    });
    it('should create a License with specific values', () => {
        const data = {
            id: 'test-id',
            issueState: new State(),
            issueDate: 'test-issueDate',
            renewalDate: 'test-renewalDate',
            expireDate: 'test-expireDate',
            type: LicenseType.AUDIOLOGIST,
        };
        const license = new License(data);

        // Test field values
        expect(license).to.be.an.instanceof(License);
        expect(license.id).to.equal(data.id);
        expect(license.issueState).to.be.an.instanceof(State);
        expect(license.issueDate).to.equal(data.issueDate);
        expect(license.renewalDate).to.equal(data.renewalDate);
        expect(license.expireDate).to.equal(data.expireDate);
        expect(license.type).to.equal(data.type);

        // Test methods
        expect(license.issueDateDisplay()).to.equal('Invalid date');
        expect(license.renewalDateDisplay()).to.equal('Invalid date');
        expect(license.expireDateDisplay()).to.equal('Invalid date');
        expect(license.isExpired()).to.equal(false);
    });
    it('should create a License with specific values through serializer', () => {
        const data = {
            id: 'test-id',
            issueState: new State(),
            issueDate: moment().format(serverDateFormat),
            renewalDate: moment().format(serverDateFormat),
            expireDate: moment().subtract(1, 'day').format(serverDateFormat),
            type: LicenseType.AUDIOLOGIST,
        };
        const license = LicenseSerializer.fromServer(data);

        // Test field values
        expect(license).to.be.an.instanceof(License);
        expect(license.id).to.equal(data.id);
        expect(license.issueState).to.be.an.instanceof(State);
        expect(license.issueDate).to.equal(data.issueDate);
        expect(license.renewalDate).to.equal(data.renewalDate);
        expect(license.expireDate).to.equal(data.expireDate);
        expect(license.type).to.equal(data.type);

        // Test methods
        expect(license.issueDateDisplay()).to.equal(
            moment(data.issueDate, serverDateFormat).format(displayDateFormat)
        );
        expect(license.renewalDateDisplay()).to.equal(
            moment(data.renewalDate, serverDateFormat).format(displayDateFormat)
        );
        expect(license.expireDateDisplay()).to.equal(
            moment(data.expireDate, serverDateFormat).format(displayDateFormat)
        );
        expect(license.isExpired()).to.equal(true);
    });
    it('should serialize a License for transmission to server', () => {
        const license = LicenseSerializer.fromServer({
            id: 'test-id',
            issueState: new State(),
            issueDate: moment().format(serverDateFormat),
            renewalDate: moment().format(serverDateFormat),
            expireDate: moment().subtract(1, 'day').format(serverDateFormat),
            type: LicenseType.AUDIOLOGIST,
        });
        const transmit = LicenseSerializer.toServer(license);

        expect(transmit.id).to.equal(license.id);
    });
});
