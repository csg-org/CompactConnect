//
//  users.getters.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 9/4/24.
//

export default {
    lastKey: (state: any) => state.lastKey,
    prevLastKey: (state: any) => state.prevLastKey,
    userById: (state: any) => (userId: string) => {
        const users = state.model || [];

        return users.find((user) => user.id === userId);
    },
};
