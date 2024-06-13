//
//  InputPhone.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/19/2020.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import InputPhone from '@components/Forms/InputPhone/InputPhone.vue';
import { FormInput } from '@models/FormInput/FormInput.model';

describe('InputPhone component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputPhone, {
            props: {
                formInput: new FormInput(),
            },
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputPhone).exists()).to.equal(true);
    });
});
