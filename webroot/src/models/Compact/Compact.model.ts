//
//  Compact.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/27/2024.
//

import { compacts as compactConfigs, FeeTypes } from '@/app.config';
import deleteUndefinedProperties from '@models/_helpers';
import { PrivilegePurchaseOption } from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';
import { State } from '@models/State/State.model';

// ========================================================
// =                       Interface                      =
// ========================================================
export enum CompactType { // Temp server definition until server returns via endpoint
    ASLP = 'aslp',
    OT = 'octp',
    COUNSILING = 'coun',
}

export interface PaymentProcessorConfig {
    apiLoginId: string;
    transactionKey: string;
    processor: string;
}

export interface InterfaceCompactCreate {
    id?: string | null;
    type?: CompactType | null;
    memberStates?: Array<State>;
    privilegePurchaseOptions?: Array <PrivilegePurchaseOption>;
    compactCommissionFee?: number | null;
    perPrivilegeTransactionFeeAmount?: number | null;
    isPerPrivilegeTransactionFeeActive?: boolean;
    compactCommissionFeeType?: FeeTypes | null;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class Compact implements InterfaceCompactCreate {
    public $tm?: any = () => [];
    public id? = null;
    public type? = null;
    public memberStates? = [];
    public privilegePurchaseOptions? = [];
    public compactCommissionFee? = null;
    public compactCommissionFeeType? = null;
    public perPrivilegeTransactionFeeAmount? = null;
    public isPerPrivilegeTransactionFeeActive? = false;

    constructor(data?: InterfaceCompactCreate) {
        const cleanDataObject = deleteUndefinedProperties(data);
        const global = window as any;
        const $tm = global.Vue?.config?.globalProperties?.$tm;

        if ($tm) {
            this.$tm = $tm;
        }

        Object.assign(this, cleanDataObject);
    }

    // Helper methods
    public name(): string {
        const compacts = this.$tm('compacts') || [];
        const compact = compacts.find((translate) => translate.key === this.type);
        const compactName = compact?.name || '';

        return compactName;
    }

    public abbrev(): string {
        const compacts = this.$tm('compacts') || [];
        const compact = compacts.find((translate) => translate.key === this.type);
        const compactAbbrev = compact?.abbrev || '';

        return compactAbbrev;
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class CompactSerializer {
    static fromServer(json: any): Compact {
        const compactData = {
            id: json.id,
            type: json.type,
            memberStates: [] as Array<State>,
        };
        const compactConfig: any = compactConfigs[json.type] || {};

        if (Array.isArray(compactConfig.memberStates)) {
            compactConfig.memberStates.forEach((abbrev) => {
                compactData.memberStates.push(new State({ abbrev }));
            });
        }

        return new Compact(compactData);
    }
}
