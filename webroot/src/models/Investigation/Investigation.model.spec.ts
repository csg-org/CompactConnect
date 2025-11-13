//
//  Investigation.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/28/2025.
//

import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';
import { serverDateFormat, displayDateFormat } from '@/app.config';
import { Investigation, InvestigationSerializer } from '@models/Investigation/Investigation.model';
import { State } from '@models/State/State.model';
import i18n from '@/i18n';
import moment from 'moment';

chai.use(chaiMatchPattern);

const { expect } = chai;

describe('Investigation model', () => {
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
    it('should create an Investigation model with expected defaults', () => {
        const investigation = new Investigation();

        // Test field values
        expect(investigation).to.be.an.instanceof(Investigation);
        expect(investigation.id).to.equal(null);
        expect(investigation.compactType).to.equal(null);
        expect(investigation.providerId).to.equal(null);
        expect(investigation.state).to.be.an.instanceof(State);
        expect(investigation.type).to.equal(null);
        expect(investigation.startDate).to.equal(null);
        expect(investigation.updateDate).to.equal(null);
        expect(investigation.endDate).to.equal(null);

        // Test methods
        expect(investigation.startDateDisplay()).to.equal('');
        expect(investigation.updateDateDisplay()).to.equal('');
        expect(investigation.endDateDisplay()).to.equal('');
        expect(investigation.hasEndDate()).to.equal(false);
        expect(investigation.isActive()).to.equal(false);
    });
    it('should create an Investigation model with specific values', () => {
        const data = {
            id: 'test-id',
            compactType: 'test-compactType',
            providerId: 'test-providerId',
            state: new State(),
            type: 'test-type',
            startDate: 'test-startDate',
            updateDate: 'test-updateDate',
            endDate: 'test-endDate',
        };
        const investigation = new Investigation(data);

        // Test field values
        expect(investigation).to.be.an.instanceof(Investigation);
        expect(investigation.id).to.equal(data.id);
        expect(investigation.compactType).to.equal(data.compactType);
        expect(investigation.providerId).to.equal(data.providerId);
        expect(investigation.state).to.be.an.instanceof(State);
        expect(investigation.type).to.equal(data.type);
        expect(investigation.startDate).to.equal(data.startDate);
        expect(investigation.updateDate).to.equal(data.updateDate);
        expect(investigation.endDate).to.equal(data.endDate);

        // Test methods
        expect(investigation.startDateDisplay()).to.equal('Invalid date');
        expect(investigation.updateDateDisplay()).to.equal('Invalid date');
        expect(investigation.endDateDisplay()).to.equal('Invalid date');
        expect(investigation.hasEndDate()).to.equal(true);
        expect(investigation.isActive()).to.equal(false);
    });
    it('should create an Investigation model with specific values (startDate but no endDate)', () => {
        const data = {
            startDate: moment().format(serverDateFormat),
        };
        const investigation = new Investigation(data);

        // Test field values
        expect(investigation).to.be.an.instanceof(Investigation);
        expect(investigation.startDate).to.equal(data.startDate);
        expect(investigation.endDate).to.equal(null);

        // Test methods
        expect(investigation.isActive()).to.equal(true);
    });
    it('should create an Investigation model with specific values (endDate but no startDate)', () => {
        const data = {
            endDate: moment().add(1, 'day').format(serverDateFormat),
        };
        const investigation = new Investigation(data);

        // Test field values
        expect(investigation).to.be.an.instanceof(Investigation);
        expect(investigation.startDate).to.equal(null);
        expect(investigation.endDate).to.equal(data.endDate);

        // Test methods
        expect(investigation.isActive()).to.equal(true);
    });
    it('should create an Investigation model with specific values (endDate of today should count as lifted)', () => {
        const data = {
            startDate: moment().format(serverDateFormat),
            endDate: moment().format(serverDateFormat),
        };
        const investigation = new Investigation(data);

        // Test field values
        expect(investigation).to.be.an.instanceof(Investigation);
        expect(investigation.startDate).to.equal(data.startDate);
        expect(investigation.endDate).to.equal(data.endDate);

        // Test methods
        expect(investigation.isActive()).to.equal(false);
    });
    it('should create an Investigation model with specific values through serializer', () => {
        const data = {
            investigationId: 'test-id',
            compact: 'aslp',
            providerId: 'test-providerId',
            jurisdiction: 'al',
            type: 'test-type',
            creationDate: moment.utc().format(serverDateFormat),
            dateOfUpdate: moment.utc().format(serverDateFormat),
            endDate: moment.utc().add(1, 'day').format(serverDateFormat),
        };
        const investigation = InvestigationSerializer.fromServer(data);

        // Test field values
        expect(investigation).to.be.an.instanceof(Investigation);
        expect(investigation.id).to.equal(data.investigationId);
        expect(investigation.compactType).to.equal(data.compact);
        expect(investigation.providerId).to.equal(data.providerId);
        expect(investigation.state).to.be.an.instanceof(State);
        expect(investigation.state.name()).to.equal('Alabama');
        expect(investigation.type).to.equal(data.type);
        expect(investigation.startDate).to.equal(data.creationDate);
        expect(investigation.updateDate).to.equal(data.dateOfUpdate);
        expect(investigation.endDate).to.equal(data.endDate);

        // Test methods
        expect(investigation.startDateDisplay()).to.equal(
            moment(data.creationDate, serverDateFormat).format(displayDateFormat)
        );
        expect(investigation.updateDateDisplay()).to.equal(
            moment(data.dateOfUpdate, serverDateFormat).format(displayDateFormat)
        );
        expect(investigation.endDateDisplay()).to.equal(
            moment(data.endDate, serverDateFormat).format(displayDateFormat)
        );
        expect(investigation.hasEndDate()).to.equal(true);
        expect(investigation.isActive()).to.equal(true);
    });
});
