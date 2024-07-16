//
//  FormInput.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/25/2020.
//
import deleteUndefinedProperties from '@models/_helpers';
import { ComputedRef } from 'vue';
import { Schema as JoiSchema } from 'joi';

// ========================================================
// =                 Form Input Interface                 =
// ========================================================
export interface InterfaceFormInput {
    id?: string;
    name?: string;
    label?: string | ComputedRef<string>;
    shouldHideLabel?: boolean;
    isLabelHTML?: boolean;
    placeholder?: string | ComputedRef<string>;
    value?: string | number | boolean | null | Array<File>;
    valueOptions?: Array<{ value: any; name: string | ComputedRef<string>; }>;
    autocomplete?: string;
    fileConfig?: {
        accepts?: Array<string>;
        allowMultiple?: boolean;
        maxSizeMbPer?: number;
        maxSizeMbAll?: number;
        hint?: string | ComputedRef<string>;
    };
    rangeConfig?: {
        min?: number;
        max?: number;
        stepInterval?: number;
        displayFormatter?: (value: any) => string;
    };
    isTouched?: boolean;
    validation?: JoiSchema | null;
    showMax?: boolean;
    enforceMax?: boolean;
    errorMessage?: string | ComputedRef<string>;
    isValid?: boolean;
    isSubmitInput?: boolean;
    isFormRow?: boolean;
    isDisabled?: boolean;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class FormInput implements InterfaceFormInput {
    public id = '';
    public name = '';
    public label = '';
    public shouldHideLabel = false;
    public isLabelHTML = false;
    public placeholder = '';
    public value = '';
    public valueOptions = [];
    public autocomplete = 'on';
    public fileConfig = {
        accepts: [],
        allowMultiple: false,
        maxSizeMbPer: 0,
        maxSizeMbAll: 0,
        hint: '',
    };
    public rangeConfig = { // eslint-disable-line lines-between-class-members
        min: 0,
        max: 0,
        stepInterval: 1,
        displayFormatter: (value: any) => new Intl.NumberFormat().format(value),
    };
    public isTouched = false; // eslint-disable-line lines-between-class-members
    public isEdited = false;
    public validation = null;
    public showMax = false;
    public enforceMax = false;
    public errorMessage = '';
    public successMessage = '';
    public isValid = false;
    public isSubmitInput = false;
    public isFormRow = false;
    public isDisabled = false;

    constructor(data?: InterfaceFormInput) {
        const cleanDataObject = deleteUndefinedProperties(data);

        Object.assign(this, cleanDataObject);
    }

    public blur(): void {
        this.isTouched = true;
        this.validate();
    }

    public input(): void {
        this.isEdited = true;

        if (this.enforceMax) {
            this.enforceLength();
        }

        this.validate();
    }

    public maxLength(): number {
        const { validation } = this;
        let max = -1;

        if (validation) {
            const { _rules: rules = []} = validation;
            const maxRule: any = rules?.find((rule) => (rule as any).name === 'max') || null;

            if (maxRule) {
                max = maxRule?.args?.limit || -1;
            }
        }

        return max;
    }

    public enforceLength(): void {
        const { enforceMax, value } = this;
        const maxLength = this.maxLength();

        if (enforceMax) {
            const valueLength = (value) ? value.length : 0;

            if (maxLength >= 0 && valueLength > maxLength) {
                this.value = this.value.slice(0, maxLength);
            }
        }
    }

    public validate(): void {
        // @TODO: Better typing for Joi schemas
        const { validation } = this;

        if (validation && (validation as any).validate) {
            const result = (validation as any).validate(this.value);

            if (result.error) {
                this.isValid = false;

                if (this.isTouched) {
                    this.errorMessage = result.error.message;
                }
            } else {
                this.errorMessage = '';
                this.isValid = true;
            }
        } else {
            this.errorMessage = '';
            this.isValid = true;
        }
    }
}
