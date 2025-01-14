//
//  User.model.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/2020.
//
import { MilitaryAffiliationSerializer, MilitaryAffiliation } from '@models/MilitaryAffiliation/MilitaryAffiliation.model';
import { dateDisplay } from '@models/_formatters/date';
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
    it('should create a MilitaryAffiliation with expected defaults', () => {
        const militaryAffiliation = new MilitaryAffiliation();

        expect(militaryAffiliation).to.be.an.instanceof(MilitaryAffiliation);
        expect(militaryAffiliation.affiliationType).to.equal(null);
        expect(militaryAffiliation.compact).to.equal(null);
        expect(militaryAffiliation.dateOfUpdate).to.equal(null);
        expect(militaryAffiliation.dateOfUpload).to.equal(null);
        expect(militaryAffiliation.documentKeys).to.equal(null);
        expect(militaryAffiliation.fileNames).to.equal(null);
        expect(militaryAffiliation.status).to.equal(null);

        // Test methods
        expect(militaryAffiliation.dateOfUpdateDisplay()).to.equal('');
        expect(militaryAffiliation.dateOfUploadDisplay()).to.equal('');
    });
    it('should create a MilitaryAffiliation with specific values', () => {
        const data = {
            affiliationType: 'affiliationType',
            compact: 'aslp',
            dateOfUpdate: '2025-01-07T23:50:17+00:00',
            dateOfUpload: '2025-01-03T23:50:17+00:00',
            documentKeys: ['key'],
            fileNames: ['file.png'],
            status: 'active'
        };

        const militaryAffiliation = new MilitaryAffiliation(data);

        expect(militaryAffiliation).to.be.an.instanceof(MilitaryAffiliation);
        expect(militaryAffiliation.affiliationType).to.equal(data.affiliationType);
        expect(militaryAffiliation.compact).to.equal(data.compact);
        expect(militaryAffiliation.dateOfUpdate).to.equal(data.dateOfUpdate);
        expect(militaryAffiliation.dateOfUpload).to.equal(data.dateOfUpload);
        expect(militaryAffiliation.documentKeys).to.matchPattern(data.documentKeys);
        expect(militaryAffiliation.fileNames).to.matchPattern(data.fileNames);
        expect(militaryAffiliation.status).to.equal(data.status);

        // Test methods
        expect(militaryAffiliation.dateOfUpdateDisplay()).to.equal(dateDisplay(data.dateOfUpdate));
        expect(militaryAffiliation.dateOfUploadDisplay()).to.equal(dateDisplay(data.dateOfUpload));
    });
    it('should create a MilitaryAffiliation with specific values through MilitaryAffiliation serializer', () => {
        const data = {
            affiliationType: 'affiliationType',
            compact: 'aslp',
            dateOfUpdate: '2025-01-07T23:50:17+00:00',
            dateOfUpload: '2025-01-03T23:50:17+00:00',
            documentKeys: ['key'],
            fileNames: ['file.png'],
            status: 'active'
        };

        const militaryAffiliation = MilitaryAffiliationSerializer.fromServer(data);

        expect(militaryAffiliation).to.be.an.instanceof(MilitaryAffiliation);
        expect(militaryAffiliation.affiliationType).to.equal(data.affiliationType);
        expect(militaryAffiliation.compact).to.equal(data.compact);
        expect(militaryAffiliation.dateOfUpdate).to.equal(data.dateOfUpdate);
        expect(militaryAffiliation.dateOfUpload).to.equal(data.dateOfUpload);
        expect(militaryAffiliation.documentKeys).to.matchPattern(data.documentKeys);
        expect(militaryAffiliation.fileNames).to.matchPattern(data.fileNames);
        expect(militaryAffiliation.status).to.equal(data.status);

        // Test methods
        expect(militaryAffiliation.dateOfUpdateDisplay()).to.equal(dateDisplay(data.dateOfUpdate));
        expect(militaryAffiliation.dateOfUploadDisplay()).to.equal(dateDisplay(data.dateOfUpload));
    });
});
