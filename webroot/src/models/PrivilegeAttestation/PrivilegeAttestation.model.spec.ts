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
        expect(privilegeAttestation.compact).to.equal(null);
        expect(privilegeAttestation.type).to.equal(null);
        expect(privilegeAttestation.text).to.equal(null);
        expect(privilegeAttestation.version).to.equal(null);
        expect(privilegeAttestation.isRequired).to.equal(false);

        // Test methods
        expect(privilegeAttestation.dateCreatedDisplay()).to.equal('');
    });
    it('should create a PrivilegeAttestation with specific values', () => {
        const data = {
            id: 'test-id',
            dateCreated: '2020-01-01',
            compact: new Compact(),
            type: 'test-type',
            text: 'test-text',
            version: 'test-version',
            isRequired: true,
        };
        const privilegeAttestation = new PrivilegeAttestation(data);

        // Test field values
        expect(privilegeAttestation).to.be.an.instanceof(PrivilegeAttestation);
        expect(privilegeAttestation.id).to.equal(data.id);
        expect(privilegeAttestation.dateCreated).to.equal(data.dateCreated);
        expect(privilegeAttestation.compact).to.be.an.instanceof(Compact);
        expect(privilegeAttestation.type).to.equal(data.type);
        expect(privilegeAttestation.text).to.equal(data.text);
        expect(privilegeAttestation.version).to.equal(data.version);
        expect(privilegeAttestation.isRequired).to.equal(data.isRequired);

        // Test methods
        expect(privilegeAttestation.dateCreatedDisplay()).to.equal(
            moment(data.dateCreated, serverDateFormat).format(displayDateFormat)
        );
    });
    it('should create a PrivilegeAttestation with specific values through serializer', () => {
        const data = {
            dateCreated: '2020-01-01',
            compact: new Compact(),
            type: 'test-type',
            text: 'test-text',
            version: 'test-version',
            required: true,
        };
        const privilegeAttestation = PrivilegeAttestationSerializer.fromServer(data, 'test-id');

        // Test field values
        expect(privilegeAttestation).to.be.an.instanceof(PrivilegeAttestation);
        expect(privilegeAttestation.id).to.equal('test-id');
        expect(privilegeAttestation.dateCreated).to.equal(data.dateCreated);
        expect(privilegeAttestation.compact).to.be.an.instanceof(Compact);
        expect(privilegeAttestation.type).to.equal(data.type);
        expect(privilegeAttestation.text).to.equal(data.text);
        expect(privilegeAttestation.version).to.equal(data.version);
        expect(privilegeAttestation.isRequired).to.equal(true);

        // Test methods
        expect(privilegeAttestation.dateCreatedDisplay()).to.equal(
            moment(data.dateCreated, serverDateFormat).format(displayDateFormat)
        );
    });
    it('should prepare a Staff User for server request through serializer', () => {
        const privilegeAttestation = new PrivilegeAttestation({
            id: 'test-id',
            dateCreated: '2020-01-01',
            compact: new Compact(),
            type: 'test-type',
            text: 'test-text',
            version: 'test-version',
            isRequired: true,
        });
        const requestData = PrivilegeAttestationSerializer.toServer(privilegeAttestation);

        expect(requestData).to.matchPattern({
            attestationId: privilegeAttestation.id,
            version: privilegeAttestation.version,
        });
    });
});
