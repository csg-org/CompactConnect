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
        expect(licenseHistoryItem.dateOfUpdate).to.equal(null);
        expect(licenseHistoryItem.createDate).to.equal(null);
        expect(licenseHistoryItem.effectiveDate).to.equal(null);
        expect(licenseHistoryItem.serverNote).to.equal(null);
        expect(licenseHistoryItem.effectiveDateDisplay()).to.equal('');
        expect(licenseHistoryItem.createDateDisplay()).to.equal('');
        expect(licenseHistoryItem.isActivatingEvent()).to.equal(false);
        expect(licenseHistoryItem.isDeactivatingEvent()).to.equal(false);
        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('Unknown');
        expect(licenseHistoryItem.noteDisplay()).to.equal('');
    });
    it('should create a LicenseHistoryItem with specific values', () => {
        const data = {
            type: 'privilegeUpdate',
            updateType: 'renewal',
            dateOfUpdate: '2025-05-01T15:27:35+00:00',
            effectiveDate: '2025-05-01T15:27:35+00:00',
            createDate: '2025-05-01T15:27:35+00:00',
            serverNote: 'Note'
        };
        const licenseHistoryItem = new LicenseHistoryItem(data);

        // Test field values
        expect(licenseHistoryItem).to.be.an.instanceof(LicenseHistoryItem);
        expect(licenseHistoryItem.type).to.equal(data.type);
        expect(licenseHistoryItem.updateType).to.equal(data.updateType);
        expect(licenseHistoryItem.dateOfUpdate).to.equal(data.dateOfUpdate);
        expect(licenseHistoryItem.createDate).to.equal(data.createDate);
        expect(licenseHistoryItem.effectiveDate).to.equal(data.effectiveDate);
        expect(licenseHistoryItem.serverNote).to.equal(data.serverNote);
        expect(licenseHistoryItem.effectiveDateDisplay()).to.equal('5/1/2025');
        expect(licenseHistoryItem.createDateDisplay()).to.equal('5/1/2025');
        expect(licenseHistoryItem.isActivatingEvent()).to.equal(true);
        expect(licenseHistoryItem.isDeactivatingEvent()).to.equal(false);
        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('Renewal');
        expect(licenseHistoryItem.noteDisplay()).to.equal('Note');
    });
    it('should create a LicenseHistoryItem with specific values through serializer', () => {
        const data = {
            type: 'privilegeUpdate',
            updateType: 'renewal',
            dateOfUpdate: '2025-05-01T15:27:35+00:00',
            effectiveDate: '2025-05-01T15:27:35+00:00',
            createDate: '2025-05-01T15:27:35+00:00',
            note: 'Note'
        };
        const licenseHistoryItem = LicenseHistoryItemSerializer.fromServer(data);

        expect(licenseHistoryItem).to.be.an.instanceof(LicenseHistoryItem);
        expect(licenseHistoryItem.type).to.equal(data.type);
        expect(licenseHistoryItem.updateType).to.equal(data.updateType);
        expect(licenseHistoryItem.dateOfUpdate).to.equal(data.dateOfUpdate);
        expect(licenseHistoryItem.createDate).to.equal(data.createDate);
        expect(licenseHistoryItem.effectiveDate).to.equal(data.effectiveDate);
        expect(licenseHistoryItem.serverNote).to.equal(data.note);
        expect(licenseHistoryItem.effectiveDateDisplay()).to.equal('5/1/2025');
        expect(licenseHistoryItem.createDateDisplay()).to.equal('5/1/2025');
        expect(licenseHistoryItem.isActivatingEvent()).to.equal(true);
        expect(licenseHistoryItem.isDeactivatingEvent()).to.equal(false);
        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('Renewal');
        expect(licenseHistoryItem.noteDisplay()).to.equal('Note');
    });
    it('should create a LicenseHistoryItem with corrected display values for a homeJurisdictionChange', () => {
        const data = {
            type: 'privilegeUpdate',
            updateType: 'homeJurisdictionChange',
            dateOfUpdate: '2025-05-01T15:27:35+00:00',
            effectiveDate: '2025-05-01T15:27:35+00:00',
            createDate: '2025-05-01T15:27:35+00:00',
            note: 'Note'
        };
        const licenseHistoryItem = LicenseHistoryItemSerializer.fromServer(data);

        expect(licenseHistoryItem).to.be.an.instanceof(LicenseHistoryItem);
        expect(licenseHistoryItem.type).to.equal(data.type);
        expect(licenseHistoryItem.updateType).to.equal(data.updateType);
        expect(licenseHistoryItem.dateOfUpdate).to.equal(data.dateOfUpdate);
        expect(licenseHistoryItem.createDate).to.equal(data.createDate);
        expect(licenseHistoryItem.effectiveDate).to.equal(data.effectiveDate);
        expect(licenseHistoryItem.serverNote).to.equal(data.note);
        expect(licenseHistoryItem.effectiveDateDisplay()).to.equal('5/1/2025');
        expect(licenseHistoryItem.createDateDisplay()).to.equal('5/1/2025');
        expect(licenseHistoryItem.isActivatingEvent()).to.equal(false);
        expect(licenseHistoryItem.isDeactivatingEvent()).to.equal(true);
        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('Deactivation');
        expect(licenseHistoryItem.noteDisplay()).to.equal('Deactivated due to home state change');
    });
    it('should create a LicenseHistoryItem with corrected display values for a licenseDeactivation', () => {
        const data = {
            type: 'privilegeUpdate',
            updateType: 'licenseDeactivation',
            dateOfUpdate: '2025-05-01T15:27:35+00:00',
            effectiveDate: '2025-05-01T15:27:35+00:00',
            createDate: '2025-05-01T15:27:35+00:00',
            note: 'Note'
        };
        const licenseHistoryItem = LicenseHistoryItemSerializer.fromServer(data);

        expect(licenseHistoryItem).to.be.an.instanceof(LicenseHistoryItem);
        expect(licenseHistoryItem.type).to.equal(data.type);
        expect(licenseHistoryItem.updateType).to.equal(data.updateType);
        expect(licenseHistoryItem.dateOfUpdate).to.equal(data.dateOfUpdate);
        expect(licenseHistoryItem.createDate).to.equal(data.createDate);
        expect(licenseHistoryItem.effectiveDate).to.equal(data.effectiveDate);
        expect(licenseHistoryItem.serverNote).to.equal(data.note);
        expect(licenseHistoryItem.effectiveDateDisplay()).to.equal('5/1/2025');
        expect(licenseHistoryItem.createDateDisplay()).to.equal('5/1/2025');
        expect(licenseHistoryItem.isActivatingEvent()).to.equal(false);
        expect(licenseHistoryItem.isDeactivatingEvent()).to.equal(true);
        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('Deactivation');
        expect(licenseHistoryItem.noteDisplay()).to.equal('Deactivated due to associated license being deactivated');
    });
    it('should create a LicenseHistoryItem with correct display values for an encumbrance', () => {
        const data = {
            type: 'privilegeUpdate',
            updateType: 'encumbrance',
            dateOfUpdate: '2025-05-01T15:27:35+00:00',
            effectiveDate: '2025-05-01T15:27:35+00:00',
            createDate: '2025-05-01T15:27:35+00:00',
            note: 'Misconduct or Abuse'
        };
        const licenseHistoryItem = LicenseHistoryItemSerializer.fromServer(data);

        expect(licenseHistoryItem).to.be.an.instanceof(LicenseHistoryItem);
        expect(licenseHistoryItem.type).to.equal(data.type);
        expect(licenseHistoryItem.updateType).to.equal(data.updateType);
        expect(licenseHistoryItem.dateOfUpdate).to.equal(data.dateOfUpdate);
        expect(licenseHistoryItem.createDate).to.equal(data.createDate);
        expect(licenseHistoryItem.effectiveDate).to.equal(data.effectiveDate);
        expect(licenseHistoryItem.serverNote).to.equal(data.note);
        expect(licenseHistoryItem.effectiveDateDisplay()).to.equal('5/1/2025');
        expect(licenseHistoryItem.createDateDisplay()).to.equal('5/1/2025');
        expect(licenseHistoryItem.isActivatingEvent()).to.equal(false);
        expect(licenseHistoryItem.isDeactivatingEvent()).to.equal(true);
        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('Encumbrance');
        expect(licenseHistoryItem.noteDisplay()).to.equal('Misconduct or Abuse');
    });
});
