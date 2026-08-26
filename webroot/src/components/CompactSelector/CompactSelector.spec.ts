//
//  CompactSelector.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/2/2024.
//

import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import CompactSelector from '@components/CompactSelector/CompactSelector.vue';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { MutationTypes } from '@store/user/user.mutations';
import { StaffUser, CompactPermission } from '@models/StaffUser/StaffUser.model';
import store from '@store/index';

chai.use(chaiMatchPattern);

const { expect } = chai;

const buildCompactPermission = (compactType: CompactType | string): CompactPermission => ({
    compact: new Compact({ type: compactType as CompactType }),
    isReadPrivate: true,
    isReadSsn: false,
    isAdmin: false,
    states: [],
});

const seedPermissionBasedUser = (compactTypes: Array<CompactType | string>) => {
    store.commit(
        `user/${MutationTypes.STORE_UPDATE_USER}`,
        new StaffUser({
            permissions: compactTypes.map((compactType) => buildCompactPermission(compactType)),
        })
    );
};

const resetUserStore = () => {
    store.commit(`user/${MutationTypes.STORE_RESET_USER}`);
};

describe('CompactSelector component', async () => {
    beforeEach(() => {
        resetUserStore();
    });

    afterEach(() => {
        resetUserStore();
    });

    it('should mount the component', async () => {
        const wrapper = await mountShallow(CompactSelector);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(CompactSelector).exists()).to.equal(true);
    });
    it('should successfully include only enabled compacts in permission-based options', async () => {
        seedPermissionBasedUser([
            CompactType.ASLP,
            CompactType.COUNSELING,
            'unknown-compact',
        ]);

        const wrapper = await mountShallow(CompactSelector, {
            props: { isPermissionBased: true },
        });
        const component = wrapper.vm;
        const enabledTypes = component.$compactsEnabled.map((compact) => compact.type);
        const optionValues = component.compactOptions.map((option) => option.value);

        expect(optionValues).to.include(CompactType.ASLP);
        expect(optionValues).to.include(CompactType.COUNSELING);
        expect(optionValues).to.not.include('unknown-compact');
        optionValues.forEach((optionValue) => {
            expect(enabledTypes).to.include(optionValue);
        });
    });
    it('should successfully omit unknown compact types from permission-based options', async () => {
        seedPermissionBasedUser(['unknown-compact']);

        const wrapper = await mountShallow(CompactSelector, {
            props: { isPermissionBased: true },
        });

        expect(wrapper.vm.compactOptions).to.matchPattern([]);
    });
});
