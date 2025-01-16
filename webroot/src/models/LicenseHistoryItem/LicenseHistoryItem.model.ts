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
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class LicenseHistoryItemSerializer {
    static fromServer(json: any): LicenseHistoryItem {
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
