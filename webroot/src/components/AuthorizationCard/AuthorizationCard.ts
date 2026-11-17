//
//  AuthorizationCard.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/10/2026.
//

import {
    Component,
    Vue,
    Prop,
    toNative
} from 'vue-facing-decorator';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import { Authorization } from '@models/Authorization/Authorization.model';
import { ApplicationType } from '@models/Application/Application.model';

@Component({
    name: 'AuthorizationCard',
    components: {
        InputButton,
    },
})
class AuthorizationCard extends Vue {
    @Prop({ required: true }) authorizationType!: ApplicationType;
    @Prop({ default: null }) authorization!: Authorization | null;

    //
    // Computed
    //
    get authorizationTypeConfig(): { abbrev?: string, description?: string } {
        const authorizationTypes = this.$tm('application.applicationTypes') || [];

        return authorizationTypes.find((authorizationType) => authorizationType.key === this.authorizationType) || {};
    }

    get typeAbbrev(): string {
        return this.authorizationTypeConfig.abbrev || '';
    }

    get title(): string {
        return `${this.typeAbbrev} ${this.$t('application.authorization')}`;
    }

    get description(): string {
        return this.authorizationTypeConfig.description || '';
    }

    get isExpired(): boolean {
        return Boolean(this.authorization?.isExpired());
    }

    get isActive(): boolean {
        return Boolean(this.authorization?.isActive()) && !this.isExpired;
    }

    get statusDisplay(): string {
        return this.authorization?.statusDisplay() || '';
    }

    get expireDateDisplay(): string {
        return this.authorization?.expireDateDisplay() || '';
    }

    get isExpiredDateDisplayed(): boolean {
        return this.isExpired && Boolean(this.expireDateDisplay);
    }

    get applyAriaLabel(): string {
        return this.$t('application.applyForAuthorization', { type: this.typeAbbrev });
    }

    //
    // Methods
    //
    applyForAuthorization(): void {
        this.$router.push({
            name: 'ApplicationStart',
            params: { compact: this.$store.state.user.currentCompact?.type },
            query: { types: this.authorizationType },
        });
    }
}

export default toNative(AuthorizationCard);

// export default AuthorizationCard;
