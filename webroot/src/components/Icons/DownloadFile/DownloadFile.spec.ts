//
//  DownloadFile.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/13/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import DownloadFile from '@components/Icons/DownloadFile/DownloadFile.vue';

describe('DownloadFile component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(DownloadFile);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(DownloadFile).exists()).to.equal(true);
    });
});
