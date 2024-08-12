//
//  State.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/2/2024.
//

import deleteUndefinedProperties from '@models/_helpers';

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
    public id? = null;
    public abbrev? = null;

    constructor(data?: InterfaceStateCreate) {
        const cleanDataObject = deleteUndefinedProperties(data);
        const global = window as any;
        const $tm = global.Vue?.config?.globalProperties?.$tm;

        if ($tm) {
            this.$tm = $tm;
        }

        Object.assign(this, cleanDataObject);
    }

    // Helper methods
    public name(): string {
        const abbrev = (this.abbrev || '').toUpperCase() || '';
        let states = this.$tm('common.states') || [];

        if (typeof states[0]?.abbrev === 'function') {
            const normalize = ([value]) => value;

            states = states.map((st) => ({
                abbrev: st.abbrev({ normalize }),
                full: st.full({ normalize }),
            }));
        }

        const state = states.find((st) => st.abbrev === abbrev);
        const stateName = state?.full || '';

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
