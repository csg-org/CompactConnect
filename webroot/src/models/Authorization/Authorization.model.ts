//
//  Authorization.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/29/2026.
//

import { deleteUndefinedProperties, isDatePastExpiration } from '@models/_helpers';
import { serverDateFormat } from '@/app.config';
import { dateDisplay } from '@models/_formatters/date';
import { ApplicationType } from '@models/Application/Application.model';
import moment from 'moment';
import { StatsigClient } from '@statsig/js-client';

export enum AuthorizationStatus {
    ACTIVE = 'active',
    INACTIVE = 'inactive',
}

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfaceAuthorizationCreate {
    id?: string | null;
    type?: ApplicationType | null,
    status?: AuthorizationStatus,
    issueDate?: string | null;
    renewalDate?: string | null;
    expireDate?: string | null;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class Authorization implements InterfaceAuthorizationCreate {
    public $tm?: any = () => [];
    public $features?: StatsigClient | null = null;
    public id? = null;
    public type?: ApplicationType | null = null;
    public status? = AuthorizationStatus.INACTIVE;
    public issueDate? = null;
    public renewalDate? = null;
    public expireDate? = null;

    constructor(data?: InterfaceAuthorizationCreate) {
        const cleanDataObject = deleteUndefinedProperties(data);
        const global = window as any;
        const { $tm, $features } = global.Vue?.config?.globalProperties || {};

        this.$tm = $tm;
        this.$features = $features;

        Object.assign(this, cleanDataObject);
    }

    // Helper methods
    public issueDateDisplay(): string {
        return dateDisplay(this.issueDate);
    }

    public renewalDateDisplay(): string {
        return dateDisplay(this.renewalDate);
    }

    public expireDateDisplay(): string {
        return dateDisplay(this.expireDate);
    }

    public isExpired(): boolean {
        const now = moment().format(serverDateFormat);
        const { expireDate } = this;

        return isDatePastExpiration({ date: now, dateOfExpiration: expireDate });
    }

    public typeDisplay(): string {
        const authorizationTypes = this.$tm('application.applicationTypes') || [];
        const authorizationType = authorizationTypes.find((translate) => translate.key === this.type);
        const authorizationTypeDisplay = authorizationType?.name || '';

        return authorizationTypeDisplay;
    }

    public typeAbbreviation(): string {
        const authorizationTypes = this.$tm('application.applicationTypes') || [];
        const authorizationType = authorizationTypes.find((translate) => translate.key === this.type);
        const authorizationTypeAbbrev = authorizationType?.abbrev || '';
        const upperCaseAbbrev = authorizationTypeAbbrev.toUpperCase();

        return upperCaseAbbrev;
    }

    public statusDisplay(): string {
        const authorizationStatuses = this.$tm('application.authorizationStatusOptions') || {};
        const authorizationStatusDisplay = authorizationStatuses[this.status || AuthorizationStatus.INACTIVE] || '';

        return authorizationStatusDisplay;
    }

    public isActive(): boolean {
        return this.status === AuthorizationStatus.ACTIVE;
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class AuthorizationSerializer {
    static fromServer(json: any): Authorization {
        const authorizationData = {
            id: json.id,
            type: json.type,
            status: json.status,
            issueDate: json.issueDate,
            renewalDate: json.renewalDate,
            expireDate: json.expireDate,
        };

        return new Authorization(authorizationData);
    }
}
