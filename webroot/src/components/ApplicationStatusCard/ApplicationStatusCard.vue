<!--
    ApplicationStatusCard.vue
    CompactConnect

    Created by InspiringApps on 11/10/2026.
-->

<template>
    <div
        class="application-status-card-container"
        :class="{
            'needs-attention': isNeedsAttention,
            'rejected': isRejectedOrDeactivated,
        }"
    >
        <div class="application-heading-row">
            <h2 class="application-title">{{ title }}</h2>
            <div v-if="isFeeWaived" class="fee-waived-pill">
                <CheckCircleIcon class="fee-waived-icon" />
                {{ $t('application.feeWaived') }}
            </div>
        </div>
        <div v-if="summary" class="application-summary">{{ summary }}</div>
        <ol class="status-track">
            <li
                v-for="step in steps"
                :key="step.number"
                class="step-item"
                :class="{ 'is-current': step.isCurrent }"
            >
                <div class="step" :aria-current="(step.isCurrent) ? 'step' : null">
                    <div class="step-node" :class="step.state">
                        <CheckCircleIcon
                            v-if="step.state === stepStates.COMPLETE || step.state === stepStates.APPROVED"
                            class="step-icon check"
                        />
                        <AlertTriangleIcon v-else-if="step.state === stepStates.ATTENTION" class="step-icon alert" />
                        <CloseXIcon v-else-if="step.state === stepStates.REJECTED" class="step-icon closed" />
                        <span v-else aria-hidden="true">{{ step.number }}</span>
                    </div>
                    <div class="step-label">
                        <span class="visually-hidden">
                            {{ $t('application.stepOfTotal', { step: step.number, total: steps.length }) }}:
                        </span>
                        {{ step.label }}
                    </div>
                </div>
                <div v-if="step.number < steps.length" class="connector" aria-hidden="true"></div>
            </li>
        </ol>
        <div v-if="notes.length" class="application-notes">
            <div class="notes-title">{{ notesTitle }}</div>
            <p v-for="(note, index) in notes" :key="index" class="note">{{ note }}</p>
        </div>
        <InputButton
            v-if="isUpdateAvailable"
            :label="updateButtonLabel"
            :aria-label="updateButtonLabel"
            :shouldHideMargin="true"
            class="update-application-btn"
            @click="updateApplication"
        />
    </div>
</template>

<script lang="ts" src="./ApplicationStatusCard.ts"></script>
<style scoped lang="less" src="./ApplicationStatusCard.less"></style>
