<!--
    ApplicationChecklist.vue
    CompactConnect

    Created by InspiringApps on 11/17/2026.
-->

<template>
    <div class="application-checklist-container">
        <div class="checklist-content">
            <div class="breadcrumbs">
                <router-link
                    class="breadcrumb-link"
                    :to="{ name: 'LicenseeDashboard', params: { compact: compactType } }"
                >
                    {{ $t('navigation.dashboard') }}
                </router-link>
                <span class="breadcrumb-current">/ {{ $t('application.checklistBreadcrumb') }}</span>
            </div>
            <h1 class="checklist-title">{{ $t('application.checklistTitle') }}</h1>
            <p class="checklist-intro">{{ $t('application.checklistIntro') }}</p>
            <div v-if="isLoadError" class="checklist-load-error" role="alert">
                <p class="load-error-message">{{ $t('application.checklistLoadError') }}</p>
                <router-link
                    class="text-link"
                    :to="{ name: 'LicenseeDashboard', params: { compact: compactType } }"
                >
                    {{ $t('auth.backToDashboard') }}
                </router-link>
            </div>
            <template v-else-if="application">
                <div class="checklist-progress">
                    <ProgressBar :progressPercent="progressPercent" class="checklist-progress-bar" />
                    <span class="progress-display">{{ progressDisplay }}</span>
                </div>
                <section class="checklist-card" aria-labelledby="checklist-section-header">
                    <div class="checklist-header">
                        <span id="checklist-section-header" class="header-section">
                            {{ $t('application.checklistSectionHeader') }}
                        </span>
                        <span class="header-status" aria-hidden="true">{{ $t('common.status') }}</span>
                    </div>
                    <ul class="section-list">
                        <li
                            v-for="section in sections"
                            :key="section.key"
                            class="section-row"
                            :class="section.key"
                        >
                            <div class="section-status">
                                <span class="status-pill" :class="section.statusClass">
                                    <span class="visually-hidden">{{ $t('common.status') }}:</span>
                                    {{ section.statusDisplay }}
                                </span>
                            </div>
                            <div class="section-info">
                                <component :is="section.icon" class="section-icon" />
                                <div class="section-text">
                                    <div class="section-name">{{ section.name }}</div>
                                    <div class="section-description">{{ section.description }}</div>
                                </div>
                            </div>
                            <div class="section-action">
                                <InputButton
                                    :label="section.buttonLabel"
                                    :isTransparent="!section.isIncomplete"
                                    :isEnabled="isEditable"
                                    :shouldHideMargin="true"
                                    class="section-button"
                                    @click="openSection(section)"
                                />
                            </div>
                        </li>
                    </ul>
                </section>
            </template>
        </div>
        <div v-if="application" class="checklist-footer">
            <div class="checklist-footer-content">
                <InputButton
                    :label="continueLabel"
                    :isEnabled="isContinueEnabled"
                    :shouldHideMargin="true"
                    class="continue-button"
                    @click="continueApplication"
                />
            </div>
        </div>
    </div>
</template>

<script lang="ts" src="./ApplicationChecklist.ts"></script>
<style scoped lang="less" src="./ApplicationChecklist.less"></style>
