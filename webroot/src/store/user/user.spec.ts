//
//  user.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/12/24.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import mutations, { MutationTypes } from './user.mutations';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('Use Store Mutations', () => {
    it('should successfully get login request', () => {
        const state = {};

        mutations[MutationTypes.LOGIN_REQUEST](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully get login failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.LOGIN_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully get login success', () => {
        const state = {};

        mutations[MutationTypes.LOGIN_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.isLoggedIn).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully get login reset', () => {
        const state = {};

        mutations[MutationTypes.LOGIN_RESET](state);

        expect(state.error).to.equal(null);
    });
    it('should successfully get logout request', () => {
        const state = {};

        mutations[MutationTypes.LOGOUT_REQUEST](state);

        expect(state.isLoading).to.equal(true);
    });
    it('should successfully get logout failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.LOGOUT_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully get logout success', () => {
        const state = {};

        mutations[MutationTypes.LOGOUT_SUCCESS](state);

        expect(state.model).to.equal(null);
        expect(state.isLoading).to.equal(false);
        expect(state.isLoggedIn).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully get account request', () => {
        const state = {};

        mutations[MutationTypes.GET_ACCOUNT_REQUEST](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully get account failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.GET_ACCOUNT_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully get account success', () => {
        const state = {};

        mutations[MutationTypes.GET_ACCOUNT_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully update user', () => {
        const state = {};
        const user = { id: 1 };

        mutations[MutationTypes.STORE_UPDATE_USER](state, user);

        expect(state.model).to.equal(user);
    });
    it('should successfully reset user', () => {
        const state = {};

        mutations[MutationTypes.STORE_RESET_USER](state);

        expect(state.model).to.equal(null);
        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully update account request', () => {
        const state = {};

        mutations[MutationTypes.UPDATE_ACCOUNT_REQUEST](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully update account failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.UPDATE_ACCOUNT_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully update account success', () => {
        const state = {};

        mutations[MutationTypes.UPDATE_ACCOUNT_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
});
