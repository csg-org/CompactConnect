//
//  InputCheckbox.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 1/22/2021.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
import { FormInput } from '@models/FormInput/FormInput.model';

describe('InputCheckbox component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputCheckbox, {
            props: {
                formInput: new FormInput(),
            }
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputCheckbox).exists()).to.equal(true);
    });
    it('should have the required attributes', async () => {
        const wrapper = await mountShallow(InputCheckbox, {
            props: {
                formInput: new FormInput({ id: 'id', name: 'name' }),
            }
        });
        const checkbox = wrapper.find('input');

        expect(checkbox.attributes('type')).to.equal('checkbox');
        expect(checkbox.attributes('id')).to.equal('id');
        expect(checkbox.attributes('name')).to.equal('name');
    });
    it('should have the label text', async () => {
        const labelText = 'Checkbox Label';
        const wrapper = await mountShallow(InputCheckbox, {
            props: {
                formInput: new FormInput({ label: labelText }),
            }
        });
        const checkbox = wrapper.find('input');

        expect(wrapper.find('label').text()).equal(labelText);
        expect(checkbox.attributes('aria-label')).to.equal(labelText);
    });
});
