//
//  Sorting.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/2/2020.
//

// import sinon from 'sinon';
import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Sorting from '@components/Lists/Sorting/Sorting.vue';

describe('Sorting component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Sorting, {
            props: {
                sortingId: 'test',
                sortOptions: [],
                // sortChange: () => null,
            }
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Sorting).exists()).to.equal(true);
    });

    // @TODO
});
