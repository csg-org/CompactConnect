//
//  License.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/2/2024.
//

import deleteUndefinedProperties from '@models/_helpers';
import { serverDateFormat } from '@/app.config';
import { dateDisplay, dateDiff } from '@models/_formatters/date';
import { Compact } from '@models/Compact/Compact.model';
import { State } from '@models/State/State.model';
import moment from 'moment';

// ========================================================
// =                       Interface                      =
// ========================================================
export enum LicenseOccupation { // Temp server definition until server returns via endpoint
    AUDIOLOGIST = 'audiologist',
    SPEECH_LANGUAGE_PATHOLOGIST = 'speech-language pathologist',
    SPEECH_AND_LANGUAGE_PATHOLOGIST = 'speech and language pathologist',
    OCCUPATIONAL_THERAPIST = 'occupational therapist',
    OCCUPATIONAL_THERAPY_ASSISTANT = 'occupational therapy assistant',
    PROFESSIONAL_COUNSELOR = 'licensed professional counselor',
    MENTAL_HEALTH_COUNSELOR = 'licensed mental health counselor',
    CLINICAL_MENTAL_HEALTH_COUNSELOR = 'licensed clinical mental health counselor',
    PROFESSIONAL_CLINICAL_COUNSELOR = 'licensed professional clinical counselor',
}

export enum LicenseStatus { // Temp server definition until server returns via endpoint
    ACTIVE = 'active',
    INACTIVE = 'inactive',
}

export interface InterfaceLicense {
    id?: string | null;
    compact?: Compact | null;
    isPrivilege?: boolean;
    issueState?: State,
    isHomeState?: boolean;
    issueDate?: string | null;
    renewalDate?: string | null;
    expireDate?: string | null;
    occupation?: LicenseOccupation | null,
    statusState?: LicenseStatus,
    statusCompact?: LicenseStatus,
}

// ========================================================
// =                        Model                         =
// ========================================================
export class License implements InterfaceLicense {
    public $tm?: any = () => [];
    public id? = null;
    public compact? = null;
    public isPrivilege? = false;
    public issueState? = new State();
    public isHomeState? = false;
    public issueDate? = null;
    public renewalDate? = null;
    public expireDate? = null;
    public occupation? = null;
    public statusState? = LicenseStatus.INACTIVE;
    public statusCompact? = LicenseStatus.INACTIVE;

    constructor(data?: InterfaceLicense) {
        const cleanDataObject = deleteUndefinedProperties(data);
        const global = window as any;
        const $tm = global.Vue?.config?.globalProperties?.$tm;

        if ($tm) {
            this.$tm = $tm;
        }

        Object.assign(this, cleanDataObject);
    }

    // Helpers
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
        const diff = dateDiff(now, expireDate, 'days') || 0;

        return Boolean(diff > 0);
    }

    public occupationName(): string {
        const occupations = this.$tm('licensing.occupations') || [];
        const occupation = occupations.find((translate) => translate.key === this.occupation);
        const occupationName = occupation?.name || '';

        return occupationName;
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class LicenseSerializer {
    static fromServer(json: any): License {
        const licenseData = {
            id: json.id,
            compact: new Compact({ type: json.compact }),
            isPrivilege: Boolean(json.type === 'privilege'),
            issueState: new State({ abbrev: json.jurisdiction || json.licenseJurisdiction }),
            isHomeState: Boolean(json.type === 'license-home'),
            issueDate: json.dateOfIssuance,
            renewalDate: json.dateOfRenewal,
            expireDate: json.dateOfExpiration,
            occupation: json.licenseType,
            statusState: json.status,
            statusCompact: json.status, // In the near future, the server will send a separate field for this
        };

        return new License(licenseData);
    }
}
