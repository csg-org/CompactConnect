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
    toNative
} from 'vue-facing-decorator';
import MixinInput from '@components/Forms/_mixins/input.mixin';
import VueDatePicker, { DatePickerMarker } from '@vuepic/vue-datepicker';
import '@vuepic/vue-datepicker/dist/main.css';

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
    }

    //
    // Computed
    //
    get dateDisplay(): string {
        const currentDate = this.localValue;

        // Remove all non-numeric characters
        const numericOnly = currentDate.replace(/\D/g, '');

        // Apply MM/dd/yyyy formatting
        let formatted = numericOnly;

        if (numericOnly.length >= 2) {
            formatted = `${numericOnly.substring(0, 2)}/${numericOnly.substring(2)}`;
        }
        if (numericOnly.length >= 4) {
            formatted = `${numericOnly.substring(0, 2)}/${numericOnly.substring(2, 4)}/${numericOnly.substring(4, 8)}`;
        }

        return formatted;
    }

    set dateDisplay(value: string) {
        // Store the raw input, removing non-numeric characters but preserving partial input
        const numericOnly = value.replace(/\D/g, '');

        this.localValue = numericOnly.substring(0, 8);

        // Update form input value with the properly formatted date
        this.formInput.value = this.dateRaw;
        this.formInput.validate();
    }

    get dateRaw(): string {
        const { localValue } = this;
        let raw = '';

        // Convert MM/dd/yyyy to yyyy-MM-dd format for the form value
        const numericOnly = localValue.replace(/\D/g, '');

        if (numericOnly.length === 8) {
            const month = numericOnly.substring(0, 2);
            const day = numericOnly.substring(2, 4);
            const year = numericOnly.substring(4, 8);

            // Validate basic ranges
            const monthNum = parseInt(month, 10);
            const dayNum = parseInt(day, 10);
            const yearNum = parseInt(year, 10);

            if (monthNum >= 1 && monthNum <= 12 && dayNum >= 1 && dayNum <= 31 && yearNum >= 1900 && yearNum <= 2100) {
                raw = `${year}-${month}-${day}`;
            }
        }

        return raw;
    }

    get isDateValid(): boolean {
        const { dateRaw } = this;
        let isValid = false;

        // Try to create a valid date from the formatted input
        if (dateRaw) {
            const date = new Date(dateRaw);
            const isValidDate = date instanceof Date && !Number.isNaN(date.getTime());

            if (isValidDate) {
                // Additional validation: check if the date components match what was input
                const [year, month, day] = dateRaw.split('-').map((num) => parseInt(num, 10));

                isValid = date.getFullYear() === year
                    && date.getMonth() + 1 === month
                    && date.getDate() === day;
            }
        }

        return isValid;
    }

    //
    // Methods
    //
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
