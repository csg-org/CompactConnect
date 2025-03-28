//
//  LicenseHistoryItem.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/2/2024.
//
import deleteUndefinedProperties from '@models/_helpers';
// import { serverDateFormat } from '@/app.config';
// import { dateDisplay, dateDiff } from '@models/_formatters/date';
import { dateDisplay } from '@models/_formatters/date';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfaceLicenseHistoryItem {
    type?: string | null;
    updateType?: string;
    dateOfUpdate?: string | null;
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
    public $tm?: any = () => [];
    public $t?: any = () => '';
    public type? = null;
    public updateType? = '';
    public dateOfUpdate? = null;
    public previousValues? = {};
    public updatedValues? = {};

    constructor(data?: InterfaceLicenseHistoryItem) {
        const cleanDataObject = deleteUndefinedProperties(data);
        const global = window as any;
        const { $tm, $t } = global.Vue?.config?.globalProperties || {};

        if ($tm) {
            this.$tm = $tm;
            this.$t = $t;
        }

        Object.assign(this, cleanDataObject);
    }

    public dateOfUpdateDisplay(): string {
        return dateDisplay(this.dateOfUpdate);
    }

    public isActivatingEvent(): boolean {
        const activatingEvents = [ 'purchased', 'renewal' ];

        return activatingEvents.some((event) => (this.updateType && event === this.updateType));
    }

    public isDeactivatingEvent(): boolean {
        const deactivatingEvents = ['expired', 'deactivation'];

        return deactivatingEvents.some((event) => (this.updateType && event === this.updateType));
    }

    public updateTypeDisplay(): string {
        const updateType = this.updateType || '';
        const events = this.$tm('licensing.licenseEvents') || [];
        const event = events.find((st) => st.key === updateType);
        const eventName = event.name || this.$t('common.stateUnknown');

        return eventName;
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
