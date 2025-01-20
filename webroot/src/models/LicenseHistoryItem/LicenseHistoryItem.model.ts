//
//  LicenseHistoryItem.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/2/2024.
//

import deleteUndefinedProperties from '@models/_helpers';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfaceLicenseHistoryItem {
    type?: string | null;
    updateType?: string | null;
    previousValues?: {
        compactTransactionId?: string | null,
        dateOfExpiration?: string | null,
        dateOfIssuance?: string | null,
        dateOfRenewal?: string | null,
        dateOfUpdate?: string | null,
    };
    updatedValues?: {
        compactTransactionId?: string | null,
        dateOfExpiration?: string | null,
        dateOfIssuance?: string | null,
        dateOfRenewal?: string | null,
    };
}

// ========================================================
// =                        Model                         =
// ========================================================
export class LicenseHistoryItem implements InterfaceLicenseHistoryItem {
    public type? = null;
    public updateType? = null;
    public previousValues? = {};
    public updatedValues? = {};

    constructor(data?: InterfaceLicenseHistoryItem) {
        const cleanDataObject = deleteUndefinedProperties(data);

        Object.assign(this, cleanDataObject);
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class LicenseHistoryItemSerializer {
    static fromServer(json: any): LicenseHistoryItem {
        // All license fields can possibly appear in the values below, however the frontend only utilizes
        // renewals at this time, these are the relevant fields for renewals
        const licenseHistoryData = {
            type: json.type,
            updateType: json.updateType,
            dateOfUpdate: json.dateOfUpdate,
            previousValues: {
                compactTransactionId: json.previous?.compactTransactionId || '',
                dateOfExpiration: json.previous?.dateOfExpiration || '',
                dateOfIssuance: json.previous?.dateOfIssuance || '',
                dateOfRenewal: json.previous?.dateOfRenewal || '',
                dateOfUpdate: json.previous?.dateOfUpdate || '',
            },
            updatedValues: {
                compactTransactionId: json.updatedValues?.compactTransactionId || '',
                dateOfExpiration: json.updatedValues?.dateOfExpiration || '',
                dateOfIssuance: json.updatedValues?.dateOfIssuance || '',
                dateOfRenewal: json.updatedValues?.dateOfRenewal || '',
            }
        };

        return new LicenseHistoryItem(licenseHistoryData);
    }
}
