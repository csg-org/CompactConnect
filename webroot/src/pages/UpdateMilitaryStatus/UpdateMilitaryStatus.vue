<!--
    UpdateMilitaryStatus.vue
    CompactConnect

    Created by InspiringApps on 12/20/2024.
-->

<template>
    <div class="update-military-status-container">
        <div class="update-military-status-content-container">
            <InputButton
                :label="$t('common.back')"
                :aria-label="$t('common.back')"
                :isTextLike="true"
                :shouldHideMargin="true"
                class="back-btn"
                @click="goBack"
            />
            <div class="update-military-status-title">
                {{ $t('military.militaryStatusTitle') }}
            </div>
            <div class="core-info-block">
                <div class="button-row">
                    <InputSubmit
                        class="understand-button"
                        :formInput="formData.submitEnd"
                        :label="yesEndText"
                        :aria-label="yesEndText"
                    />
                </div>
            </div>
        </div>
   </div>
</template>

<script lang="ts" src="./UpdateMilitaryStatus.ts"></script>
<style scoped lang="less" src="./UpdateMilitaryStatus.less"></style>
