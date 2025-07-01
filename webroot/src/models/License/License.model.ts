//
//  License.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/2/2024.
//

import { deleteUndefinedProperties, isDatePastExpiration } from '@models/_helpers';
import { serverDateFormat } from '@/app.config';
import { dateDisplay } from '@models/_formatters/date';
import { Compact } from '@models/Compact/Compact.model';
import { State } from '@models/State/State.model';
import { LicenseHistoryItem, LicenseHistoryItemSerializer } from '@models/LicenseHistoryItem/LicenseHistoryItem.model';
import { Address, AddressSerializer } from '@models/Address/Address.model';
import { AdverseAction, AdverseActionSerializer } from '@models/AdverseAction/AdverseAction.model';
import moment from 'moment';

// ========================================================
// =                       Interface                      =
// ========================================================
export enum LicenseType { // Temp server definition until server returns via endpoint
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

export enum EligibilityStatus {
    ELIGIBLE = 'eligible',
    INELIGIBLE = 'ineligible',
    NA = 'n/a',
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
    licenseType?: LicenseType | null,
    history?: Array<LicenseHistoryItem>,
    status?: LicenseStatus,
    statusDescription?: string | null,
    eligibility?: EligibilityStatus,
    adverseActions?: Array<AdverseAction>,
}

// ========================================================
// =                        Model                         =
// ========================================================
export class License implements InterfaceLicense {
    // This model is used to represent both privileges and licenses as their shape almost entirely overlaps
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
    public licenseType? = null;
    public history? = [];
    public status? = LicenseStatus.INACTIVE;
    public statusDescription? = null;
    public eligibility? = EligibilityStatus.INELIGIBLE;
    public adverseActions? = [];

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

        return isDatePastExpiration({ date: now, dateOfExpiration: expireDate });
    }

    public isDeactivated(): boolean {
        const { history } = this;
        const historyLength = history?.length || 0;
        const lastEvent = (history && historyLength) ? history[historyLength - 1] : new LicenseHistoryItem();

        const isLastEventDeactivation = lastEvent.updateType === 'deactivation';
        const isInactive = this.status === LicenseStatus.INACTIVE;

        return isLastEventDeactivation && isInactive;
    }

    public isCompactEligible(): boolean {
        return this.eligibility === EligibilityStatus.ELIGIBLE;
    }

    public licenseTypeAbbreviation(): string {
        const licenseTypes = this.$tm('licensing.licenseTypes') || [];
        const licenseType = licenseTypes.find((translate) => translate.key === this.licenseType);
        const licenseTypeAbbrev = licenseType?.abbrev || '';
        const upperCaseAbbrev = licenseTypeAbbrev.toUpperCase();

        return upperCaseAbbrev;
    }

    public displayName(delimiter = ' - ', displayAbbrev = false): string {
        const stateName = this.issueState?.name() || '';
        const licenseTypeToShow = (displayAbbrev) ? this.licenseTypeAbbreviation() : this.licenseType;

        return `${stateName}${stateName && licenseTypeToShow ? delimiter : ''}${licenseTypeToShow || ''}`;
    }

    public historyWithFabricatedEvents(): Array<LicenseHistoryItem> {
        // inject purchase event
        const historyWithFabricatedEvents = [ new LicenseHistoryItem({
            type: 'fabricatedEvent',
            updateType: 'purchased',
            dateOfUpdate: this.issueDate
        })];

        // inject expiration events
        if (Array.isArray(this.history)) {
            this.history.forEach((historyItem) => {
                const { updateType, previousValues, dateOfUpdate } = historyItem;
                const { dateOfExpiration } = previousValues as any;

                if (updateType === 'renewal'
                    && (previousValues as any)?.dateOfExpiration
                    && dateOfUpdate
                    && (isDatePastExpiration({ date: dateOfUpdate, dateOfExpiration }))) {
                    historyWithFabricatedEvents.push(new LicenseHistoryItem({
                        type: 'fabricatedEvent',
                        updateType: 'expired',
                        dateOfUpdate: dateOfExpiration
                    }));
                }

                historyWithFabricatedEvents.push(historyItem);
            });

            if (this.isExpired()) {
                historyWithFabricatedEvents.push(new LicenseHistoryItem({
                    type: 'fabricatedEvent',
                    updateType: 'expired',
                    dateOfUpdate: this.expireDate
                }));
            }
        }

        return historyWithFabricatedEvents;
    }

    public isEncumbered(): boolean {
        return this.adverseActions?.some((adverseAction: AdverseAction) => adverseAction.isActive()) || false;
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class LicenseSerializer {
    static fromServer(json: any): License {
        const licenseData = {
            id: `${json.providerId}-${json.jurisdiction}-${json.licenseType}`,
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
            licenseNumber: json.licenseNumber, // License field only
            privilegeId: json.privilegeId, // Privilege field only
            renewalDate: json.dateOfRenewal,
            expireDate: json.dateOfExpiration,
            licenseType: json.licenseType,
            history: [] as Array<LicenseHistoryItem>,
            status: json.licenseStatus || json.status,
            statusDescription: json.licenseStatusName,
            eligibility: (json.type === 'license' || json.type === 'license-home')
                ? json.compactEligibility
                : EligibilityStatus.NA,
            adverseActions: [] as Array<AdverseAction>,
        };

        if (Array.isArray(json.history)) {
            json.history.forEach((serverHistoryItem) => {
                licenseData.history.push(LicenseHistoryItemSerializer.fromServer(serverHistoryItem));
            });
        }

        if (Array.isArray(json.adverseActions)) {
            json.adverseActions.forEach((serverAdverseAction) => {
                licenseData.adverseActions.push(AdverseActionSerializer.fromServer(serverAdverseAction));
            });
        }

        return new License(licenseData);
    }
}
