//
//  LicenseHistoryItem.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/8/2024.
//

import { expect } from 'chai';
import {
    LicenseHistoryItem,
    LicenseHistoryItemSerializer
} from '@models/LicenseHistoryItem/LicenseHistoryItem.model';

describe('LicenseHistoryItem model', () => {
    it('should create a LicenseHistoryItem with expected defaults', () => {
        const licenseHistoryItem = new LicenseHistoryItem();

        // Test field values
        expect(licenseHistoryItem).to.be.an.instanceof(LicenseHistoryItem);
        expect(licenseHistoryItem.type).to.equal(null);
        expect(licenseHistoryItem.updateType).to.equal(null);
        expect(licenseHistoryItem.previousValues).to.matchPattern({});
        expect(licenseHistoryItem.updatedValues).to.matchPattern({});
    });
    it('should create a LicenseHistoryItem with specific values', () => {
        const data = {
            type: 'privilegeUpdate',
            updateType: 'renewal',
            dateOfUpdate: '2023-08-29',
            previousValues: {
                compactTransactionId: '123',
                dateOfIssuance: '2022-08-29',
                dateOfRenewal: '2023-08-29',
                dateOfUpdate: '2023-08-29',
                dateOfExpiration: '2025-08-29',
            },
            updatedValues: {
                compactTransactionId: '124',
                dateOfIssuance: '2022-08-29',
                dateOfRenewal: '2024-08-29',
                dateOfExpiration: '2025-08-29',
            }
        };
        const licenseHistoryItem = new LicenseHistoryItem(data);

        // Test field values
        expect(licenseHistoryItem).to.be.an.instanceof(LicenseHistoryItem);
        expect(licenseHistoryItem.type).to.equal(data.type);
        expect(licenseHistoryItem.updateType).to.equal(data.updateType);
        expect(licenseHistoryItem.previousValues).to.matchPattern({
            compactTransactionId: '123',
            dateOfIssuance: '2022-08-29',
            dateOfRenewal: '2023-08-29',
            dateOfUpdate: '2023-08-29',
            dateOfExpiration: '2025-08-29',
        });
        expect(licenseHistoryItem.updatedValues).to.matchPattern({
            compactTransactionId: '124',
            dateOfIssuance: '2022-08-29',
            dateOfRenewal: '2024-08-29',
            dateOfExpiration: '2025-08-29',
        });
    });
    it('should create a LicenseHistoryItem with specific values through serializer', () => {
        const data = {
            type: 'privilegeUpdate',
            updateType: 'renewal',
            dateOfUpdate: '2023-08-29',
            previous: {
                compactTransactionId: '123',
                dateOfIssuance: '2022-08-29',
                dateOfRenewal: '2023-08-29',
                dateOfUpdate: '2023-08-29',
                dateOfExpiration: '2025-08-29',
            },
            updatedValues: {
                compactTransactionId: '124',
                dateOfIssuance: '2022-08-29',
                dateOfRenewal: '2024-08-29',
                dateOfExpiration: '2025-08-29',
            }
        };
        const licenseHistoryItem = LicenseHistoryItemSerializer.fromServer(data);

        expect(licenseHistoryItem).to.be.an.instanceof(LicenseHistoryItem);
        expect(licenseHistoryItem.type).to.equal(data.type);
        expect(licenseHistoryItem.updateType).to.equal(data.updateType);
        expect(licenseHistoryItem.previousValues).to.matchPattern({
            compactTransactionId: '123',
            dateOfIssuance: '2022-08-29',
            dateOfRenewal: '2023-08-29',
            dateOfUpdate: '2023-08-29',
            dateOfExpiration: '2025-08-29',
        });
        expect(licenseHistoryItem.updatedValues).to.matchPattern({
            compactTransactionId: '124',
            dateOfIssuance: '2022-08-29',
            dateOfRenewal: '2024-08-29',
            dateOfExpiration: '2025-08-29',
        });
    });
    it('should create a LicenseHistoryItem with empty values through serializer', () => {
        const data = {
            type: 'privilegeUpdate',
            updateType: 'renewal',
            dateOfUpdate: '2023-08-29',
        };
        const licenseHistoryItem = LicenseHistoryItemSerializer.fromServer(data);

        expect(licenseHistoryItem).to.be.an.instanceof(LicenseHistoryItem);
        expect(licenseHistoryItem.type).to.equal(data.type);
        expect(licenseHistoryItem.updateType).to.equal(data.updateType);
        expect(licenseHistoryItem.previousValues).to.matchPattern({
            compactTransactionId: '',
            dateOfIssuance: '',
            dateOfRenewal: '',
            dateOfUpdate: '',
            dateOfExpiration: '',
        });
        expect(licenseHistoryItem.updatedValues).to.matchPattern({
            compactTransactionId: '',
            dateOfIssuance: '',
            dateOfRenewal: '',
            dateOfExpiration: '',
        });
    });
});
