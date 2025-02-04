//
//  PurchaseFlowStep.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 2/4/2025.
//

import { expect } from 'chai';
import { PurchaseFlowStep } from '@models/PurchaseFlowStep/PurchaseFlowStep.model';

describe('PurchaseFlowStep model', () => {
    it('should create a PurchaseFlowStep', () => {
        const purchaseFlowStep = new PurchaseFlowStep();

        expect(purchaseFlowStep).to.be.an.instanceof(PurchaseFlowStep);
    });
});
