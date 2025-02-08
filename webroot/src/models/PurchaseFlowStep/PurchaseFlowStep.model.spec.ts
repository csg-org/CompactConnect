//
//  PurchaseFlowStep.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 2/4/2025.
//
import { PurchaseFlowStep } from '@models/PurchaseFlowStep/PurchaseFlowStep.model';
import { AcceptedAttestationToSend } from '@models/AcceptedAttestationToSend/AcceptedAttestationToSend.model';

import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';

chai.use(chaiMatchPattern);

const { expect } = chai;

describe('PurchaseFlowStep model', () => {
    it('should create a PrivilegePurchaseOption with expected defaults', () => {
        const purchaseFlowStep = new PurchaseFlowStep();

        expect(purchaseFlowStep).to.be.an.instanceof(PurchaseFlowStep);
        expect(purchaseFlowStep.stepNum).to.equal(0);
        expect(purchaseFlowStep.attestationsAccepted).to.matchPattern([]);
        expect(purchaseFlowStep.selectedPrivilegesToPurchase).to.matchPattern([]);
    });
    it('should create a PurchaseFlowStep with specific values', () => {
        const data = {
            stepNum: 0,
            attestationsAccepted: [ new AcceptedAttestationToSend({
                attestationId: 'attestation-id',
                version: '1'
            })],
            selectedPrivilegesToPurchase: ['ne']
        };
        const purchaseFlowStep = new PurchaseFlowStep(data);

        expect(purchaseFlowStep).to.be.an.instanceof(PurchaseFlowStep);
        expect(purchaseFlowStep.stepNum).to.equal(0);
        expect(purchaseFlowStep.attestationsAccepted[0]).to.be.an.instanceof(AcceptedAttestationToSend);
        expect(purchaseFlowStep.selectedPrivilegesToPurchase[0]).to.be.equal('ne');
    });
});
