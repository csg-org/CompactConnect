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
import { LicenseHistoryItem, LicenseHistoryItemSerializer } from '@models/LicenseHistoryItem/LicenseHistoryItem.model';
import { Address, AddressSerializer } from '@models/Address/Address.model';
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
    licenseeId?: string | null;
    issueState?: State,
    isHomeState?: boolean;
    issueDate?: string | null;
    renewalDate?: string | null;
    mailingAddress?: Address;
    expireDate?: string | null;
    npi?: string | null;
    licenseNumber?: string | null;
    privilegeId?: string | null;
    occupation?: LicenseOccupation | null,
    history?: Array<LicenseHistoryItem>,
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
    public licenseeId? = null;
    public issueState? = new State();
    public issueDate? = null;
    public mailingAddress? = new Address();
    public renewalDate? = null;
    public npi? = null;
    public licenseNumber? = null;
    public privilegeId? = null;
    public expireDate? = null;
    public occupation? = null;
    public history? = [];
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

    public occupationAbbreviation(): string {
        const occupations = this.$tm('licensing.occupations') || [];
        const occupation = occupations.find((translate) => translate.key === this.occupation);
        const occupationAbbrev = occupation?.abbrev || '';
        const upperCaseAbbrev = occupationAbbrev.toUpperCase();

        return upperCaseAbbrev;
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
            licenseeId: json.providerId,
            mailingAddress: AddressSerializer.fromServer({
                street1: json.homeAddressStreet1,
                street2: json.homeAddressStreet2,
                city: json.homeAddressCity,
                state: json.homeAddressState,
                zip: json.homeAddressPostalCode,
            }),
            issueState: new State({ abbrev: json.jurisdiction || json.licenseJurisdiction }),
            issueDate: json.dateOfIssuance,
            npi: json.npi,
            licenseNumber: json.licenseNumber,
            privilegeId: json.privilegeId,
            renewalDate: json.dateOfRenewal,
            expireDate: json.dateOfExpiration,
            occupation: json.licenseType,
            statusState: json.status,
            history: [] as Array <LicenseHistoryItem>,
            statusCompact: json.status, // In the near future, the server will send a separate field for this
        };

        if (Array.isArray(json.history)) {
            json.history.forEach((serverHistoryItem) => {
                // We are only populating renewals at this time
                if (serverHistoryItem.updateType === 'renewal') {
                    licenseData.history.push(LicenseHistoryItemSerializer.fromServer(serverHistoryItem));
                }
            });
        }

        return new License(licenseData);
    }
}
