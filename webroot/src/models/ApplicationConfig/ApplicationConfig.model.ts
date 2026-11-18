//
//  ApplicationConfig.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/17/2026.
//

import { deleteUndefinedProperties } from '@models/_helpers';
import { ApplicationType } from '@models/Application/Application.model';

// ========================================================
// =                       Interface                      =
// ========================================================
export type ApplicationFees = Partial<Record<ApplicationType, number>>;

export interface InterfaceApplicationConfigCreate {
    compactType?: string | null;
    fees?: ApplicationFees;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class ApplicationConfig implements InterfaceApplicationConfigCreate {
    public compactType? = null;
    public fees?: ApplicationFees = {};

    constructor(data?: InterfaceApplicationConfigCreate) {
        const cleanDataObject = deleteUndefinedProperties(data);

        Object.assign(this, cleanDataObject);
    }

    // Helper methods
    public feeForType(type: ApplicationType): number {
        const fees: ApplicationFees = this.fees || {};

        return fees[type] || 0;
    }

    public totalFeeForTypes(types: Array<ApplicationType>): number {
        return types.reduce((total, type) => total + this.feeForType(type), 0);
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class ApplicationConfigSerializer {
    static fromServer(json: any): ApplicationConfig {
        const { compact, applicationFees } = json || {};
        const fees: ApplicationFees = {};

        if (Array.isArray(applicationFees)) {
            applicationFees.forEach(({ applicationType, amount }) => {
                fees[applicationType] = Number(amount) || 0;
            });
        }

        const applicationConfigData = {
            compactType: compact,
            fees,
        };

        return new ApplicationConfig(applicationConfigData);
    }
}
