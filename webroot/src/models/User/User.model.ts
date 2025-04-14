//
//  user.model.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

/* eslint-disable max-classes-per-file */
import { AuthTypes } from '@/app.config';
import { deleteUndefinedProperties } from '@models/_helpers';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfaceUserCreate {
    id?: string | null;
    firstName?: string | null;
    lastName?: string | null;
    compactConnectEmail?: string | null;
    userType?: AuthTypes | null;
    accountStatus?: string;
    serverPage?: number;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class User implements InterfaceUserCreate {
    public $tm?: any = () => [];
    public $t?: any = () => '';
    public id? = null;
    public firstName? = null;
    public lastName? = null;
    public compactConnectEmail? = null
    public userType? = null;
    public accountStatus? = '';
    public serverPage? = 0;

    constructor(data?: InterfaceUserCreate) {
        const cleanDataObject = deleteUndefinedProperties(data);
        const global = window as any;
        const { $tm, $t } = global.Vue?.config?.globalProperties || {};

        if ($tm) {
            this.$tm = $tm;
            this.$t = $t;
        }

        Object.assign(this, cleanDataObject);
    }

    public getFullName(): string {
        const firstName = this.firstName || '';
        const lastName = this.lastName || '';

        return `${firstName} ${lastName}`.trim();
    }

    public getInitials(): string {
        const firstName = this.firstName || '';
        const lastName = this.lastName || '';
        let initials = '';

        initials += firstName.charAt(0).toUpperCase();
        initials += lastName.charAt(0).toUpperCase();

        return initials.trim();
    }

    public accountStatusDisplay(): string {
        const { accountStatus } = this;
        let display = '';

        if (accountStatus) {
            display = this.$t(`account.status.${accountStatus}`);
        }

        return display;
    }
}
