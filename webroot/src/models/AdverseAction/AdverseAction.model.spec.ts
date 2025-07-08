//
//  AdverseAction.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 6/18/2025.
//

import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';
import {
    serverDateFormat,
    serverDatetimeFormat,
    displayDateFormat,
    displayDatetimeFormat
} from '@/app.config';
import { AdverseAction, AdverseActionSerializer } from '@models/AdverseAction/AdverseAction.model';
import { State } from '@models/State/State.model';
import i18n from '@/i18n';
import moment from 'moment';

chai.use(chaiMatchPattern);

const { expect } = chai;

describe('AdverseAction model', () => {
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
    it('should create an AdverseAction model with expected defaults', () => {
        const adverseAction = new AdverseAction();

        // Test field values
        expect(adverseAction).to.be.an.instanceof(AdverseAction);
        expect(adverseAction.id).to.equal(null);
        expect(adverseAction.compactType).to.equal(null);
        expect(adverseAction.providerId).to.equal(null);
        expect(adverseAction.state).to.be.an.instanceof(State);
        expect(adverseAction.type).to.equal(null);
        expect(adverseAction.npdbType).to.equal(null);
        expect(adverseAction.creationDate).to.equal(null);
        expect(adverseAction.startDate).to.equal(null);
        expect(adverseAction.endDate).to.equal(null);

        // Test methods
        expect(adverseAction.creationDateDisplay()).to.equal('');
        expect(adverseAction.startDateDisplay()).to.equal('');
        expect(adverseAction.endDateDisplay()).to.equal('');
        expect(adverseAction.npdbTypeName()).to.equal('');
        expect(adverseAction.isActive()).to.equal(false);
    });
    it('should create an AdverseAction model with specific values', () => {
        const data = {
            id: 'test-id',
            compactType: 'test-compactType',
            providerId: 'test-providerId',
            state: new State(),
            type: 'test-type',
            npdbType: 'test-npdbType',
            creationDate: 'test-creationDate',
            startDate: 'test-startDate',
            endDate: 'test-endDate',
        };
        const adverseAction = new AdverseAction(data);

        // Test field values
        expect(adverseAction).to.be.an.instanceof(AdverseAction);
        expect(adverseAction.id).to.equal(data.id);
        expect(adverseAction.compactType).to.equal(data.compactType);
        expect(adverseAction.providerId).to.equal(data.providerId);
        expect(adverseAction.state).to.be.an.instanceof(State);
        expect(adverseAction.type).to.equal(data.type);
        expect(adverseAction.npdbType).to.equal(data.npdbType);
        expect(adverseAction.creationDate).to.equal(data.creationDate);
        expect(adverseAction.startDate).to.equal(data.startDate);
        expect(adverseAction.endDate).to.equal(data.endDate);

        // Test methods
        expect(adverseAction.creationDateDisplay()).to.equal('Invalid date');
        expect(adverseAction.startDateDisplay()).to.equal('Invalid date');
        expect(adverseAction.endDateDisplay()).to.equal('Invalid date');
        expect(adverseAction.npdbTypeName()).to.equal('');
        expect(adverseAction.isActive()).to.equal(false);
    });
    it('should create an AdverseAction model with specific values (startDate but no endDate)', () => {
        const data = {
            startDate: moment().format(serverDateFormat),
        };
        const adverseAction = new AdverseAction(data);

        // Test field values
        expect(adverseAction).to.be.an.instanceof(AdverseAction);
        expect(adverseAction.startDate).to.equal(data.startDate);
        expect(adverseAction.endDate).to.equal(null);

        // Test methods
        expect(adverseAction.isActive()).to.equal(true);
    });
    it('should create an AdverseAction model with specific values (endDate but no startDate)', () => {
        const data = {
            endDate: moment().format(serverDateFormat),
        };
        const adverseAction = new AdverseAction(data);

        // Test field values
        expect(adverseAction).to.be.an.instanceof(AdverseAction);
        expect(adverseAction.startDate).to.equal(null);
        expect(adverseAction.endDate).to.equal(data.endDate);

        // Test methods
        expect(adverseAction.isActive()).to.equal(true);
    });
    it('should create an AdverseAction model with specific values through serializer', () => {
        const data = {
            adverseActionId: 'test-id',
            compact: 'aslp',
            providerId: 'test-providerId',
            jurisdiction: 'al',
            type: 'test-type',
            clinicalPrivilegeActionCategory: 'Non-compliance With Requirements',
            creationDate: moment.utc().format(serverDatetimeFormat),
            effectiveStartDate: moment().subtract(1, 'day').format(serverDateFormat),
            effectiveLiftDate: moment().add(1, 'day').format(serverDateFormat),
        };
        const adverseAction = AdverseActionSerializer.fromServer(data);

        // Test field values
        expect(adverseAction).to.be.an.instanceof(AdverseAction);
        expect(adverseAction.id).to.equal(data.adverseActionId);
        expect(adverseAction.compactType).to.equal(data.compact);
        expect(adverseAction.providerId).to.equal(data.providerId);
        expect(adverseAction.state).to.be.an.instanceof(State);
        expect(adverseAction.state.name()).to.equal('Alabama');
        expect(adverseAction.type).to.equal(data.type);
        expect(adverseAction.npdbType).to.equal(data.clinicalPrivilegeActionCategory);
        expect(adverseAction.creationDate).to.equal(data.creationDate);
        expect(adverseAction.startDate).to.equal(data.effectiveStartDate);
        expect(adverseAction.endDate).to.equal(data.effectiveLiftDate);

        // Test methods
        expect(moment.isMoment(moment(adverseAction.creationDateDisplay(), displayDatetimeFormat))).to.equal(true);
        expect(adverseAction.startDateDisplay()).to.equal(
            moment(data.effectiveStartDate, serverDateFormat).format(displayDateFormat)
        );
        expect(adverseAction.endDateDisplay()).to.equal(
            moment(data.effectiveLiftDate, serverDateFormat).format(displayDateFormat)
        );
        expect(adverseAction.npdbTypeName()).to.equal('Non-compliance With Requirements');
        expect(adverseAction.isActive()).to.equal(true);
    });
});
