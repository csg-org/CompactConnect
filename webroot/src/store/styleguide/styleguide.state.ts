//
//  styleguide.state.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//  Copyright © 2024. InspiringApps. All rights reserved.
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
