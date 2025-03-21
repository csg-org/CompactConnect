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
    stateProvidedEmail?: string | null;
    licensee?: Licensee | null;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class LicenseeUser extends User implements InterfaceLicenseeUserCreate {
    public stateProvidedEmail? = null;
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
            stateProvidedEmail: json.emailAddress,
            compactConnectEmail: json.compactConnectRegisteredEmailAddress,
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
    static toServer({
        formValues,
        statesSelected,
        attestationsSelected,
        selectedPurchaseLicense
    }): any {
        const purchaseData: any = {
            selectedJurisdictions: statesSelected,
            attestations: attestationsSelected,
            licenseType: selectedPurchaseLicense.licenseType,
            orderInformation: {
                card: {
                    number: formValues.creditCard.replace(/\s+/g, ''),
                    expiration: `20${formValues.expYear}-${formValues.expMonth}`,
                    cvv: formValues.cvv
                },
                billing: {
                    firstName: formValues.firstName,
                    lastName: formValues.lastName,
                    streetAddress: formValues.streetAddress1,
                    streetAddress2: formValues.streetAddress2,
                    state: formValues.stateSelect.toUpperCase(),
                    zip: formValues.zip
                }
            },
        };

        return purchaseData;
    }
}
