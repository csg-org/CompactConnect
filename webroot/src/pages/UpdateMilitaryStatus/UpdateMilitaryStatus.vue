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
                {{ $t('military.updateMilitaryStatusTitle') }}
            </div>
            <div class="core-info-block">
                <div class="title-row">
                    {{attestationTitleText}}
                </div>
                <form @submit.prevent="handleSubmit">
                    <InputRadioGroup :formInput="formData.status" />
                    <div class="button-row">
                        <InputSubmit
                            class="understand-button"
                            :formInput="formData.submit"
                            :label="$t('common.submit')"
                            :aria-label="$t('common.submit')"
                        />
                    </div>
                </form>
            </div>
        </div>
   </div>
</template>

<script lang="ts" src="./UpdateMilitaryStatus.ts"></script>
<style scoped lang="less" src="./UpdateMilitaryStatus.less"></style>
