//
//  LicenseHistoryItem.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/2/2024.
//
import { deleteUndefinedProperties } from '@models/_helpers';
import { LicenseHistoryItem, LicenseHistoryItemSerializer } from '@models/LicenseHistoryItem/LicenseHistoryItem.model';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfaceLicenseHistory {
    compact?: string | null;
    jurisdiction?: string | null;
    licenseType?: string | null,
    privilegeId?: string | null;
    providerId?: string | null;
    events?: Array<LicenseHistoryItem>;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class LicenseHistory implements InterfaceLicenseHistory {
    public $tm?: any = () => [];
    public $t?: any = () => '';
    public compact? = null;
    public jurisdiction? = null;
    public licenseType? = null;
    public privilegeId? = null;
    public providerId? = null;
    public events? = [];

    constructor(data?: InterfaceLicenseHistory) {
        const cleanDataObject = deleteUndefinedProperties(data);
        const global = window as any;
        const { $tm, $t } = global.Vue?.config?.globalProperties || {};

        if ($tm) {
            this.$tm = $tm;
            this.$t = $t;
        }

        Object.assign(this, cleanDataObject);
    }

    public licenseTypeAbbreviation(): string {
        const licenseTypes = this.$tm('licensing.licenseTypes') || [];
        const licenseType = licenseTypes.find((translate) => translate.key === this.licenseType);
        const licenseTypeAbbrev = licenseType?.abbrev || '';
        const upperCaseAbbrev = licenseTypeAbbrev.toUpperCase();

        return upperCaseAbbrev;
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class LicenseHistorySerializer {
    static fromServer(json: any): LicenseHistory {
        // All license fields can possibly appear in the values below, however the frontend only utilizes
        // renewals at this time, these are the relevant fields for renewals
        console.log('json', json);

        const licenseHistoryData = {
            compact: json.compact,
            jurisdiction: json.jurisdiction,
            licenseType: json.licenseType,
            privilegeId: json.privilegeId,
            providerId: json.providerId,
            events: [] as Array<LicenseHistoryItem>,
        };

        if (Array.isArray(json.events)) {
            json.events.forEach((serverHistoryItem) => {
                licenseHistoryData.events.push(LicenseHistoryItemSerializer.fromServer(serverHistoryItem));
            });
        }

        return new LicenseHistory(licenseHistoryData);
    }
}
