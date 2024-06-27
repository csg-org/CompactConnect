//
//  InputRadioGroup.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/12/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import InputRadioGroup from '@components/Forms/InputRadioGroup/InputRadioGroup.vue';
import { FormInput } from '@models/FormInput/FormInput.model';

describe('InputRadioGroup component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputRadioGroup, {
            props: {
                formInput: new FormInput(),
            },
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputRadioGroup).exists()).to.equal(true);
    });
});
