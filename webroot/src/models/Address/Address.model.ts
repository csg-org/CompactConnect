//
//  Address.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/2/2024.
//

import { deleteUndefinedProperties } from '@models/_helpers';
import { State } from '@models/State/State.model';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfaceAddress {
    id?: string | null;
    street1?: string | null;
    street2?: string | null;
    city?: string | null;
    state?: State;
    zip?: string | null;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class Address implements InterfaceAddress {
    public id? = null;
    public street1? = null;
    public street2? = null;
    public city? = null;
    public state? = new State();
    public zip? = null;

    constructor(data?: InterfaceAddress) {
        const cleanDataObject = deleteUndefinedProperties(data);

        Object.assign(this, cleanDataObject);
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class AddressSerializer {
    static fromServer(json: any): Address {
        const addressData = {
            id: json.id,
            street1: json.street1,
            street2: json.street2,
            city: json.city,
            state: new State({ abbrev: json.state }),
            zip: json.zip,
        };

        return new Address(addressData);
    }

    static toServer(addressModel: Address): any {
        return {
            street1: (typeof addressModel.street1 === 'string') ? addressModel.street1 : undefined,
            street2: (typeof addressModel.street2 === 'string') ? addressModel.street2 : undefined,
            city: (typeof addressModel.city === 'string') ? addressModel.city : undefined,
            state: addressModel.state?.abbrev || undefined,
            zip: (typeof addressModel.zip === 'string') ? addressModel.zip : undefined,
        };
    }
}
