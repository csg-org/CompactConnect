//
//  InputSubmit.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/22/2020.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import { FormInput } from '@/models/FormInput/FormInput.model';

describe('InputSubmit component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputSubmit, {
            props: {
                formInput: new FormInput(),
            }
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputSubmit).exists()).to.equal(true);
    });
    it('should be disabled', async () => {
        const wrapper = await mountShallow(InputSubmit, {
            props: {
                formInput: new FormInput(),
                isEnabled: false,
            }
        });
        const input = wrapper.find('input');

        expect(input.html()).to.contain('disabled');
    });
});
