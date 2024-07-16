//
//  InputButton.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/27/2020.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import InputButton from '@components/Forms/InputButton/InputButton.vue';

describe('InputButton component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputButton, {
            props: {
                label: 'Test',
                onClick: () => 'test',
            }
        });
        const component = wrapper.vm;

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputButton).exists()).to.equal(true);
        expect(component.onClick()).to.equal('test');
    });
});
