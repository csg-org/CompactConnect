//
//  PurchaseFlowStep.ts
//  CompactConnect
//
//  Created by InspiringApps on 2/4/2025.
//

import deleteUndefinedProperties from '@models/_helpers';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfacePurchaseFlowStepCreate {
    stepNum?: number;
    attestationsAccepted?: Array<any>;
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

    // Helper methods
    // @TODO
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class PurchaseFlowStepSerializer {
    // static fromServer(json: any): PurchaseFlowStep {
    //     const purchaseFlowStepData = {
    //         id: json.id,
    //     };

    //     return new PurchaseFlowStep(purchaseFlowStepData);
    // }

    // static toServer({ stepNum, atte}): any {
    //     return {
    //         stepNum: number,
    //         attestationsAccepted:
    //         selectedPrivilegesToPurchase?: Array<string>;
    //     };
    // }
}
