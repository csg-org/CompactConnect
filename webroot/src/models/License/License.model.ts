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
import { LicenseHistoryItem } from '@models/LicenseHistoryItem/LicenseHistoryItem.model';
import { Address, AddressSerializer } from '@models/Address/Address.model';
import { AdverseAction, AdverseActionSerializer } from '@models/AdverseAction/AdverseAction.model';
import { Investigation, InvestigationSerializer } from '@models/Investigation/Investigation.model';
import moment from 'moment';
import { StatsigClient } from '@statsig/js-client';

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
    activeFromDate?: string | null;
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
    investigations?: Array<Investigation>,
}

// ========================================================
// =                        Model                         =
// ========================================================
export class License implements InterfaceLicense {
    // This model is used to represent both privileges and licenses as their shape almost entirely overlaps
    public $tm?: any = () => [];
    public $features?: StatsigClient | null = null;
    public id? = null;
    public compact? = null;
    public isPrivilege? = false;
    public licenseeId? = null;
    public issueState? = new State();
    public issueDate? = null;
    public activeFromDate? = null;
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
    public investigations? = [];

    constructor(data?: InterfaceLicense) {
        const cleanDataObject = deleteUndefinedProperties(data);
        const global = window as any;
        const { $tm, $features } = global.Vue?.config?.globalProperties || {};

        this.$tm = $tm;
        this.$features = $features;

        Object.assign(this, cleanDataObject);
    }

    // Helpers
    public issueDateDisplay(): string {
        return dateDisplay(this.issueDate);
    }

    public renewalDateDisplay(): string {
        return dateDisplay(this.renewalDate);
    }

    public activeFromDateDisplay(): string {
        return dateDisplay(this.activeFromDate);
    }

    public expireDateDisplay(): string {
        return dateDisplay(this.expireDate);
    }

    public isExpired(): boolean {
        const now = moment().format(serverDateFormat);
        const { expireDate } = this;

        return isDatePastExpiration({ date: now, dateOfExpiration: expireDate });
    }

    public isAdminDeactivated(): boolean {
        // NOTE: History is needed to determine this status; and history may be fetched in a separate API call and not always available on the License / Privilege list fetch
        const adminDeactivateList = ['deactivation', 'licenseDeactivation', 'homeJurisdictionChange'];
        const isInactive = this.status === LicenseStatus.INACTIVE;
        const lastEvent: LicenseHistoryItem = this.history?.at(-1) || new LicenseHistoryItem();
        const lastEventType = lastEvent?.updateType || '';

        return isInactive && adminDeactivateList.includes(lastEventType);
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

    public isEncumbered(): boolean {
        return this.adverseActions?.some((adverseAction: AdverseAction) => adverseAction.isActive()) || false;
    }

    public isLatestLiftedEncumbranceWithinWaitPeriod(): boolean {
        const encumbrances = this.adverseActions || [];
        const inactiveEncumbrancesWithEndDate: Array<AdverseAction> = encumbrances.filter((encumbrace: AdverseAction) =>
            !encumbrace.isActive() && encumbrace.endDate);
        let isWithinWaitPeriod = false;

        if (inactiveEncumbrancesWithEndDate.length) {
            const latestEncumbrance = inactiveEncumbrancesWithEndDate.reduce(
                (prev: AdverseAction, curr: AdverseAction): AdverseAction => (
                    moment(prev.endDate, serverDateFormat).isAfter(moment(curr.endDate, serverDateFormat)) ? prev : curr
                )
            );

            // Check if the end date is within the last 2 years (within wait period)
            const endDate = moment(latestEncumbrance.endDate, serverDateFormat);
            const waitPeriod = moment().subtract(2, 'years');

            isWithinWaitPeriod = endDate.isAfter(waitPeriod);
        }

        return isWithinWaitPeriod;
    }

    public isUnderInvestigation(): boolean {
        return this.investigations?.some((investigation: Investigation) => investigation.isActive()) || false;
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
            activeFromDate: json.activeSince,
            npi: json.npi,
            licenseNumber: json.licenseNumber, // License field only
            privilegeId: json.privilegeId, // Privilege field only
            renewalDate: json.dateOfRenewal,
            expireDate: json.dateOfExpiration,
            licenseType: json.licenseType,
            status: json.licenseStatus || json.status,
            statusDescription: json.licenseStatusName,
            eligibility: (json.type === 'license' || json.type === 'license-home')
                ? json.compactEligibility
                : EligibilityStatus.NA,
            adverseActions: [] as Array<AdverseAction>,
            investigations: [] as Array<Investigation>,
        };

        if (Array.isArray(json.adverseActions)) {
            json.adverseActions.forEach((serverAdverseAction) => {
                licenseData.adverseActions.push(AdverseActionSerializer.fromServer(serverAdverseAction));
            });
        }

        if (Array.isArray(json.investigations)) {
            json.investigations.forEach((serverInvestigation) => {
                licenseData.investigations.push(InvestigationSerializer.fromServer(serverInvestigation));
            });
        }

        return new License(licenseData);
    }
}
