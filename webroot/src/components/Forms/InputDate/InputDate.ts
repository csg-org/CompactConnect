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
    // https://vue3datepicker.com/props/modes/
    @Prop({ default: 'yyyy-MM-dd' }) modelFormat?: string; // https://date-fns.org/v2.16.1/docs/format
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
    // Methods
    //
    input(): void {
        const { formInput } = this;

        if (formInput?.value === null) {
            formInput.value = '';
            formInput.validate();
        }
    }
}

export default toNative(InputDate);

// export default InputDate;
