//
//  PurchaseFlowState.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 2/4/2025.
//

import { PurchaseFlowState } from '@models/PurchaseFlowState/PurchaseFlowState.model';
import { PurchaseFlowStep } from '@models/PurchaseFlowStep/PurchaseFlowStep.model';

import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';

chai.use(chaiMatchPattern);

const { expect } = chai;

describe('PurchaseFlowState model', () => {
    it('should create a PrivilegePurchaseOption with expected defaults', () => {
        const purchaseFlowState = new PurchaseFlowState();

        expect(purchaseFlowState).to.be.an.instanceof(PurchaseFlowState);
        expect(purchaseFlowState.steps).to.matchPattern([]);
    });
    it('should create a PurchaseFlowState with specific values', () => {
        const data = {
            steps: [ new PurchaseFlowStep()]
        };
        const purchaseFlowState = new PurchaseFlowState(data);

        expect(purchaseFlowState).to.be.an.instanceof(PurchaseFlowState);
        expect(purchaseFlowState.steps).to.be.an.instanceof(Array);
        expect(purchaseFlowState.steps[0]).to.to.be.an.instanceof(PurchaseFlowStep);
    });
});
