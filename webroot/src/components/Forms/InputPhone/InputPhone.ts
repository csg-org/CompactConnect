//
//  InputPhone.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/19/2020.
//

import {
    Component,
    mixins,
    toNative
} from 'vue-facing-decorator';
import { reactive } from 'vue';
import MixinInput from '@components/Forms/_mixins/input.mixin';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import { FormInput } from '@models/FormInput/FormInput.model';
import { countries as countryData } from 'country-codes-flags-phone-codes';
import { AsYouType, parsePhoneNumber, CountryCode } from 'libphonenumber-js';

@Component({
    name: 'InputPhone',
    components: {
        InputSelect,
    },
})
class InputPhone extends mixins(MixinInput) {
    //
    // Data
    //
    formData: any = {};
    localValue = '';

    //
    // Lifecycle
    //
    created() {
        this.initFormInputs();
        this.localValue = this.formInput.value;
    }

    //
    // Computed
    //
    get countryCodes(): Array<{ value: string, name: string }> {
        const allowedCountryCodes = ['US'];
        const allowedCountries = countryData.filter((country) => allowedCountryCodes.includes(country.code));
        const sortedCountries = allowedCountries.sort((a, b) =>
            allowedCountryCodes.indexOf(a.code) - allowedCountryCodes.indexOf(b.code));
        const countries = sortedCountries.map((country) => ({
            value: country.code,
            name: `${country.flag} ${country.dialCode}`,
        }));

        return countries;
    }

    get selectedCountry(): CountryCode {
        return this.formData.country?.value || 'US';
    }

    get phoneDisplay(): string {
        const { selectedCountry } = this;
        const currentPhone = this.localValue;
        const format = new AsYouType(selectedCountry);
        const formatted = format.input(currentPhone);

        return formatted;
    }

    set phoneDisplay(value) {
        const { selectedCountry } = this;
        let raw = '';

        try {
            const parsed = parsePhoneNumber(this.localValue, selectedCountry);

            raw = parsed.number;
        } catch (e) {
            // Continue
        }

        this.phoneDisplay = raw;
    }

    get phoneRaw(): string {
        const { selectedCountry } = this;
        let raw = '';

        try {
            const parsed = parsePhoneNumber(this.localValue, selectedCountry);

            raw = parsed.number;
        } catch (e) {
            // Continue
        }

        return raw;
    }

    get isPhoneValid(): boolean {
        const { selectedCountry } = this;
        let isValid = false;

        try {
            const parsed = parsePhoneNumber(this.localValue, selectedCountry);

            isValid = parsed.isValid();
        } catch (e) {
            // Continue
        }

        return isValid;
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            country: new FormInput({
                id: 'country',
                name: 'country',
                label: 'country',
                shouldHideLabel: true,
                value: this.countryCodes[0]?.value || '',
                valueOptions: this.countryCodes,
            }),
        });
    }

    validate(): void {
        const { isPhoneValid, formInput } = this;

        if (!isPhoneValid && formInput.isTouched) {
            formInput.errorMessage = `Must be a valid phone number, including area code, for the selected country`;
            formInput.isValid = false;
        } else {
            formInput.errorMessage = ``;
            formInput.isValid = true;
        }
    }

    input(formInput: FormInput): void {
        formInput.value = this.phoneRaw;
        this.validate();
    }

    blur(formInput: FormInput): void {
        formInput.isTouched = true;
        this.validate();
    }

    inputCountry(): void {
        this.validate();
    }

    blurCountry(): void {
        this.validate();
    }
}

export default toNative(InputPhone);

// export { InputPhone };
