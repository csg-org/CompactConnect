//
//  PurchaseFlowState.ts
//  CompactConnect
//
//  Created by InspiringApps on 2/4/2025.
//

import { deleteUndefinedProperties } from '@models/_helpers';
import { PurchaseFlowStep } from '@models/PurchaseFlowStep/PurchaseFlowStep.model';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfacePurchaseFlowStateCreate {
    steps?: Array<PurchaseFlowStep>;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class PurchaseFlowState implements InterfacePurchaseFlowStateCreate {
    public steps? = [];

    constructor(data?: InterfacePurchaseFlowStateCreate) {
        const cleanDataObject = deleteUndefinedProperties(data);

        Object.assign(this, cleanDataObject);
    }
}
