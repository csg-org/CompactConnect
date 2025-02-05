//
//  License.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/8/2024.
//

import { expect } from 'chai';
import { serverDateFormat, displayDateFormat } from '@/app.config';
import {
    License,
    LicenseOccupation,
    LicenseStatus,
    LicenseSerializer
} from '@models/License/License.model';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { State } from '@models/State/State.model';
import { Address } from '@models/Address/Address.model';
import { LicenseHistoryItem } from '@models/LicenseHistoryItem/LicenseHistoryItem.model';
import i18n from '@/i18n';
import moment from 'moment';

describe('License model', () => {
    before(() => {
        const { tm: $tm } = i18n.global;

        (window as any).Vue = {
            config: {
                globalProperties: {
                    $tm,
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
        expect(license.issueState).to.be.an.instanceof(State);
        expect(license.issueDate).to.equal(null);
        expect(license.renewalDate).to.equal(null);
        expect(license.expireDate).to.equal(null);
        expect(license.npi).to.equal(null);
        expect(license.licenseNumber).to.equal(null);
        expect(license.mailingAddress).to.be.an.instanceof(Address);
        expect(license.occupation).to.equal(null);
        expect(license.history).to.matchPattern([]);
        expect(license.statusState).to.equal(LicenseStatus.INACTIVE);
        expect(license.statusCompact).to.equal(LicenseStatus.INACTIVE);

        // Test methods
        expect(license.issueDateDisplay()).to.equal('');
        expect(license.renewalDateDisplay()).to.equal('');
        expect(license.expireDateDisplay()).to.equal('');
        expect(license.isExpired()).to.equal(false);
        expect(license.occupationName()).to.equal('');
    });
    it('should create a License with specific values', () => {
        const data = {
            id: 'test-id',
            compact: new Compact(),
            isPrivilege: true,
            issueState: new State(),
            isHomeState: true,
            issueDate: 'test-issueDate',
            renewalDate: 'test-renewalDate',
            expireDate: 'test-expireDate',
            licenseNumber: 'test-license-number',
            mailingAddress: new Address(),
            npi: 'test-npi',
            occupation: LicenseOccupation.AUDIOLOGIST,
            statusState: LicenseStatus.ACTIVE,
            statusCompact: LicenseStatus.ACTIVE,
            history: [new LicenseHistoryItem()]
        };
        const license = new License(data);

        // Test field values
        expect(license).to.be.an.instanceof(License);
        expect(license.id).to.equal(data.id);
        expect(license.compact).to.be.an.instanceof(Compact);
        expect(license.isPrivilege).to.equal(data.isPrivilege);
        expect(license.issueState).to.be.an.instanceof(State);
        expect(license.issueDate).to.equal(data.issueDate);
        expect(license.renewalDate).to.equal(data.renewalDate);
        expect(license.expireDate).to.equal(data.expireDate);
        expect(license.mailingAddress).to.be.an.instanceof(Address);
        expect(license.npi).to.equal(data.npi);
        expect(license.licenseNumber).to.equal(data.licenseNumber);
        expect(license.occupation).to.equal(data.occupation);
        expect(license.statusState).to.equal(data.statusState);
        expect(license.statusCompact).to.equal(data.statusCompact);
        expect(license.history[0]).to.be.an.instanceof(LicenseHistoryItem);

        // Test methods
        expect(license.issueDateDisplay()).to.equal('Invalid date');
        expect(license.renewalDateDisplay()).to.equal('Invalid date');
        expect(license.expireDateDisplay()).to.equal('Invalid date');
        expect(license.isExpired()).to.equal(false);
        expect(license.occupationName()).to.equal('Audiologist');
    });
    it('should create a License with specific values through serializer', () => {
        const data = {
            id: 'test-id',
            compact: CompactType.ASLP,
            type: 'privilege',
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
            licenseType: LicenseOccupation.AUDIOLOGIST,
            status: LicenseStatus.ACTIVE,
            history: [{
                type: 'privilegeUpdate',
                updateType: 'renewal',
                previous: {
                    compactTransactionId: '123',
                    dateOfIssuance: '2022-08-29',
                    dateOfRenewal: '2023-08-29',
                    dateOfExpiration: '2025-08-29',
                },
                updatedValues: {
                    compactTransactionId: '124',
                    dateOfIssuance: '2022-08-29',
                    dateOfRenewal: '2024-08-29',
                    dateOfExpiration: '2025-08-29',
                }
            }]
        };
        const license = LicenseSerializer.fromServer(data);

        // Test field values
        expect(license).to.be.an.instanceof(License);
        expect(license.id).to.equal(data.id);
        expect(license.compact).to.be.an.instanceof(Compact);
        expect(license.isPrivilege).to.equal(true);
        expect(license.issueState).to.be.an.instanceof(State);
        expect(license.mailingAddress).to.be.an.instanceof(Address);
        expect(license.history[0]).to.be.an.instanceof(LicenseHistoryItem);
        expect(license.issueState.abbrev).to.equal(data.jurisdiction);
        expect(license.issueDate).to.equal(data.dateOfIssuance);
        expect(license.renewalDate).to.equal(data.dateOfRenewal);
        expect(license.expireDate).to.equal(data.dateOfExpiration);
        expect(license.occupation).to.equal(data.licenseType);
        expect(license.statusState).to.equal(data.status);
        expect(license.statusCompact).to.equal(data.status);

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
        expect(license.occupationName()).to.equal('Audiologist');
    });
    it('should create a License with specific values through serializer and not populate history when change is not renewal', () => {
        const data = {
            id: 'test-id',
            compact: CompactType.ASLP,
            type: 'privilege',
            jurisdiction: 'al',
            dateOfIssuance: moment().format(serverDateFormat),
            dateOfRenewal: moment().format(serverDateFormat),
            dateOfExpiration: moment().subtract(1, 'day').format(serverDateFormat),
            npi: 'npi',
            licenseNumber: 'licenseNumber',
            licenseType: LicenseOccupation.AUDIOLOGIST,
            status: LicenseStatus.ACTIVE,
            homeAddressStreet1: 'test-street1',
            homeAddressStreet2: 'test-street2',
            homeAddressCity: 'test-city',
            homeAddressState: 'co',
            homeAddressPostalCode: 'test-zip',
            history: [{
                type: 'privilegeUpdate',
                updateType: 'notrenewal',
                previous: {
                    compactTransactionId: '123',
                    dateOfIssuance: '2022-08-29',
                    dateOfRenewal: '2023-08-29',
                    dateOfExpiration: '2025-08-29',
                },
                updatedValues: {
                    compactTransactionId: '124',
                    dateOfIssuance: '2022-08-29',
                    dateOfRenewal: '2024-08-29',
                    dateOfExpiration: '2025-08-29',
                }
            }]
        };
        const license = LicenseSerializer.fromServer(data);

        // Test field values
        expect(license).to.be.an.instanceof(License);
        expect(license.id).to.equal(data.id);
        expect(license.compact).to.be.an.instanceof(Compact);
        expect(license.isPrivilege).to.equal(true);
        expect(license.issueState).to.be.an.instanceof(State);
        expect(license.history.length).to.equal(0);
        expect(license.mailingAddress).to.be.an.instanceof(Address);
        expect(license.issueState.abbrev).to.equal(data.jurisdiction);
        expect(license.issueDate).to.equal(data.dateOfIssuance);
        expect(license.renewalDate).to.equal(data.dateOfRenewal);
        expect(license.expireDate).to.equal(data.dateOfExpiration);
        expect(license.npi).to.equal(data.npi);
        expect(license.licenseNumber).to.equal(data.licenseNumber);
        expect(license.occupation).to.equal(data.licenseType);
        expect(license.statusState).to.equal(data.status);
        expect(license.statusCompact).to.equal(data.status);

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
        expect(license.occupationName()).to.equal('Audiologist');
    });
});
