<!--
    MilitaryStatus.vue
    CompactConnect

    Created by InspiringApps on 12/20/2024.
-->

<template>
   <div class="military-status-container">
        <InputButton
            :label="$t('common.back')"
            :aria-label="$t('common.back')"
            :isTextLike="true"
            :shouldHideMargin="true"
            class="back-btn"
            @click="goBack"
        />
        <div class="military-status-title">
            {{ $t('military.militaryStatusTitle') }}
        </div>
        <div class="core-info-block">
            <div class="info-row">
                <div class="chunk">
                    <div class="chunk-title">{{statusTitleText}}</div>
                    <div class="chunk-text">{{status}}</div>
                </div>
                <div class="chunk">
                    <div class="chunk-title">{{affiliationTypeTitle}}</div>
                    <div class="chunk-text">{{affiliationType}}</div>
                </div>
            </div>
            <div class="chunk">
                <div class="chunk-title">{{previouslyUploadedTitle}}</div>
                <div class="prev-doc-table"></div>
            </div>
            <div class="button-row">
                <InputButton
                    :label="$t('military.endMilitaryAffiliation')"
                    :aria-label="$t('military.endMilitaryAffiliation')"
                    :isTextLike="true"
                    :shouldHideMargin="true"
                    class="end-aff-button"
                    @click="endAffiliation"
                />
                <InputButton
                    :label="$t('military.editInfo')"
                    :aria-label="$t('military.editInfo')"
                    :shouldHideMargin="true"
                    class="edit-info-button"
                    @click="editInfo"
                />
            </div>
        </div>
   </div>
</template>

<script lang="ts" src="./MilitaryStatus.ts"></script>
<style scoped lang="less" src="./MilitaryStatus.less"></style>
