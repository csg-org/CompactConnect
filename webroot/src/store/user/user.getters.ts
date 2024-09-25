//
//  user.getters.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//
import { authStorage, AuthTypes, tokens } from '@/app.config';

export default {
    state: (state: any) => state,
    currentCompact: (state: any) => state.currentCompact,
    highestPermissionAuthType: () => () => {
        let loggedInAsType = '';

        if (authStorage.getItem(tokens[AuthTypes.STAFF]?.AUTH_TOKEN)) {
            loggedInAsType = AuthTypes.STAFF;
        } else if (authStorage.getItem(tokens[AuthTypes.LICENSEE]?.AUTH_TOKEN)) {
            loggedInAsType = AuthTypes.LICENSEE;
        }

        return loggedInAsType;
    },
};
