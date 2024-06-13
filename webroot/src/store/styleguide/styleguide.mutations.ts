//
//  styleguide.mutations.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

export enum MutationTypes {
    GET_STYLEGUIDE_COUNT_REQUEST = '[Styleguide] Get Styleguide Count Request',
    GET_STYLEGUIDE_COUNT_FAILURE = '[Styleguide] Get Styleguide Count Failure',
    GET_STYLEGUIDE_COUNT_SUCCESS = '[Styleguide] Get Styleguide Count Success',
    GET_PETS_REQUEST = '[Styleguide] Get Pets Request',
    GET_PETS_FAILURE = '[Styleguide] Get Pets Failure',
    GET_PETS_SUCCESS = '[Styleguide] Get Pets Success',
    STORE_UPDATE_COUNT = '[Styleguide] Updated total count in store',
    STORE_SET_PETS = '[Styleguide] Set Pets in store',
    STORE_UPDATE_PET = '[Styleguide] Updated Pet in store',
    STORE_REMOVE_PET = '[Styleguide] Remove Pet from store',
    STORE_RESET_STYLEGUIDE = '[Styleguide] Reset styleguide in store',
}

export default {
    [MutationTypes.GET_STYLEGUIDE_COUNT_REQUEST]: (state: any) => {
        state.isLoading = true;
        state.error = null;
    },
    [MutationTypes.GET_STYLEGUIDE_COUNT_FAILURE]: (state: any, error: Error) => {
        state.isLoading = false;
        state.error = error;
    },
    [MutationTypes.GET_STYLEGUIDE_COUNT_SUCCESS]: (state: any) => {
        state.isLoading = false;
        state.error = null;
    },
    [MutationTypes.GET_PETS_REQUEST]: (state: any) => {
        state.isLoading = true;
        state.error = null;
    },
    [MutationTypes.GET_PETS_FAILURE]: (state: any, error: Error) => {
        state.isLoading = false;
        state.error = error;
    },
    [MutationTypes.GET_PETS_SUCCESS]: (state: any) => {
        state.isLoading = false;
        state.error = null;
    },
    [MutationTypes.STORE_UPDATE_COUNT]: (state: any, count: number) => {
        state.total = count;
    },
    [MutationTypes.STORE_SET_PETS]: (state: any, pets: Array<any>) => {
        state.model = pets;
    },
    [MutationTypes.STORE_UPDATE_PET]: (state: any, pet: any) => {
        if (pet.id) { // Don't put objects with NULL IDs in the store
            if (state.model && state.model.length) {
                const petToUpdateIndex = state.model
                    .findIndex((p: any) => Number(p.id) === Number(pet.id));

                if (petToUpdateIndex !== -1) {
                    state.model.splice(petToUpdateIndex, 1, pet);
                } else {
                    state.model.push(pet);
                }
            } else {
                state.model = [pet];
            }
        } else {
            console.warn('Cannot put Pet with null ID in the store:');
            console.warn(JSON.stringify(pet, null, 2));
        }
    },
    [MutationTypes.STORE_REMOVE_PET]: (state: any, petId: string | number) => {
        if (petId) { // Can't remove pet with NULL IDs from the store
            if (state.model && state.model.length) {
                const petToRemoveIndex = state.model
                    .findIndex((p: any) => Number(p.id) === Number(petId));

                if (petToRemoveIndex !== -1) {
                    state.model.splice(petToRemoveIndex, 1);
                }
            }
        } else {
            console.warn('Cannot remove Pet with null ID from the store:');
        }
    },
    [MutationTypes.STORE_RESET_STYLEGUIDE]: (state: any) => {
        state.model = null;
        state.total = 0;
        state.isLoading = false;
        state.error = null;
    },
};
