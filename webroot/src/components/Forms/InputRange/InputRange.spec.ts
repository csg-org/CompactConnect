//
//  InputRange.spec.ts
//  <the-app-name>
//
//  Created by InspiringApps on 5/21/2024.
//  Copyright © 2024. <the-customer-name>. All rights reserved.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import InputRange from '@components/Forms/InputRange/InputRange.vue';
import { FormInput } from '@models/FormInput/FormInput.model';

describe('InputRange component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputRange, {
            props: {
                formInput: new FormInput(),
            },
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputRange).exists()).to.equal(true);
    });
});
