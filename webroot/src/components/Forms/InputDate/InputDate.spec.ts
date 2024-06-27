//
//  InputDate.spec.ts
//  <the-app-name>
//
//  Created by InspiringApps on 6/7/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import InputDate from '@components/Forms/InputDate/InputDate.vue';

describe('InputDate component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputDate);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputDate).exists()).to.equal(true);
    });
});
