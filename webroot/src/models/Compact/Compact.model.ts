//
//  Compact.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/27/2024.
//

import { deleteUndefinedProperties } from '@models/_helpers';
import { PrivilegePurchaseOption } from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';
import { State } from '@models/State/State.model';
import { CompactFeeConfig } from '@models/CompactFeeConfig/CompactFeeConfig.model';

// ========================================================
// =                       Interface                      =
// ========================================================
export enum CompactType { // Temp server definition until server returns via endpoint
    ASLP = 'aslp',
    OT = 'octp',
    COUNSELING = 'coun',
}

export interface PaymentProcessorConfig {
    apiLoginId: string;
    transactionKey: string;
    processor: string;
}

export enum FeeType {
    FLAT_RATE = 'FLAT_RATE',
    FLAT_FEE_PER_PRIVILEGE = 'FLAT_FEE_PER_PRIVILEGE',
}

export interface CompactConfig {
    compactAbbr?: string,
    compactName?: string,
    licenseeRegistrationEnabled: boolean,
    compactCommissionFee: {
        feeType: FeeType,
        feeAmount: number,
    },
    compactOperationsTeamEmails: Array<string>,
    compactAdverseActionsNotificationEmails: Array<string>,
    compactSummaryReportNotificationEmails: Array<string>,
    transactionFeeConfiguration: {
        licenseeCharges: {
            active: boolean,
            chargeType: FeeType,
            chargeAmount: number,
        },
    },
    configuredStates: Array<{
        postalAbbreviation: string,
        isLive: boolean,
    }>,
}

export interface CompactStateConfig {
    compact?: string,
    jurisdictionName?: string,
    postalAbbreviation?: string,
    licenseeRegistrationEnabled: boolean,
    privilegeFees: Array<{
        licenseTypeAbbreviation: string,
        amount: number,
        militaryRate: number | null, // Specific mix of number & null required by server
        name?: string,
    }>
    jurisprudenceRequirements: {
        required: boolean,
        linkToDocumentation: string | null,
    },
    jurisdictionOperationsTeamEmails: Array<string>,
    jurisdictionAdverseActionsNotificationEmails: Array<string>,
    jurisdictionSummaryReportNotificationEmails: Array<string>,
}

export interface InterfaceCompactCreate {
    id?: string | null;
    type?: CompactType | null;
    memberStates?: Array<State>;
    privilegePurchaseOptions?: Array<PrivilegePurchaseOption>;
    fees?: CompactFeeConfig;
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
    public fees? = new CompactFeeConfig();

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
            memberStates: json.memberStates || [] as Array<State>,
        };

        return new Compact(compactData);
    }
}
