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

    public practicingLocationsAll(): string {
        const states: Array<string> = this.licenses?.map((license: License) => license.issueState?.name() || '') || [];
        const stateList = states.filter((state) => state).join(', ') || '';

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
            id: json.providerId,
            firstName: json.givenName,
            middleName: json.middleName,
            lastName: json.familyName,
            dob: json.dateOfBirth,
            ssn: json.ssn,
            address: AddressSerializer.fromServer({
                street1: json.homeStateStreet1,
                street2: json.homeStateStreet2,
                city: json.homeStateCity,
                state: json.jurisdiction,
                zip: json.homeStatePostalCode,
            }),
            licenses: [
                LicenseSerializer.fromServer({
                    issueState: json.jurisdiction,
                    issueDate: json.dateOfIssuance,
                    renewalDate: json.dateOfRenewal,
                    expireDate: json.dateOfExpiration,
                    type: json.licenseType,
                }),
            ],
            status: json.status,
            lastUpdated: json.dateOfUpdate,
        };

        return new Licensee(licenseeData);
    }

    static toServer(licenseeModel: Licensee): any {
        return {
            id: licenseeModel.id,
        };
    }
}
