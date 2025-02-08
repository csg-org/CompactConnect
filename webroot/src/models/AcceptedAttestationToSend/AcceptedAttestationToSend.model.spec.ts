//
//  AcceptedAttestationToSend.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 2/4/2025.
//
import { AcceptedAttestationToSend } from '@models/AcceptedAttestationToSend/AcceptedAttestationToSend.model';

import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';

chai.use(chaiMatchPattern);

const { expect } = chai;

describe('AcceptedAttestationToSend model', () => {
    it('should create a PrivilegePurchaseOption with expected defaults', () => {
        const acceptedAttestationToSend = new AcceptedAttestationToSend();

        expect(acceptedAttestationToSend).to.be.an.instanceof(AcceptedAttestationToSend);
        expect(acceptedAttestationToSend.attestationId).to.equal(null);
        expect(acceptedAttestationToSend.version).to.equal(null);
    });
    it('should create a AcceptedAttestationToSend with specific values', () => {
        const data = {
            attestationId: 'attest-attaestation',
            version: '1'
        };
        const acceptedAttestationToSend = new AcceptedAttestationToSend(data);

        expect(acceptedAttestationToSend).to.be.an.instanceof(AcceptedAttestationToSend);
        expect(acceptedAttestationToSend.attestationId).to.equal(data.attestationId);
        expect(acceptedAttestationToSend.version).to.equal(data.version);
    });
});
