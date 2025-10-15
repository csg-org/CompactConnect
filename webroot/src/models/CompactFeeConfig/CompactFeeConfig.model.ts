//
//  CompactFeeConfig.ts
//  CompactConnect
//
//  Created by InspiringApps on 2/17/2025.
//

import { FeeTypes } from '@/app.config';
import { deleteUndefinedProperties } from '@models/_helpers';
import { StatsigClient } from '@statsig/js-client';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface PaymentSdkConfig {
    loginId?: string;
    clientKey?: string;
    isSandboxMode?: boolean;
}

export interface InterfaceCompactFeeConfigCreate {
    compactAbbr?: string
    compactCommissionFee?: number;
    compactCommissionFeeType?: FeeTypes | null;
    perPrivilegeTransactionFeeAmount?: number;
    isPerPrivilegeTransactionFeeActive?: boolean;
    paymentSdkConfig?: PaymentSdkConfig;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class CompactFeeConfig implements InterfaceCompactFeeConfigCreate {
    public $features?: StatsigClient | null = null;
    public compactType? = '';
    public compactCommissionFee? = 0;
    public compactCommissionFeeType? = null;
    public perPrivilegeTransactionFeeAmount? = 0;
    public isPerPrivilegeTransactionFeeActive? = false;
    public paymentSdkConfig: PaymentSdkConfig = {};

    constructor(data?: InterfaceCompactFeeConfigCreate) {
        const cleanDataObject = deleteUndefinedProperties(data);
        const global = window as any;
        const { $features } = global.Vue?.config?.globalProperties || {};

        if ($features) {
            this.$features = $features;
        }

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
        const {
            compactAbbr,
            compactCommissionFee,
            transactionFeeConfiguration,
            paymentProcessorPublicFields,
            isSandbox
        } = json;
        const { licenseeCharges } = transactionFeeConfiguration || {};

        const compactFeeConfigData = {
            compactType: compactAbbr,
            compactCommissionFeeType: compactCommissionFee?.feeType,
            compactCommissionFee: compactCommissionFee?.feeAmount,
            perPrivilegeTransactionFeeAmount: licenseeCharges?.chargeAmount,
            isPerPrivilegeTransactionFeeActive: licenseeCharges?.active
                && licenseeCharges?.chargeType === FeeTypes.FLAT_FEE_PER_PRIVILEGE,
            paymentSdkConfig: {
                loginId: paymentProcessorPublicFields?.apiLoginId || '',
                clientKey: paymentProcessorPublicFields?.publicClientKey || '',
                isSandboxMode: (typeof isSandbox === 'boolean') ? isSandbox : false,
            },
        };

        return new CompactFeeConfig(compactFeeConfigData);
    }
}
