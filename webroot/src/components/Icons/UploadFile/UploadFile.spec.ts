//
//  UploadFile.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 6/18/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import UploadFile from '@components/Icons/UploadFile/UploadFile.vue';

describe('UploadFile component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(UploadFile);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(UploadFile).exists()).to.equal(true);
    });
});
