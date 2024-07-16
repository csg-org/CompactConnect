//
//  FormInput.model.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { FormInput } from '@models/FormInput/FormInput.model';
import Joi from 'joi';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('FormInput model', () => {
    it('should create a FormInput with expected defaults', () => {
        const formInput = new FormInput();

        // Test field defaults
        expect(formInput).to.be.an.instanceof(FormInput);
        expect(formInput.id).to.equal('');
        expect(formInput.name).to.equal('');
        expect(formInput.label).to.equal('');
        expect(formInput.shouldHideLabel).to.equal(false);
        expect(formInput.isLabelHTML).to.equal(false);
        expect(formInput.placeholder).to.equal('');
        expect(formInput.value).to.equal('');
        expect(formInput.valueOptions).to.be.an('array').that.is.empty;
        expect(formInput.autocomplete).to.equal('on');
        expect(formInput.fileConfig).to.be.an('object');
        expect(formInput.fileConfig.accepts).to.be.an('array').that.is.empty;
        expect(formInput.fileConfig.allowMultiple).to.equal(false);
        expect(formInput.fileConfig.maxSizeMbPer).to.equal(0);
        expect(formInput.fileConfig.maxSizeMbAll).to.equal(0);
        expect(formInput.fileConfig.hint).to.equal('');
        expect(formInput.rangeConfig).to.be.an('object');
        expect(formInput.rangeConfig.min).to.equal(0);
        expect(formInput.rangeConfig.max).to.equal(0);
        expect(formInput.rangeConfig.stepInterval).to.equal(1);
        expect(formInput.rangeConfig.displayFormatter).to.be.a('function');
        expect(formInput.rangeConfig.displayFormatter()).to.equal('NaN');
        expect(formInput.rangeConfig.displayFormatter('')).to.equal('0');
        expect(formInput.rangeConfig.displayFormatter(0)).to.equal('0');
        expect(formInput.rangeConfig.displayFormatter(1)).to.equal('1');
        expect(formInput.rangeConfig.displayFormatter(100)).to.equal('100');
        expect(formInput.rangeConfig.displayFormatter(1000)).to.equal('1,000');
        expect(formInput.isTouched).to.equal(false);
        expect(formInput.isEdited).to.equal(false);
        expect(formInput.validation).to.equal(null);
        expect(formInput.showMax).to.equal(false);
        expect(formInput.enforceMax).to.equal(false);
        expect(formInput.errorMessage).to.equal('');
        expect(formInput.successMessage).to.equal('');
        expect(formInput.isValid).to.equal(false);
        expect(formInput.isSubmitInput).to.equal(false);
        expect(formInput.isFormRow).to.equal(false);
        expect(formInput.isDisabled).to.equal(false);
        expect(formInput.maxLength()).to.equal(-1);

        // Test methods
        formInput.blur();
        expect(formInput.isTouched).to.equal(true);
        expect(formInput.errorMessage).to.equal('');
        expect(formInput.isValid).to.equal(true);

        formInput.input();
        expect(formInput.isEdited).to.equal(true);
        expect(formInput.errorMessage).to.equal('');
        expect(formInput.isValid).to.equal(true);

        formInput.enforceLength();
        expect(formInput.value).to.equal('');

        formInput.validate();
        expect(formInput.errorMessage).to.equal('');
        expect(formInput.isValid).to.equal(true);
    });
    it('should create a FormInput with specific values', () => {
        const values = {
            id: 'test',
            name: 'test',
            label: 'test',
            shouldHideLabel: true,
            isLabelHTML: true,
            placeholder: 'test',
            value: 'test',
            valueOptions: [{ value: 'test', name: 'test' }],
            autocomplete: 'off',
            fileConfig: {
                accepts: ['application/pdf'],
                allowMultiple: true,
                maxSizeMbPer: 1,
                maxSizeMbAll: 1,
                hint: 'test',
            },
            rangeConfig: {
                min: 1,
                max: 10,
                stepInterval: 5,
                displayFormatter: (value: any) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value),
            },
            isTouched: true,
            isEdited: true,
            validation: Joi.string().min(1).max(1),
            showMax: true,
            enforceMax: true,
            errorMessage: 'test',
            successMessage: 'test',
            isValid: true,
            isSubmitInput: true,
            isFormRow: true,
            isDisabled: true,
        };
        const formInput = new FormInput(values);

        // Test field defaults
        expect(formInput).to.be.an.instanceof(FormInput);
        expect(formInput.id).to.equal(values.id);
        expect(formInput.name).to.equal(values.name);
        expect(formInput.label).to.equal(values.label);
        expect(formInput.shouldHideLabel).to.equal(values.shouldHideLabel);
        expect(formInput.isLabelHTML).to.equal(values.isLabelHTML);
        expect(formInput.placeholder).to.equal(values.placeholder);
        expect(formInput.value).to.equal(values.value);
        expect(formInput.valueOptions).to.be.an('array').with.length(1);
        expect(formInput.valueOptions).to.have.members(values.valueOptions);
        expect(formInput.autocomplete).to.equal(values.autocomplete);
        expect(formInput.fileConfig).to.be.an('object');
        expect(formInput.fileConfig.accepts).to.be.an('array').with.length(1);
        expect(formInput.fileConfig.accepts).to.have.members(values.fileConfig.accepts);
        expect(formInput.fileConfig.allowMultiple).to.equal(values.fileConfig.allowMultiple);
        expect(formInput.fileConfig.maxSizeMbPer).to.equal(values.fileConfig.maxSizeMbPer);
        expect(formInput.fileConfig.maxSizeMbAll).to.equal(values.fileConfig.maxSizeMbAll);
        expect(formInput.fileConfig.hint).to.equal(values.fileConfig.hint);
        expect(formInput.rangeConfig).to.be.an('object');
        expect(formInput.rangeConfig.min).to.equal(values.rangeConfig.min);
        expect(formInput.rangeConfig.max).to.equal(values.rangeConfig.max);
        expect(formInput.rangeConfig.stepInterval).to.equal(values.rangeConfig.stepInterval);
        expect(formInput.rangeConfig.displayFormatter).to.be.a('function');
        expect(formInput.rangeConfig.displayFormatter()).to.equal('$NaN');
        expect(formInput.rangeConfig.displayFormatter('')).to.equal('$0.00');
        expect(formInput.rangeConfig.displayFormatter(0)).to.equal('$0.00');
        expect(formInput.rangeConfig.displayFormatter(1)).to.equal('$1.00');
        expect(formInput.rangeConfig.displayFormatter(100)).to.equal('$100.00');
        expect(formInput.rangeConfig.displayFormatter(1000)).to.equal('$1,000.00');
        expect(formInput.isTouched).to.equal(values.isTouched);
        expect(formInput.isEdited).to.equal(values.isEdited);
        expect(Joi.isSchema(formInput.validation)).to.equal(true);
        expect(formInput.showMax).to.equal(values.showMax);
        expect(formInput.enforceMax).to.equal(values.enforceMax);
        expect(formInput.errorMessage).to.equal(values.errorMessage);
        expect(formInput.successMessage).to.equal(values.successMessage);
        expect(formInput.isValid).to.equal(values.isValid);
        expect(formInput.isSubmitInput).to.equal(values.isSubmitInput);
        expect(formInput.isFormRow).to.equal(values.isFormRow);
        expect(formInput.isDisabled).to.equal(true);
        expect(formInput.maxLength()).to.equal(1);

        // Test methods
        formInput.blur();
        expect(formInput.isTouched).to.equal(true);
        expect(formInput.errorMessage).to.equal(`"value" length must be less than or equal to 1 characters long`);
        expect(formInput.isValid).to.equal(false);

        formInput.enforceLength();
        expect(formInput.value).to.equal('t');

        formInput.input();
        expect(formInput.isEdited).to.equal(true);
        expect(formInput.errorMessage).to.equal('');
        expect(formInput.isValid).to.equal(true);

        formInput.validate();
        expect(formInput.errorMessage).to.equal('');
        expect(formInput.isValid).to.equal(true);
    });
});
