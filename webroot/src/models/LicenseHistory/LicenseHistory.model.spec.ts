//
//  LicenseHistory.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/8/2024.
//

import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';
import { LicenseHistory } from '@models/LicenseHistory/LicenseHistory.model';
import { LicenseHistoryItem } from '@models/LicenseHistoryItem/LicenseHistoryItem.model';
import i18n from '@/i18n';

chai.use(chaiMatchPattern);

const { expect } = chai;

describe('LicenseHistory model', () => {
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
    it('should create a LicenseHistory with expected defaults', () => {
        const licenseHistory = new LicenseHistory();

        // Test field values
        expect(licenseHistory).to.be.an.instanceof(LicenseHistory);
        expect(licenseHistory.providerId).to.equal(null);
        expect(licenseHistory.compact).to.equal(null);
        expect(licenseHistory.jurisdiction).to.equal(null);
        expect(licenseHistory.licenseType).to.equal(null);
        expect(licenseHistory.privilegeId).to.equal(null);
        expect(licenseHistory.events).to.matchPattern([]);

        expect(licenseHistory.licenseTypeAbbreviation()).to.equal('');
    });
    it('should create a LicenseHistory with specific values', () => {
        const data = {
            providerId: '1b6bcfa2-28ad-4f9a-acf4-bba771f6cc11',
            compact: 'aslp',
            jurisdiction: 'ky',
            licenseType: 'speech-language pathologist',
            privilegeId: 'SLP-KY-26',
            events: [
                new LicenseHistoryItem({
                    type: 'privilegeUpdate',
                    updateType: 'renewal',
                    dateOfUpdate: '2025-05-01T15:27:35+00:00',
                    effectiveDate: '2025-05-01',
                    createDate: '2025-05-01T15:27:35+00:00',
                    serverNote: 'Note'
                })
            ]
        };
        const licenseHistory = new LicenseHistory(data);

        // Test field values
        expect(licenseHistory).to.be.an.instanceof(LicenseHistory);
        expect(licenseHistory.providerId).to.equal(data.providerId);
        expect(licenseHistory.compact).to.equal(data.compact);
        expect(licenseHistory.jurisdiction).to.equal(data.jurisdiction);
        expect(licenseHistory.licenseType).to.equal(data.licenseType);
        expect(licenseHistory.privilegeId).to.equal(data.privilegeId);
        // expect(licenseHistory.events).to.matchPattern([{
        //     type: 'privilegeUpdate',
        //     updateType: 'renewal',
        //     dateOfUpdate: '2025-05-01T15:27:35+00:00',
        //     effectiveDate: '2025-05-01',
        //     createDate: '2025-05-01T15:27:35+00:00',
        //     serverNote: 'Note'
        // }]);

        expect(licenseHistory.licenseTypeAbbreviation()).to.equal('SLP');
    });
    // it('should create a LicenseHistory with specific values through serializer', () => {
    //     const data = {
    //         type: 'privilegeUpdate',
    //         updateType: 'deactivation',
    //         dateOfUpdate: '2023-08-29',
    //         previous: {
    //             compactTransactionId: '123',
    //             dateOfIssuance: '2022-08-29',
    //             dateOfRenewal: '2023-08-29',
    //             dateOfUpdate: '2023-08-29',
    //             dateOfExpiration: '2025-08-29',
    //         },
    //         updatedValues: {
    //             compactTransactionId: '124',
    //             dateOfIssuance: '2022-08-29',
    //             dateOfRenewal: '2024-08-29',
    //             dateOfExpiration: '2025-08-29',
    //         }
    //     };
    //     const licenseHistory = LicenseHistorySerializer.fromServer(data);

    //     expect(licenseHistory).to.be.an.instanceof(LicenseHistory);
    //     expect(licenseHistory.type).to.equal(data.type);
    //     expect(licenseHistory.updateType).to.equal(data.updateType);
    //     expect(licenseHistory.previousValues).to.matchPattern({
    //         compactTransactionId: '123',
    //         dateOfIssuance: '2022-08-29',
    //         dateOfRenewal: '2023-08-29',
    //         dateOfUpdate: '2023-08-29',
    //         dateOfExpiration: '2025-08-29',
    //     });
    //     expect(licenseHistory.updatedValues).to.matchPattern({
    //         compactTransactionId: '124',
    //         dateOfIssuance: '2022-08-29',
    //         dateOfRenewal: '2024-08-29',
    //         dateOfExpiration: '2025-08-29',
    //     });

    //     expect(licenseHistory.dateOfUpdateDisplay()).to.equal('8/29/2023');
    //     expect(licenseHistory.isActivatingEvent()).to.equal(false);
    //     expect(licenseHistory.isDeactivatingEvent()).to.equal(true);
    //     expect(licenseHistory.updateTypeDisplay()).to.equal('Deactivation');
    // });
});
