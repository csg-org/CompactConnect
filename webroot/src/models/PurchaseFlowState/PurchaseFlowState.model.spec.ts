//
//  PurchaseFlowState.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 2/4/2025.
//

import { expect } from 'chai';
import { PurchaseFlowState } from '@models/PurchaseFlowState/PurchaseFlowState.model';

describe('PurchaseFlowState model', () => {
    it('should create a PurchaseFlowState', () => {
        const purchaseFlowState = new PurchaseFlowState();

        expect(purchaseFlowState).to.be.an.instanceof(PurchaseFlowState);
    });
});
