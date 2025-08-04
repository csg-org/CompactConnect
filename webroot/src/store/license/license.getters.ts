//
//  license.getters.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 7/2/24.
//
import { State as LicenseState } from '@/store/license/license.state';

export default {
    lastKey: (state: LicenseState) => state.lastKey,
    prevLastKey: (state: LicenseState) => state.prevLastKey,
    licenseeById: (state: LicenseState) => (licenseeId: string) => {
        const licensees = state.model || [];

        return licensees.find((licensee) => licensee.id === licenseeId);
    },
    getPrivilegeByLicenseeIdAndId: (state: LicenseState) => ({ licenseeId, privilegeId }) => {
        console.log({ licenseeId, privilegeId });
        const licensees = state.model || [];

        const foundLicensee = licensees.find((licensee) => licensee.id === licenseeId);

        console.log('foundLicensee', foundLicensee);

        return foundLicensee?.privileges?.find((privilege) => (privilege.id === privilegeId)) || null;
    }
};
