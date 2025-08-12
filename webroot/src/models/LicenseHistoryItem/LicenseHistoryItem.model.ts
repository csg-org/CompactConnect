//
//  LicenseHistoryItem.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/2/2024.
//
import { deleteUndefinedProperties } from '@models/_helpers';
import { dateDisplay } from '@models/_formatters/date';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfaceLicenseHistoryItem {
    type?: string | null;
    updateType?: string;
    dateOfUpdate?: string | null;
    createDate?: string | null;
    effectiveDate?: string | null;
    serverNote?: string | null;
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
    public createDate? = null;
    public effectiveDate? = null;
    public serverNote? = null;

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

    public effectiveDateDisplay(): string {
        return dateDisplay(this.effectiveDate);
    }

    public isActivatingEvent(): boolean {
        const activatingEvents = ['renewal'];

        return activatingEvents.some((event) => (this.updateType && event === this.updateType));
    }

    public isDeactivatingEvent(): boolean {
        const deactivatingEvents = [
            'expired',
            'deactivation',
            'encumbrance',
            'homeJurisdictionChange',
            'licenseDeactivation'
        ];

        return deactivatingEvents.some((event) => (this.updateType && event === this.updateType));
    }

    public updateTypeDisplay(): string {
        const updateType = this.updateType || '';
        const events = this.$tm('licensing.licenseEvents') || [];
        const event = events.find((st) => st.key === updateType);
        let eventName = event?.name || this.$t('common.stateUnknown');

        if (updateType === 'homeJurisdictionChange' || updateType === 'licenseDeactivation') {
            eventName = this.$t('licensing.deactivation');
        }

        return eventName;
    }

    public noteDisplay(): string {
        const updateType = this.updateType || '';
        let noteDisplay = this.serverNote || '';

        if (updateType === 'homeJurisdictionChange') {
            noteDisplay = this.$t('licensing.homeStateChangeNote');
        } else if (updateType === 'licenseDeactivation') {
            noteDisplay = this.$t('licensing.licenseDeactivationNote');
        }

        return noteDisplay;
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
            createDate: json.createDate,
            effectiveDate: json.effectiveDate,
            dateOfUpdate: json.dateOfUpdate,
            serverNote: json.note,
        };

        return new LicenseHistoryItem(licenseHistoryData);
    }
}
