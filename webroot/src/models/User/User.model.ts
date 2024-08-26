//
//  user.model.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import deleteUndefinedProperties from '@models/_helpers';

export enum Compact {
    ASLP = 'aslp',
    OT = 'ot',
    COUNSILING = 'counseling',
}

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfaceUserCreate {
    id?: string | null;
    email?: string | null;
    firstName?: string | null;
    lastName?: string | null;
    serverPage?: number;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class User implements InterfaceUserCreate {
    public id? = null;
    public email? = null;
    public firstName? = null;
    public lastName? = null;
    public serverPage? = 0;

    constructor(data?: InterfaceUserCreate) {
        const cleanDataObject = deleteUndefinedProperties(data);

        Object.assign(this, cleanDataObject);
    }

    /**
     * Concatenated full name
     */
    public getFullName(): string {
        const firstName = this.firstName || '';
        const lastName = this.lastName || '';

        return `${firstName} ${lastName}`.trim();
    }

    /**
     * Parse user initials from name
     */
    public getInitials(): string {
        const firstName = this.firstName || '';
        const lastName = this.lastName || '';
        let initials = '';

        initials += firstName.charAt(0).toUpperCase();
        initials += lastName.charAt(0).toUpperCase();

        return initials.trim();
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class UserSerializer {
    static fromServer(json: any, fetchConfig?: any): User {
        const userData: any = {
            id: json.id,
            email: json.email,
            firstName: json.firstName,
            lastName: json.lastName,
            serverPage: (fetchConfig && fetchConfig.pageNum) ? fetchConfig.pageNum : 0,
        };

        return new User(userData);
    }

    static toServer(): any {
        // @TODO
    }
}
