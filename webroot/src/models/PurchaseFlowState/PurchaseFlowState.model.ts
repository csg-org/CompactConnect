//
//  PurchaseFlowState.ts
//  CompactConnect
//
//  Created by InspiringApps on 2/4/2025.
//

import deleteUndefinedProperties from '@models/_helpers';
import { PurchaseFlowStep } from '@models/PurchaseFlowStep/PurchaseFlowStep.model';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfacePurchaseFlowStateCreate {
    totalSteps?: number;
    steps?: Array<PurchaseFlowStep>;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class PurchaseFlowState implements InterfacePurchaseFlowStateCreate {
    public totalSteps? = 0;
    public steps? = [];

    constructor(data?: InterfacePurchaseFlowStateCreate) {
        const cleanDataObject = deleteUndefinedProperties(data);

        Object.assign(this, cleanDataObject);
    }

    // Helper methods
    // @TODO
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class PurchaseFlowStateSerializer {
    static fromServer(json: any): PurchaseFlowState {
        const purchaseFlowStateData = {
            id: json.id,
        };

        return new PurchaseFlowState(purchaseFlowStateData);
    }

    static toServer(purchaseFlowStateModel: PurchaseFlowState): any {
        return {
            id: purchaseFlowStateModel.id,
        };
    }
}
