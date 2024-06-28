//
//  StateUpload.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 6/18/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import StateUpload from '@components/StateUpload/StateUpload.vue';

describe('StateUpload component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(StateUpload);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(StateUpload).exists()).to.equal(true);
    });
});
