//
//  styleguide.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/12/24.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import mutations, { MutationTypes } from './styleguide.mutations';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('Styleguide Store Mutations', () => {
    it('should successfully get styleguide count request', () => {
        const state = {};

        mutations[MutationTypes.GET_STYLEGUIDE_COUNT_REQUEST](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully get styleguide count failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.GET_STYLEGUIDE_COUNT_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully get styleguide count success', () => {
        const state = {};

        mutations[MutationTypes.GET_STYLEGUIDE_COUNT_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully get pets request', () => {
        const state = {};

        mutations[MutationTypes.GET_PETS_REQUEST](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully get pets failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.GET_PETS_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully get pets success', () => {
        const state = {};

        mutations[MutationTypes.GET_PETS_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully update count', () => {
        const state = {};
        const count = 1;

        mutations[MutationTypes.STORE_UPDATE_COUNT](state, count);

        expect(state.total).to.equal(count);
    });
    it('should successfully set pets', () => {
        const state = {};
        const pets = [];

        mutations[MutationTypes.STORE_SET_PETS](state, pets);

        expect(state.model).to.equal(pets);
    });
    it('should successfully update pet (missing id)', () => {
        const state = {};
        const pet = {};

        mutations[MutationTypes.STORE_UPDATE_PET](state, pet);

        expect(state).to.equal(state);
    });
    it('should successfully update pet (not already in store - empty store)', () => {
        const state = {};
        const pet = { id: 1 };

        mutations[MutationTypes.STORE_UPDATE_PET](state, pet);

        expect(state.model).to.matchPattern([pet]);
    });
    it('should successfully update pet (not already in store - non-empty store)', () => {
        const state = { model: [{ id: 2 }]};
        const pet = { id: 1 };

        mutations[MutationTypes.STORE_UPDATE_PET](state, pet);

        expect(state.model).to.matchPattern([ { id: 2 }, pet]);
    });
    it('should successfully update pet (already in store)', () => {
        const state = { model: [{ id: 1, name: 'test1' }]};
        const pet = { id: 1, name: 'test2' };

        mutations[MutationTypes.STORE_UPDATE_PET](state, pet);

        expect(state.model).to.matchPattern([pet]);
    });
    it('should successfully remove pet (id missing)', () => {
        const state = {};
        const petId = '';

        mutations[MutationTypes.STORE_REMOVE_PET](state, petId);

        expect(state).to.equal(state);
    });
    it('should successfully remove pet (not already in store)', () => {
        const state = {};
        const petId = 1;

        mutations[MutationTypes.STORE_REMOVE_PET](state, petId);

        expect(state).to.equal(state);
    });
    it('should successfully remove pet (already in store)', () => {
        const state = { model: [{ id: 1 }, { id: 2 }]};
        const petId = 1;

        mutations[MutationTypes.STORE_REMOVE_PET](state, petId);

        expect(state.model).to.matchPattern([{ id: 2 }]);
    });
    it('should successfully remove pet (already in store - only record)', () => {
        const state = { model: [{ id: 1 }]};
        const petId = 1;

        mutations[MutationTypes.STORE_REMOVE_PET](state, petId);

        expect(state.model).to.matchPattern([]);
    });
    it('should successfully reset styleguide store', () => {
        const state = {
            model: [{ id: 1 }],
            total: 1,
            isLoading: true,
            error: new Error(),
        };

        mutations[MutationTypes.STORE_RESET_STYLEGUIDE](state);

        expect(state).to.matchPattern({
            model: null,
            total: 0,
            isLoading: false,
            error: null,
        });
    });
});
