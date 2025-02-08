//
//  PurchaseFlowStep.ts
//  CompactConnect
//
//  Created by InspiringApps on 2/4/2025.
//

import deleteUndefinedProperties from '@models/_helpers';
import { AcceptedAttestationToSend } from '@models/AcceptedAttestationToSend/AcceptedAttestationToSend.model';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfacePurchaseFlowStepCreate {
    stepNum?: number;
    attestationsAccepted?: Array<AcceptedAttestationToSend>;
    selectedPrivilegesToPurchase?: Array<string>;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class PurchaseFlowStep implements InterfacePurchaseFlowStepCreate {
    public stepNum? = 0;
    public attestationsAccepted? = [];
    public selectedPrivilegesToPurchase? = [];

    constructor(data?: InterfacePurchaseFlowStepCreate) {
        const cleanDataObject = deleteUndefinedProperties(data);

        Object.assign(this, cleanDataObject);
    }
}
