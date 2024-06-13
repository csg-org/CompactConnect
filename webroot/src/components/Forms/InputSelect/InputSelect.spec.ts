//
//  InputSelect.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/28/2020.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { nextTick } from 'vue';
import { expect } from 'chai';
import { mountShallow, mountFull } from '@tests/helpers/setup';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import { FormInput } from '@/models/FormInput/FormInput.model';

const options = [
    { value: 10, name: '10' },
    { value: 20, name: '20' },
    { value: 50, name: '50' }
];

describe('InputSelect component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputSelect, {
            props: {
                formInput: new FormInput(),
            }
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputSelect).exists()).to.equal(true);
    });

    it('should emit an change event when the select is changed', async () => {
        const wrapper = await mountFull(InputSelect, {
            props: {
                formInput: new FormInput({ valueOptions: options }),
            }
        });
        const optionsEl = wrapper.find('select').findAll('option');

        await optionsEl.at(1).setSelected();
        await nextTick();

        const emittedEventBus = wrapper.emitted().change;

        expect(emittedEventBus).to.be.an('Array');
        expect(emittedEventBus.length).to.equal(1);
    });
});
