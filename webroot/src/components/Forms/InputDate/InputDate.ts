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
import { FormInput } from '@/models/FormInput/FormInput.model';
import {
    formatDateInput,
    dateInputToServerFormat,
    serverFormatToDateInput
} from '@models/_formatters/date';

@Component({
    name: 'InputDate',
    components: {
        VueDatePicker,
    },
    emits: ['open', 'close'],
})
class InputDate extends mixins(MixinInput) {
    //
    // Data
    //
    localValue = '';
    lastDatePickerValue = '';
    previousLength = 0;

    // https://vue3datepicker.com
    // https://vue3datepicker.com/props/modes/
    @Prop({ default: 'yyyy-MM-dd' }) modelFormat?: string; // https://date-fns.org/v2.16.1/docs/format
    @Prop({ default: null }) textInput?: { format?: string; openMenu?: boolean } | null;
    @Prop({ default: false }) isDisabled?: boolean;
    @Prop({ default: false }) isReadOnly?: boolean;
    @Prop({ default: false }) isInline?: boolean;
    @Prop({ default: 'center' }) position?: string;
    @Prop({ default: false }) teleport?: boolean;
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
        this.previousLength = this.localValue.length;
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
            } else {
                const newDateInput = serverFormatToDateInput(newValue);

                this.localValue = formatDateInput(newDateInput);
            }

            // Only update lastDatePickerValue for genuine datepicker changes
            this.lastDatePickerValue = newValue;
        }
    }

    //
    // Computed
    //
    get dateRaw(): string {
        return dateInputToServerFormat(this.localValue);
    }

    //
    // Methods
    //
    onOpen(formInput: FormInput): void {
        this.$emit('open', formInput);
    }

    onInput(): void {
        const currentLength = this.localValue.length;
        const isDeleting = currentLength < this.previousLength;

        if (!isDeleting) {
            // Format the input as user types (only when adding characters)
            this.localValue = formatDateInput(this.localValue);
        }

        // Update form value with slight delay to prevent VueDatePicker conflicts
        this.$nextTick(() => {
            this.formInput.value = this.dateRaw;
            this.formInput.validate();
        });

        // Update previous length for next comparison
        this.previousLength = this.localValue.length;
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

    onClose(formInput: FormInput): void {
        this.$emit('close', formInput);
        this.blur();
    }

    onInputBlur(): void {
        const hasManualChanges = this.dateRaw && this.dateRaw !== this.lastDatePickerValue;

        if (hasManualChanges) {
            // Update lastDatePickerValue with manual input and skip VueDatePicker's selectDate
            this.lastDatePickerValue = this.dateRaw;
        } else {
            // No manual changes, let VueDatePicker handle its normal blur logic
            try {
                (this.$refs.datepicker as any)?.selectDate();
            } catch {
                // Continue
            }
        }

        this.formInput.isTouched = true;
        this.formInput.validate();
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
