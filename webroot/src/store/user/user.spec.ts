//
//  user.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/12/24.
//

import {
    authStorage,
    tokens,
    FeeTypes,
    AuthTypes
} from '@/app.config';
import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { PrivilegePurchaseOption } from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';
import { PurchaseFlowStep } from '@models/PurchaseFlowStep/PurchaseFlowStep.model';
import { PurchaseFlowState } from '@models/PurchaseFlowState/PurchaseFlowState.model';
import { State } from '@models/State/State.model';
import { License } from '@models/License/License.model';
import { LicenseeUser } from '@models/LicenseeUser/LicenseeUser.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { Address } from '@models/Address/Address.model';
import mutations, { MutationTypes } from './user.mutations';
import actions from './user.actions';
import getters from './user.getters';

chai.use(chaiMatchPattern);
const sinon = require('sinon');

const { expect } = chai;

describe('Use Store Mutations', () => {
    it('should successfully get login request', () => {
        const state = {};

        mutations[MutationTypes.LOGIN_REQUEST](state);

        expect(state.isLoadingAccount).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully get login failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.LOGIN_FAILURE](state, error);

        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully get login success', () => {
        const state = {};

        mutations[MutationTypes.LOGIN_SUCCESS](state, AuthTypes.LICENSEE);

        expect(state.isLoadingAccount).to.equal(false);
        expect(state.isLoggedIn).to.equal(true);
        expect(state.isLoggedInAsLicensee).to.equal(true);
        expect(state.isLoggedInAsStaff).to.equal(false);
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

        expect(state.isLoadingAccount).to.equal(true);
    });
    it('should successfully get logout failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.LOGOUT_FAILURE](state, error);

        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully get logout success', () => {
        const state = {};

        mutations[MutationTypes.LOGOUT_SUCCESS](state);

        expect(state.model).to.equal(null);
        expect(state.isLoadingAccount).to.equal(false);
        expect(state.isLoggedIn).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully create licensee account request', () => {
        const state = {};

        mutations[MutationTypes.CREATE_LICENSEE_ACCOUNT_REQUEST](state);

        expect(state.isLoadingAccount).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully create licensee account failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.CREATE_LICENSEE_ACCOUNT_FAILURE](state, error);

        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully create licensee account success', () => {
        const state = {};

        mutations[MutationTypes.CREATE_LICENSEE_ACCOUNT_SUCCESS](state);

        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully get account request', () => {
        const state = {};

        mutations[MutationTypes.GET_ACCOUNT_REQUEST](state);

        expect(state.isLoadingAccount).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully get account failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.GET_ACCOUNT_FAILURE](state, error);

        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully get account success', () => {
        const state = {};

        mutations[MutationTypes.GET_ACCOUNT_SUCCESS](state);

        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully get compact states request', () => {
        const state = {};

        mutations[MutationTypes.GET_COMPACT_STATES_REQUEST](state);

        expect(state.isLoadingCompactStates).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully get compact states failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.GET_COMPACT_STATES_FAILURE](state, error);

        expect(state.isLoadingCompactStates).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully get compact states success (no compact to update)', () => {
        const state = {};

        mutations[MutationTypes.GET_COMPACT_STATES_SUCCESS](state);

        expect(state.isLoadingCompactStates).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully get compact states success (compact updated with states)', () => {
        const state = { currentCompact: new Compact() };

        mutations[MutationTypes.GET_COMPACT_STATES_SUCCESS](state, [new State()]);

        expect(state.isLoadingCompactStates).to.equal(false);
        expect(state.error).to.equal(null);
        expect(state.currentCompact.memberStates.length).to.equal(1);
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
        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully update account request', () => {
        const state = {};

        mutations[MutationTypes.UPDATE_ACCOUNT_REQUEST](state);

        expect(state.isLoadingAccount).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully update account failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.UPDATE_ACCOUNT_FAILURE](state, error);

        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully update account success', () => {
        const state = {};

        mutations[MutationTypes.UPDATE_ACCOUNT_SUCCESS](state);

        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully set refresh token timeout id', () => {
        const state = {};
        const timeoutId = 1;

        mutations[MutationTypes.SET_REFRESH_TIMEOUT_ID](state, timeoutId);

        expect(state.refreshTokenTimeoutId).to.equal(timeoutId);
    });
    it('should successfully upload military affiliation request', () => {
        const state = {};

        mutations[MutationTypes.UPLOAD_MILITARY_AFFILIATION_REQUEST](state);

        expect(state.isLoadingAccount).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully upload military affiliation failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.UPLOAD_MILITARY_AFFILIATION_FAILURE](state, error);

        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully upload military affiliation success', () => {
        const state = {};

        mutations[MutationTypes.UPLOAD_MILITARY_AFFILIATION_SUCCESS](state);

        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully end military affiliation request', () => {
        const state = {};

        mutations[MutationTypes.END_MILITARY_AFFILIATION_REQUEST](state);

        expect(state.isLoadingAccount).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully end military affiliation failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.END_MILITARY_AFFILIATION_FAILURE](state, error);

        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully end military affiliation success', () => {
        const state = {};

        mutations[MutationTypes.END_MILITARY_AFFILIATION_SUCCESS](state);

        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully post privilege purchase request', () => {
        const state = {};

        mutations[MutationTypes.POST_PRIVILEGE_PURCHASE_REQUEST](state);

        expect(state.isLoadingPrivilegePurchaseOptions).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully post privilege purchase success', () => {
        const state = {
            selectedPrivilegesToPurchase: ['ky'],
        };

        mutations[MutationTypes.POST_PRIVILEGE_PURCHASE_SUCCESS](state);

        expect(state.isLoadingPrivilegePurchaseOptions).to.equal(false);
        expect(state.selectedPrivilegesToPurchase).to.equal(null);
        expect(state.error).to.equal(null);
    });
    it('should successfully post privilege purchase failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.POST_PRIVILEGE_PURCHASE_FAILURE](state, error);

        expect(state.isLoadingPrivilegePurchaseOptions).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully get privilege purchase information request', () => {
        const state = {};

        mutations[MutationTypes.GET_PRIVILEGE_PURCHASE_INFORMATION_REQUEST](state);

        expect(state.isLoadingPrivilegePurchaseOptions).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully get privilege purchase information failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.GET_PRIVILEGE_PURCHASE_INFORMATION_FAILURE](state, error);

        expect(state.isLoadingPrivilegePurchaseOptions).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully get privilege purchase information success', () => {
        const state = {};

        mutations[MutationTypes.GET_PRIVILEGE_PURCHASE_INFORMATION_SUCCESS](state);

        expect(state.isLoadingPrivilegePurchaseOptions).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully reset to purchase flow step', () => {
        const state = {
            purchase: new PurchaseFlowState({
                steps: [
                    new PurchaseFlowStep({
                        stepNum: 0
                    }),
                    new PurchaseFlowStep({
                        stepNum: 4
                    })
                ]
            })
        };

        mutations[MutationTypes.RESET_TO_PURCHASE_FLOW_STEP](state, 1);

        expect(state.purchase.steps.length).to.equal(1);
    });
    it('should successfully save a purchase flow step', () => {
        const purchase = new PurchaseFlowState();

        purchase.steps = [
            new PurchaseFlowStep({
                stepNum: 0
            })
        ];

        const state = {
            purchase
        };

        expect(state.purchase.steps.length).to.equal(1);

        mutations[MutationTypes.SAVE_PURCHASE_FLOW_STEP](state, new PurchaseFlowStep({
            stepNum: 1
        }));

        expect(state.purchase.steps.length).to.equal(2);
    });
    it('should handle UPDATE_HOME_JURISDICTION_REQUEST', () => {
        const state: any = {};

        mutations[MutationTypes.UPDATE_HOME_JURISDICTION_REQUEST](state);
        expect(state.isLoadingAccount).to.equal(true);
        expect(state.error).to.equal(null);
    });

    it('should handle UPDATE_HOME_JURISDICTION_FAILURE', () => {
        const state: any = {};
        const error = new Error('Test error');

        mutations[MutationTypes.UPDATE_HOME_JURISDICTION_FAILURE](state, error);
        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(error);
    });

    it('should handle UPDATE_HOME_JURISDICTION_SUCCESS', () => {
        const state: any = {};

        mutations[MutationTypes.UPDATE_HOME_JURISDICTION_SUCCESS](state);
        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully get privilege history request', () => {
        const state = {};

        mutations[MutationTypes.GET_PRIVILEGE_HISTORY_REQUEST](state);

        expect(state.isLoadingPrivilegeHistory).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully get privilege history failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.GET_PRIVILEGE_HISTORY_FAILURE](state, error);

        expect(state.isLoadingPrivilegeHistory).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully get privilege history success', () => {
        const licensee = {
            id: '1',
            privileges: [
                new License({ id: '1-2-3' }),
                new License({ id: '22' }),
            ]
        };
        const model = {
            licensee,
        };
        const state = { model };
        const history = {
            providerId: '1',
            jurisdiction: '2',
            licenseType: '3',
            events: ['1']
        };

        mutations[MutationTypes.GET_PRIVILEGE_HISTORY_SUCCESS](state, { history });

        expect(state.isLoadingPrivilegeHistory).to.equal(false);
        expect(state.error).to.equal(null);
        expect(state.model.licensee.privileges[0].history.length).to.equal(1);
    });
    it('should successfully get privilege history success for privilege not found', () => {
        const licensee = {
            id: '1',
            privileges: [
                new License({ id: '1-2-4' }),
                new License({ id: '22' }),
            ]
        };
        const model = {
            licensee,
        };
        const state = { model };
        const history = {
            providerId: '1',
            jurisdiction: '2',
            licenseType: '3',
            events: ['1']
        };

        mutations[MutationTypes.GET_PRIVILEGE_HISTORY_SUCCESS](state, { history });

        expect(state.isLoadingPrivilegeHistory).to.equal(false);
        expect(state.error).to.equal(null);
        expect(state.model.licensee.privileges[0].history.length).to.equal(0);
    });
    it('should successfully reset mfa licensee account request', () => {
        const state = {};

        mutations[MutationTypes.RESET_MFA_LICENSEE_ACCOUNT_REQUEST](state);

        expect(state.isLoadingAccount).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully reset mfa licensee account failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.RESET_MFA_LICENSEE_ACCOUNT_FAILURE](state, error);

        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully reset mfa licensee account success', () => {
        const state = {};

        mutations[MutationTypes.RESET_MFA_LICENSEE_ACCOUNT_SUCCESS](state);

        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully confirm mfa licensee account request', () => {
        const state = {};

        mutations[MutationTypes.CONFIRM_MFA_LICENSEE_ACCOUNT_REQUEST](state);

        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully confirm mfa licensee account failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.CONFIRM_MFA_LICENSEE_ACCOUNT_FAILURE](state, error);

        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully confirm mfa licensee account success', () => {
        const state = {};

        mutations[MutationTypes.CONFIRM_MFA_LICENSEE_ACCOUNT_SUCCESS](state);

        expect(state.isLoadingAccount).to.equal(false);
        expect(state.error).to.equal(null);
    });
});
describe('User Store Actions', async () => {
    it('should successfully start login request', () => {
        const commit = sinon.spy();

        actions.loginRequest({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.LOGIN_REQUEST]);
    });
    it('should successfully start login success', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();

        await actions.loginSuccess({ commit, dispatch }, AuthTypes.LICENSEE);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.LOGIN_SUCCESS, AuthTypes.LICENSEE]);
        expect(dispatch.calledOnce).to.equal(false);
    });
    it('should successfully start login failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.loginFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.LOGIN_FAILURE, error]);
    });
    it('should successfully start logout request', () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();

        actions.logoutRequest({ commit, dispatch }, 'staff');

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.LOGOUT_REQUEST]);
        expect(dispatch.callCount).to.equal(4);
    });
    it('should successfully start logout success', () => {
        const commit = sinon.spy();

        actions.logoutSuccess({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.LOGOUT_SUCCESS]);
    });
    it('should successfully start logout failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.logoutFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.LOGOUT_FAILURE, error]);
    });
    it('should successfully create licensee account request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const payload = {};

        await actions.createLicenseeAccountRequest({ commit, dispatch }, payload);

        expect(commit.calledOnce, 'commit').to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.CREATE_LICENSEE_ACCOUNT_REQUEST]);
        expect(dispatch.calledOnce, 'dispatch').to.equal(true);
    });
    it('should successfully create licensee account success', () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();

        actions.createLicenseeAccountSuccess({ commit, dispatch });

        expect(commit.calledOnce, 'commit').to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.CREATE_LICENSEE_ACCOUNT_SUCCESS]);
    });
    it('should successfully create licensee account failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.createLicenseeAccountFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.CREATE_LICENSEE_ACCOUNT_FAILURE, error]);
    });
    it('should successfully start staff account request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();

        await actions.getStaffAccountRequest({ commit, dispatch });

        expect(commit.calledOnce, 'commit').to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_ACCOUNT_REQUEST]);
        expect(dispatch.calledOnce, 'dispatch').to.equal(true);
    });
    it('should successfully start licensee account request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();

        await actions.getLicenseeAccountRequest({ commit, dispatch });

        expect(commit.calledOnce, 'commit').to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_ACCOUNT_REQUEST]);
        expect(dispatch.calledOnce, 'dispatch').to.equal(true);
    });
    it('should successfully start account success', () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const account = {};

        actions.getAccountSuccess({ commit, dispatch }, account);

        expect(commit.calledOnce, 'commit').to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_ACCOUNT_SUCCESS, account]);
        expect(dispatch.calledOnce, 'dispatch').to.equal(true);
    });
    it('should successfully start account failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.getAccountFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_ACCOUNT_FAILURE, error]);
    });
    it('should successfully set user', () => {
        const commit = sinon.spy();
        const user = {};

        actions.setStoreUser({ commit }, user);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_UPDATE_USER, user]);
    });
    it('should successfully reset user', () => {
        const commit = sinon.spy();

        actions.resetStoreUser({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_RESET_USER]);
    });
    it('should successfully store staff auth tokens with a tokenResponse', () => {
        const dispatch = sinon.spy();
        const authType = 'staff';

        const tokenResponse = {
            access_token: 'test_access_token',
            token_type: 'test_token_type',
            expires_in: 1,
            id_token: 'test_id_token',
            refresh_token: 'test_refresh_token',
        };

        actions.storeAuthTokens({ dispatch }, { tokenResponse, authType });

        expect(dispatch.calledOnce).to.equal(true);
        expect(dispatch.firstCall.args).to.matchPattern(['startRefreshTokenTimer', 'staff']);
    });
    it('should successfully store licensee auth tokens without a tokenResponse', () => {
        const dispatch = sinon.spy();

        const authType = 'licensee';

        actions.storeAuthTokens({ dispatch }, { tokenResponse: null, authType });

        expect(dispatch.calledOnce).to.equal(true);
        expect(dispatch.firstCall.args).to.matchPattern(['startRefreshTokenTimer', 'licensee']);
    });
    it('should successfully start refresh token timer with data', () => {
        const dispatch = sinon.spy();

        const authType = 'staff';

        actions.startRefreshTokenTimer({ dispatch }, authType);

        expect(dispatch.calledOnce).to.equal(true);
    });
    it('should successfully not start refresh token timer without data', () => {
        const dispatch = sinon.spy();

        authStorage.removeItem(tokens.staff.AUTH_TOKEN_EXPIRY);
        authStorage.removeItem(tokens.staff.REFRESH_TOKEN);

        const authType = 'licensee';

        actions.startRefreshTokenTimer({ dispatch }, authType);

        expect(dispatch.calledOnce).to.equal(false);
    });
    it('should successfully set staff refresh token timeout', () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const refreshToken = 'test_refresh_token';
        const expiresIn = 7200;
        const authType = 'staff';

        actions.setRefreshTokenTimeout({ commit, dispatch }, { refreshToken, expiresIn, authType });

        expect(commit.calledOnce).to.equal(true);
        expect(dispatch.calledOnce).to.equal(false);
    });
    it('should successfully set licensee refresh token timeout', () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const refreshToken = 'test_refresh_token';
        const expiresIn = 7200;
        const authType = 'licensee';

        actions.setRefreshTokenTimeout({ commit, dispatch }, { refreshToken, expiresIn, authType });

        expect(commit.calledOnce).to.equal(true);
        expect(dispatch.calledOnce).to.equal(false);
    });
    it('should successfully clear refresh token timeout', () => {
        const commit = sinon.spy();
        const state = { refreshTokenTimeoutId: 1 };

        actions.clearRefreshTokenTimeout({ commit, state });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.SET_REFRESH_TIMEOUT_ID, null]);
    });
    it('should successfully clear and update auth tokens by clearing existing ones except for auth token, then storing', () => {
        const dispatch = sinon.spy();
        const authType = 'staff';

        const tokenResponse = {
            access_token: 'test_access_token',
            token_type: 'test_token_type',
            expires_in: 1,
            id_token: 'test_id_token',
            refresh_token: 'test_refresh_token',
        };

        actions.updateAuthTokens({ dispatch }, { tokenResponse, authType });

        expect(dispatch.callCount).to.equal(2);
    });
    it('should successfully clear session stores', () => {
        const dispatch = sinon.spy();

        actions.clearSessionStores({ dispatch });

        expect(dispatch.callCount).to.equal(5);
    });
    it('should successfully start get privilege purchase information request', () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();

        actions.getPrivilegePurchaseInformationRequest({ commit, dispatch });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_PRIVILEGE_PURCHASE_INFORMATION_REQUEST]);
    });
    it('should successfully start get privilege purchase information success', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const state = { currentCompact: new Compact({ type: CompactType.ASLP }) };

        const data = {
            jurisdiction: new State({ abbrev: 'ca' }),
            compactType: CompactType.ASLP,
            fee: 5,
            isMilitaryDiscountActive: true,
            militaryDiscountType: FeeTypes.FLAT_RATE,
            militaryDiscountAmount: 10,
            isJurisprudenceRequired: true,
        };
        const privilegePurchaseOption = new PrivilegePurchaseOption(data);

        const privilegePurchaseData = {
            privilegePurchaseOptions: [ privilegePurchaseOption ],
            compactCommissionFee: { compactType: CompactType.ASLP, feeType: 'FLAT_RATE', feeAmount: 3.5 }
        };

        await actions.getPrivilegePurchaseInformationSuccess({ commit, dispatch, state }, privilegePurchaseData);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_PRIVILEGE_PURCHASE_INFORMATION_SUCCESS]);
        expect(dispatch.calledOnce).to.equal(true);
        expect([dispatch.firstCall.args[0]]).to.matchPattern(['setCurrentCompact']);
    });
    it('should successfully start get privilege purchase information failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.getPrivilegePurchaseInformationFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern(
            [MutationTypes.GET_PRIVILEGE_PURCHASE_INFORMATION_FAILURE, error]
        );
    });
    it('should successfully start post privilege purchase request', () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();

        actions.postPrivilegePurchases({ commit, dispatch }, true);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.POST_PRIVILEGE_PURCHASE_REQUEST]);
    });
    it('should successfully start post privilege purchases success', () => {
        const commit = sinon.spy();

        actions.postPrivilegePurchasesSuccess({ commit }, true);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern(
            [MutationTypes.POST_PRIVILEGE_PURCHASE_SUCCESS]
        );
    });
    it('should successfully start post privilege purchases failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.postPrivilegePurchasesFailure({ commit }, true);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern(
            [MutationTypes.POST_PRIVILEGE_PURCHASE_FAILURE, error]
        );
    });
    it('should successfully start reset to purchase flow step', () => {
        const commit = sinon.spy();

        actions.resetToPurchaseFlowStep({ commit }, 3);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern(
            [MutationTypes.RESET_TO_PURCHASE_FLOW_STEP, 3]
        );
    });
    it('should successfully start save purchase flow step', () => {
        const commit = sinon.spy();
        const flowStep = new PurchaseFlowStep();

        actions.saveFlowStep({ commit }, flowStep);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern(
            [MutationTypes.SAVE_PURCHASE_FLOW_STEP, flowStep]
        );
    });
    it('should successfully start end military affiliation request', () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();

        actions.endMilitaryAffiliationRequest({ commit, dispatch });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.END_MILITARY_AFFILIATION_REQUEST]);
    });
    it('should successfully start end military affiliation success', () => {
        const commit = sinon.spy();

        actions.endMilitaryAffiliationSuccess({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern(
            [MutationTypes.END_MILITARY_AFFILIATION_SUCCESS]
        );
    });
    it('should successfully start end military affiliation failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.endMilitaryAffiliationFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern(
            [MutationTypes.END_MILITARY_AFFILIATION_FAILURE, error]
        );
    });
    it('should successfully start upload military affiliation document request', () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const documentData = {
            affiliationType: 'militaryMemberSpouse',
            document: {
                name: 'WyldPets_Backdrop1.jpeg'
            },
            fileNames: ['WyldPets_Backdrop1.jpeg']
        };

        actions.uploadMilitaryAffiliationRequest({ commit, dispatch }, documentData);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.UPLOAD_MILITARY_AFFILIATION_REQUEST]);
    });
    it('should successfully start upload military affiliation document success', () => {
        const commit = sinon.spy();

        actions.uploadMilitaryAffiliationSuccess({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern(
            [MutationTypes.UPLOAD_MILITARY_AFFILIATION_SUCCESS]
        );
    });
    it('should successfully start upload military affiliation document failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.uploadMilitaryAffiliationFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern(
            [MutationTypes.UPLOAD_MILITARY_AFFILIATION_FAILURE, error]
        );
    });
    it('should successfully start compact states request (logged in as staff)', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const state = { isLoggedInAsStaff: true };

        await actions.getCompactStatesRequest({ commit, dispatch, state }, CompactType.ASLP);

        expect(commit.calledOnce, 'commit').to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_COMPACT_STATES_REQUEST]);
        expect(dispatch.calledOnce, 'dispatch').to.equal(true);
        expect([dispatch.firstCall.args[0]]).to.matchPattern(['getCompactStatesSuccess']);
    });
    it('should successfully start compact states request (not logged in as staff)', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const state = { isLoggedInAsStaff: false };

        await actions.getCompactStatesRequest({ commit, dispatch, state }, CompactType.ASLP);

        expect(commit.calledOnce, 'commit').to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_COMPACT_STATES_REQUEST]);
        expect(dispatch.calledOnce, 'dispatch').to.equal(true);
        expect([dispatch.firstCall.args[0]]).to.matchPattern(['getCompactStatesSuccess']);
    });
    it('should successfully start compact states success', () => {
        const commit = sinon.spy();
        const states = [new State()];

        actions.getCompactStatesSuccess({ commit }, states);

        expect(commit.calledOnce, 'commit').to.equal(true);
        expect(commit.firstCall.args[0]).to.equal(MutationTypes.GET_COMPACT_STATES_SUCCESS);
    });
    it('should successfully start compact states failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.getCompactStatesFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_COMPACT_STATES_FAILURE, error]);
    });
    it('should successfully set current compact (null)', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();

        await actions.setCurrentCompact({ commit, dispatch }, null);

        expect(commit.calledOnce, 'commit').to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_UPDATE_CURRENT_COMPACT, null]);
        expect(dispatch.callCount, 'dispatch').to.equal(0);
    });
    it('should successfully set current compact (with compact)', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const compact = new Compact({ type: CompactType.ASLP });

        await actions.setCurrentCompact({ commit, dispatch }, compact);

        expect(commit.calledOnce, 'commit').to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_UPDATE_CURRENT_COMPACT, compact]);
        expect(dispatch.callCount, 'dispatch').to.equal(1);
        expect([dispatch.firstCall.args[0]]).to.matchPattern(['getCompactStatesRequest']);
    });
    it('should successfully start updateHomeJurisdictionRequest', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.stub();
        const data = { jurisdiction: 'co' };

        dispatch.withArgs('setStoreUser').resolves();
        dispatch.withArgs('updateHomeJurisdictionSuccess').resolves();

        await actions.updateHomeJurisdictionRequest({ commit, dispatch }, data);

        expect(commit.calledWith(MutationTypes.UPDATE_HOME_JURISDICTION_REQUEST)).to.equal(true);
        expect(dispatch.calledWith('setStoreUser')).to.equal(true);
        expect(dispatch.calledWith('updateHomeJurisdictionSuccess')).to.equal(true);
    });
    it('should successfully start updateHomeJurisdictionSuccess', () => {
        const commit = sinon.spy();

        actions.updateHomeJurisdictionSuccess({ commit });
        expect(commit.calledWith(MutationTypes.UPDATE_HOME_JURISDICTION_SUCCESS)).to.equal(true);
    });
    it('should successfully start updateHomeJurisdictionFailure', () => {
        const commit = sinon.spy();
        const error = new Error('Test error');

        actions.updateHomeJurisdictionFailure({ commit }, error);
        expect(commit.calledWith(MutationTypes.UPDATE_HOME_JURISDICTION_FAILURE, error)).to.equal(true);
    });
    it('should successfully start privilege history request request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const licenseTypeAbbrev = 'SLP';
        const jurisdiction = 'ky';

        await actions.getPrivilegeHistoryRequestLicensee({ commit, dispatch }, { jurisdiction, licenseTypeAbbrev });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_PRIVILEGE_HISTORY_REQUEST]);
        expect(dispatch.calledOnce).to.equal(true);
    });
    it('should successfully start privilege history failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.getPrivilegeHistoryFailureLicensee({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_PRIVILEGE_HISTORY_FAILURE, error]);
    });
    it('should successfully start start privilege history success', () => {
        const commit = sinon.spy();
        const history = {};

        actions.getPrivilegeHistorySuccessLicensee({ commit }, history);

        expect(commit.calledOnce).to.equal(true);

        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_PRIVILEGE_HISTORY_SUCCESS, { history }]);
    });
    it('should successfully reset mfa licensee account request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const payload = { data: {}};

        await actions.resetMfaLicenseeAccountRequest({ commit, dispatch }, payload);

        expect(commit.calledOnce, 'commit').to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.RESET_MFA_LICENSEE_ACCOUNT_REQUEST]);
        expect(dispatch.calledOnce, 'dispatch').to.equal(true);
    });
    it('should successfully reset mfa licensee account request (intentional error)', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const payload = {};

        await actions.resetMfaLicenseeAccountRequest({ commit, dispatch }, payload).catch((error) => {
            expect(error).to.be.an('error').with.property('message', 'failed mfa reset request');
        });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.RESET_MFA_LICENSEE_ACCOUNT_REQUEST]);
        expect(dispatch.calledOnce).to.equal(true);
        expect(dispatch.firstCall.args[0]).to.equal('resetMfaLicenseeAccountFailure');
    });
    it('should successfully reset mfa licensee account success', () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();

        actions.resetMfaLicenseeAccountSuccess({ commit, dispatch });

        expect(commit.calledOnce, 'commit').to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.RESET_MFA_LICENSEE_ACCOUNT_SUCCESS]);
    });
    it('should successfully reset mfa licensee account failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.resetMfaLicenseeAccountFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.RESET_MFA_LICENSEE_ACCOUNT_FAILURE, error]);
    });
    it('should successfully confirm mfa licensee account request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const payload = { data: {}};

        await actions.confirmMfaLicenseeAccountRequest({ commit, dispatch }, payload);

        expect(commit.calledOnce, 'commit').to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.CONFIRM_MFA_LICENSEE_ACCOUNT_REQUEST]);
        expect(dispatch.calledOnce, 'dispatch').to.equal(true);
    });
    it('should successfully confirm mfa licensee account request (intentional error)', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const payload = {};

        await actions.confirmMfaLicenseeAccountRequest({ commit, dispatch }, payload).catch((error) => {
            expect(error).to.be.an('error').with.property('message', 'failed mfa reset confirm');
        });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.CONFIRM_MFA_LICENSEE_ACCOUNT_REQUEST]);
        expect(dispatch.calledOnce).to.equal(true);
        expect(dispatch.firstCall.args[0]).to.equal('confirmMfaLicenseeAccountFailure');
    });
    it('should successfully confirm mfa licensee account success', () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();

        actions.confirmMfaLicenseeAccountSuccess({ commit, dispatch });

        expect(commit.calledOnce, 'commit').to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.CONFIRM_MFA_LICENSEE_ACCOUNT_SUCCESS]);
    });
    it('should successfully confirm mfa licensee account failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.confirmMfaLicenseeAccountFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.CONFIRM_MFA_LICENSEE_ACCOUNT_FAILURE, error]);
    });
});
describe('User Store Getters', async () => {
    it('should successfully get state', async () => {
        const state = {};
        const prevLastKey = getters.state(state);

        expect(prevLastKey).to.matchPattern(state);
    });
    it('should successfully get current compact', async () => {
        const state = { currentCompact: CompactType.ASLP };
        const compact = getters.currentCompact(state);

        expect(compact).to.equal(CompactType.ASLP);
    });
    it('should successfully get the next needed purchase flow step)', async () => {
        const state = {
            purchase: new PurchaseFlowState({
                steps: [
                    new PurchaseFlowStep({
                        stepNum: 0
                    }),
                    new PurchaseFlowStep({
                        stepNum: 4
                    })
                ]
            })
        };

        const nextStep = getters.getNextNeededPurchaseFlowStep(state)();

        expect(nextStep).to.equal(1);
    });
    it('should successfully get the saved license by Id', async () => {
        const state = {
            purchase: new PurchaseFlowState({
                steps: [
                    new PurchaseFlowStep({
                        stepNum: 0,
                        licenseSelected: 'license-1'
                    }),
                ],
            }),
            model: new LicenseeUser({
                licensee: new Licensee({
                    licenses: [
                        new License({
                            id: 'license-1',
                            issueState: new State({ abbrev: 'co' }),
                            mailingAddress: new Address({
                                street1: 'test-street1',
                                street2: 'test-street2',
                                city: 'test-city',
                                state: 'co',
                                zip: 'test-zip'
                            }),
                            licenseNumber: '1',
                            status: 'active'
                        }),
                        new License({
                            id: 'license-2',
                            issueState: new State({ abbrev: 'co' }),
                            mailingAddress: new Address({
                                street1: 'test-street1',
                                street2: 'test-street2',
                                city: 'test-city',
                                state: 'co',
                                zip: 'test-zip'
                            }),
                            licenseNumber: '2',
                            status: 'inactive'
                        }),
                        new License(),
                    ],
                })
            })
        };

        const licenseSelected = getters.getLicenseSelected(state)();

        expect(licenseSelected.licenseNumber).to.equal('1');
    });
    it('should successfully get the user privilege by Id', async () => {
        const state = {
            model: new LicenseeUser({
                licensee: new Licensee({
                    privileges: [
                        new License({
                            id: 'license-1',
                            issueState: new State({ abbrev: 'co' }),
                            mailingAddress: new Address({
                                street1: 'test-street1',
                                street2: 'test-street2',
                                city: 'test-city',
                                state: 'co',
                                zip: 'test-zip'
                            }),
                            licenseNumber: '1',
                            status: 'active'
                        }),
                        new License({
                            id: 'license-2',
                            issueState: new State({ abbrev: 'mi' }),
                            mailingAddress: new Address({
                                street1: 'test-street1',
                                street2: 'test-street2',
                                city: 'test-city',
                                state: 'co',
                                zip: 'test-zip'
                            }),
                            status: 'inactive'
                        }),
                        new License(),
                    ],
                })
            })
        };

        const licenseSelected = getters.getUserPrivilegeById(state)('license-2');

        expect(licenseSelected.id).to.equal('license-2');
    });
    it('should not successfully get the user privilege by Id', async () => {
        const state = {
            model: new LicenseeUser({
                licensee: new Licensee({
                    privileges: [
                        new License({
                            id: 'license-1',
                            issueState: new State({ abbrev: 'co' }),
                            mailingAddress: new Address({
                                street1: 'test-street1',
                                street2: 'test-street2',
                                city: 'test-city',
                                state: 'co',
                                zip: 'test-zip'
                            }),
                            licenseNumber: '1',
                            status: 'active'
                        }),
                        new License({
                            id: 'license-2',
                            issueState: new State({ abbrev: 'mi' }),
                            mailingAddress: new Address({
                                street1: 'test-street1',
                                street2: 'test-street2',
                                city: 'test-city',
                                state: 'co',
                                zip: 'test-zip'
                            }),
                            status: 'inactive'
                        }),
                        new License(),
                    ],
                })
            })
        };

        const licenseSelected = getters.getUserPrivilegeById(state)('license-3');

        expect(licenseSelected).to.equal(null);
    });
});
