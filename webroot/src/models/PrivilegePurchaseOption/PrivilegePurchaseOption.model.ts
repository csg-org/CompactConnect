//
//  License.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/2/2024.
//
import { FeeTypes } from '@/app.config';
import deleteUndefinedProperties from '@models/_helpers';
import { State } from '@models/State/State.model';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfacePrivilegePurchaseOption {
    jurisdiction?: State;
    compact?: string | null;
    fee?: number | null;
    feeType?: FeeTypes | null;
    isMilitaryDiscountActive?: boolean;
    militaryDiscountType?: FeeTypes | null;
    militaryDiscountAmount?: number | null;
    isJurisprudenceRequired?: boolean;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class PrivilegePurchaseOption implements InterfacePrivilegePurchaseOption {
    public $tm?: any = () => [];
    public jurisdiction? = new State();
    public compact? = null;
    public fee? = null;
    public feeType? = null;
    public isMilitaryDiscountActive? = false;
    public militaryDiscountType? = null;
    public militaryDiscountAmount? = null;
    public isJurisprudenceRequired? = false;

    constructor(data?: InterfacePrivilegePurchaseOption) {
        const cleanDataObject = deleteUndefinedProperties(data);
        const global = window as any;
        const $tm = global.Vue?.config?.globalProperties?.$tm;

        if ($tm) {
            this.$tm = $tm;
        }

        Object.assign(this, cleanDataObject);
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class PrivilegePurchaseOptionSerializer {
    static fromServer(json: any): PrivilegePurchaseOption {
        const purchaseOptionData = {
            jurisdiction: new State({ abbrev: json.postalAbbreviation }),
            compact: json.compact,
            fee: json.jurisdictionFee,
            isMilitaryDiscountActive: json?.militaryDiscount?.active === true || false,
            militaryDiscountType: json?.militaryDiscount?.discountType || null,
            militaryDiscountAmount: json?.militaryDiscount?.discountAmount || null,
            isJurisprudenceRequired: json?.jurisprudenceRequirements?.required || false,
        };

        return new PrivilegePurchaseOption(purchaseOptionData);
    }
}
