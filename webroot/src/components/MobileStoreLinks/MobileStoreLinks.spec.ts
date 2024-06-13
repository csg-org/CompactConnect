//
//  MobileStoreLinks.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 9/4/2020.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import MobileStoreLinks from '@components/MobileStoreLinks/MobileStoreLinks.vue';
import { mobileStoreLinks } from '@/app.config';

describe('MobileStoreLinks component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(MobileStoreLinks);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(MobileStoreLinks).exists()).to.equal(true);
    });
    it('should have apple link image', async () => {
        const wrapper = await mountShallow(MobileStoreLinks);
        const appleLink = wrapper.find('a.apple');

        expect(appleLink.exists(), 'apple link exists').to.equal(true);

        const appleImg = appleLink.find('img');

        expect(appleImg.attributes('alt'), 'apple image exists').to.equal('Download on the Apple App Store');
        expect(appleLink.attributes('href'), 'apple href').to.equal(mobileStoreLinks.APPLE_STORE_LINK);
    });
    it('should have google link image', async () => {
        const wrapper = await mountShallow(MobileStoreLinks);
        const googleLink = wrapper.find('a.google');

        expect(googleLink.exists(), 'google link exists').to.equal(true);

        const googleImg = googleLink.find('img');

        expect(googleImg.attributes('alt'), 'google image exists').to.equal('Download on Google Play');
        expect(googleLink.attributes('href'), 'google href').to.equal(mobileStoreLinks.GOOGLE_STORE_LINK);
    });
});
