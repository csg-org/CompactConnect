//
//  Authorization.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/29/2026.
//

import { expect } from 'chai';
import { serverDateFormat, serverDatetimeFormat, displayDateFormat } from '@/app.config';
import {
    Authorization,
    AuthorizationStatus,
    AuthorizationSerializer
} from '@models/Authorization/Authorization.model';
import { ApplicationType } from '@models/Application/Application.model';
import i18n from '@/i18n';
import moment from 'moment';

describe('Authorization model', () => {
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
    it('should create an Authorization model with expected defaults', () => {
        const authorization = new Authorization();

        // Test field values
        expect(authorization).to.be.an.instanceof(Authorization);
        expect(authorization.id).to.equal(null);
        expect(authorization.type).to.equal(null);
        expect(authorization.status).to.equal(AuthorizationStatus.INACTIVE);
        expect(authorization.issueDate).to.equal(null);
        expect(authorization.renewalDate).to.equal(null);
        expect(authorization.expireDate).to.equal(null);

        // Test methods
        expect(authorization.issueDateDisplay()).to.equal('');
        expect(authorization.renewalDateDisplay()).to.equal('');
        expect(authorization.expireDateDisplay()).to.equal('');
        expect(authorization.isExpired()).to.equal(false);
        expect(authorization.typeDisplay()).to.equal('');
        expect(authorization.typeAbbreviation()).to.equal('');
        expect(authorization.statusDisplay()).to.equal('Inactive');
        expect(authorization.isActive()).to.equal(false);
    });
    it('should create an Authorization model with specific values', () => {
        const data = {
            id: 'test-id',
            type: ApplicationType.TAP,
            status: AuthorizationStatus.ACTIVE,
            issueDate: 'test-issueDate',
            renewalDate: 'test-renewalDate',
            expireDate: 'test-expireDate',
        };
        const authorization = new Authorization(data);

        // Test field values
        expect(authorization).to.be.an.instanceof(Authorization);
        expect(authorization.id).to.equal(data.id);
        expect(authorization.type).to.equal(data.type);
        expect(authorization.status).to.equal(data.status);
        expect(authorization.issueDate).to.equal(data.issueDate);
        expect(authorization.renewalDate).to.equal(data.renewalDate);
        expect(authorization.expireDate).to.equal(data.expireDate);

        // Test methods
        expect(authorization.issueDateDisplay()).to.equal('Invalid date');
        expect(authorization.renewalDateDisplay()).to.equal('Invalid date');
        expect(authorization.expireDateDisplay()).to.equal('Invalid date');
        expect(authorization.isExpired()).to.equal(false);
        expect(authorization.typeDisplay()).to.equal('TAP');
        expect(authorization.typeAbbreviation()).to.equal('TAP');
        expect(authorization.statusDisplay()).to.equal('Active');
        expect(authorization.isActive()).to.equal(true);
    });
    it('should create an Authorization model with specific values through serializer', () => {
        const data = {
            id: 'test-id',
            type: ApplicationType.APIT,
            status: AuthorizationStatus.ACTIVE,
            issueDate: moment().subtract(11, 'months').format(serverDatetimeFormat),
            renewalDate: moment().subtract(1, 'month').format(serverDatetimeFormat),
            expireDate: moment().add(1, 'month').format(serverDatetimeFormat),
        };
        const authorization = AuthorizationSerializer.fromServer(data);

        // Test field values
        expect(authorization).to.be.an.instanceof(Authorization);
        expect(authorization.id).to.equal(data.id);
        expect(authorization.type).to.equal(data.type);
        expect(authorization.status).to.equal(data.status);
        expect(authorization.issueDate).to.equal(data.issueDate);
        expect(authorization.renewalDate).to.equal(data.renewalDate);
        expect(authorization.expireDate).to.equal(data.expireDate);

        // Test methods
        expect(authorization.issueDateDisplay()).to.equal(
            moment(data.issueDate, serverDatetimeFormat).format(displayDateFormat)
        );
        expect(authorization.renewalDateDisplay()).to.equal(
            moment(data.renewalDate, serverDatetimeFormat).format(displayDateFormat)
        );
        expect(authorization.expireDateDisplay()).to.equal(
            moment(data.expireDate, serverDatetimeFormat).format(displayDateFormat)
        );
        expect(authorization.isExpired()).to.equal(false);
        expect(authorization.typeDisplay()).to.equal('APIT');
        expect(authorization.typeAbbreviation()).to.equal('APIT');
        expect(authorization.statusDisplay()).to.equal('Active');
        expect(authorization.isActive()).to.equal(true);
    });
    it('should create an Authorization model with specific values (past expiration)', () => {
        const authorization = new Authorization({
            status: AuthorizationStatus.INACTIVE,
            expireDate: moment().subtract(1, 'day').format(serverDateFormat),
        });

        // Test methods
        expect(authorization.isExpired()).to.equal(true);
        expect(authorization.statusDisplay()).to.equal('Inactive');
        expect(authorization.isActive()).to.equal(false);
    });
    it('should create an Authorization model without Vue i18n helpers', () => {
        const previousVue = (window as any).Vue;

        (window as any).Vue = undefined;

        const authorization = new Authorization();

        (window as any).Vue = previousVue;

        // Test field values
        expect(authorization).to.be.an.instanceof(Authorization);
        expect(authorization.$tm).to.equal(undefined);
        expect(authorization.$features).to.equal(undefined);
    });
    it('should fall back when translation helpers return empty values', () => {
        const authorization = new Authorization({
            type: ApplicationType.APIT,
            status: AuthorizationStatus.ACTIVE,
        });

        authorization.$tm = () => null;

        // Test methods
        expect(authorization.typeDisplay()).to.equal('');
        expect(authorization.typeAbbreviation()).to.equal('');
        expect(authorization.statusDisplay()).to.equal('');
    });
    it('should create an Authorization model with an inactive status display fallback', () => {
        const authorization = new Authorization();

        authorization.status = undefined;

        // Test methods
        expect(authorization.statusDisplay()).to.equal('Inactive');
    });
});
