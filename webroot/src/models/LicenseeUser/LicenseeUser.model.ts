//
//  user.model.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

/* eslint-disable max-classes-per-file */
import { AuthTypes } from '@/app.config';
import deleteUndefinedProperties from '@models/_helpers';
import { Licensee, LicenseeSerializer } from '@models/Licensee/Licensee.model';
import { User, InterfaceUserCreate } from '@models/User/User.model';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfaceLicenseeUserCreate extends InterfaceUserCreate {
    licensee?: Licensee | null;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class LicenseeUser extends User implements InterfaceLicenseeUserCreate {
    public licensee? = null;

    constructor(data?: InterfaceLicenseeUserCreate) {
        super(data);
        const cleanDataObject = deleteUndefinedProperties(data);
        const global = window as any;
        const { $tm, $t } = global.Vue?.config?.globalProperties || {};

        if ($tm) {
            this.$tm = $tm;
            this.$t = $t;
        }

        Object.assign(this, cleanDataObject);
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class LicenseeUserSerializer {
    static fromServer(json: any): LicenseeUser {
        const userData: any = {
            id: json.providerId,
            email: json.emailAddress,
            firstName: json.givenName,
            lastName: json.familyName,
            accountStatus: json.status || 'inactive',
            userType: AuthTypes.LICENSEE,
            licensee: LicenseeSerializer.fromServer(json)
        };

        return new LicenseeUser(userData);
    }
}

export class LicenseeUserPurchaseSerializer {
    static toServer({ formData, statesSelected }): any {
        // console.log('madeItIn', { formData, statesSelected });

        const purchaseData: any = {
            selectedJurisdictions: statesSelected,
            orderInformation: {
                card: {
                    number: formData.creditCard.value.replace(/\s+/g, ''),
                    expiration: `20${formData.expYear.value}-${formData.expMonth.value}`,
                    cvv: formData.cvv
                },
                billing: {
                    firstName: formData.firstName.value,
                    lastName: formData.lastName.value,
                    streetAddress: formData.streetAddress1.value,
                    streetAddress2: formData.streetAddress2.value,
                    state: formData.stateSelect.value.toUpperCase(),
                    zip: formData.zip.value
                }
            }
        };

        console.log('purchaseData', purchaseData);

        return purchaseData;
    }
}
