//
//  License.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/2/2024.
//

import deleteUndefinedProperties from '@models/_helpers';
import { dateDisplay } from '@models/_formatters/date';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfaceLicenseHistoryItem {
    type?: string | null;
    updateType?: string | null;
    previousValues?: object | null;
    updatedValues?: object | null;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class LicenseHistoryItem implements InterfaceLicenseHistoryItem {
    public type? = null;
    public updateType? = null;
    public previousValues? = null;
    public updatedValues? = null;

    constructor(data?: InterfaceLicenseHistoryItem) {
        const cleanDataObject = deleteUndefinedProperties(data);

        Object.assign(this, cleanDataObject);
    }

    // Helpers
    public previousIssueDateDisplay(): string {
        return dateDisplay((this.previousValues as any)?.dateOfIssuance || '');
    }

    public previousExpireDateDisplay(): string {
        return dateDisplay((this.previousValues as any)?.dateOfExpiration || '');
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class LicenseHistoryItemSerializer {
    static fromServer(json: any): LicenseHistoryItem {
        const licenseData = {
            type: json.type,
            updateType: json.updateType,
            previousValues: {
                compactTransactionId: json?.previous.compactTransactionId || '',
                dateOfExpiration: json?.previous.dateOfExpiration || '',
                dateOfIssuance: json?.previous.dateOfIssuance || '',
                dateOfRenewal: json?.previous.dateOfRenewal || '',
            },
            updatedValues: {
                compactTransactionId: json?.updatedValues.compactTransactionId || '',
                dateOfExpiration: json?.updatedValues.dateOfExpiration || '',
                dateOfIssuance: json?.updatedValues.dateOfIssuance || '',
                dateOfRenewal: json?.updatedValues.dateOfRenewal || '',
            }
        };

        return new LicenseHistoryItem(licenseData);
    }
}
