//
//  LicenseHistoryItem.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/2/2024.
//

import { deleteUndefinedProperties } from '@models/_helpers';
import { displayDateFormat } from '@/app.config';
import { dateDisplay } from '@models/_formatters/date';
import { State } from '@models/State/State.model';
import moment from 'moment';

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
    npdbCategories?: string[] | null;
    encumbranceType?: string | null;
    licenseScope?: string | null;
    state?: State;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class LicenseHistoryItem implements InterfaceLicenseHistoryItem {
    public $tm?: any = () => [];
    public $t?: any = () => '';
    public type?: string | null = null;
    public updateType? = '';
    public dateOfUpdate? = null;
    public createDate? = null;
    public effectiveDate? = null;
    public serverNote? = null;
    public npdbCategories?: string[] | null = null;
    public encumbranceType? = null;
    public licenseScope?: string | null = null;
    public state? = new State();

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

    public effectiveDateSortValue(): number {
        const dateOnly = this.effectiveDateDisplay();
        let sortValue = 0;

        if (dateOnly) {
            sortValue = moment(dateOnly, displayDateFormat).valueOf();
        }

        return sortValue;
    }

    public createDateDisplay(): string {
        return dateDisplay(this.createDate);
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

    public isDisciplineEvent(): boolean {
        return this.updateType === 'encumbrance';
    }

    public updateTypeDisplay(): string {
        const updateType = this.updateType || '';
        const events = this.$tm('licensing.licenseEvents') || [];
        const event = events.find((st) => st.key === updateType);
        let eventName = event?.name || this.$t('common.stateUnknown');

        if (updateType === 'licenseDeactivation') {
            eventName = this.$t('licensing.deactivation');
        } else if (updateType === 'issuance' && this.type === 'licenseUpdate') {
            const licenseScopes = this.$tm('licensing.licenseScopes') || [];
            const licenseScope = licenseScopes.find((translate) => translate.key === this.licenseScope);
            const scopeDisplay = licenseScope?.name || '';

            eventName = (scopeDisplay)
                ? this.$t('licensing.licenseIssuance', { scope: scopeDisplay })
                : this.$t('licensing.licenseIssuanceNoScope');
        } else if (updateType === 'issuance') {
            eventName = this.$t('licensing.privilegeIssuance');
        }

        return eventName;
    }

    public encumbranceTypeName(): string {
        const encumbranceTypes = this.$tm('licensing.disciplineTypes') || [];
        const encumbranceType = encumbranceTypes.find((translate) => translate.key === this.encumbranceType);
        const typeName = encumbranceType?.name || '';

        return typeName;
    }

    public npdbTypeName(npdbTypeKey: string): string {
        const npdbTypes = this.$tm('licensing.npdbTypes') || [];
        const npdbType = npdbTypes.find((translate) => translate.key === npdbTypeKey);
        const typeName = npdbType?.name || npdbTypeKey || '';

        return typeName;
    }

    public npdbTypeNames(): Array<string> {
        return this.npdbCategories?.map((npdbTypeKey) => this.npdbTypeName(npdbTypeKey))
            .filter((npdbTypeName) => npdbTypeName.length) || [];
    }

    public noteDisplay(): string {
        const updateType = this.updateType || '';
        let noteDisplay = this.serverNote || '';

        if (updateType === 'homeJurisdictionChange') {
            noteDisplay = this.$t('licensing.homeStateChangeNote');
        } else if (updateType === 'licenseDeactivation') {
            noteDisplay = this.$t('licensing.licenseDeactivationNote');
        } else if (updateType === 'encumbrance') {
            // For encumbrance events, use npdbCategories
            if (this.npdbCategories && this.npdbCategories.length > 0) {
                noteDisplay = this.npdbTypeNames().join(', ');
            }
        }

        return noteDisplay;
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
            createDate: json.createDate,
            effectiveDate: json.effectiveDate || json.dateOfUpdate,
            dateOfUpdate: json.dateOfUpdate,
            serverNote: json.note,
            npdbCategories: json.npdbCategories,
            encumbranceType: json.encumbranceType,
            licenseScope: json.licenseScope,
            state: new State({ abbrev: json.jurisdiction }),
        };

        return new LicenseHistoryItem(licenseHistoryData);
    }
}
