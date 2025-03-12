//
//  Licensee.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/1/2024.
//

import deleteUndefinedProperties from '@models/_helpers';
import { dateDisplay, relativeFromNowDisplay } from '@models/_formatters/date';
import { formatPhoneNumber, stripPhoneNumber } from '@models/_formatters/phone';
import { Address, AddressSerializer } from '@models/Address/Address.model';
import {
    License,
    LicenseType,
    LicenseSerializer,
    LicenseStatus
} from '@models/License/License.model';
import { MilitaryAffiliation, MilitaryAffiliationSerializer } from '@models/MilitaryAffiliation/MilitaryAffiliation.model';
import { State } from '@models/State/State.model';
import moment from 'moment';

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
    homeJurisdictionLicenseAddress?: Address;
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
    public id? = null;
    public npi? = null;
    public licenseNumber?= null;
    public firstName? = null;
    public middleName? = null;
    public lastName? = null;
    public homeJurisdiction? = new State();
    public homeJurisdictionLicenseAddress? = new Address();
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
        const { $tm, $t } = global.Vue?.config?.globalProperties || {};

        if ($tm) {
            this.$tm = $tm;
            this.$t = $t;
        }

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

    public isMilitary(): boolean {
        // The API does not return the affiliations in the get-all endpoint therefore all users will appear unaffiliated
        // if only that endpoint has been called
        return this.militaryAffiliations?.some((affiliation) => ((affiliation as MilitaryAffiliation).status as any) === 'active') || false;
    }

    public aciveMilitaryAffiliation(): MilitaryAffiliation | null {
        // The API does not return the affiliations in the get-all endpoint therefore all users will appear unaffiliated
        // if only that endpoint has been called
        return this.militaryAffiliations?.find((affiliation) => ((affiliation as MilitaryAffiliation).status as any) === 'active') || null;
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
            bestHomeLicense = activeHomeJurisdictionLicenses.reduce(
                function getMostRecent(prev: License, current: License) {
                    return (prev && moment(prev.issueDate).isAfter(current.issueDate)) ? prev : current;
                } as any
            );
        } else if (inactiveHomeJurisdictionLicenses.length) {
            bestHomeLicense = inactiveHomeJurisdictionLicenses.reduce(
                function getMostRecent(prev: License, current: License) {
                    return (prev && moment(prev.issueDate).isAfter(current.issueDate)) ? prev : current;
                } as any
            );
        }

        return bestHomeLicense;
    }

    public bestHomeJurisdictionLicenseMailingAddress(): Address {
        return this.bestHomeJurisdictionLicense().mailingAddress || new Address();
    }

    public canPurchasePrivileges(): boolean {
        // Return true if the user has an active license in their chosen homestate
        return !!this.activeHomeJurisdictionLicenses().length;
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
            // If the user has registered, json.homeJurisdictionSelection will be populated with the user's selected home state
            // licenseJurisdiction is the server's best guess at their home state. Once #467 is merged we can simply use
            // json.licenseJurisdiction as this will be updated to match the users' choice once that happens, therefor always
            // being the best choice for this field. Also json.homeJurisdictionSelection is not available in get all responses
            homeJurisdiction: json.homeJurisdictionSelection
                ? new State({ abbrev: json.homeJurisdictionSelection.jurisdiction })
                : new State({ abbrev: json.licenseJurisdiction }),
            // This value is updated to equal bestHomeJurisdictionLicenseMailingAddress() whenever a License record is added or updated for the user.
            // In the edge case where the user's best home state license expires this can get out of sync with that calulated value.
            homeJurisdictionLicenseAddress: AddressSerializer.fromServer({
                street1: json.homeAddressStreet1,
                street2: json.homeAddressStreet2,
                city: json.homeAddressCity,
                state: json.homeAddressState,
                zip: json.homeAddressPostalCode,
            }),
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
            status: json.status,
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
