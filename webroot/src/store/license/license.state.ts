//
//  license.state.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 7/2/24.
//
import { LicenseSearchLegacy } from '@components/Licensee/LicenseeSearchLegacy/LicenseeSearchLegacy.vue';

export interface State {
    model: Array<any> | null;
    total: number;
    prevLastKey: string | null;
    lastKey: string | null;
    isLoading: boolean;
    error: any | null;
    search: LicenseSearchLegacy;
}

export const state: State = {
    model: null,
    total: 0,
    prevLastKey: null,
    lastKey: null,
    isLoading: false,
    error: null,
    search: {
        compact: '',
        firstName: '',
        lastName: '',
        state: '',
    },
};
