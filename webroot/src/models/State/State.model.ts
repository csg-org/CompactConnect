//
//  State.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/2/2024.
//

import { deleteUndefinedProperties } from '@models/_helpers';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfaceStateCreate {
    id?: string | null;
    abbrev?: string | null;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class State implements InterfaceStateCreate {
    public $tm?: any = () => [];
    public $t?: any = () => '';
    public id? = null;
    public abbrev? = '';

    constructor(data?: InterfaceStateCreate) {
        const cleanDataObject = deleteUndefinedProperties(data);
        const global = window as any;
        const { $tm, $t } = global.Vue?.config?.globalProperties || {};

        if ($tm) {
            this.$tm = $tm;
            this.$t = $t;
        }

        Object.assign(this, cleanDataObject);
    }

    // Helper methods
    public name(): string {
        let stateName = '';
        const abbrev = this.abbrev || '';

        if (abbrev.toLowerCase() === 'other') {
            stateName = this.$t('common.stateNotListed');
        } else {
            const abbrevUpper = abbrev.toUpperCase() || '';
            const states = this.$tm('common.states') || [];
            const stateFound = states.find((state) => state.abbrev === abbrevUpper);

            stateName = stateFound?.full || this.$t('common.stateUnknown');
        }

        return stateName;
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class StateSerializer {
    static fromServer(json: any): State {
        const stateData = {
            id: json.id,
            abbrev: json.abbrev,
        };

        return new State(stateData);
    }

    static toServer(stateModel: State): any {
        return {
            id: stateModel.id,
            abbrev: stateModel.abbrev,
        };
    }
}
