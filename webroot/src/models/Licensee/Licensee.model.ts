//
//  Licensee.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/1/2024.
//

import deleteUndefinedProperties from '@models/_helpers';
import { dateDisplay, relativeFromNowDisplay } from '@models/_formatters/date';
import { Address, AddressSerializer } from '@models/Address/Address.model';
import { License, LicenseSerializer } from '@models/License/License.model';

// ========================================================
// =                       Interface                      =
// ========================================================
export enum LicenseeStatus {
    ACTIVE = 'active',
    INACTIVE = 'inactive',
}

export interface InterfaceLicensee {
    id?: string | null;
    firstName?: string | null;
    middleName?: string | null;
    lastName?: string | null;
    address?: Address;
    licenses?: Array<License>
    dob?: string | null;
    ssn?: string | null;
    lastUpdated?: string | null;
    status?: LicenseeStatus | null;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class Licensee implements InterfaceLicensee {
    public id? = null;
    public firstName? = null;
    public middleName? = null;
    public lastName? = null;
    public address? = new Address();
    public licenses? = [];
    public dob? = null;
    public ssn? = null;
    public lastUpdated? = null;
    public status? = null;

    constructor(data?: InterfaceLicensee) {
        const cleanDataObject = deleteUndefinedProperties(data);

        Object.assign(this, cleanDataObject);
    }

    // Helpers
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
            masked = (ssn as string).replace(/[0-9]/g, '#') || '';
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

    public licenseStatesDisplay(): string {
        const states: Array<string> = this.licenses?.map((license: License) => license.issueState?.name() || '') || [];
        const maxNames = 2;
        let stateList = '';

        if (states.length > maxNames) {
            states.forEach((state, idx) => {
                if (idx === 0) {
                    stateList += state;
                } else if (idx + 1 <= maxNames) {
                    stateList += (state) ? `, ${state}` : '';
                }
            });

            stateList += (stateList) ? ` +` : '';
        } else {
            stateList = states.join(', ');
        }

        return stateList;
    }

    public practicingLocationsDisplay(): string {
        const states: Array<string> = this.licenses?.map((license: License) => license.issueState?.name() || '') || [];
        const maxNames = 2;
        let stateList = '';

        if (states.length > maxNames) {
            states.forEach((state, idx) => {
                if (idx === 0) {
                    stateList += state;
                } else if (idx + 1 <= maxNames) {
                    stateList += (state) ? `, ${state}` : '';
                }
            });

            stateList += (stateList) ? ` +` : '';
        } else {
            stateList = states.join(', ');
        }

        return stateList;
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class LicenseeSerializer {
    static fromServer(json: any): Licensee {
        const licenseeData: any = {
            id: json.id,
            firstName: json.given_name,
            middleName: json.middle_name,
            lastName: json.family_name,
            dob: json.date_of_birth,
            ssn: json.ssn,
            address: AddressSerializer.fromServer({
                street1: json.home_state_street_1,
                street2: json.home_state_street_2,
                city: json.home_state_city,
                state: json.jurisdiction,
                zip: json.home_state_postal_code,
            }),
            licenses: [
                LicenseSerializer.fromServer({
                    issueState: json.jurisdiction,
                    issueDate: json.date_of_issuance,
                    renewalDate: json.date_of_renewal,
                    expireDate: json.date_of_expiration,
                    type: json.license_type,
                }),
            ],
            status: json.status,
            lastUpdated: json.date_of_update,
        };

        return new Licensee(licenseeData);
    }

    static toServer(licenseeModel: Licensee): any {
        return {
            id: licenseeModel.id,
        };
    }
}
