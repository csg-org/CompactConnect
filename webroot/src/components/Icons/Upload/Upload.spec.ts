//
//  Upload.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/16/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Upload from '@components/Icons/Upload/Upload.vue';

describe('Upload component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Upload);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Upload).exists()).to.equal(true);
    });
});
