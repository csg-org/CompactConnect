//
//  styleguide.actions.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { dataApi } from '@network/data.api';
import { MutationTypes } from './styleguide.mutations';

export default {
    // GET PETS COUNT
    getPetsCountRequest: async ({ commit, dispatch }, payload: any) => {
        commit(MutationTypes.GET_STYLEGUIDE_COUNT_REQUEST);
        // await new Promise((resolve) => { setTimeout(() => { console.log('count'); resolve(); }, 2000); }); // @DEBUGz
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
            // await new Promise((resolve) => { setTimeout(() => { console.log('pets'); resolve(); }, 2000); }); // @DEBUG
            // await Promise.all(pets.map((pet) => dispatch('setStorePet', pet))); // This would update records if they already existed; more performant but need to reconcile sorting.
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
