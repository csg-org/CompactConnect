//
//  styleguide.state.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

export interface State {
    model: Array<any> | null;
    total: number;
    isLoading: boolean;
    error: any | null;
}

export const state: State = {
    model: null,
    total: 0,
    isLoading: false,
    error: null,
};
