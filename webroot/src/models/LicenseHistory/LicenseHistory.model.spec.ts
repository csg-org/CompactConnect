//
//  LicenseHistoryItem.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/8/2024.
//

import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';
import {
    LicenseHistoryItem,
    LicenseHistoryItemSerializer
} from '@models/LicenseHistoryItem/LicenseHistoryItem.model';
import i18n from '@/i18n';

chai.use(chaiMatchPattern);

const { expect } = chai;

describe('LicenseHistoryItem model', () => {
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
    it('should create a LicenseHistoryItem with expected defaults', () => {
        const licenseHistoryItem = new LicenseHistoryItem();

        // Test field values
        expect(licenseHistoryItem).to.be.an.instanceof(LicenseHistoryItem);
        expect(licenseHistoryItem.type).to.equal(null);
        expect(licenseHistoryItem.updateType).to.equal('');
        expect(licenseHistoryItem.previousValues).to.matchPattern({});
        expect(licenseHistoryItem.updatedValues).to.matchPattern({});

        expect(licenseHistoryItem.dateOfUpdateDisplay()).to.equal('');
        expect(licenseHistoryItem.isActivatingEvent()).to.equal(false);
        expect(licenseHistoryItem.isDeactivatingEvent()).to.equal(false);
        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('Unknown');
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

        expect(licenseHistoryItem.dateOfUpdateDisplay()).to.equal('8/29/2023');
        expect(licenseHistoryItem.isActivatingEvent()).to.equal(true);
        expect(licenseHistoryItem.isDeactivatingEvent()).to.equal(false);
        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('Renewal');
    });
    it('should create a LicenseHistoryItem with specific values through serializer', () => {
        const data = {
            type: 'privilegeUpdate',
            updateType: 'deactivation',
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

        expect(licenseHistoryItem.dateOfUpdateDisplay()).to.equal('8/29/2023');
        expect(licenseHistoryItem.isActivatingEvent()).to.equal(false);
        expect(licenseHistoryItem.isDeactivatingEvent()).to.equal(true);
        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('Deactivation');
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

        expect(licenseHistoryItem.dateOfUpdateDisplay()).to.equal('8/29/2023');
        expect(licenseHistoryItem.isActivatingEvent()).to.equal(true);
        expect(licenseHistoryItem.isDeactivatingEvent()).to.equal(false);
        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('Renewal');
    });
});
