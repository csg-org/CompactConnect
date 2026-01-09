//
//  Pagination.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/1/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Pagination from '@components/Lists/Pagination/Pagination.vue';

describe('Pagination component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Pagination, {
            props: {
                pageChange: () => null,
            },
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Pagination).exists()).to.equal(true);
    });
});
