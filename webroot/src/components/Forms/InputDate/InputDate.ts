//
//  InputDate.ts
//  <the-app-name>
//
//  Created by InspiringApps on 6/7/2024.
//

import {
    Component,
    mixins,
    Prop,
    toNative,
    Watch
} from 'vue-facing-decorator';
import MixinInput from '@components/Forms/_mixins/input.mixin';
import VueDatePicker, { DatePickerMarker } from '@vuepic/vue-datepicker';
import '@vuepic/vue-datepicker/dist/main.css';
import {
    formatDateInput,
    dateInputToServerFormat,
    serverFormatToDateInput,
    isValidDateInput
} from '@models/_formatters/date';

@Component({
    name: 'InputDate',
    components: {
        VueDatePicker,
    },
})
class InputDate extends mixins(MixinInput) {
    //
    // Data
    //
    localValue = '';
    lastDatePickerValue = '';

    // https://vue3datepicker.com/props/modes/
    @Prop({ default: 'yyyy-MM-dd' }) modelFormat?: string; // https://date-fns.org/v2.16.1/docs/format
    @Prop({ default: null }) textInput?: { format?: string; openMenu?: boolean } | null;
    @Prop({ default: false }) isDisabled?: boolean;
    @Prop({ default: false }) isReadOnly?: boolean;
    @Prop({ default: false }) isInline?: boolean;
    @Prop({ default: 'off' }) isAutoComplete?: boolean;
    @Prop({ default: true }) isAutoApply?: boolean;
    @Prop({ default: true }) isClearable?: boolean;
    @Prop({ default: true }) isTodayHighlighted?: boolean;
    @Prop({ default: false }) multiCalendar?: boolean | number;
    @Prop({ default: false }) enableRangePicker?: boolean;
    @Prop({ default: [] }) markers?: Array<DatePickerMarker>;
    @Prop({ default: null }) minDate?: Date | string | null;
    @Prop({ default: null }) maxDate?: Date | string | null;
    @Prop({ default: true }) preventMinMaxNavigation?: boolean;
    @Prop({ default: null }) startDate?: string | null;
    @Prop({ default: null }) allowedDates?: Array<Date | string> | null;
    @Prop({ default: [] }) disabledDates?: Array<Date | string | ((date: Date) => boolean)>;
    @Prop({ default: [1900, 2100] }) yearRange?: [number, number];
    @Prop({ default: false }) enableTimePicker?: boolean;
    @Prop({ default: false }) enableSeconds?: boolean;
    @Prop({ default: null }) minTime?: null | {
        hours?: number | string;
        minutes?: number | string;
        seconds?: number | string;
    }
    @Prop({ default: null }) maxTime?: null | { // eslint-disable-line lines-between-class-members
        hours?: number | string;
        minutes?: number | string;
        seconds?: number | string;
    }
    @Prop({ default: false }) isTime24?: boolean; // eslint-disable-line lines-between-class-members
    @Prop({ default: false }) isLoading?: boolean;

    //
    // Lifecycle
    //
    created() {
        this.localValue = this.formInput.value || '';
        this.lastDatePickerValue = this.formInput.value || '';
    }

    //
    // Watchers
    //
    @Watch('formInput.value')
    onFormInputValueChange(newValue: string): void {
        // Only update if this is actually a new datepicker selection
        if (newValue !== this.lastDatePickerValue && newValue !== this.dateRaw) {
            if (!newValue) {
                this.localValue = '';
                this.lastDatePickerValue = '';
            } else {
                const newDateInput = serverFormatToDateInput(newValue);

                this.localValue = formatDateInput(newDateInput);
                this.lastDatePickerValue = newValue;
            }
        }
    }

    //
    // Computed
    //
    get dateDisplay(): string {
        return formatDateInput(this.localValue);
    }

    set dateDisplay(value: string) {
        // Store the raw value as-is to preserve cursor position
        const numericOnly = value.replace(/\D/g, '').substring(0, 8);

        this.localValue = numericOnly;

        // Only update form value if we have a complete date
        const serverFormat = this.dateRaw;

        if (serverFormat !== this.formInput.value) {
            this.formInput.value = serverFormat;
            this.formInput.validate();
        }
    }

    get dateRaw(): string {
        return dateInputToServerFormat(this.localValue.replace(/\D/g, ''));
    }

    get isDateValid(): boolean {
        return isValidDateInput(this.localValue.replace(/\D/g, ''));
    }

    //
    // Methods
    //
    onInput(): void {
        // Format the input as user types
        const numericOnly = this.localValue.replace(/\D/g, '');

        this.localValue = formatDateInput(numericOnly);

        // Update form value
        this.formInput.value = this.dateRaw;
        this.formInput.validate();
    }

    input(): void {
        const { formInput } = this;

        if (formInput?.value === null) {
            formInput.value = '';
            formInput.validate();
        }
    }

    focus(): void {
        (this.$refs.datepicker as any)?.openMenu();
    }

    blur(): void {
        try {
            (this.$refs.datepicker as any)?.selectDate();
        } catch {
            // Continue
        }

        this.formInput.isTouched = true;
        this.formInput.validate();
    }
}

export default toNative(InputDate);

// export default InputDate;
