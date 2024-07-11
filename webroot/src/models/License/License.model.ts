//
//  License.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/2/2024.
//

import deleteUndefinedProperties from '@models/_helpers';
import { serverDateFormat } from '@/app.config';
import { dateDisplay, dateDiff } from '@models/_formatters/date';
import { State } from '@models/State/State.model';
import moment from 'moment';

// ========================================================
// =                       Interface                      =
// ========================================================
export enum LicenseType {
    AUDIOLOGIST = 'audiologist',
    COUNSELOR = 'counselor',
    OCCUPATIONAL_THERAPIST = 'occupational therapist',
    OCCUPATIONAL_THERAPY_ASSISTANT = 'occupational therapy assistant',
    SPEECH_LANGUAGE_PATHOLOGIST = 'speech language pathologist',
}

export interface InterfaceLicense {
    id?: string | null;
    issueState?: State,
    issueDate?: string | null;
    renewalDate?: string | null;
    expireDate?: string | null;
    type?: LicenseType | null,
}

// ========================================================
// =                        Model                         =
// ========================================================
export class License implements InterfaceLicense {
    public id? = null;
    public issueState? = new State();
    public issueDate? = null;
    public renewalDate? = null;
    public expireDate? = null;
    public type? = null;

    constructor(data?: InterfaceLicense) {
        const cleanDataObject = deleteUndefinedProperties(data);

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
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class LicenseSerializer {
    static fromServer(json: any): License {
        const licenseData = {
            id: json.id,
            issueState: new State({ abbrev: json.issueState }),
            issueDate: json.issueDate,
            renewalDate: json.renewalDate,
            expireDate: json.expireDate,
            type: json.type,
        };

        return new License(licenseData);
    }

    static toServer(licenseModel: License): any {
        return {
            id: licenseModel.id,
        };
    }
}
