//
//  Licensee.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/1/2024.
//

import deleteUndefinedProperties from '@models/_helpers';
import { dateDisplay, relativeFromNowDisplay } from '@models/_formatters/date';
import { Address, AddressSerializer } from '@models/Address/Address.model';
import { License, LicenseOccupation, LicenseSerializer } from '@models/License/License.model';
import { MilitaryAffiliation, MilitaryAffiliationSerializer } from '@models/MilitaryAffiliation/MilitaryAffiliation.model';
import { State } from '@models/State/State.model';

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
    firstName?: string | null;
    middleName?: string | null;
    lastName?: string | null;
    address?: Address;
    dob?: string | null;
    birthMonthDay?: string | null;
    ssn?: string | null;
    occupation?: LicenseOccupation | null;
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
    public firstName? = null;
    public middleName? = null;
    public lastName? = null;
    public address? = new Address();
    public dob? = null;
    public birthMonthDay? = null;
    public ssn? = null;
    public occupation? = null;
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

    public residenceLocation(): string {
        return this.address?.state?.name() || '';
    }

    public dobDisplay(): string {
        return dateDisplay(this.dob);
    }

    public ssnMaskedFull(): string {
        const { ssn } = this;
        let masked = '';

        if (ssn) {
            masked = (ssn as string).replace(/[0-9]/g, '#');
        }

        return masked;
    }

    public ssnMaskedPartial(): string {
        const { ssn } = this;
        const masked = (ssn) ? (ssn as string).slice(0, 7).replace(/[0-9]/g, '#') : '';
        const unmasked = (ssn) ? (ssn as string).slice(-4) : '';
        const partial = `${masked}${unmasked}`;

        return partial;
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
            stateNames = this.privileges.map((privilege: License) => privilege?.issueState?.name() || '');
        } else {
            stateNames = this.privilegeStates?.map((state: State) => state.name()) || [];
        }

        return this.getStateListDisplay(stateNames);
    }

    public occupationName(): string {
        const occupations = this.$tm('licensing.occupations') || [];
        const occupation = occupations.find((translate) => translate.key === this.occupation);
        const occupationName = occupation?.name || '';

        return occupationName;
    }

    public statusDisplay(): string {
        return this.$t(`licensing.statusOptions.${this.status}`);
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
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class LicenseeSerializer {
    static fromServer(json: any): Licensee {
        const licenseeData: any = {
            id: json.providerId,
            npi: json.npi,
            firstName: json.givenName,
            middleName: json.middleName,
            lastName: json.familyName,
            address: AddressSerializer.fromServer({
                street1: json.homeAddressStreet1,
                street2: json.homeAddressStreet2,
                city: json.homeAddressCity,
                state: json.homeAddressState,
                zip: json.homeAddressPostalCode,
            }),
            dob: json.dateOfBirth,
            birthMonthDay: json.birthMonthDay,
            ssn: json.ssn,
            occupation: json.licenseType,
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
