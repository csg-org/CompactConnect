//
//  PrivilegePurchaseOption.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/2/2024.
//
import { FeeTypes } from '@/app.config';
import { deleteUndefinedProperties } from '@models/_helpers';
import { State } from '@models/State/State.model';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfacePrivilegePurchaseOption {
    jurisdiction?: State;
    compactType?: string | null;
    fees?: { [key: string]: number };
    isMilitaryDiscountActive?: boolean;
    militaryDiscountType?: FeeTypes | null;
    militaryDiscountAmount?: number;
    isJurisprudenceRequired?: boolean;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class PrivilegePurchaseOption implements InterfacePrivilegePurchaseOption {
    public $tm?: any = () => [];
    public jurisdiction? = new State();
    public compactType? = null;
    public fees? = {};
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
        console.log('json', json);

        const purchaseOptionData = {
            jurisdiction: new State({ abbrev: json.postalAbbreviation }),
            compactType: json.compact,
            fees: {},
            isJurisprudenceRequired: json?.jurisprudenceRequirements?.required || false,
        };

        if (Array.isArray(json.privilegeFees)) {
            json.privilegeFees.forEach((fee) => {
                if (fee.licenseTypeAbbreviation) {
                    purchaseOptionData.fees[fee.licenseTypeAbbreviation] = { baseRate: fee.amount || 0 };
                    purchaseOptionData.fees[fee.licenseTypeAbbreviation].militaryRate = fee.militaryRate;
                }
            });
        }

        console.log('purchaseOptionData', purchaseOptionData);

        return new PrivilegePurchaseOption(purchaseOptionData);
    }
}
