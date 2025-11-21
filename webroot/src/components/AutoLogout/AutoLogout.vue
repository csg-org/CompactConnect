<!--
    AutoLogout.vue
    CompactConnect

    Created by InspiringApps on 11/13/2025.
-->

<template>
    <Modal
        v-if="userStore.isAutoLogoutWarning && gracePeriodExtendEnabled"
        modalId="auto-logout-modal"
        class="auto-logout-modal"
        :title="$t('account.autoLogoutWarningTitle')"
        :showActions="false"
        @keydown.tab="focusTrapAutoLogoutModal($event)"
        @keyup.esc="staySignedIn"
    >
        <template v-slot:content>
            <div
                class="modal-content auto-logout-modal-content"
                aria-live="assertive"
                role="status"
            >
                <form class="auto-logout-form" @submit.prevent="staySignedIn">
                    <div class="description-container">{{ $t('account.autoLogoutWarningDescription') }}</div>
                    <div class="action-button-row">
                        <InputSubmit
                            :formInput="formData.stayLoggedIn"
                            class="action-button auto-logout-cancel-button"
                            :label="$t('account.autoLogoutStaySignedIn')"
                        />
                    </div>
                </form>
            </div>
        </template>
    </Modal>
</template>

<script lang="ts" src="./AutoLogout.ts"></script>
<style scoped lang="less" src="./AutoLogout.less"></style>
