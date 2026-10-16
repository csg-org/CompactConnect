//
//  UserRowEdit.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/14/2024.
//

import { expect } from 'chai';
import sinon from 'sinon';
import { mountShallow } from '@tests/helpers/setup';
import UserRowEdit from '@components/Users/UserRowEdit/UserRowEdit.vue';
import { Permission } from '@/app.config';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { State } from '@models/State/State.model';
import store from '@store/index';
import { MutationTypes } from '@store/user/user.mutations';
import {
    StaffUser,
    CompactPermission,
    StatePermission
} from '@models/StaffUser/StaffUser.model';

const compactType = CompactType.ASLP;
const memberStates = [
    new State({ abbrev: 'ky' }),
    new State({ abbrev: 'oh' }),
];
const buildCompactPermission = (
    compactOverrides: Partial<CompactPermission> = {},
    stateOverrides: Array<Partial<StatePermission>> = []
): CompactPermission => ({
    compact: new Compact({ type: compactType }),
    isReadPrivate: false,
    isReadSsn: false,
    isAdmin: false,
    states: stateOverrides.map((stateOverride) => ({
        state: { abbrev: 'ky' } as any,
        isReadPrivate: false,
        isReadSsn: false,
        isWrite: false,
        isAdmin: false,
        ...stateOverride,
    })),
    ...compactOverrides,
});
const setFormData = (wrapper, data: Record<string, unknown>) => {
    wrapper.vm.formData = Object.keys(data).reduce((preppedData, key) => ({
        ...preppedData,
        [key]: {
            value: data[key],
            isDisabled: false,
            isSubmitInput: false,
        },
    }), {});
};
const storeSetup = (wrapper) => {
    wrapper.vm.$store.commit(`user/${MutationTypes.STORE_UPDATE_CURRENT_COMPACT}`, new Compact({
        type: compactType,
        memberStates,
    }));
    wrapper.vm.$store.commit(`user/${MutationTypes.STORE_UPDATE_USER}`, new StaffUser({
        permissions: [buildCompactPermission({
            isReadPrivate: true,
            isReadSsn: true,
            isAdmin: true,
        })],
    }));
};
const storeSetupBeforeMount = () => {
    store.commit(`user/${MutationTypes.STORE_UPDATE_CURRENT_COMPACT}`, new Compact({
        type: compactType,
        memberStates,
    }));
    store.commit(`user/${MutationTypes.STORE_UPDATE_USER}`, new StaffUser({
        permissions: [buildCompactPermission({
            isReadPrivate: true,
            isReadSsn: true,
            isAdmin: true,
        })],
    }));
};

