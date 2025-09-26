//
//  styleguide.actions.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { FeatureGates } from '@/app.config';
import { dataApi } from '@network/data.api';
import { MutationTypes } from './styleguide.mutations';

export default {
    // GET PETS COUNT
    getPetsCountRequest: async ({ commit, dispatch }, payload: any) => {
        commit(MutationTypes.GET_STYLEGUIDE_COUNT_REQUEST);
        await dataApi.getStyleguidePetsCount(payload).then(async (response) => {
            const petCount = response.count;

            dispatch('setStorePetCount', petCount);
            dispatch('getPetsCountSuccess');
        }).catch((error) => {
            dispatch('getPetsCountFailure', error);
        });
    },
    getPetsCountSuccess: ({ commit }) => {
        commit(MutationTypes.GET_STYLEGUIDE_COUNT_SUCCESS);
    },
    getPetsCountFailure: ({ commit }, error: Error) => {
        commit(MutationTypes.GET_STYLEGUIDE_COUNT_FAILURE, error);
    },
    // GET PETS
    getPetsRequest: async ({ commit, dispatch }, payload: any) => {
        commit(MutationTypes.GET_PETS_REQUEST);
        await dataApi.getStyleguidePets(payload).then(async (pets) => {
            await dispatch('setStorePets', pets);
            dispatch('getPetsSuccess', pets);
        }).catch((error) => {
            dispatch('getPetsFailure', error);
        });
    },
    getPetsSuccess: ({ commit }) => {
        commit(MutationTypes.GET_PETS_SUCCESS);
    },
    getPetsFailure: ({ commit }, error: Error) => {
        commit(MutationTypes.GET_PETS_FAILURE, error);
    },
    // GET FEATURE GATE IN STORE ACTION EXAMPLE
    getFeatureGateExample: () => {
        const { $features } = (window as any).Vue?.config?.globalProperties || {};

        // Obviously store actions aren't needed to *just* check a feature gate;
        // This is just an example of how a feature gate can be evaluated in a store action if needed.
        return $features?.checkGate(FeatureGates.EXAMPLE_FEATURE_1) || false;
    },
    // SET THE STORE STATE
    setStorePetCount: ({ commit }, count) => {
        commit(MutationTypes.STORE_UPDATE_COUNT, count);
    },
    setStorePets: ({ commit }, pets) => {
        commit(MutationTypes.STORE_SET_PETS, pets);
    },
    setStorePet: ({ commit }, pet) => {
        commit(MutationTypes.STORE_UPDATE_PET, pet);
    },
    // RESET STYLEGUIDE STORE STATE
    resetStoreUser: ({ commit }) => {
        commit(MutationTypes.STORE_RESET_STYLEGUIDE);
    },
};
