//
//  license.getters.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 7/2/24.
//

export default {
    lastKey: (state: any) => state.lastKey,
    licenseeById: (state: any) => (licenseeId: string) => {
        const licensees = state.model || [];

        return licensees.find((licensee) => licensee.id === licenseeId);
    },
};
