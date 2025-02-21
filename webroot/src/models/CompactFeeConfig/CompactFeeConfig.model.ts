//
//  CompactFeeConfig.ts
//  CompactConnect
//
//  Created by InspiringApps on 2/17/2025.
//

import { FeeTypes } from '@/app.config';
import deleteUndefinedProperties from '@models/_helpers';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfaceCompactFeeConfigCreate {
    compactAbbr?: string
    compactCommissionFee?: number;
    compactCommissionFeeType?: FeeTypes | null;
    perPrivilegeTransactionFeeAmount?: number;
    isPerPrivilegeTransactionFeeActive?: boolean;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class CompactFeeConfig implements InterfaceCompactFeeConfigCreate {
    public compactType? = '';
    public compactCommissionFee? = 0;
    public compactCommissionFeeType? = null;
    public perPrivilegeTransactionFeeAmount? = 0;
    public isPerPrivilegeTransactionFeeActive? = false;

    constructor(data?: InterfaceCompactFeeConfigCreate) {
        const cleanDataObject = deleteUndefinedProperties(data);

        Object.assign(this, cleanDataObject);
    }

    // Helper methods
    // @TODO
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class CompactFeeConfigSerializer {
    static fromServer(json: any): CompactFeeConfig {
        const { compactAbbr, compactCommissionFee, transactionFeeConfiguration } = json;
        const { licenseeCharges } = transactionFeeConfiguration || {};

        const compactFeeConfigData = {
            compactType: compactAbbr,
            compactCommissionFeeType: compactCommissionFee?.feeType,
            compactCommissionFee: compactCommissionFee?.feeAmount,
            perPrivilegeTransactionFeeAmount: licenseeCharges?.chargeAmount,
            isPerPrivilegeTransactionFeeActive: licenseeCharges?.active
                && licenseeCharges?.chargeType === FeeTypes.FLAT_FEE_PER_PRIVILEGE
        };

        return new CompactFeeConfig(compactFeeConfigData);
    }
}
