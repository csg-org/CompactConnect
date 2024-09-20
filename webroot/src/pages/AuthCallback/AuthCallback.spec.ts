//
//  AuthCallback.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/12/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import AuthCallback from '@pages/AuthCallback/AuthCallback.vue';

describe('AuthCallback page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(AuthCallback);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(AuthCallback).exists()).to.equal(true);
    });
});
