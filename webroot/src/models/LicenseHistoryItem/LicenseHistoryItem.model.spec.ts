//
//  LicenseHistoryItem.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/8/2024.
//

import chaiMatchPattern from 'chai-match-pattern';
import { use, expect } from 'chai';
import {
    LicenseHistoryItem,
    LicenseHistoryItemSerializer
} from '@models/LicenseHistoryItem/LicenseHistoryItem.model';
import { State } from '@models/State/State.model';
import i18n from '@/i18n';

use(chaiMatchPattern);

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
        i18n.global.locale.value = 'en';
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
        expect(licenseHistoryItem.npdbCategories).to.equal(null);
        expect(licenseHistoryItem.encumbranceType).to.equal(null);
        expect(licenseHistoryItem.licenseScope).to.equal(null);
        expect(licenseHistoryItem.state).to.be.an.instanceof(State);
        expect(licenseHistoryItem.effectiveDateDisplay()).to.equal('');
        expect(licenseHistoryItem.effectiveDateSortValue()).to.equal(0);
        expect(licenseHistoryItem.createDateDisplay()).to.equal('');
        expect(licenseHistoryItem.isActivatingEvent()).to.equal(false);
        expect(licenseHistoryItem.isDeactivatingEvent()).to.equal(false);
        expect(licenseHistoryItem.isDisciplineEvent()).to.equal(false);
        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('Unknown');
        expect(licenseHistoryItem.encumbranceTypeName()).to.equal('');
        expect(licenseHistoryItem.npdbTypeNames()).to.matchPattern([]);
        expect(licenseHistoryItem.noteDisplay()).to.equal('');
    });
    it('should create a LicenseHistoryItem with specific values', () => {
        const data = {
            type: 'privilegeUpdate',
            updateType: 'renewal',
            dateOfUpdate: '2025-05-01T15:27:35+00:00',
            effectiveDate: '2025-05-01T15:27:35+00:00',
            createDate: '2025-05-01T15:27:35+00:00',
            serverNote: 'Note',
            encumbranceType: 'fine',
            npdbCategories: ['Non-compliance With Requirements'],
            state: new State({ abbrev: 'oh' }),
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
        expect(licenseHistoryItem.encumbranceType).to.equal(data.encumbranceType);
        expect(licenseHistoryItem.npdbCategories).to.matchPattern(data.npdbCategories);
        expect(licenseHistoryItem.state).to.be.an.instanceof(State);
        expect(licenseHistoryItem.state.abbrev).to.equal('oh');
        expect(licenseHistoryItem.effectiveDateDisplay()).to.equal('5/1/2025');
        expect(licenseHistoryItem.createDateDisplay()).to.equal('5/1/2025');
        expect(licenseHistoryItem.isActivatingEvent()).to.equal(true);
        expect(licenseHistoryItem.isDeactivatingEvent()).to.equal(false);
        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('Renewal');
        expect(licenseHistoryItem.encumbranceTypeName()).to.equal('Fine');
        expect(licenseHistoryItem.npdbTypeNames()).to.matchPattern(['Non-compliance With Requirements']);
        expect(licenseHistoryItem.noteDisplay()).to.equal('Note');
    });
    it('should create a LicenseHistoryItem with specific values through serializer', () => {
        const data = {
            type: 'privilegeUpdate',
            updateType: 'renewal',
            dateOfUpdate: '2025-05-01T15:27:35+00:00',
            effectiveDate: '2025-05-01T15:27:35+00:00',
            createDate: '2025-05-01T15:27:35+00:00',
            note: 'Note',
            jurisdiction: 'ne',
        };
        const licenseHistoryItem = LicenseHistoryItemSerializer.fromServer(data);

        expect(licenseHistoryItem).to.be.an.instanceof(LicenseHistoryItem);
        expect(licenseHistoryItem.type).to.equal(data.type);
        expect(licenseHistoryItem.updateType).to.equal(data.updateType);
        expect(licenseHistoryItem.dateOfUpdate).to.equal(data.dateOfUpdate);
        expect(licenseHistoryItem.createDate).to.equal(data.createDate);
        expect(licenseHistoryItem.effectiveDate).to.equal(data.effectiveDate);
        expect(licenseHistoryItem.serverNote).to.equal(data.note);
        expect(licenseHistoryItem.state).to.be.an.instanceof(State);
        expect(licenseHistoryItem.state.abbrev).to.equal(data.jurisdiction);
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
        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('Home Jurisdiction Change');
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
    it('should create a LicenseHistoryItem with correct display values for an encumbrance with npdbCategories', () => {
        const data = {
            type: 'privilegeUpdate',
            updateType: 'encumbrance',
            dateOfUpdate: '2025-05-01T15:27:35+00:00',
            effectiveDate: '2025-05-01T15:27:35+00:00',
            createDate: '2025-05-01T15:27:35+00:00',
            encumbranceType: 'required supervision',
            npdbCategories: ['Misconduct or Abuse', 'Non-compliance With Requirements'],
            jurisdiction: 'tx',
        };
        const licenseHistoryItem = LicenseHistoryItemSerializer.fromServer(data);

        expect(licenseHistoryItem).to.be.an.instanceof(LicenseHistoryItem);
        expect(licenseHistoryItem.type).to.equal(data.type);
        expect(licenseHistoryItem.updateType).to.equal(data.updateType);
        expect(licenseHistoryItem.dateOfUpdate).to.equal(data.dateOfUpdate);
        expect(licenseHistoryItem.createDate).to.equal(data.createDate);
        expect(licenseHistoryItem.effectiveDate).to.equal(data.effectiveDate);
        expect(licenseHistoryItem.encumbranceType).to.equal(data.encumbranceType);
        expect(licenseHistoryItem.npdbCategories).to.deep.equal(data.npdbCategories);
        expect(licenseHistoryItem.state.abbrev).to.equal(data.jurisdiction);
        expect(licenseHistoryItem.effectiveDateDisplay()).to.equal('5/1/2025');
        expect(licenseHistoryItem.createDateDisplay()).to.equal('5/1/2025');
        expect(licenseHistoryItem.isActivatingEvent()).to.equal(false);
        expect(licenseHistoryItem.isDeactivatingEvent()).to.equal(true);
        expect(licenseHistoryItem.isDisciplineEvent()).to.equal(true);
        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('Encumbrance');
        expect(licenseHistoryItem.encumbranceTypeName()).to.equal('Required supervision');
        expect(licenseHistoryItem.npdbTypeNames()).to.matchPattern([
            'Misconduct or Abuse',
            'Non-compliance With Requirements',
        ]);
        expect(licenseHistoryItem.noteDisplay()).to.equal('Misconduct or Abuse, Non-compliance With Requirements');
    });
    it('should create a LicenseHistoryItem with correct display values for an encumbrance with single category', () => {
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
    it('should create a LicenseHistoryItem with correct display values for a liftingEncumbrance', () => {
        const data = {
            type: 'licenseUpdate',
            updateType: 'liftingEncumbrance',
            effectiveDate: '2023-01-05',
            createDate: '2023-01-05T09:00:00+00:00',
            jurisdiction: 'ne',
        };
        const licenseHistoryItem = LicenseHistoryItemSerializer.fromServer(data);

        expect(licenseHistoryItem).to.be.an.instanceof(LicenseHistoryItem);
        expect(licenseHistoryItem.updateType).to.equal(data.updateType);
        expect(licenseHistoryItem.effectiveDate).to.equal(data.effectiveDate);
        expect(licenseHistoryItem.createDate).to.equal(data.createDate);
        expect(licenseHistoryItem.state.abbrev).to.equal(data.jurisdiction);
        expect(licenseHistoryItem.effectiveDateDisplay()).to.equal('1/5/2023');
        expect(licenseHistoryItem.isActivatingEvent()).to.equal(false);
        expect(licenseHistoryItem.isDeactivatingEvent()).to.equal(false);
        expect(licenseHistoryItem.isDisciplineEvent()).to.equal(false);
        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('Encumbrance lifted');
        expect(licenseHistoryItem.encumbranceTypeName()).to.equal('');
        expect(licenseHistoryItem.npdbTypeNames()).to.matchPattern([]);
        expect(licenseHistoryItem.noteDisplay()).to.equal('');
    });
    it('should create a LicenseHistoryItem with correct display values for a lifting_encumbrance', () => {
        const licenseHistoryItem = new LicenseHistoryItem({
            updateType: 'lifting_encumbrance',
        });

        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('Privilege Unencumbered');
    });
    it('should display License issuance with scope for a licenseUpdate issuance event', () => {
        const licenseHistoryItem = new LicenseHistoryItem({
            type: 'licenseUpdate',
            updateType: 'issuance',
            licenseScope: 'multi-state',
        });

        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('License issuance (multi state)');
    });
    it('should display License issuance without scope when licenseScope is missing', () => {
        const licenseHistoryItem = new LicenseHistoryItem({
            type: 'licenseUpdate',
            updateType: 'issuance',
        });

        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('License issuance');
    });
    it('should display Privilege issuance for a privilegeUpdate issuance event', () => {
        const licenseHistoryItem = new LicenseHistoryItem({
            type: 'privilegeUpdate',
            updateType: 'issuance',
        });

        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('Privilege issuance');
    });
    it('should sort by date-only so same calendar day values are equal', () => {
        const morningEvent = new LicenseHistoryItem({
            effectiveDate: '2026-08-03T08:15:12+00:00',
        });
        const eveningEvent = new LicenseHistoryItem({
            effectiveDate: '2026-08-03T22:15:12+00:00',
        });
        const dateOnlyEvent = new LicenseHistoryItem({
            effectiveDate: '2026-08-03',
        });

        expect(morningEvent.effectiveDateSortValue()).to.equal(eveningEvent.effectiveDateSortValue());
        expect(morningEvent.effectiveDateSortValue()).to.equal(dateOnlyEvent.effectiveDateSortValue());
    });
    it('should fall back to dateOfUpdate when effectiveDate is missing through serializer', () => {
        const data = {
            type: 'privilegeUpdate',
            updateType: 'deactivation',
            dateOfUpdate: '2022-03-19T22:02:17+00:00',
        };
        const licenseHistoryItem = LicenseHistoryItemSerializer.fromServer(data);

        expect(licenseHistoryItem.effectiveDate).to.equal(data.dateOfUpdate);
        expect(licenseHistoryItem.effectiveDateDisplay()).to.equal('3/19/2022');
    });
    it('should create a LicenseHistoryItem without Vue i18n helpers', () => {
        const previousVue = (window as any).Vue;

        (window as any).Vue = undefined;

        const licenseHistoryItem = new LicenseHistoryItem({
            updateType: 'renewal',
        });

        (window as any).Vue = previousVue;

        expect(licenseHistoryItem).to.be.an.instanceof(LicenseHistoryItem);
        expect(licenseHistoryItem.updateType).to.equal('renewal');
        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('');
        expect(licenseHistoryItem.encumbranceTypeName()).to.equal('');
        expect(licenseHistoryItem.npdbTypeName('Misconduct or Abuse')).to.equal('Misconduct or Abuse');
        expect(licenseHistoryItem.npdbTypeNames()).to.matchPattern([]);
    });
    it('should fall back when translation helpers return empty values', () => {
        const licenseHistoryItem = new LicenseHistoryItem({
            updateType: 'issuance',
            encumbranceType: 'fine',
            npdbCategories: ['Unknown Category', ''],
        });

        licenseHistoryItem.$tm = () => null;
        licenseHistoryItem.$t = () => '';

        expect(licenseHistoryItem.updateTypeDisplay()).to.equal('');
        expect(licenseHistoryItem.encumbranceTypeName()).to.equal('');
        expect(licenseHistoryItem.npdbTypeName('Unknown Category')).to.equal('Unknown Category');
        expect(licenseHistoryItem.npdbTypeName('')).to.equal('');
        expect(licenseHistoryItem.npdbTypeNames()).to.matchPattern(['Unknown Category']);
    });
    it('should create a LicenseHistoryItem with corrected display values for expired and deactivation events', () => {
        const expiredItem = new LicenseHistoryItem({ updateType: 'expired' });
        const deactivationItem = new LicenseHistoryItem({ updateType: 'deactivation' });

        expect(expiredItem.isDeactivatingEvent()).to.equal(true);
        expect(deactivationItem.isDeactivatingEvent()).to.equal(true);
    });
    it('should keep the server note for an encumbrance without npdbCategories', () => {
        const licenseHistoryItem = new LicenseHistoryItem({
            updateType: 'encumbrance',
            serverNote: 'Server note',
            npdbCategories: [],
        });

        expect(licenseHistoryItem.noteDisplay()).to.equal('Server note');
    });
});
