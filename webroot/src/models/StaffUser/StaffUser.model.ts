//
//  user.model.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

/* eslint-disable max-classes-per-file */

import deleteUndefinedProperties from '@models/_helpers';
import { AuthTypes } from '@/app.config';
import { Compact, CompactType, CompactSerializer } from '@models/Compact/Compact.model';
import { State } from '@models/State/State.model';
import { User, InterfaceUserCreate } from '@models/User/User.model';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface StatePermission {
    state: State;
    isWrite: boolean;
    isAdmin: boolean;
}

export interface CompactPermission {
    compact: Compact;
    isRead: boolean;
    isAdmin: boolean;
    states: Array<StatePermission>;
}

export interface InterfaceStaffUserCreate extends InterfaceUserCreate {
    permissions?: Array<CompactPermission>;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class StaffUser extends User implements InterfaceStaffUserCreate {
    public permissions? = [];

    constructor(data?: InterfaceStaffUserCreate) {
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

    public permissionsShortDisplay(currentCompactType?: CompactType): string {
        let { permissions } = this;
        let isReadUsed = false;
        let isWriteUsed = false;
        let isAdminUsed = false;
        let display = '';

        if (currentCompactType) {
            permissions = permissions?.filter((compactPermission: any) =>
                compactPermission.compact?.type === currentCompactType);
        }

        permissions?.forEach((compactPermission: CompactPermission) => {
            const {
                isRead,
                isAdmin,
                states
            } = compactPermission;

            if (isRead || isAdmin) {
                // If the user has compact-level permissions
                if (isRead && !isReadUsed) {
                    const readDisplay = this.$t('account.accessLevel.read');

                    display += (display) ? `, ${readDisplay}` : readDisplay;
                    isReadUsed = true;
                }
                if (isAdmin && !isAdminUsed) {
                    const adminDisplay = this.$t('account.accessLevel.admin');

                    display += (display) ? `, ${adminDisplay}` : adminDisplay;
                    isAdminUsed = true;
                }
            } else {
                // Otherwise look for state-level permissions
                states?.forEach((statePermission) => {
                    const { isWrite, isAdmin: isStateAdmin } = statePermission;

                    if (isWrite && !isWriteUsed) {
                        const writeDisplay = this.$t('account.accessLevel.write');

                        display += (display) ? `, ${writeDisplay}` : writeDisplay;
                        isWriteUsed = true;
                    }
                    if (isStateAdmin && !isAdminUsed) {
                        const adminDisplay = this.$t('account.accessLevel.admin');

                        display += (display) ? `, ${adminDisplay}` : adminDisplay;
                        isAdminUsed = true;
                    }
                });
            }
        });

        return display;
    }

    public permissionsFullDisplay(currentCompactType?: CompactType): Array<string> {
        let { permissions } = this;
        const display: Array<string> = [];

        if (currentCompactType) {
            permissions = permissions?.filter((compactPermission: any) =>
                compactPermission.compact?.type === currentCompactType);
        }

        permissions?.forEach((compactPermission: CompactPermission) => {
            const {
                compact,
                isRead,
                isAdmin,
                states
            } = compactPermission;

            if (isRead || isAdmin) {
                let accessLevels = '';

                if (isRead) {
                    accessLevels += this.$t('account.accessLevel.read');
                }
                if (isAdmin) {
                    const adminAccess = this.$t('account.accessLevel.admin');

                    accessLevels += (accessLevels) ? `, ${adminAccess}` : adminAccess;
                }

                display.push(`${compact.abbrev()}: ${accessLevels}`);
            }

            states?.forEach((statePermission) => {
                const { state, isWrite, isAdmin: isStateAdmin } = statePermission;
                let stateAccessLevels = '';

                if (isWrite) {
                    stateAccessLevels += this.$t('account.accessLevel.write');
                }
                if (isStateAdmin) {
                    const stateAdminAccess = this.$t('account.accessLevel.admin');

                    stateAccessLevels += (stateAccessLevels) ? `, ${stateAdminAccess}` : stateAdminAccess;
                }

                display.push(`${state.name()}: ${stateAccessLevels}`);
            });
        });

        return display;
    }

    public getStateListDisplay(stateNames: Array<string>, maxNames = 2): string {
        let stateList = '';

        if (stateNames.length > maxNames) {
            stateNames.forEach((stateName, idx) => {
                if (stateName && idx + 1 <= maxNames) {
                    stateList += (stateList) ? `, ${stateName}` : stateName;
                }
            });

            stateList += (stateList) ? ` +` : '';
        } else {
            stateList = stateNames.join(', ');
        }

        return stateList;
    }

    public affiliationDisplay(currentCompactType?: CompactType): string {
        let { permissions } = this;
        const stateNames: Array<string> = [];
        let display = '';

        if (currentCompactType) {
            permissions = permissions?.filter((compactPermission: any) =>
                compactPermission.compact?.type === currentCompactType);
        }

        permissions?.forEach((compactPermission: CompactPermission) => {
            const {
                compact,
                isRead,
                isAdmin,
                states
            } = compactPermission as CompactPermission;

            if (isRead || isAdmin) {
                // If the user has compact-level permissions
                const compactAbbrev = compact.abbrev();

                display += (display) ? `, ${compactAbbrev}` : compactAbbrev;
            } else {
                // Otherwise look for state-level permissions
                states?.forEach((statePermission) => {
                    const { isWrite, isAdmin: isStateAdmin } = statePermission;
                    const stateName = statePermission.state.name();

                    if ((isWrite || isStateAdmin) && !stateNames.includes(stateName)) {
                        stateNames.push(statePermission.state.name());
                    }
                });
            }
        });

        if (stateNames.length) {
            const stateListDisplay = this.getStateListDisplay(stateNames);

            display += (display) ? `, ${stateListDisplay}` : stateListDisplay;
        }

        return display;
    }

    public statesDisplay(currentCompactType?: CompactType): string {
        let { permissions } = this;
        const stateNames: Array<string> = [];
        let display = '';

        if (currentCompactType) {
            permissions = permissions?.filter((compactPermission: any) =>
                compactPermission.compact?.type === currentCompactType);
        }

        permissions?.forEach((compactPermission: CompactPermission) => {
            const { states } = compactPermission as CompactPermission;

            states?.forEach((statePermission) => {
                const { isWrite, isAdmin } = statePermission;
                const stateName = statePermission.state.name();

                if ((isWrite || isAdmin) && !stateNames.includes(stateName)) {
                    stateNames.push(statePermission.state.name());
                }
            });
        });

        display = this.getStateListDisplay(stateNames);

        return display;
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class StaffUserSerializer {
    static fromServer(json: any, fetchConfig?: any): User {
        const userData: any = {
            id: json.userId,
            email: json.attributes?.email,
            firstName: json.attributes?.givenName,
            lastName: json.attributes?.familyName,
            userType: AuthTypes.STAFF,
            permissions: [],
            accountStatus: json.status || 'inactive',
            serverPage: (fetchConfig && fetchConfig.pageNum) ? fetchConfig.pageNum : 0,
        };

        // Convert the server permission structure into a more iterable format for the client side
        Object.keys(json.permissions || {}).forEach((compactType) => {
            const { actions = {}, jurisdictions = {}} = json.permissions?.[compactType] || {};
            const compactPermission: CompactPermission = {
                compact: CompactSerializer.fromServer({ type: compactType }),
                isRead: actions?.read || false,
                isAdmin: actions?.admin || false,
                states: [],
            };

            Object.keys(jurisdictions).forEach((stateCode) => {
                compactPermission.states.push({
                    state: new State({ abbrev: stateCode }),
                    isWrite: jurisdictions[stateCode]?.actions?.write || false,
                    isAdmin: jurisdictions[stateCode]?.actions?.admin || false,
                });
            });

            userData.permissions.push(compactPermission);
        });

        return new StaffUser(userData);
    }

    static toServer(data) {
        const serverData: any = {};
        // Prepare state permissions for server request
        const deserializeStatePermission = (statePermission, jurisdictions) => {
            const hasStateWriteSetting = Object.prototype.hasOwnProperty.call(statePermission, 'isWrite');
            const hasStateAdminSetting = Object.prototype.hasOwnProperty.call(statePermission, 'isAdmin');

            if (hasStateWriteSetting || hasStateAdminSetting) {
                const actions: any = {};

                jurisdictions[statePermission.abbrev] = { actions };

                if (hasStateWriteSetting) {
                    actions.write = statePermission.isWrite;
                }
                if (hasStateAdminSetting) {
                    actions.admin = statePermission.isAdmin;
                }
            }
        };
        // Prepare compact permissions for server request
        const deserializeCompactPermission = (compactPermission) => {
            const hasCompactReadSetting = Object.prototype.hasOwnProperty.call(compactPermission, 'isRead');
            const hasCompactAdminSetting = Object.prototype.hasOwnProperty.call(compactPermission, 'isAdmin');
            const hasStates = Boolean(compactPermission.states?.length);

            if (hasCompactReadSetting || hasCompactAdminSetting) {
                const actions: any = {};

                serverData.permissions[compactPermission.compact] = { actions };

                if (hasCompactReadSetting) {
                    actions.read = compactPermission.isRead;
                }
                if (hasCompactAdminSetting) {
                    actions.admin = compactPermission.isAdmin;
                }
            }

            if (hasStates) {
                const jurisdictions: any = {};

                serverData.permissions[compactPermission.compact].jurisdictions = jurisdictions;

                compactPermission.states.forEach((statePermission) => {
                    deserializeStatePermission(statePermission, jurisdictions);
                });
            }
        };

        // Initiate server prep
        if (data?.permissions) {
            serverData.permissions = {};

            data.permissions.forEach((compactPermission) => {
                deserializeCompactPermission(compactPermission);
            });
        }

        return serverData;
    }
}
