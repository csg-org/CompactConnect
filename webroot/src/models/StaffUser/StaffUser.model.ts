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
    isReadPrivate: boolean;
    isWrite: boolean;
    isAdmin: boolean;
}

export interface CompactPermission {
    compact: Compact;
    isReadPrivate: boolean;
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
        let isReadPrivateUsed = false;
        let isWriteUsed = false;
        let isAdminUsed = false;
        let display = '';

        if (currentCompactType) {
            permissions = permissions?.filter((compactPermission: any) =>
                compactPermission.compact?.type === currentCompactType);
        }

        permissions?.forEach((compactPermission: CompactPermission) => {
            const {
                isReadPrivate: isCompactReadPrivate,
                isAdmin: isCompactAdmin,
                states
            } = compactPermission;

            if (isCompactReadPrivate || isCompactAdmin) {
                // If the user has compact-level permissions
                if (isCompactReadPrivate && !isReadPrivateUsed) {
                    const readPrivateDisplay = this.$t('account.accessLevel.readPrivate');

                    display += (display) ? `, ${readPrivateDisplay}` : readPrivateDisplay;
                    isReadPrivateUsed = true;
                }
                if (isCompactAdmin && !isAdminUsed) {
                    const adminDisplay = this.$t('account.accessLevel.admin');

                    display += (display) ? `, ${adminDisplay}` : adminDisplay;
                    isAdminUsed = true;
                }
            } else {
                // Otherwise look for state-level permissions
                states?.forEach((statePermission) => {
                    const {
                        isReadPrivate: isStateReadPrivate,
                        isWrite: isStateWrite,
                        isAdmin: isStateAdmin
                    } = statePermission;

                    if (isStateReadPrivate && !isReadPrivateUsed) {
                        const readPrivateDisplay = this.$t('account.accessLevel.readPrivate');

                        display += (display) ? `, ${readPrivateDisplay}` : readPrivateDisplay;
                        isReadPrivateUsed = true;
                    }
                    if (isStateWrite && !isWriteUsed) {
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
                isReadPrivate: isCompactReadPrivate,
                isAdmin: isCompactAdmin,
                states
            } = compactPermission;

            if (isCompactReadPrivate || isCompactAdmin) {
                let accessLevels = '';

                if (isCompactReadPrivate) {
                    accessLevels += this.$t('account.accessLevel.readPrivate');
                }
                if (isCompactAdmin) {
                    const adminAccess = this.$t('account.accessLevel.admin');

                    accessLevels += (accessLevels) ? `, ${adminAccess}` : adminAccess;
                }

                display.push(`${compact.abbrev()}: ${accessLevels}`);
            }

            states?.forEach((statePermission) => {
                const {
                    state,
                    isReadPrivate: isStateReadPrivate,
                    isWrite: isStateWrite,
                    isAdmin: isStateAdmin
                } = statePermission;
                let stateAccessLevels = '';

                if (isStateReadPrivate) {
                    stateAccessLevels += this.$t('account.accessLevel.readPrivate');
                }
                if (isStateWrite) {
                    const stateWriteAccess = this.$t('account.accessLevel.write');

                    stateAccessLevels += (stateAccessLevels) ? `, ${stateWriteAccess}` : stateWriteAccess;
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
                isReadPrivate: isCompactReadPrivate,
                isAdmin: isCompactAdmin,
                states
            } = compactPermission as CompactPermission;

            if (isCompactReadPrivate || isCompactAdmin) {
                // If the user has compact-level permissions
                const compactAbbrev = compact.abbrev();

                display += (display) ? `, ${compactAbbrev}` : compactAbbrev;
            } else {
                // Otherwise look for state-level permissions
                states?.forEach((statePermission) => {
                    const {
                        isReadPrivate: isStateReadPrivate,
                        isWrite: isStateWrite,
                        isAdmin: isStateAdmin
                    } = statePermission;
                    const stateName = statePermission.state.name();

                    if ((isStateReadPrivate || isStateWrite || isStateAdmin) && !stateNames.includes(stateName)) {
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
                const { isReadPrivate, isWrite, isAdmin } = statePermission;
                const stateName = statePermission.state.name();

                if ((isReadPrivate || isWrite || isAdmin) && !stateNames.includes(stateName)) {
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
            accountStatus: json.status || 'active', // Temp 'active' fallback until server responses include this field, per team discussion
            serverPage: (fetchConfig && fetchConfig.pageNum) ? fetchConfig.pageNum : 0,
        };

        // Convert the server permission structure into a more iterable format for the client side
        Object.keys(json.permissions || {}).forEach((compactType) => {
            const { actions = {}, jurisdictions = {}} = json.permissions?.[compactType] || {};
            const compactPermission: CompactPermission = {
                compact: CompactSerializer.fromServer({ type: compactType }),
                isReadPrivate: actions?.readPrivate || false,
                isAdmin: actions?.admin || false,
                states: [],
            };

            Object.keys(jurisdictions).forEach((stateCode) => {
                compactPermission.states.push({
                    state: new State({ abbrev: stateCode }),
                    isReadPrivate: jurisdictions[stateCode]?.actions?.readPrivate || false,
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
            const hasStateReadPrivateSetting = Object.prototype.hasOwnProperty.call(statePermission, 'isReadPrivate');
            const hasStateWriteSetting = Object.prototype.hasOwnProperty.call(statePermission, 'isWrite');
            const hasStateAdminSetting = Object.prototype.hasOwnProperty.call(statePermission, 'isAdmin');

            if (hasStateReadPrivateSetting || hasStateWriteSetting || hasStateAdminSetting) {
                const actions: any = {};

                jurisdictions[statePermission.abbrev] = { actions };

                if (hasStateReadPrivateSetting) {
                    actions.readPrivate = statePermission.isReadPrivate;
                }
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
            const hasCompactReadPrivateSetting = Object.prototype.hasOwnProperty.call(compactPermission, 'isReadPrivate');
            const hasCompactAdminSetting = Object.prototype.hasOwnProperty.call(compactPermission, 'isAdmin');
            const hasStates = Boolean(compactPermission.states?.length);

            if (hasCompactReadPrivateSetting || hasCompactAdminSetting) {
                const actions: any = {};

                serverData.permissions[compactPermission.compact] = { actions };

                if (hasCompactReadPrivateSetting) {
                    actions.readPrivate = compactPermission.isReadPrivate;
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
                serverData.permissions[compactPermission.compact] = {};
                deserializeCompactPermission(compactPermission);
            });
        }

        if (data?.attributes) {
            serverData.attributes = {};

            if (data.attributes.email) {
                serverData.attributes.email = data.attributes.email;
            }
            if (data.attributes.firstName) {
                serverData.attributes.givenName = data.attributes.firstName;
            }
            if (data.attributes.lastName) {
                serverData.attributes.familyName = data.attributes.lastName;
            }
        }

        return serverData;
    }
}