describe('UserRowEdit component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(UserRowEdit, {
            props: {
                user: new StaffUser(),
            },
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(UserRowEdit).exists()).to.equal(true);
    });
    it('should successfully preserve missing compact permissions', async () => {
        const wrapper = await mountShallow(UserRowEdit, {
            props: {
                user: new StaffUser(),
            },
        });

        storeSetup(wrapper);
        setFormData(wrapper, {
            compact: compactType,
            compactPermission: Permission.NONE,
        });

        const preppedData = wrapper.vm.prepFormData();

        expect(preppedData).to.deep.equal({
            compact: compactType,
            states: [],
        });
    });
    it('should successfully remove compact permissions', async () => {
        const wrapper = await mountShallow(UserRowEdit, {
            props: {
                user: new StaffUser({
                    permissions: [buildCompactPermission({
                        isReadPrivate: true,
                        isReadSsn: false,
                        isAdmin: true,
                    })],
                }),
            },
        });

        storeSetup(wrapper);
        setFormData(wrapper, {
            compact: compactType,
            compactPermission: Permission.NONE,
        });

        const preppedData = wrapper.vm.prepFormData();

        expect(preppedData).to.deep.equal({
            compact: compactType,
            isReadPrivate: false,
            isAdmin: false,
            states: [],
        });
    });
    it('should successfully preserve missing state permissions', async () => {
        const wrapper = await mountShallow(UserRowEdit, {
            props: {
                user: new StaffUser({
                    permissions: [buildCompactPermission({}, [
                        { state: { abbrev: 'ky' }},
                    ])],
                }),
            },
        });

        storeSetup(wrapper);
        setFormData(wrapper, {
            compact: compactType,
            compactPermission: Permission.NONE,
            'state-option-0': 'ky',
            'state-permission-0': Permission.NONE,
        });

        const preppedData = wrapper.vm.prepFormData();

        expect(preppedData).to.deep.equal({
            compact: compactType,
            states: [
                { abbrev: 'ky' },
            ],
        });
    });
    it('should successfully remove state permissions', async () => {
        const wrapper = await mountShallow(UserRowEdit, {
            props: {
                user: new StaffUser({
                    permissions: [buildCompactPermission({}, [
                        {
                            state: { abbrev: 'ky' } as any,
                            isReadPrivate: true,
                            isReadSsn: true,
                            isWrite: true,
                            isAdmin: true,
                        },
                    ])],
                }),
            },
        });

        storeSetup(wrapper);
        setFormData(wrapper, {
            compact: compactType,
            compactPermission: Permission.NONE,
            'state-option-0': 'ky',
            'state-permission-0': Permission.READ_PRIVATE,
        });

        const preppedData = wrapper.vm.prepFormData();

        expect(preppedData).to.deep.equal({
            compact: compactType,
            states: [
                {
                    abbrev: 'ky',
                    isReadPrivate: true,
                    isReadSsn: false,
                    isWrite: false,
                    isAdmin: false,
                },
            ],
        });
    });
    it('should successfully update state permissions', async () => {
        const wrapper = await mountShallow(UserRowEdit, {
            props: {
                user: new StaffUser({
                    permissions: [buildCompactPermission()],
                }),
            },
        });

        storeSetup(wrapper);
        setFormData(wrapper, {
            compact: compactType,
            compactPermission: Permission.NONE,
            'state-option-0': 'ky',
            'state-permission-0': Permission.WRITE,
        });

        const preppedData = wrapper.vm.prepFormData();

        expect(preppedData).to.deep.equal({
            compact: compactType,
            states: [
                {
                    abbrev: 'ky',
                    isReadPrivate: true,
                    isReadSsn: true,
                    isWrite: true,
                },
            ],
        });
    });
    it('should disable the affiliation permission select when the saved permission is admin', async () => {
        storeSetupBeforeMount();

        const wrapper = await mountShallow(UserRowEdit, {
            props: {
                user: new StaffUser({
                    permissions: [buildCompactPermission({
                        isReadPrivate: true,
                        isReadSsn: true,
                        isAdmin: true,
                    })],
                }),
            },
        });

        expect(wrapper.vm.formData.compactPermission.isDisabled).to.equal(true);
    });
    it('should not disable the affiliation permission select when the saved permission is not admin', async () => {
        storeSetupBeforeMount();

        const wrapper = await mountShallow(UserRowEdit, {
            props: {
                user: new StaffUser({
                    permissions: [buildCompactPermission({
                        isReadPrivate: true,
                        isReadSsn: false,
                        isAdmin: false,
                    })],
                }),
            },
        });

        expect(wrapper.vm.formData.compactPermission.isDisabled).to.equal(false);
    });
    it('should disable the state permission select when the saved permission is admin', async () => {
        storeSetupBeforeMount();

        const wrapper = await mountShallow(UserRowEdit, {
            props: {
                user: new StaffUser({
                    permissions: [buildCompactPermission({}, [
                        {
                            state: { abbrev: 'ky' } as any,
                            isReadPrivate: true,
                            isReadSsn: true,
                            isWrite: true,
                            isAdmin: true,
                        },
                    ])],
                }),
            },
        });

        expect(wrapper.vm.formData['state-permission-0'].isDisabled).to.equal(true);
    });
    it('should not disable the state permission select when the saved permission is not admin', async () => {
        storeSetupBeforeMount();

        const wrapper = await mountShallow(UserRowEdit, {
            props: {
                user: new StaffUser({
                    permissions: [buildCompactPermission({}, [
                        {
                            state: { abbrev: 'ky' } as any,
                            isReadPrivate: true,
                            isReadSsn: true,
                            isWrite: true,
                            isAdmin: false,
                        },
                    ])],
                }),
            },
        });

        expect(wrapper.vm.formData['state-permission-0'].isDisabled).to.equal(false);
    });
    it('should not disable the state permission select for newly added state permissions', async () => {
        storeSetupBeforeMount();

        const wrapper = await mountShallow(UserRowEdit, {
            props: {
                user: new StaffUser({
                    permissions: [buildCompactPermission()],
                }),
            },
        });

        wrapper.vm.addStateFormInput();

        expect(wrapper.vm.formData['state-permission-0'].isDisabled).to.equal(false);
    });
    it('should emit cancel when continuing without logging out', async () => {
        let didEmitCancel = false;
        const wrapper = await mountShallow(UserRowEdit, {
            props: {
                user: new StaffUser(),
                onCancel: () => {
                    didEmitCancel = true;
                },
            },
        });

        wrapper.vm.handleContinueWithoutLoggingOut();

        expect(didEmitCancel).to.equal(true);
    });
    it('should route to Logout when logging out from the success state', async () => {
        const wrapper = await mountShallow(UserRowEdit, {
            props: {
                user: new StaffUser(),
            },
        });
        const pushStub = sinon.stub(wrapper.vm.$router, 'push').resolves();

        wrapper.vm.handleLogout();

        expect(pushStub.calledOnceWith({ name: 'Logout' })).to.equal(true);
    });
    it('should show the success state content when the form is successful for the current user', async () => {
        const currentUser = new StaffUser({ id: 'user-1', firstName: 'Jane', lastName: 'Admin' });

        store.commit(`user/${MutationTypes.STORE_UPDATE_USER}`, currentUser);

        const wrapper = await mountShallow(UserRowEdit, {
            props: {
                user: currentUser,
            },
        });

        wrapper.vm.isFormSuccessful = true;
        await wrapper.vm.$nextTick();

        expect(wrapper.find('.edit-user-success').exists()).to.equal(true);
        expect(wrapper.find('.icon-container').exists()).to.equal(true);
        expect(wrapper.find('#log-out-edit-user').exists()).to.equal(true);
        expect(wrapper.text()).to.include('Your permissions have been updated');
        expect(wrapper.text()).to.include('You must log out and back in in order to access new permissions');
        expect(wrapper.text()).to.not.include('Edit user permissions');
    });
    it('should show the other user name in the success title when editing another staff member', async () => {
        const currentUser = new StaffUser({ id: 'user-1', firstName: 'Jane', lastName: 'Admin' });
        const otherUser = new StaffUser({ id: 'user-2', firstName: 'John', lastName: 'Doe' });

        store.commit(`user/${MutationTypes.STORE_UPDATE_USER}`, currentUser);

        const wrapper = await mountShallow(UserRowEdit, {
            props: {
                user: otherUser,
            },
        });

        wrapper.vm.isFormSuccessful = true;
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).to.include('John Doe\'s permissions have been updated');
        expect(wrapper.text()).to.include('They must log out and back in in order to access new permissions');
        expect(wrapper.find('#log-out-edit-user').exists()).to.equal(false);
        expect(wrapper.text()).to.not.include('Your permissions have been updated');
        expect(wrapper.text()).to.not.include('You must log out');
    });
});
