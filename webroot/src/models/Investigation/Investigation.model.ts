//
//  Investigation.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/28/2025.
//

import { deleteUndefinedProperties } from '@models/_helpers';
import { serverDateFormat } from '@/app.config';
import { dateDisplay } from '@models/_formatters/date';
import { CompactType } from '@models/Compact/Compact.model';
import { State } from '@models/State/State.model';
import moment from 'moment';
import { StatsigClient } from '@statsig/js-client';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfaceInvestigationCreate {
    id?: string | null;
    compactType?: CompactType | null;
    providerId?: string | null;
    state?: State;
    type?: string | null;
    startDate?: string | null;
    updateDate?: string | null;
    endDate?: string | null;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class Investigation implements InterfaceInvestigationCreate {
    public $tm?: any = () => [];
    public $features?: StatsigClient | null = null;
    public id? = null;
    public compactType? = null;
    public providerId? = null;
    public state? = new State();
    public type? = null;
    public startDate? = null;
    public updateDate? = null;
    public endDate? = null;

    constructor(data?: InterfaceInvestigationCreate) {
        const cleanDataObject = deleteUndefinedProperties(data);
        const global = window as any;
        const { $tm, $features } = global.Vue?.config?.globalProperties || {};

        this.$tm = $tm;
        this.$features = $features;

        Object.assign(this, cleanDataObject);
    }

    // Helper methods
    public startDateDisplay(): string {
        return dateDisplay(this.startDate);
    }

    public updateDateDisplay(): string {
        return dateDisplay(this.updateDate);
    }

    public endDateDisplay(): string {
        return dateDisplay(this.endDate);
    }

    public hasEndDate(): boolean {
        return Boolean(this.endDate);
    }

    public isActive(): boolean {
        // Determine whether the investigation is currently in effect
        const { startDate, endDate } = this;
        const startDateMoment = (startDate) ? moment(startDate, serverDateFormat) : null;
        const endDateMoment = (endDate) ? moment(endDate, serverDateFormat) : null;
        const now = moment();
        const isAfterStartDate = (startDateMoment?.isValid()) ? now.isSameOrAfter(startDateMoment, 'day') : false;
        const isBeforeEndDate = (endDateMoment?.isValid()) ? now.isBefore(endDateMoment, 'day') : false;
        let isInvestigationActive = false;

        if (isAfterStartDate && isBeforeEndDate) {
            isInvestigationActive = true;
        } else if (startDate && !endDate && isAfterStartDate) {
            isInvestigationActive = true;
        } else if (endDate && !startDate && isBeforeEndDate) {
            isInvestigationActive = true;
        }

        return isInvestigationActive;
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class InvestigationSerializer {
    static fromServer(json: any): Investigation {
        const investigationData = {
            id: json.investigationId,
            compactType: json.compact,
            providerId: json.providerId,
            state: new State({ abbrev: json.jurisdiction }),
            type: json.type,
            startDate: json.creationDate,
            updateDate: json.dateOfUpdate,
            endDate: json.endDate,
        };

        return new Investigation(investigationData);
    }
}
