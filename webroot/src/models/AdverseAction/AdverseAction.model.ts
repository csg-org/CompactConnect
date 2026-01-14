//
//  AdverseAction.ts
//  CompactConnect
//
//  Created by InspiringApps on 6/18/2025.
//

import { deleteUndefinedProperties } from '@models/_helpers';
import { serverDateFormat } from '@/app.config';
import { dateDisplay, datetimeDisplay } from '@models/_formatters/date';
import { CompactType } from '@models/Compact/Compact.model';
import { State } from '@models/State/State.model';
import moment from 'moment';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfaceAdverseActionCreate {
    id?: string | null;
    compactType?: CompactType | null;
    providerId?: string | null;
    state?: State;
    type?: string | null;
    encumbranceType?: string | null;
    npdbType?: string | null;
    npdbTypes?: Array<string>;
    creationDate?: string | null;
    startDate?: string | null;
    endDate?: string | null;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class AdverseAction implements InterfaceAdverseActionCreate {
    public $tm?: any = () => [];
    public id? = null;
    public compactType? = null;
    public providerId? = null;
    public state? = new State();
    public type? = null;
    public encumbranceType? = null;
    public npdbType? = null;
    public npdbTypes? = [];
    public creationDate? = null;
    public startDate? = null;
    public endDate? = null;

    constructor(data?: InterfaceAdverseActionCreate) {
        const cleanDataObject = deleteUndefinedProperties(data);
        const global = window as any;
        const $tm = global.Vue?.config?.globalProperties?.$tm;

        if ($tm) {
            this.$tm = $tm;
        }

        Object.assign(this, cleanDataObject);
    }

    // Helpers
    public creationDateDisplay(): string {
        return datetimeDisplay(this.creationDate);
    }

    public startDateDisplay(): string {
        return dateDisplay(this.startDate);
    }

    public endDateDisplay(): string {
        return dateDisplay(this.endDate);
    }

    public hasEndDate(): boolean {
        return Boolean(this.endDate);
    }

    public encumbranceTypeName(): string {
        const encumbranceTypes = this.$tm('licensing.disciplineTypes') || [];
        const encumbranceType = encumbranceTypes.find((translate) => translate.key === this.encumbranceType);
        const typeName = encumbranceType?.name || '';

        return typeName;
    }

    public isActive(): boolean {
        // Determine whether the adverse action is currently in effect
        const { startDate, endDate } = this;
        const startDateMoment = (startDate) ? moment(startDate, serverDateFormat) : null;
        const endDateMoment = (endDate) ? moment(endDate, serverDateFormat) : null;
        const now = moment();
        const isAfterStartDate = (startDateMoment?.isValid()) ? now.isSameOrAfter(startDateMoment, 'day') : false;
        const isBeforeEndDate = (endDateMoment?.isValid()) ? now.isBefore(endDateMoment, 'day') : false;
        let isAdverseActionActive = false;

        if (isAfterStartDate && isBeforeEndDate) {
            isAdverseActionActive = true;
        } else if (startDate && !endDate && isAfterStartDate) {
            isAdverseActionActive = true;
        } else if (endDate && !startDate && isBeforeEndDate) {
            isAdverseActionActive = true;
        }

        return isAdverseActionActive;
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class AdverseActionSerializer {
    static fromServer(json: any): AdverseAction {
        const adverseActionData = {
            id: json.adverseActionId,
            compactType: json.compact,
            providerId: json.providerId,
            state: new State({ abbrev: json.jurisdiction }),
            type: json.type,
            encumbranceType: json.encumbranceType,
            npdbTypes: Array.isArray(json.clinicalPrivilegeActionCategories)
                ? json.clinicalPrivilegeActionCategories
                : [],
            creationDate: json.creationDate,
            startDate: json.effectiveStartDate,
            endDate: json.effectiveLiftDate,
        };

        return new AdverseAction(adverseActionData);
    }
}
