//
//  PrivilegeAttestation.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 1/21/2025.
//

import { serverDateFormat, displayDateFormat } from '@/app.config';
import { PrivilegeAttestation, PrivilegeAttestationSerializer } from '@models/PrivilegeAttestation/PrivilegeAttestation.model';
import { Compact } from '@models/Compact/Compact.model';
import i18n from '@/i18n';
import moment from 'moment';
import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';

chai.use(chaiMatchPattern);

const { expect } = chai;

describe('PrivilegeAttestation model', () => {
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
    it('should create a PrivilegeAttestation with expected defaults', () => {
        const privilegeAttestation = new PrivilegeAttestation();

        // Test field values
        expect(privilegeAttestation).to.be.an.instanceof(PrivilegeAttestation);
        expect(privilegeAttestation.id).to.equal(null);
        expect(privilegeAttestation.dateCreated).to.equal(null);
        expect(privilegeAttestation.dateUpdated).to.equal(null);
        expect(privilegeAttestation.compact).to.equal(null);
        expect(privilegeAttestation.type).to.equal(null);
        expect(privilegeAttestation.name).to.equal(null);
        expect(privilegeAttestation.text).to.equal(null);
        expect(privilegeAttestation.version).to.equal(null);
        expect(privilegeAttestation.locale).to.equal(null);
        expect(privilegeAttestation.isRequired).to.equal(false);

        // Test methods
        expect(privilegeAttestation.dateCreatedDisplay()).to.equal('');
        expect(privilegeAttestation.dateUpdatedDisplay()).to.equal('');
    });
    it('should create a PrivilegeAttestation with specific values', () => {
        const data = {
            id: 'test-id',
            dateCreated: '2020-01-01',
            dateUpdated: '2021-12-31',
            compact: new Compact(),
            type: 'test-type',
            name: 'test-name',
            text: 'test-text',
            version: 'test-version',
            locale: 'test-locale',
            isRequired: true,
        };
        const privilegeAttestation = new PrivilegeAttestation(data);

        // Test field values
        expect(privilegeAttestation).to.be.an.instanceof(PrivilegeAttestation);
        expect(privilegeAttestation.id).to.equal(data.id);
        expect(privilegeAttestation.dateCreated).to.equal(data.dateCreated);
        expect(privilegeAttestation.dateUpdated).to.equal(data.dateUpdated);
        expect(privilegeAttestation.compact).to.be.an.instanceof(Compact);
        expect(privilegeAttestation.type).to.equal(data.type);
        expect(privilegeAttestation.name).to.equal(data.name);
        expect(privilegeAttestation.text).to.equal(data.text);
        expect(privilegeAttestation.version).to.equal(data.version);
        expect(privilegeAttestation.locale).to.equal(data.locale);
        expect(privilegeAttestation.isRequired).to.equal(data.isRequired);

        // Test methods
        expect(privilegeAttestation.dateCreatedDisplay()).to.equal(
            moment(data.dateCreated, serverDateFormat).format(displayDateFormat)
        );
        expect(privilegeAttestation.dateUpdatedDisplay()).to.equal(
            moment(data.dateUpdated, serverDateFormat).format(displayDateFormat)
        );
    });
    it('should create a PrivilegeAttestation with specific values through serializer', () => {
        const data = {
            attestationId: 'test-id',
            dateCreated: '2020-01-01',
            dateOfUpdate: '2021-12-31',
            compact: 'aslp',
            type: 'test-type',
            displayName: 'test-name',
            text: 'test-text',
            version: 'test-version',
            locale: 'test-locale',
            required: true,
        };
        const privilegeAttestation = PrivilegeAttestationSerializer.fromServer(data);

        // Test field values
        expect(privilegeAttestation).to.be.an.instanceof(PrivilegeAttestation);
        expect(privilegeAttestation.id).to.equal(data.attestationId);
        expect(privilegeAttestation.dateCreated).to.equal(data.dateCreated);
        expect(privilegeAttestation.dateUpdated).to.equal(data.dateOfUpdate);
        expect(privilegeAttestation.compact).to.be.an.instanceof(Compact);
        expect(privilegeAttestation.type).to.equal(data.type);
        expect(privilegeAttestation.name).to.equal(data.displayName);
        expect(privilegeAttestation.text).to.equal(data.text);
        expect(privilegeAttestation.version).to.equal(data.version);
        expect(privilegeAttestation.locale).to.equal(data.locale);
        expect(privilegeAttestation.isRequired).to.equal(true);

        // Test methods
        expect(privilegeAttestation.dateCreatedDisplay()).to.equal(
            moment(data.dateCreated, serverDateFormat).format(displayDateFormat)
        );
        expect(privilegeAttestation.dateUpdatedDisplay()).to.equal(
            moment(data.dateOfUpdate, serverDateFormat).format(displayDateFormat)
        );
    });
    it('should prepare a PrivilegeAttestation for server request through serializer', () => {
        const privilegeAttestation = new PrivilegeAttestation({
            id: 'test-id',
            dateCreated: '2020-01-01',
            dateUpdated: '2021-12-31',
            compact: new Compact(),
            type: 'test-type',
            name: 'test-name',
            text: 'test-text',
            version: 'test-version',
            locale: 'test-locale',
            isRequired: true,
        });
        const requestData = PrivilegeAttestationSerializer.toServer(privilegeAttestation);

        expect(requestData).to.matchPattern({
            attestationId: privilegeAttestation.id,
            version: privilegeAttestation.version,
        });
    });
});
