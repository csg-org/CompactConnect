//
//  Licensee.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/1/2024.
//

import { deleteUndefinedProperties } from '@models/_helpers';
import { dateDisplay, relativeFromNowDisplay } from '@models/_formatters/date';
import { formatPhoneNumber, stripPhoneNumber } from '@models/_formatters/phone';
import { Address } from '@models/Address/Address.model';
import {
    License,
    LicenseType,
    LicenseSerializer,
    LicenseStatus,
    EligibilityStatus
} from '@models/License/License.model';
import { MilitaryAffiliation, MilitaryAffiliationSerializer } from '@models/MilitaryAffiliation/MilitaryAffiliation.model';
import { Investigation } from '@models/Investigation/Investigation.model';
import { State } from '@models/State/State.model';
import moment from 'moment';
import { StatsigClient } from '@statsig/js-client';

/**
 * This model is used to represent both get one and get all server responses
 * the params: licenses, privileges and militaryAffiliations are not present on get all responses
 * those params will be therefore be empty arrays on such objects
 */

// ========================================================
// =                       Interface                      =
// ========================================================
export enum LicenseeStatus {
    ACTIVE = 'active',
    INACTIVE = 'inactive',
}

export interface InterfaceLicensee {
    id?: string | null;
    npi?: string | null;
    licenseNumber?: string | null;
    firstName?: string | null;
    middleName?: string | null;
    lastName?: string | null;
    homeJurisdiction?: State;
    dob?: string | null;
    birthMonthDay?: string | null;
    ssnLastFour?: string | null;
    phoneNumber?: string | null;
    licenseType?: LicenseType | null;
    militaryAffiliations?: Array <MilitaryAffiliation>;
    licenseStates?: Array<State>;
    licenses?: Array<License>;
    privilegeStates?: Array<State>;
    privileges?: Array<License>;
    lastUpdated?: string | null;
    status?: LicenseeStatus;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class Licensee implements InterfaceLicensee {
    public $tm?: any = () => [];
    public $t?: any = () => '';
    public $features?: StatsigClient | null = null;
    public id? = null;
    public npi? = null;
    public licenseNumber?= null;
    public firstName? = null;
    public middleName? = null;
    public lastName? = null;
    public homeJurisdiction? = new State();
    public dob? = null;
    public birthMonthDay? = null;
    public ssnLastFour? = null;
    public phoneNumber? = null;
    public licenseType? = null;
    public licenseStates? = [];
    public licenses? = [];
    public privilegeStates? = [];
    public militaryAffiliations? = [];
    public privileges? = [];
    public lastUpdated? = null;
    public status? = LicenseeStatus.INACTIVE;

    constructor(data?: InterfaceLicensee) {
        const cleanDataObject = deleteUndefinedProperties(data);
        const global = window as any;
        const { $tm, $t, $features } = global.Vue?.config?.globalProperties || {};

        this.$tm = $tm;
        this.$t = $t;
        this.$features = $features;

        Object.assign(this, cleanDataObject);
    }

    // Helpers
    public nameDisplay(): string {
        const firstName = this.firstName || '';
        const lastName = this.lastName || '';

        return `${firstName} ${lastName}`.trim();
    }

    public dobDisplay(): string {
        return dateDisplay(this.dob);
    }

    public ssnDisplay(): string {
        const { ssnLastFour } = this;

        return (ssnLastFour) ? `*** ** ${ssnLastFour}` : '';
    }

    public lastUpdatedDisplay(): string {
        return dateDisplay(this.lastUpdated);
    }

    public lastUpdatedDisplayRelative(): string {
        return relativeFromNowDisplay(this.lastUpdated, true);
    }

    public getStateListDisplay(stateNames: Array<string>, maxNames = 2): string {
        let stateList = '';

        if (stateNames.length > maxNames) {
            stateNames.forEach((state, idx) => {
                if (idx === 0) {
                    stateList += state;
                } else if (idx + 1 <= maxNames) {
                    stateList += (state) ? `, ${state}` : '';
                }
            });

            stateList += (stateList) ? ` +` : '';
        } else {
            stateList = stateNames.join(', ');
        }

        return stateList;
    }

    public licenseStatesDisplay(): string {
        let stateNames: Array<string> = [];

        if (this.licenses?.length) {
            stateNames = this.licenses.map((license: License) => license?.issueState?.name() || '');
        } else {
            stateNames = this.licenseStates?.map((state: State) => state.name()) || [];
        }

        return this.getStateListDisplay(stateNames);
    }

    public privilegeStatesAllDisplay(): string {
        const maxStateNamesToShow = 99;
        let stateNames: Array<string> = [];

        if (this.privileges?.length) {
            stateNames = this.privileges.map((privilege: License) => privilege?.issueState?.name() || '');
        } else {
            stateNames = this.privilegeStates?.map((state: State) => state.name()) || [];
        }

        return this.getStateListDisplay(stateNames, maxStateNamesToShow);
    }

    public privilegeStatesDisplay(): string {
        let stateNames: Array<string> = [];

        if (this.privileges?.length) {
            stateNames = this.privileges.filter((privilege: License) => (privilege?.status === LicenseStatus.ACTIVE)).map((privilege: License) => privilege?.issueState?.name() || '');
        } else {
            stateNames = this.privilegeStates?.map((state: State) => state.name()) || [];
        }

        return this.getStateListDisplay(stateNames);
    }

    public licenseTypeName(): string {
        const licenseTypes = this.$tm('licensing.licenseTypes') || [];
        const licenseType = licenseTypes.find((translate) => translate.key === this.licenseType);
        const licenseTypeName = licenseType?.name || '';

        return licenseTypeName;
    }

    public statusDisplay(): string {
        return this.$t(`licensing.statusOptions.${this.status}`);
    }

    public phoneNumberDisplay(): string {
        return this.phoneNumber ? formatPhoneNumber(stripPhoneNumber(this.phoneNumber)) : '';
    }

    public isMilitaryStatusActive(): boolean {
        // The API does not return the affiliations in the get-all endpoint therefore all users will appear unaffiliated
        // if only that endpoint has been called
        return this.militaryAffiliations?.some((affiliation: MilitaryAffiliation) => affiliation.status as any === 'active') || false;
    }

    public isMilitaryStatusInitializing(): boolean {
        // The API does not return the affiliations in the get-all endpoint therefore this will always return false
        // if only that endpoint has been called even if the user has initializing affiliations
        return this.militaryAffiliations?.some((affiliation: MilitaryAffiliation) => affiliation.status as any === 'initializing') || false;
    }

    public activeMilitaryAffiliation(): MilitaryAffiliation | null {
        // The API does not return the affiliations in the get-all endpoint therefore this will always return null
        // if only that endpoint has been called even if the user has active affiliations
        return this.militaryAffiliations?.find((affiliation: MilitaryAffiliation) => affiliation.status as any === 'active') || null;
    }

    public homeJurisdictionLicenses(): Array<License> {
        return this.licenses?.filter((license: License) =>
            (license.issueState?.abbrev === this.homeJurisdiction?.abbrev)) || [];
    }

    public activeHomeJurisdictionLicenses(): Array<License> {
        return this.homeJurisdictionLicenses().filter((license: License) =>
            (license.status === LicenseStatus.ACTIVE));
    }

    public inactiveHomeJurisdictionLicenses(): Array<License> {
        return this.homeJurisdictionLicenses().filter((license: License) =>
            (license.status === LicenseStatus.INACTIVE));
    }

    public homeJurisdictionDisplay(): string {
        return this.homeJurisdiction?.name() || '';
    }

    public bestHomeJurisdictionLicense(): License {
        // Return most recently issued active license that matches the best guess at the user's home jurisdiction
        // If no active license return  most recently issued inactive license that matches the user's registered home jurisdiction
        let bestHomeLicense = new License();
        const activeHomeJurisdictionLicenses = this.activeHomeJurisdictionLicenses();
        const inactiveHomeJurisdictionLicenses = this.inactiveHomeJurisdictionLicenses();

        if (activeHomeJurisdictionLicenses.length) {
            bestHomeLicense = this.findMostRecentLicense(activeHomeJurisdictionLicenses);
        } else if (inactiveHomeJurisdictionLicenses.length) {
            bestHomeLicense = this.findMostRecentLicense(inactiveHomeJurisdictionLicenses);
        }

        return bestHomeLicense;
    }

    public bestHomeJurisdictionLicenseMailingAddress(): Address {
        return this.bestHomeJurisdictionLicense().mailingAddress || new Address();
    }

    private findMostRecentLicense(licenses: Array<License>): License {
        let result: License = new License();

        if (licenses.length) {
            result = licenses.reduce((prev: License, current: License) => {
                let moreRecentLicense: License;

                if (!prev.issueDate) {
                    moreRecentLicense = current;
                } else if (!current.issueDate) {
                    moreRecentLicense = prev;
                } else {
                    moreRecentLicense = moment(prev.issueDate).isAfter(current.issueDate) ? prev : current;
                }

                return moreRecentLicense;
            });
        }

        return result;
    }

    public bestLicense(): License {
        let bestLicense: License = new License();
        const bestHomeLicense: License = this.bestHomeJurisdictionLicense();

        if (bestHomeLicense.licenseeId) {
            bestLicense = bestHomeLicense;
        } else {
            // If no home jurisdiction license, get the most recent active non-home state license
            const nonHomeStateLicenses: Array<License> = (this.licenses?.filter((license: License) =>
                license.issueState?.abbrev !== this.homeJurisdiction?.abbrev) || []);
            let bestNonHomeLicense: License = new License();

            if (nonHomeStateLicenses.length) {
                // First check for active licenses
                const activeNonHomeLicenses = nonHomeStateLicenses.filter((license: License) =>
                    license.status === LicenseStatus.ACTIVE);

                if (activeNonHomeLicenses.length) {
                    // Find the most recent active non-home license
                    bestNonHomeLicense = this.findMostRecentLicense(activeNonHomeLicenses);
                } else {
                    // If no active found, get most recent inactive license
                    bestNonHomeLicense = this.findMostRecentLicense(nonHomeStateLicenses);
                }
            }

            if (bestNonHomeLicense.licenseeId) {
                bestLicense = bestNonHomeLicense;
            }
        }

        return bestLicense;
    }

    public bestLicenseMailingAddress(): Address {
        return this.bestLicense().mailingAddress || new Address();
    }

    public hasEncumberedLicenses(): boolean {
        return this.licenses?.some((license: License) => license.isEncumbered()) || false;
    }

    public hasEncumberedPrivileges(): boolean {
        return this.privileges?.some((privilege: License) => privilege.isEncumbered()) || false;
    }

    public isEncumbered(): boolean {
        return this.hasEncumberedLicenses() || this.hasEncumberedPrivileges();
    }

    public hasEncumbranceLiftedWithinWaitPeriod(): boolean {
        return this.privileges?.some((privilege: License) =>
            privilege.isLatestLiftedEncumbranceWithinWaitPeriod()) || false;
    }

    public hasUnderInvestigationLicenses(): boolean {
        return this.licenses?.some((license: License) => license.isUnderInvestigation()) || false;
    }

    public hasUnderInvestigationPrivileges(): boolean {
        return this.privileges?.some((privilege: License) => privilege.isUnderInvestigation()) || false;
    }

    public isUnderInvestigation(): boolean {
        return this.hasUnderInvestigationLicenses() || this.hasUnderInvestigationPrivileges();
    }

    public underInvestigationStates(): Array<State> {
        const investigationStates: Array<State> = [];
        const investigationStatesAbbrev: Array<string> = [];

        this.licenses?.forEach((license: License) => {
            if (license.isUnderInvestigation()) {
                license.investigations?.forEach((investigation: Investigation) => {
                    const investigationState = investigation.state;
                    const investigationStateAbbrev = investigation.state?.abbrev;

                    if (investigation.isActive()
                        && investigationState
                        && investigationStateAbbrev
                        && !investigationStatesAbbrev.includes(investigationStateAbbrev)) {
                        investigationStates.push(investigationState);
                        investigationStatesAbbrev.push(investigationStateAbbrev);
                    }
                });
            }
        });

        this.privileges?.forEach((privilege: License) => {
            if (privilege.isUnderInvestigation()) {
                privilege.investigations?.forEach((investigation: Investigation) => {
                    const investigationState = investigation.state;
                    const investigationStateAbbrev = investigation.state?.abbrev;

                    if (investigation.isActive()
                        && investigationState
                        && investigationStateAbbrev
                        && !investigationStatesAbbrev.includes(investigationStateAbbrev)) {
                        investigationStates.push(investigationState);
                        investigationStatesAbbrev.push(investigationStateAbbrev);
                    }
                });
            }
        });

        return investigationStates;
    }

    public purchaseEligibleLicenses(): Array<License> {
        return this.activeHomeJurisdictionLicenses()
            .filter((license: License) => (license.eligibility === EligibilityStatus.ELIGIBLE));
    }

    public canPurchasePrivileges(): boolean {
        return !!this.purchaseEligibleLicenses().length
            && !this.isMilitaryStatusInitializing()
            && !this.isEncumbered()
            && !this.hasEncumbranceLiftedWithinWaitPeriod();
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class LicenseeSerializer {
    static fromServer(json: any): Licensee {
        const licenseeData: any = {
            id: json.providerId,
            npi: json.npi,
            licenseNumber: json.licenseNumber,
            firstName: json.givenName,
            middleName: json.middleName,
            lastName: json.familyName,
            // json.homeJurisdictionSelection has been deprecated and replaced with json.currentHomeJurisdiction
            homeJurisdiction: (json.currentHomeJurisdiction && json.currentHomeJurisdiction.trim().toLowerCase() !== 'unknown')
                ? new State({ abbrev: json.currentHomeJurisdiction })
                : new State({ abbrev: json.licenseJurisdiction }),
            dob: json.dateOfBirth,
            birthMonthDay: json.birthMonthDay,
            ssnLastFour: json.ssnLastFour,
            phoneNumber: json.phoneNumber,
            licenseType: json.licenseType,
            licenseStates: [] as Array<State>,
            licenses: [] as Array<License>,
            privilegeStates: [] as Array<State>,
            privileges: [] as Array<License>,
            militaryAffiliations: [] as Array<MilitaryAffiliation>,
            status: json.licenseStatus,
            lastUpdated: json.dateOfUpdate,
        };

        // In get-all responses, server only returns a license state, not the actual license objects
        if (json.licenseJurisdiction) {
            licenseeData.licenseStates.push(new State({ abbrev: json.licenseJurisdiction }));
        }

        // In get-one responses, server returns actual license objects
        if (Array.isArray(json.licenses)) {
            json.licenses.forEach((serverLicense) => {
                licenseeData.licenses.push(LicenseSerializer.fromServer(serverLicense));
            });
        }

        // In get-all responses, server only returns privilege states, not the actual privilege objects
        if (Array.isArray(json.privilegeJurisdictions)) {
            json.privilegeJurisdictions.forEach((serverPrivilegeJurisdiction) => {
                licenseeData.privilegeStates.push(new State({ abbrev: serverPrivilegeJurisdiction }));
            });
        }

        // In get-one responses, server returns actual privilege objects
        if (Array.isArray(json.privileges)) {
            json.privileges.forEach((serverPrivilege) => {
                licenseeData.privileges.push(LicenseSerializer.fromServer(serverPrivilege));
            });
        }

        // In get-one responses, server returns military affiliation ojects, does not in get-all
        if (Array.isArray(json.militaryAffiliations)) {
            json.militaryAffiliations.forEach((serverAffiliation) => {
                licenseeData.militaryAffiliations.push(MilitaryAffiliationSerializer.fromServer(serverAffiliation));
            });
        }

        return new Licensee(licenseeData);
    }

    static toServer(licenseeModel: Licensee): any {
        return {
            id: licenseeModel.id,
        };
    }
}
