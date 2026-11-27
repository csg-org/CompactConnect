<!--
    AuthorizationCard.vue
    CompactConnect

    Created by InspiringApps on 11/10/2026.
-->

<template>
    <div v-if="isActive" class="authorization-card-container active">
        <div class="authorization-heading-row">
            <div class="authorization-title">{{ title }}</div>
            <div class="authorization-status">{{ statusDisplay }}</div>
        </div>
        <div class="authorization-info-grid">
            <div class="info-item-container">
                <div class="info-item-title">{{ $t('licensing.expires') }}</div>
                <div class="info-item">{{ expireDateDisplay }}</div>
            </div>
        </div>
    </div>
    <div v-else class="authorization-card-container apply">
        <div class="apply-plus" aria-hidden="true">+</div>
        <div class="apply-title">{{ title }}</div>
        <div class="authorization-description">{{ description }}</div>
        <div v-if="isExpiredDateDisplayed" class="authorization-expired">
            {{ $t('licensing.expired') }} {{ expireDateDisplay }}
        </div>
        <InputButton
            :label="$t('application.apply')"
            :aria-label="applyAriaLabel"
            :shouldHideMargin="true"
            class="apply-btn"
            @click="applyForAuthorization"
        />
    </div>
</template>

<script lang="ts" src="./AuthorizationCard.ts"></script>
<style scoped lang="less" src="./AuthorizationCard.less"></style>
