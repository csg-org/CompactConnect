//
//  UserRowEdit.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/14/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import UserRowEdit from '@components/Users/UserRowEdit/UserRowEdit.vue';
import { Permission } from '@/app.config';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { MutationTypes } from '@store/user/user.mutations';
import {
    StaffUser,
    CompactPermission,
    StatePermission
} from '@models/StaffUser/StaffUser.model';

const compactType = CompactType.ASLP;
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
    wrapper.vm.$store.commit(`user/${MutationTypes.STORE_UPDATE_CURRENT_COMPACT}`, new Compact({ type: compactType }));
    wrapper.vm.$store.commit(`user/${MutationTypes.STORE_UPDATE_USER}`, new StaffUser({
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
});
