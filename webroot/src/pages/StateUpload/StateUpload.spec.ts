//
//  StateUpload.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/19/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import StateUpload from '@pages/StateUpload/StateUpload.vue';

describe('StateUpload page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(StateUpload);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(StateUpload).exists()).to.equal(true);
    });
});
